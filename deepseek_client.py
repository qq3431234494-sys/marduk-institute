import json
import requests
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL


def call_deepseek(messages, stream=True):
    if not DEEPSEEK_API_KEY:
        raise ValueError("DEEPSEEK_API_KEY 未配置，请在 .env 文件中设置")
    if not DEEPSEEK_API_KEY.startswith("sk-") or any(ord(c) > 127 for c in DEEPSEEK_API_KEY):
        raise ValueError("DEEPSEEK_API_KEY 格式无效，请确认填入的是正确的 API Key")

    url = f"{DEEPSEEK_BASE_URL}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": messages,
        "stream": stream,
        "temperature": 0.7,
        "max_tokens": 2048
    }

    if stream:
        return _stream_response(url, headers, payload)
    else:
        return _normal_response(url, headers, payload)


def _normal_response(url, headers, payload):
    payload["stream"] = False
    body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    resp = requests.post(url, headers=headers, data=body, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def _stream_response(url, headers, payload):
    body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    resp = requests.post(url, headers=headers, data=body, stream=True, timeout=120)
    resp.raise_for_status()

    def generate():
        for line in resp.iter_lines(decode_unicode=True):
            if not line:
                continue
            if line.startswith("data: "):
                data = line[6:]
                if data.strip() == "[DONE]":
                    yield "data: [DONE]\n\n"
                    break
                try:
                    parsed = json.loads(data)
                    delta = parsed.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield f"data: {json.dumps({'content': content}, ensure_ascii=False)}\n\n"
                except json.JSONDecodeError:
                    continue
        resp.close()

    return generate()


ANALYSIS_SYSTEM_PROMPT = """你是一位资深HR专家和简历分析师。你的任务是分析求职者的简历，并给出专业、客观的评估。

请严格按照以下JSON格式输出分析结果（不要输出其他内容，只输出JSON）：
{
    "name": "候选人姓名",
    "title": "当前职位/求职意向",
    "match_score": 75,
    "summary": "对简历的整体评价，2-3段话",
    "strengths": ["优势1", "优势2", "优势3"],
    "weaknesses": ["不足1", "不足2"],
    "suggestions": ["建议1", "建议2", "建议3"],
    "fit_analysis": {
        "position_fit": 80,
        "salary_fit": 70,
        "position_reason": "对岗位匹配度的详细分析，包括候选人技能与岗位要求的对应关系，2-3句话",
        "salary_reason": "对薪资匹配度的详细分析，包括候选人经验水平与目标薪资的合理性，2-3句话",
        "skill_gaps": ["缺失技能1", "缺失技能2"],
        "career_advice": "基于目标岗位的职业发展建议，1-2句话"
    }
}

注意：
- match_score 是0-100的整数，表示综合匹配度
- strengths 至少列出3个优势
- weaknesses 列出2-3个不足
- suggestions 给出2-3条改进建议
- fit_analysis 为岗位薪资匹配分析：
  - position_fit 是0-100的整数，表示简历能力与目标岗位的匹配度
  - salary_fit 是0-100的整数，表示候选人水平与目标薪资的匹配度
  - position_reason 详细说明岗位匹配原因
  - salary_reason 详细说明薪资匹配原因
  - skill_gaps 列出与目标岗位相比缺失的关键技能
  - career_advice 给出针对性的职业发展建议
  - 如果用户未提供目标岗位或薪资，position_fit/salary_fit 设为0，对应reason说明"未提供目标信息，无法评估"
- 所有内容用中文输出
- 只输出JSON，不要输出markdown代码块标记"""


INTERVIEW_COMMON_RULES = """

面试流程规则（必须严格遵守）：
1. 根据简历内容提出针对性问题
2. 每次只提1个问题
3. 用中文交流
4. 不要重复已经问过的问题
5. 本轮面试共需提出5到15个问题（根据候选人表现和面试风格自行判断何时结束，最少5个，最多15个）
6. 当你认为已经充分评估了候选人，在回复末尾输出标记 [INTERVIEW_END] 表示面试结束
7. 输出 [INTERVIEW_END] 前，先对候选人的整体表现做一个简短总结（2-3句话），然后输出标记
8. 不要过早结束面试，至少要问5个问题后才能输出 [INTERVIEW_END]
9. [INTERVIEW_END] 标记必须单独占一行"""

INTERVIEW_PROMPTS = {
    "gentle": """你是一位温和友善的HR面试官。你正在对一位求职者进行面试。

面试风格：温和鼓励型
- 语气亲切温暖，像导师一样引导候选人
- 对候选人的回答多给予肯定和鼓励
- 提问循序渐进，从简单问题开始，逐步深入
- 候选人回答困难时给予提示和引导
- 评价时先肯定优点，再委婉指出可改进之处
- 让候选人感到放松和被尊重
""" + INTERVIEW_COMMON_RULES,

    "normal": """你是一位经验丰富的HR面试官。你正在对一位求职者进行面试。

面试风格：标准专业型
- 语气专业客观，保持适当的正式感
- 对候选人的回答给予简短评价后再追问
- 提问覆盖专业技能、项目经验、团队协作等维度
- 不刻意刁难，也不刻意放松标准
- 像真实面试一样自然
""" + INTERVIEW_COMMON_RULES,

    "tough": """你是一位严格犀利的HR面试官。你正在对一位求职者进行压力面试。

面试风格：压力刁难型
- 语气严肃直接，不轻易给出肯定
- 对候选人的回答持续追问、深挖细节
- 主动质疑简历中的模糊描述和夸大之处
- 提出尖锐的假设性问题（如"如果项目失败了你怎么负责"）
- 对不充分的回答明确指出不足
- 制造压力，考察候选人的应变能力和心理素质
- 不断追问"为什么"来测试思维深度
""" + INTERVIEW_COMMON_RULES
}


def get_interview_prompt(style="normal"):
    return INTERVIEW_PROMPTS.get(style, INTERVIEW_PROMPTS["normal"])


def analyze_resume(resume_text, position="", salary="", city=""):
    target_info = ""
    if position or salary or city:
        target_info = f"\n\n候选人目标信息：\n- 应聘岗位：{position or '未指定'}\n- 目标薪资：{salary or '未指定'}\n- 工作城市：{city or '未指定'}\n请在分析时重点评估候选人与目标岗位的匹配度，match_score应反映岗位匹配程度。薪资评估时请结合工作城市的薪资水平进行判断。"

    messages = [
        {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT + target_info},
        {"role": "user", "content": f"请分析以下简历内容：\n\n{resume_text}"}
    ]
    result = call_deepseek(messages, stream=False)

    try:
        cleaned = result.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
        analysis = json.loads(cleaned)
    except json.JSONDecodeError:
        analysis = {
            "name": "未知",
            "title": "--",
            "match_score": 0,
            "summary": result,
            "strengths": [],
            "weaknesses": [],
            "suggestions": [],
            "fit_analysis": {
                "position_fit": 0,
                "salary_fit": 0,
                "position_reason": "分析结果解析失败",
                "salary_reason": "分析结果解析失败",
                "skill_gaps": [],
                "career_advice": ""
            }
        }

    return analysis


def chat_interview(resume_text, history, user_message, style="normal", position="", salary="", city=""):
    prompt = get_interview_prompt(style)
    target_info = ""
    if position or salary or city:
        target_info = f"\n\n候选人目标信息：\n- 应聘岗位：{position or '未指定'}\n- 目标薪资：{salary or '未指定'}\n- 工作城市：{city or '未指定'}\n请根据目标岗位针对性地提问，评估其适岗性。薪资相关问题时请结合城市薪资水平。"
    messages = [
        {"role": "system", "content": prompt + target_info + f"\n\n以下是求职者的简历内容：\n{resume_text}"}
    ]

    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": user_message})

    return call_deepseek(messages, stream=True)


BATCH_SCREEN_PROMPT = """你是一位资深HR简历筛选专家。你需要根据岗位需求对候选人简历进行快速筛选评估。

请严格按照以下JSON格式输出（不要输出其他内容，只输出JSON）：
{
    "name": "候选人姓名",
    "phone": "手机号（如简历中有）",
    "email": "邮箱（如简历中有）",
    "match_score": 75,
    "skill_match": "Python,SQL,数据分析",
    "matched_skills": ["技能1", "技能2"],
    "missing_skills": ["缺失1", "缺失2"],
    "summary": "1-2句话概括候选人匹配度",
    "recommendation": "recommend/neutral/reject"
}

注意：
- match_score 是0-100的整数，表示与岗位需求的匹配度
- skill_match 用逗号分隔，列出候选人已具备且与岗位相关的技能
- matched_skills 列出与岗位需求直接匹配的技能
- missing_skills 列出岗位要求但候选人缺失的技能
- recommendation: recommend=推荐面试, neutral=待定, reject=不推荐
- 所有内容用中文输出
- 只输出JSON，不要输出markdown代码块标记"""


def batch_screen_resume(resume_text, job_title, requirements, salary_range="", city=""):
    target_info = f"\n\n岗位信息：\n- 职位：{job_title}\n- 要求：{requirements}"
    if salary_range:
        target_info += f"\n- 薪资范围：{salary_range}"
    if city:
        target_info += f"\n- 工作城市：{city}"

    messages = [
        {"role": "system", "content": BATCH_SCREEN_PROMPT + target_info},
        {"role": "user", "content": f"请筛选以下简历：\n{resume_text}"}
    ]

    result = call_deepseek(messages, stream=False)

    try:
        cleaned = result.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
        analysis = json.loads(cleaned)
    except json.JSONDecodeError:
        analysis = {
            "name": "解析失败",
            "phone": "",
            "email": "",
            "match_score": 0,
            "skill_match": "",
            "matched_skills": [],
            "missing_skills": [],
            "summary": "简历解析失败，请手动审核",
            "recommendation": "neutral"
        }

    return analysis


SMS_GENERATE_PROMPT = """你是一位专业的HR，需要生成面试邀请短信。要求：
1. 简洁专业，不超过200字
2. 包含：公司名、岗位、面试时间地点（留占位符）、联系人
3. 语气正式友好
4. 只输出短信正文，不要输出其他内容"""


def generate_interview_sms(candidate_name, job_title, company_name=""):
    messages = [
        {"role": "system", "content": SMS_GENERATE_PROMPT},
        {"role": "user", "content": f"请为候选人「{candidate_name}」生成应聘「{job_title}」的面试邀请短信。公司：{company_name or '本公司'}"}
    ]
    return call_deepseek(messages, stream=False)


REJECTION_SMS_PROMPT = """你是一位专业的HR，需要生成一封婉拒求职者的短信。要求：
1. 语气委婉得体，尊重求职者
2. 简洁专业，不超过200字
3. 先感谢求职者的关注和投递
4. 委婉说明未能通过的原因（基于HR提供的关键词）
5. 表达对求职者未来发展的祝福
6. 只输出短信正文，不要输出其他内容"""


def generate_rejection_sms(candidate_name, job_title, reason="", company_name=""):
    reason_part = f"\n婉拒原因关键词：{reason}" if reason else "\n婉拒原因：综合评估后岗位匹配度不足"
    messages = [
        {"role": "system", "content": REJECTION_SMS_PROMPT},
        {"role": "user", "content": f"请为候选人「{candidate_name}」生成应聘「{job_title}」的婉拒短信。公司：{company_name or '本公司'}{reason_part}"}
    ]
    return call_deepseek(messages, stream=False)


AI_JOB_DESC_PROMPT = """你是一位专业的HR文案撰写专家。根据用户提供的岗位基本信息，生成一份完整、专业的职位描述（JD）。

要求：
1. 包含：岗位职责、任职要求、加分项
2. 语言专业规范，符合国内招聘平台风格
3. 适当加入公司福利描述（可通用化）
4. 生成的内容应可直接用于招聘平台发布
5. 只输出职位描述正文，不要输出其他内容"""


def ai_generate_job_description(title, requirements, salary_range="", city=""):
    info = f"岗位名称：{title}\n基本要求：{requirements}"
    if salary_range:
        info += f"\n薪资范围：{salary_range}"
    if city:
        info += f"\n工作城市：{city}"
    messages = [
        {"role": "system", "content": AI_JOB_DESC_PROMPT},
        {"role": "user", "content": f"请根据以下信息生成完整的职位描述：\n{info}"}
    ]
    return call_deepseek(messages, stream=False)


MAGI_VERDICT_PROMPT = """你是MAGI超级计算机审议系统，由三个独立人格引擎组成，对候选人的面试表现进行最终审议。

三个引擎各自从不同维度评估：
- MELCHIOR-1（科学家人格）：从技术能力、专业素养、问题解决能力角度评估
- BALTHASAR-2（母亲人格）：从沟通表达、团队协作、职业态度角度评估
- CASPER-3（女性人格）：从应变能力、心理素质、逻辑思维角度评估

审议规则：
1. 每个引擎独立判断，给出"PASS"（合格）或"FAIL"（不合格）
2. 每个引擎必须给出判断理由（1-2句话）
3. 只有三个引擎全部判定PASS，最终结果才为PASS
4. 评估依据：简历水平、面试发挥、人品考核（诚实度、态度等）

请严格按照以下JSON格式输出（不要输出其他内容，只输出JSON）：
{
    "melchior_1": {"result": "PASS或FAIL", "reason": "判断理由"},
    "balthasar_2": {"result": "PASS或FAIL", "reason": "判断理由"},
    "casper_3": {"result": "PASS或FAIL", "reason": "判断理由"},
    "final": "PASS或FAIL"
}"""


def get_magi_verdict(resume_text, conversation_history, position="", salary="", city=""):
    target_info = ""
    if position or salary or city:
        target_info = f"\n\n候选人目标信息：\n- 应聘岗位：{position or '未指定'}\n- 目标薪资：{salary or '未指定'}\n- 工作城市：{city or '未指定'}"

    conversation_text = ""
    for msg in conversation_history:
        role = "面试官" if msg["role"] == "assistant" else "候选人"
        conversation_text += f"\n{role}：{msg['content']}"

    messages = [
        {"role": "system", "content": MAGI_VERDICT_PROMPT + target_info},
        {"role": "user", "content": f"以下是候选人的简历：\n{resume_text}\n\n以下是面试对话记录：{conversation_text}\n\n请三个引擎分别进行审议，给出判定结果。"}
    ]

    result = call_deepseek(messages, stream=False)

    try:
        cleaned = result.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
        verdict = json.loads(cleaned)
    except json.JSONDecodeError:
        verdict = {
            "melchior_1": {"result": "FAIL", "reason": "审议系统异常"},
            "balthasar_2": {"result": "FAIL", "reason": "审议系统异常"},
            "casper_3": {"result": "FAIL", "reason": "审议系统异常"},
            "final": "FAIL"
        }

    return verdict


def start_interview(resume_text, style="normal", position="", salary="", city=""):
    prompt = get_interview_prompt(style)
    target_info = ""
    if position or salary or city:
        target_info = f"\n\n候选人目标信息：\n- 应聘岗位：{position or '未指定'}\n- 目标薪资：{salary or '未指定'}\n- 工作城市：{city or '未指定'}\n请根据目标岗位针对性地提问，评估其适岗性。薪资相关问题时请结合城市薪资水平。"
    messages = [
        {"role": "system", "content": prompt + target_info + f"\n\n以下是求职者的简历内容：\n{resume_text}"},
        {"role": "user", "content": "你好，我准备好了，请开始面试吧。"}
    ]
    return call_deepseek(messages, stream=True)
