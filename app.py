import os
import re
import json
import functools
import io
import random
import string
import time
import jwt
from flask import Flask, render_template, request, Response, g
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from PIL import Image, ImageDraw, ImageFont
from db import (init_db, save_resume, get_resume, get_user_resumes, save_message,
                get_conversation_history, create_user, authenticate_user,
                get_user_by_id, reset_password, get_db, update_user_role,
                create_hr_job, get_hr_jobs, get_hr_job,
                add_hr_screening, update_hr_screening, get_hr_screenings,
                update_screening_sms,
                v2_create_job, v2_get_jobs, v2_get_job, v2_update_job,
                v2_create_application, v2_get_applications_for_job,
                v2_get_applications_for_user, v2_update_application,
                v2_get_application, v2_check_applied, soft_delete_resume, soft_delete_all_user_resumes_except,
                v2_save_application_analysis, v2_get_application_analysis,
                v2_get_application_analysis_by_resume_job)
from deepseek_client import (analyze_resume, chat_interview, start_interview,
                             get_magi_verdict, batch_screen_resume,
                             generate_interview_sms, generate_rejection_sms,
                             ai_generate_job_description)
from config import (MAX_UPLOAD_SIZE, DEEPSEEK_API_KEY, JWT_SECRET_KEY,
                    ALLOWED_MIME_TYPES, RATE_LIMIT_DEFAULT, RATE_LIMIT_UPLOAD,
                    RATE_LIMIT_CHAT, BACKUP_FILES_DIR, BACKUP_PAYLOADS_DIR)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = MAX_UPLOAD_SIZE
app.config['JSON_AS_ASCII'] = False
app.secret_key = JWT_SECRET_KEY

os.makedirs(BACKUP_FILES_DIR, exist_ok=True)
os.makedirs(BACKUP_PAYLOADS_DIR, exist_ok=True)


def _backup_uploaded_file(file_obj, user_id, resume_id):
    try:
        ext = os.path.splitext(file_obj.filename or "unknown")[1] or ".bin"
        ts = time.strftime("%Y%m%d_%H%M%S")
        fname = f"uid{user_id}_rid{resume_id}_{ts}{ext}"
        path = os.path.join(BACKUP_FILES_DIR, fname)
        file_obj.seek(0)
        with open(path, 'wb') as f:
            f.write(file_obj.read())
        file_obj.seek(0)
    except Exception as e:
        print(f"[WARN] backup file failed: {e}")


def _backup_payload(user_id, resume_id, action, payload_data):
    try:
        ts = time.strftime("%Y%m%d_%H%M%S")
        fname = f"uid{user_id}_rid{resume_id}_{action}_{ts}.json"
        path = os.path.join(BACKUP_PAYLOADS_DIR, fname)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(payload_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[WARN] backup payload failed: {e}")

CAPTCHA_EXPIRE = 300
_captcha_store = {}


def _cleanup_captcha_store():
    now = time.time()
    expired = [k for k, v in _captcha_store.items() if now - v['ts'] > CAPTCHA_EXPIRE]
    for k in expired:
        del _captcha_store[k]


def _generate_captcha_image(code):
    w, h = 120, 40
    img = Image.new('RGB', (w, h), (11, 11, 20))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 26)
    except Exception:
        font = ImageFont.load_default()
    for i, ch in enumerate(code):
        x = 12 + i * 24
        y = random.randint(2, 8)
        r, g, b = random.randint(180, 255), random.randint(50, 150), random.randint(50, 150)
        draw.text((x, y), ch, fill=(r, g, b), font=font)
    for _ in range(5):
        x1, y1 = random.randint(0, w), random.randint(0, h)
        x2, y2 = random.randint(0, w), random.randint(0, h)
        draw.line((x1, y1, x2, y2), fill=(random.randint(40, 100), random.randint(40, 100), random.randint(40, 100)), width=1)
    for _ in range(40):
        x, y = random.randint(0, w), random.randint(0, h)
        draw.point((x, y), fill=(random.randint(60, 180), random.randint(60, 180), random.randint(60, 180)))
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf


@app.route("/api/captcha", methods=["GET"])
def get_captcha():
    _cleanup_captcha_store()
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    captcha_id = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
    _captcha_store[captcha_id] = {'code': code, 'ts': time.time()}
    buf = _generate_captcha_image(code)
    return Response(buf.getvalue(), mimetype='image/png', headers={'X-Captcha-Id': captcha_id})

limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=[RATE_LIMIT_DEFAULT],
    storage_uri="memory://"
)


def utf8_json(data, status=200):
    body = json.dumps(data, ensure_ascii=False).encode('utf-8')
    return Response(body, content_type="application/json; charset=utf-8", status=status)


PROMPT_INJECTION_PATTERNS = [
    r'ignore\s+(all\s+)?previous\s+instructions',
    r'forget\s+(all\s+)?previous',
    r'you\s+are\s+now',
    r'system\s*:',
    r'assistant\s*:',
    r'pretend\s+you\s+are',
    r'jailbreak',
    r'prompt\s+injection',
]


def sanitize_prompt_input(text):
    for pattern in PROMPT_INJECTION_PATTERNS:
        text = re.sub(pattern, '[FILTERED]', text, flags=re.IGNORECASE)
    return text


def sanitize_error(e):
    msg = str(e)
    sensitive_keywords = ['api_key', 'API_KEY', 'secret', 'password', 'token',
                          'Authorization', 'Bearer', 'sk-', 'Traceback',
                          'File "', 'Exception', 'Error:']
    for kw in sensitive_keywords:
        if kw in msg:
            return "服务内部错误，请稍后重试"
    return msg


def require_auth(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '')
        if token.startswith('Bearer '):
            token = token[7:]
        if not token:
            return utf8_json({"error": "未登录，请先登录"}, 401)
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
            user = get_user_by_id(payload.get('user_id'))
            if not user:
                return utf8_json({"error": "用户不存在"}, 401)
            g.user = user
        except jwt.ExpiredSignatureError:
            return utf8_json({"error": "登录已过期，请重新登录"}, 401)
        except jwt.InvalidTokenError:
            return utf8_json({"error": "无效的认证信息"}, 401)
        return f(*args, **kwargs)
    return decorated


def extract_text_from_file(file_storage):
    filename = file_storage.filename
    ext = os.path.splitext(filename)[1].lower()

    if ext == '.txt':
        raw = file_storage.read()
        for encoding in ['utf-8-sig', 'utf-8', 'gbk', 'gb2312', 'gb18030']:
            try:
                return raw.decode(encoding)
            except (UnicodeDecodeError, LookupError):
                continue
        return raw.decode('utf-8', errors='replace')

    elif ext == '.pdf':
        try:
            import PyPDF2
            file_storage.seek(0)
            reader = PyPDF2.PdfReader(file_storage)
            text = ""
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            return text.strip()
        except ImportError:
            raise ValueError("PDF解析需要安装 PyPDF2")

    elif ext == '.docx':
        try:
            import docx
            file_storage.seek(0)
            doc = docx.Document(file_storage)
            text = "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
            return text.strip()
        except ImportError:
            raise ValueError("DOCX解析需要安装 python-docx")

    else:
        raise ValueError(f"不支持的文件格式：{ext}")


# ========== PAGES ==========

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/v1")
def v1_app():
    return render_template("index.html")


@app.route("/firewall")
def firewall():
    return render_template("firewall.html")


@app.route("/hr")
def hr_page():
    return render_template("hr.html")


@app.route("/v2/hr")
def v2_hr_page():
    return render_template("v2_hr.html")


@app.route("/v2/seeker")
def v2_seeker_page():
    return render_template("v2_seeker.html")


# ========== AUTH API ==========

@app.route("/api/register", methods=["POST"])
@limiter.limit("5/minute")
def register():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()
    role = (data.get("role") or "seeker").strip()

    if role not in ("hr", "seeker"):
        role = "seeker"

    if not username or not password:
        return utf8_json({"error": "用户名和密码不能为空"}, 400)
    if len(username) < 3 or len(username) > 20:
        return utf8_json({"error": "用户名长度需在3-20个字符之间"}, 400)
    if len(password) < 6:
        return utf8_json({"error": "密码长度不能少于6位"}, 400)
    if not re.match(r'^[a-zA-Z0-9_\u4e00-\u9fff]+$', username):
        return utf8_json({"error": "用户名只能包含字母、数字、下划线和中文"}, 400)

    user_id, recovery_key = create_user(username, password, role=role)
    if user_id is None:
        return utf8_json({"error": "用户名已存在"}, 409)

    token = jwt.encode(
        {"user_id": user_id, "username": username},
        JWT_SECRET_KEY,
        algorithm="HS256"
    )
    return utf8_json({"token": token, "username": username, "recovery_key": recovery_key, "role": role})


@app.route("/api/login", methods=["POST"])
@limiter.limit("10/minute")
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()
    captcha_id = (data.get("captcha_id") or "").strip()
    captcha_code = (data.get("captcha_code") or "").strip()

    if not captcha_id or not captcha_code:
        return utf8_json({"error": "请输入验证码"}, 400)

    captcha_data = _captcha_store.pop(captcha_id, None)
    if not captcha_data:
        return utf8_json({"error": "验证码已过期，请刷新"}, 400)
    if time.time() - captcha_data['ts'] > CAPTCHA_EXPIRE:
        return utf8_json({"error": "验证码已过期，请刷新"}, 400)
    if captcha_data['code'].upper() != captcha_code.upper():
        return utf8_json({"error": "验证码错误"}, 400)

    if not username or not password:
        return utf8_json({"error": "用户名和密码不能为空"}, 400)

    user = authenticate_user(username, password)
    if not user:
        return utf8_json({"error": "用户名或密码错误"}, 401)

    token = jwt.encode(
        {"user_id": user["id"], "username": user["username"]},
        JWT_SECRET_KEY,
        algorithm="HS256"
    )
    return utf8_json({"token": token, "username": user["username"], "role": user.get("role", "seeker")})


@app.route("/api/forgot-password", methods=["POST"])
@limiter.limit("5/minute")
def forgot_password():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    recovery_key = (data.get("recovery_key") or "").strip()
    new_password = (data.get("new_password") or "").strip()

    if not username or not recovery_key or not new_password:
        return utf8_json({"error": "所有字段不能为空"}, 400)
    if len(new_password) < 6:
        return utf8_json({"error": "新密码长度不能少于6位"}, 400)

    success = reset_password(username, recovery_key, new_password)
    if not success:
        return utf8_json({"error": "用户名或找回密码验证码错误"}, 401)

    return utf8_json({"message": "密码重置成功，请使用新密码登录"})


@app.route("/api/me", methods=["GET"])
@require_auth
def api_me():
    return utf8_json({"id": g.user["id"], "username": g.user["username"], "role": g.user.get("role", "seeker")})


@app.route("/api/me/role", methods=["POST"])
@require_auth
def api_update_role():
    data = request.get_json(silent=True) or {}
    role = (data.get("role") or "").strip()
    if role not in ("hr", "seeker"):
        return utf8_json({"error": "无效角色"}, 400)
    update_user_role(g.user["id"], role)
    return utf8_json({"role": role})


# ========== V1 API ==========

@app.route("/api/upload", methods=["POST"])
@require_auth
@limiter.limit(RATE_LIMIT_UPLOAD)
def upload():
    if "file" not in request.files:
        return utf8_json({"error": "未找到上传文件"}, 400)

    file = request.files["file"]
    if file.filename == "":
        return utf8_json({"error": "未选择文件"}, 400)

    mime_type = file.content_type or ""
    if mime_type and mime_type not in ALLOWED_MIME_TYPES:
        return utf8_json({"error": f"不支持的文件类型：{mime_type}"}, 400)

    try:
        text = extract_text_from_file(file)
        if not text or len(text.strip()) < 20:
            return utf8_json({"error": "简历内容过少，请上传包含有效内容的简历"}, 400)

        safe_text = sanitize_prompt_input(text)
        position = request.form.get("position", "").strip()
        salary = request.form.get("salary", "").strip()
        city = request.form.get("city", "").strip()

        analysis = analyze_resume(safe_text, position=position, salary=salary, city=city)
        resume_id = save_resume(g.user["id"], file.filename, text, analysis, position=position, salary=salary, city=city)

        _backup_uploaded_file(file, g.user["id"], resume_id)
        _backup_payload(g.user["id"], resume_id, "analyze", {
            "action": "analyze_resume",
            "filename": file.filename,
            "position": position, "salary": salary, "city": city,
            "text_length": len(safe_text),
            "text_preview": safe_text[:500]
        })

        save_message(resume_id, "system", f"已上传简历：{file.filename}")

        return utf8_json({"resume_id": resume_id, "analysis": analysis})

    except ValueError as e:
        return utf8_json({"error": str(e)}, 400)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return utf8_json({"error": sanitize_error(e)}, 500)


@app.route("/api/start-interview", methods=["POST"])
@require_auth
@limiter.limit(RATE_LIMIT_CHAT)
def api_start_interview():
    data = request.get_json(silent=True) or {}
    resume_id = data.get("resume_id")
    style = data.get("style", "normal")

    if not resume_id:
        return utf8_json({"error": "缺少 resume_id"}, 400)

    resume = get_resume(resume_id, user_id=g.user["id"])
    if not resume:
        return utf8_json({"error": "简历不存在"}, 404)

    try:
        safe_content = sanitize_prompt_input(resume["content"])
        position = resume.get("position", "")
        salary = resume.get("salary", "")
        city = resume.get("city", "")
        stream = start_interview(safe_content, style=style, position=position, salary=salary, city=city)

        _backup_payload(g.user["id"], resume_id, "start_interview", {
            "action": "start_interview",
            "style": style,
            "position": position, "salary": salary, "city": city,
            "text_length": len(safe_content),
            "text_preview": safe_content[:500]
        })

        def generate():
            full_text = ""
            for chunk in stream:
                if chunk.startswith("data: [DONE]"):
                    save_message(resume_id, "assistant", full_text)
                    yield ("data: [DONE]\n\n").encode('utf-8')
                    break
                yield chunk.encode('utf-8') if isinstance(chunk, str) else chunk
                try:
                    line = chunk.strip()
                    if line.startswith("data: "):
                        payload = json.loads(line[6:])
                        full_text += payload.get("content", "")
                except (json.JSONDecodeError, KeyError):
                    pass

        return Response(generate(), content_type="text/event-stream; charset=utf-8")

    except Exception as e:
        return utf8_json({"error": sanitize_error(e)}, 500)


@app.route("/api/chat", methods=["POST"])
@require_auth
@limiter.limit(RATE_LIMIT_CHAT)
def api_chat():
    data = request.get_json(silent=True) or {}
    resume_id = data.get("resume_id")
    message = (data.get("message") or "").strip()
    style = data.get("style", "normal")

    if not resume_id:
        return utf8_json({"error": "缺少 resume_id"}, 400)
    if not message:
        return utf8_json({"error": "消息不能为空"}, 400)
    if len(message) > 2000:
        return utf8_json({"error": "消息长度不能超过2000字"}, 400)

    resume = get_resume(resume_id, user_id=g.user["id"])
    if not resume:
        return utf8_json({"error": "简历不存在"}, 404)

    safe_message = sanitize_prompt_input(message)
    save_message(resume_id, "user", safe_message)

    history = get_conversation_history(resume_id, limit=20)

    try:
        safe_content = sanitize_prompt_input(resume["content"])
        stream = chat_interview(safe_content, history, safe_message, style=style, position=resume.get("position",""), salary=resume.get("salary",""), city=resume.get("city",""))

        _backup_payload(g.user["id"], resume_id, "chat", {
            "action": "chat_interview",
            "style": style,
            "user_message": safe_message,
            "history_length": len(history),
            "position": resume.get("position",""), "salary": resume.get("salary",""), "city": resume.get("city","")
        })

        def generate():
            full_text = ""
            for chunk in stream:
                if chunk.startswith("data: [DONE]"):
                    save_message(resume_id, "assistant", full_text)
                    yield ("data: [DONE]\n\n").encode('utf-8')
                    break
                yield chunk.encode('utf-8') if isinstance(chunk, str) else chunk
                try:
                    line = chunk.strip()
                    if line.startswith("data: "):
                        payload = json.loads(line[6:])
                        full_text += payload.get("content", "")
                except (json.JSONDecodeError, KeyError):
                    pass

        return Response(generate(), content_type="text/event-stream; charset=utf-8")

    except Exception as e:
        return utf8_json({"error": sanitize_error(e)}, 500)


@app.route("/api/verdict", methods=["POST"])
@require_auth
@limiter.limit(RATE_LIMIT_CHAT)
def api_verdict():
    data = request.get_json(silent=True) or {}
    resume_id = data.get("resume_id")

    if not resume_id:
        return utf8_json({"error": "缺少 resume_id"}, 400)

    resume = get_resume(resume_id, user_id=g.user["id"])
    if not resume:
        return utf8_json({"error": "简历不存在"}, 404)

    try:
        safe_content = sanitize_prompt_input(resume["content"])
        history = get_conversation_history(resume_id, limit=50)
        position = resume.get("position", "")
        salary = resume.get("salary", "")
        city = resume.get("city", "")

        verdict = get_magi_verdict(safe_content, history, position=position, salary=salary, city=city)

        _backup_payload(g.user["id"], resume_id, "verdict", {
            "action": "magi_verdict",
            "position": position, "salary": salary, "city": city,
            "history_length": len(history),
            "text_length": len(safe_content)
        })

        return utf8_json({"verdict": verdict})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return utf8_json({"error": sanitize_error(e)}, 500)


@app.route("/api/status")
def status():
    return utf8_json({
        "ready": bool(DEEPSEEK_API_KEY),
        "model": "deepseek-chat"
    })


# ========== V1 HR API ==========

@app.route("/api/hr/jobs", methods=["GET"])
@require_auth
def api_hr_jobs():
    jobs = get_hr_jobs(g.user["id"])
    return utf8_json(jobs)


@app.route("/api/hr/jobs", methods=["POST"])
@require_auth
@limiter.limit("5/minute")
def api_hr_create_job():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    requirements = (data.get("requirements") or "").strip()
    salary_range = (data.get("salary_range") or "").strip()
    city = (data.get("city") or "").strip()

    if not title or not requirements:
        return utf8_json({"error": "岗位名称和要求不能为空"}, 400)

    job_id = create_hr_job(g.user["id"], title, requirements, salary_range, city)
    return utf8_json({"job_id": job_id})


@app.route("/api/hr/jobs/<int:job_id>/upload", methods=["POST"])
@require_auth
@limiter.limit("3/minute")
def api_hr_upload_resumes(job_id):
    job = get_hr_job(job_id, g.user["id"])
    if not job:
        return utf8_json({"error": "岗位不存在"}, 404)

    files = request.files.getlist("files")
    if not files:
        return utf8_json({"error": "请选择文件"}, 400)

    results = []
    for file in files[:20]:
        if file.content_type not in ALLOWED_MIME_TYPES:
            results.append({"filename": file.filename, "error": "不支持的文件格式"})
            continue

        file.seek(0, 2)
        size = file.tell()
        file.seek(0)
        if size > MAX_UPLOAD_SIZE:
            results.append({"filename": file.filename, "error": "文件过大"})
            continue

        try:
            text = extract_text_from_file(file)
            if not text or len(text.strip()) < 20:
                results.append({"filename": file.filename, "error": "文件内容过少"})
                continue

            safe_text = text[:8000]
            screening_id = add_hr_screening(job_id, g.user["id"], file.filename, safe_text)

            _backup_uploaded_file(file, g.user["id"], screening_id)

            analysis = batch_screen_resume(
                safe_text, job["title"], job["requirements"],
                job.get("salary_range", ""), job.get("city", "")
            )

            match_score = analysis.get("match_score", 0)
            skill_match = analysis.get("skill_match", "")
            candidate_name = analysis.get("name", "")
            phone = analysis.get("phone", "")
            email = analysis.get("email", "")
            recommendation = analysis.get("recommendation", "neutral")

            status_map = {"recommend": "recommended", "neutral": "neutral", "reject": "rejected"}
            scr_status = status_map.get(recommendation, "neutral")

            update_hr_screening(screening_id, match_score, skill_match, analysis, scr_status)

            if candidate_name or phone:
                conn = get_db()
                conn.execute(
                    "UPDATE hr_screenings SET candidate_name=?, phone=?, email=? WHERE id=?",
                    (candidate_name, phone, email, screening_id)
                )
                conn.commit()
                conn.close()

            _backup_payload(g.user["id"], screening_id, "batch_screen", {
                "action": "batch_screen_resume",
                "job_id": job_id, "job_title": job["title"],
                "filename": file.filename,
                "match_score": match_score
            })

            results.append({
                "screening_id": screening_id,
                "filename": file.filename,
                "name": candidate_name,
                "phone": phone,
                "email": email,
                "match_score": match_score,
                "skill_match": skill_match,
                "matched_skills": analysis.get("matched_skills", []),
                "missing_skills": analysis.get("missing_skills", []),
                "summary": analysis.get("summary", ""),
                "recommendation": recommendation,
                "status": scr_status
            })
        except Exception as e:
            results.append({"filename": file.filename, "error": str(e)})

    return utf8_json({"results": results})


@app.route("/api/hr/jobs/<int:job_id>/screenings", methods=["GET"])
@require_auth
def api_hr_screenings(job_id):
    job = get_hr_job(job_id, g.user["id"])
    if not job:
        return utf8_json({"error": "岗位不存在"}, 404)
    screenings = get_hr_screenings(job_id, g.user["id"])
    return utf8_json({"job": job, "screenings": screenings})


@app.route("/api/hr/screenings/<int:screening_id>/sms", methods=["POST"])
@require_auth
def api_hr_send_sms(screening_id):
    data = request.get_json(silent=True) or {}
    custom_sms = (data.get("sms_content") or "").strip()

    conn = get_db()
    row = conn.execute(
        "SELECT s.*, j.title as job_title FROM hr_screenings s JOIN hr_jobs j ON s.job_id = j.id WHERE s.id = ? AND s.user_id = ?",
        (screening_id, g.user["id"])
    ).fetchone()
    conn.close()

    if not row:
        return utf8_json({"error": "记录不存在"}, 404)

    candidate_name = row["candidate_name"] or "候选人"
    job_title = row["job_title"] or ""

    if not custom_sms:
        try:
            custom_sms = generate_interview_sms(candidate_name, job_title)
        except Exception:
            custom_sms = f"{candidate_name}您好，您应聘的{job_title}职位已通过初筛，请留意后续面试通知。"

    update_screening_sms(screening_id, custom_sms)

    return utf8_json({"sms_content": custom_sms, "phone": row["phone"], "sent": True})


# ========== V2 API ==========

@app.route("/api/v2/jobs", methods=["GET"])
@require_auth
def api_v2_jobs():
    status_filter = request.args.get("status", "").strip()
    jobs = v2_get_jobs(user_id=g.user["id"], status=status_filter or None)
    return utf8_json(jobs)


@app.route("/api/v2/jobs/open", methods=["GET"])
def api_v2_jobs_open():
    jobs = v2_get_jobs(status="open")
    return utf8_json(jobs)


@app.route("/api/v2/jobs/<int:job_id>", methods=["GET"])
@require_auth
def api_v2_job_detail(job_id):
    job = v2_get_job(job_id)
    if not job:
        return utf8_json({"error": "岗位不存在"}, 404)
    return utf8_json(job)


@app.route("/api/v2/jobs", methods=["POST"])
@require_auth
@limiter.limit("5/minute")
def api_v2_create_job():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    description = (data.get("description") or "").strip()
    requirements = (data.get("requirements") or "").strip()
    salary_range = (data.get("salary_range") or "").strip()
    city = (data.get("city") or "").strip()
    virtual_interview = data.get("virtual_interview", False)

    if not title or not requirements:
        return utf8_json({"error": "岗位名称和要求不能为空"}, 400)

    job_id = v2_create_job(
        g.user["id"], title, description, requirements,
        salary_range, city, ai_generated=bool(description), virtual_interview=bool(virtual_interview)
    )
    return utf8_json({"job_id": job_id})


@app.route("/api/v2/jobs/<int:job_id>", methods=["PUT"])
@require_auth
@limiter.limit("10/minute")
def api_v2_update_job(job_id):
    data = request.get_json(silent=True) or {}
    job = v2_get_job(job_id, g.user["id"])
    if not job:
        return utf8_json({"error": "岗位不存在"}, 404)

    allowed = {}
    for k in ('title', 'description', 'requirements', 'salary_range', 'city', 'virtual_interview', 'status'):
        if k in data:
            allowed[k] = data[k]

    v2_update_job(job_id, g.user["id"], **allowed)
    return utf8_json({"ok": True})


@app.route("/api/v2/ai/job-desc", methods=["POST"])
@require_auth
@limiter.limit("3/minute")
def api_v2_ai_job_desc():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    requirements = (data.get("requirements") or "").strip()
    salary_range = (data.get("salary_range") or "").strip()
    city = (data.get("city") or "").strip()

    if not title:
        return utf8_json({"error": "请输入岗位名称"}, 400)

    try:
        desc = ai_generate_job_description(title, requirements, salary_range, city)
        return utf8_json({"description": desc})
    except Exception as e:
        return utf8_json({"error": sanitize_error(e)}, 500)


@app.route("/api/v2/jobs/<int:job_id>/applications", methods=["GET"])
@require_auth
def api_v2_applications(job_id):
    job = v2_get_job(job_id, g.user["id"])
    if not job:
        return utf8_json({"error": "岗位不存在"}, 404)
    apps = v2_get_applications_for_job(job_id)
    return utf8_json({"job": job, "applications": apps})


@app.route("/api/v2/hr/resume/<int:resume_id>", methods=["GET"])
@require_auth
def api_v2_hr_view_resume(resume_id):
    resume = get_resume(resume_id)
    if not resume:
        return utf8_json({"error": "简历不存在"}, 404)
    app_id = request.args.get("application_id", type=int)
    job_id = None
    chat_history = []
    app_analysis = None
    if app_id:
        app_row = v2_get_application(app_id)
        if not app_row:
            return utf8_json({"error": "申请不存在"}, 404)
        job = v2_get_job(app_row["job_id"])
        if not job or job["user_id"] != g.user["id"]:
            return utf8_json({"error": "无权限查看该简历"}, 403)
        job_id = app_row["job_id"]
        if job.get("virtual_interview"):
            conn = get_db()
            rows = conn.execute(
                "SELECT role, content FROM conversations WHERE resume_id = ? AND created_at >= ? ORDER BY created_at ASC",
                (resume_id, app_row["created_at"])
            ).fetchall()
            conn.close()
            chat_history = [{"role": row["role"], "content": row["content"]} for row in rows]
        app_analysis = v2_get_application_analysis(app_id)
    else:
        if resume["user_id"] != g.user["id"]:
            return utf8_json({"error": "无权限查看该简历"}, 403)
    return utf8_json({
        "content": resume.get("content", ""),
        "analysis": app_analysis or resume.get("analysis"),
        "chat_history": chat_history
    })


@app.route("/api/v2/applications/<int:app_id>/sms", methods=["POST"])
@require_auth
def api_v2_send_interview_sms(app_id):
    conn = get_db()
    row = conn.execute(
        "SELECT a.*, j.title as job_title, j.user_id as hr_user_id, r.filename, r.analysis FROM v2_applications a JOIN v2_jobs j ON a.job_id = j.id JOIN resumes r ON a.resume_id = r.id WHERE a.id = ?",
        (app_id,)
    ).fetchone()
    conn.close()
    if not row or row["hr_user_id"] != g.user["id"]:
        return utf8_json({"error": "记录不存在"}, 404)
    candidate_name = "候选人"
    if row["analysis"]:
        try:
            a = json.loads(row["analysis"]) if isinstance(row["analysis"], str) else row["analysis"]
            candidate_name = a.get("name", "候选人")
        except Exception:
            pass
    job_title = row["job_title"] or ""
    data = request.get_json(silent=True) or {}
    custom_sms = (data.get("sms_content") or "").strip()
    if not custom_sms:
        try:
            custom_sms = generate_interview_sms(candidate_name, job_title)
        except Exception:
            custom_sms = f"{candidate_name}您好，您应聘的{job_title}职位已通过初筛，请留意后续面试通知。"
    return utf8_json({"sms_content": custom_sms, "candidate": candidate_name, "sent": True})


@app.route("/api/v2/applications/<int:app_id>/reject-sms", methods=["POST"])
@require_auth
def api_v2_send_rejection_sms(app_id):
    conn = get_db()
    row = conn.execute(
        "SELECT a.*, j.title as job_title, j.user_id as hr_user_id, r.filename, r.analysis FROM v2_applications a JOIN v2_jobs j ON a.job_id = j.id JOIN resumes r ON a.resume_id = r.id WHERE a.id = ?",
        (app_id,)
    ).fetchone()
    conn.close()
    if not row or row["hr_user_id"] != g.user["id"]:
        return utf8_json({"error": "记录不存在"}, 404)
    candidate_name = "候选人"
    if row["analysis"]:
        try:
            a = json.loads(row["analysis"]) if isinstance(row["analysis"], str) else row["analysis"]
            candidate_name = a.get("name", "候选人")
        except Exception:
            pass
    job_title = row["job_title"] or ""
    data = request.get_json(silent=True) or {}
    custom_sms = (data.get("sms_content") or "").strip()
    reason = (data.get("reason") or "").strip()
    if not custom_sms:
        try:
            custom_sms = generate_rejection_sms(candidate_name, job_title, reason=reason)
        except Exception:
            custom_sms = f"{candidate_name}您好，感谢您对{job_title}岗位的关注，经过综合评估，很遗憾未能与您达成合作，祝您求职顺利。"
    return utf8_json({"sms_content": custom_sms, "candidate": candidate_name, "sent": True})

@app.route("/api/v2/applications/<int:app_id>/screen", methods=["POST"])
@require_auth
@limiter.limit("5/minute")
def api_v2_screen_application(app_id):
    app_data = v2_get_application(app_id)
    if not app_data:
        return utf8_json({"error": "申请不存在"}, 404)

    job = v2_get_job(app_data["job_id"])
    if not job or job["user_id"] != g.user["id"]:
        return utf8_json({"error": "无权限"}, 403)

    resume = get_resume(app_data["resume_id"])
    if not resume:
        return utf8_json({"error": "简历不存在"}, 404)

    try:
        safe_text = sanitize_prompt_input(resume["content"])[:8000]
        analysis = batch_screen_resume(
            safe_text, job["title"], job["requirements"],
            job.get("salary_range", ""), job.get("city", "")
        )

        score = analysis.get("match_score", 0)
        rec = analysis.get("recommendation", "neutral")
        new_status = "screened"
        if rec == "recommend":
            new_status = "screened_pass"
        elif rec == "reject":
            new_status = "screened_reject"

        v2_update_application(app_id, status=new_status, screening_score=score,
                              screening_result=json.dumps(analysis, ensure_ascii=False))
        v2_save_application_analysis(app_id, app_data["resume_id"], app_data["job_id"], analysis)

        return utf8_json({"analysis": analysis, "status": new_status, "score": score})
    except Exception as e:
        return utf8_json({"error": sanitize_error(e)}, 500)


@app.route("/api/v2/applications/<int:app_id>", methods=["PUT"])
@require_auth
@limiter.limit("10/minute")
def api_v2_update_application(app_id):
    app_data = v2_get_application(app_id)
    if not app_data:
        return utf8_json({"error": "申请不存在"}, 404)

    job = v2_get_job(app_data["job_id"])
    if not job or job["user_id"] != g.user["id"]:
        return utf8_json({"error": "无权限"}, 403)

    data = request.get_json(silent=True) or {}
    allowed = {}
    for k in ('status', 'interview_status'):
        if k in data:
            allowed[k] = data[k]

    v2_update_application(app_id, **allowed)
    return utf8_json({"ok": True})


# ========== SEEKER API ==========

@app.route("/api/v2/seeker/resumes", methods=["GET"])
@require_auth
def api_v2_seeker_resumes():
    resumes = get_user_resumes(g.user["id"])
    return utf8_json(resumes)


@app.route("/api/v2/seeker/resumes/<int:resume_id>", methods=["DELETE"])
@require_auth
def api_v2_seeker_delete_resume(resume_id):
    resume = get_resume(resume_id, user_id=g.user["id"])
    if not resume:
        return utf8_json({"error": "简历不存在"}, 404)
    soft_delete_resume(resume_id, g.user["id"])
    return utf8_json({"message": "简历已删除"})


@app.route("/api/v2/seeker/apply", methods=["POST"])
@require_auth
@limiter.limit("10/minute")
def api_v2_seeker_apply():
    data = request.get_json(silent=True) or {}
    job_id = data.get("job_id")
    resume_id = data.get("resume_id")
    cover_letter = (data.get("cover_letter") or "").strip()

    if not job_id or not resume_id:
        return utf8_json({"error": "缺少岗位或简历ID"}, 400)

    job = v2_get_job(job_id)
    if not job:
        return utf8_json({"error": "岗位不存在"}, 404)
    if job["status"] != "open":
        return utf8_json({"error": "该岗位已关闭"}, 400)

    resume = get_resume(resume_id, user_id=g.user["id"])
    if not resume:
        return utf8_json({"error": "简历不存在"}, 404)

    app_id = v2_create_application(job_id, g.user["id"], resume_id, cover_letter)
    if app_id is None:
        return utf8_json({"error": "投递失败"}, 500)

    if job["virtual_interview"]:
        v2_update_application(app_id, interview_status="pending")

    return utf8_json({"application_id": app_id})


@app.route("/api/v2/seeker/applications", methods=["GET"])
@require_auth
def api_v2_seeker_applications():
    apps = v2_get_applications_for_user(g.user["id"])
    return utf8_json(apps)


@app.route("/api/v2/seeker/upload-resume", methods=["POST"])
@require_auth
@limiter.limit(RATE_LIMIT_UPLOAD)
def api_v2_seeker_upload_resume():
    if "file" not in request.files:
        return utf8_json({"error": "未找到上传文件"}, 400)

    file = request.files["file"]
    if file.filename == "":
        return utf8_json({"error": "未选择文件"}, 400)

    mime_type = file.content_type or ""
    if mime_type and mime_type not in ALLOWED_MIME_TYPES:
        return utf8_json({"error": f"不支持的文件类型：{mime_type}"}, 400)

    try:
        text = extract_text_from_file(file)
        if not text or len(text.strip()) < 20:
            return utf8_json({"error": "简历内容过少"}, 400)

        safe_text = sanitize_prompt_input(text)
        position = request.form.get("position", "").strip()
        salary = request.form.get("salary", "").strip()
        city = request.form.get("city", "").strip()

        analysis = analyze_resume(safe_text, position=position, salary=salary, city=city)
        resume_id = save_resume(g.user["id"], file.filename, text, analysis, position=position, salary=salary, city=city)

        soft_delete_all_user_resumes_except(g.user["id"], resume_id)

        _backup_uploaded_file(file, g.user["id"], resume_id)

        return utf8_json({"resume_id": resume_id, "analysis": analysis})

    except ValueError as e:
        return utf8_json({"error": str(e)}, 400)
    except Exception as e:
        return utf8_json({"error": sanitize_error(e)}, 500)


if __name__ == "__main__":
    init_db()
    print("=" * 50)
    print("  MARDUK INSTITUTE - AI HR PLATFORM v2.0")
    print("=" * 50)
    if DEEPSEEK_API_KEY:
        print("  [OK] DeepSeek API Key configured")
    else:
        print("  [X] DeepSeek API Key not set")
        print("  Set DEEPSEEK_API_KEY in .env file")
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "127.0.0.1")
    print(f"  URL: http://{host}:{port}")
    print("=" * 50)
    app.run(debug=True, host=host, port=port)
