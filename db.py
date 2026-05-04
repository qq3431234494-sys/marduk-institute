import sqlite3
import json
import os
import random
import bcrypt
from cryptography.fernet import Fernet
from config import DATABASE_PATH, ENCRYPTION_KEY

_fernet = Fernet(ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY)


def encrypt_field(plaintext):
    if not plaintext:
        return ""
    return _fernet.encrypt(plaintext.encode('utf-8')).decode('utf-8')


def decrypt_field(ciphertext):
    if not ciphertext:
        return ""
    try:
        return _fernet.decrypt(ciphertext.encode('utf-8')).decode('utf-8')
    except Exception:
        return ""


def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password, hashed):
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


def get_db():
    db_dir = os.path.dirname(DATABASE_PATH)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            recovery_key TEXT NOT NULL,
            role TEXT DEFAULT 'seeker',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS resumes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            content_encrypted TEXT NOT NULL,
            analysis TEXT,
            position TEXT DEFAULT '',
            salary TEXT DEFAULT '',
            city TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            resume_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (resume_id) REFERENCES resumes(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_resumes_user_id ON resumes(user_id);
        CREATE INDEX IF NOT EXISTS idx_conversations_resume_id ON conversations(resume_id);
    """)
    conn.commit()

    try:
        conn.execute("ALTER TABLE resumes ADD COLUMN city TEXT DEFAULT ''")
    except Exception:
        pass
    try:
        conn.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'seeker'")
    except Exception:
        pass

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS hr_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            requirements TEXT NOT NULL,
            salary_range TEXT DEFAULT '',
            city TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS hr_screenings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            content_encrypted TEXT NOT NULL,
            candidate_name TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            email TEXT DEFAULT '',
            match_score INTEGER DEFAULT 0,
            skill_match TEXT DEFAULT '',
            analysis TEXT,
            status TEXT DEFAULT 'pending',
            sms_sent INTEGER DEFAULT 0,
            sms_content TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (job_id) REFERENCES hr_jobs(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_hr_jobs_user_id ON hr_jobs(user_id);
        CREATE INDEX IF NOT EXISTS idx_hr_screenings_job_id ON hr_screenings(job_id);
    """)

    conn.commit()

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS v2_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            requirements TEXT NOT NULL,
            salary_range TEXT DEFAULT '',
            city TEXT DEFAULT '',
            ai_generated INTEGER DEFAULT 0,
            virtual_interview INTEGER DEFAULT 0,
            status TEXT DEFAULT 'open',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS v2_applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            resume_id INTEGER NOT NULL,
            cover_letter TEXT DEFAULT '',
            status TEXT DEFAULT 'pending',
            screening_score INTEGER DEFAULT 0,
            screening_result TEXT DEFAULT '',
            interview_status TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (job_id) REFERENCES v2_jobs(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (resume_id) REFERENCES resumes(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_v2_jobs_user_id ON v2_jobs(user_id);
        CREATE INDEX IF NOT EXISTS idx_v2_jobs_status ON v2_jobs(status);
        CREATE INDEX IF NOT EXISTS idx_v2_applications_job_id ON v2_applications(job_id);
        CREATE INDEX IF NOT EXISTS idx_v2_applications_user_id ON v2_applications(user_id);

        CREATE TABLE IF NOT EXISTS v2_application_analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            application_id INTEGER NOT NULL UNIQUE,
            resume_id INTEGER NOT NULL,
            job_id INTEGER NOT NULL,
            analysis TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (application_id) REFERENCES v2_applications(id) ON DELETE CASCADE,
            FOREIGN KEY (resume_id) REFERENCES resumes(id) ON DELETE CASCADE,
            FOREIGN KEY (job_id) REFERENCES v2_jobs(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_v2_app_analyses_app_id ON v2_application_analyses(application_id);
        CREATE INDEX IF NOT EXISTS idx_v2_app_analyses_resume_job ON v2_application_analyses(resume_id, job_id);
    """)

    conn.commit()
    conn.close()


def generate_recovery_key():
    return str(random.randint(100000, 999999))


def create_user(username, password, role="seeker"):
    conn = get_db()
    try:
        password_hash = hash_password(password)
        recovery_key = generate_recovery_key()
        cursor = conn.execute(
            "INSERT INTO users (username, password_hash, recovery_key, role) VALUES (?, ?, ?, ?)",
            (username, password_hash, recovery_key, role)
        )
        user_id = cursor.lastrowid
        conn.commit()
        return user_id, recovery_key
    except sqlite3.IntegrityError:
        return None, None
    finally:
        conn.close()


def authenticate_user(username, password):
    conn = get_db()
    row = conn.execute(
        "SELECT id, username, password_hash, role FROM users WHERE username = ?",
        (username,)
    ).fetchone()
    conn.close()
    if row and verify_password(password, row["password_hash"]):
        return {"id": row["id"], "username": row["username"], "role": row["role"] or "seeker"}
    return None


def get_user_by_id(user_id):
    conn = get_db()
    row = conn.execute(
        "SELECT id, username, role, created_at FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def update_user_role(user_id, role):
    conn = get_db()
    conn.execute("UPDATE users SET role=? WHERE id=?", (role, user_id))
    conn.commit()
    conn.close()


def save_resume(user_id, filename, content, analysis=None, position="", salary="", city=""):
    conn = get_db()
    encrypted_content = encrypt_field(content)
    cursor = conn.execute(
        "INSERT INTO resumes (user_id, filename, content_encrypted, analysis, position, salary, city) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, filename, encrypted_content, json.dumps(analysis, ensure_ascii=False) if analysis else None, position, salary, city)
    )
    resume_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return resume_id


def get_resume(resume_id, user_id=None):
    conn = get_db()
    try:
        conn.execute("ALTER TABLE resumes ADD COLUMN is_deleted INTEGER DEFAULT 0")
        conn.commit()
    except Exception:
        pass
    if user_id:
        row = conn.execute(
            "SELECT * FROM resumes WHERE id = ? AND user_id = ? AND is_deleted = 0",
            (resume_id, user_id)
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT * FROM resumes WHERE id = ?",
            (resume_id,)
        ).fetchone()
    conn.close()
    if row:
        result = dict(row)
        result["content"] = decrypt_field(result["content_encrypted"])
        del result["content_encrypted"]
        if result.get('is_deleted') is not None:
            del result['is_deleted']
        if result['analysis']:
            result['analysis'] = json.loads(result['analysis'])
        return result
    return None


def get_user_resumes(user_id):
    conn = get_db()
    try:
        conn.execute("ALTER TABLE resumes ADD COLUMN is_deleted INTEGER DEFAULT 0")
        conn.commit()
    except Exception:
        pass
    rows = conn.execute(
        "SELECT id, filename, position, salary, city, created_at, analysis FROM resumes WHERE user_id = ? AND is_deleted = 0 ORDER BY created_at DESC",
        (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def soft_delete_resume(resume_id, user_id):
    conn = get_db()
    try:
        conn.execute("ALTER TABLE resumes ADD COLUMN is_deleted INTEGER DEFAULT 0")
        conn.commit()
    except Exception:
        pass
    conn.execute(
        "UPDATE resumes SET is_deleted = 1 WHERE id = ? AND user_id = ?",
        (resume_id, user_id)
    )
    conn.commit()
    conn.close()


def soft_delete_all_user_resumes_except(user_id, keep_resume_id):
    conn = get_db()
    try:
        conn.execute("ALTER TABLE resumes ADD COLUMN is_deleted INTEGER DEFAULT 0")
        conn.commit()
    except Exception:
        pass
    conn.execute(
        "UPDATE resumes SET is_deleted = 1 WHERE user_id = ? AND id != ? AND is_deleted = 0",
        (user_id, keep_resume_id)
    )
    conn.commit()
    conn.close()


def save_message(resume_id, role, content):
    conn = get_db()
    conn.execute(
        "INSERT INTO conversations (resume_id, role, content) VALUES (?, ?, ?)",
        (resume_id, role, content)
    )
    conn.commit()
    conn.close()


def get_conversation_history(resume_id, limit=20):
    conn = get_db()
    rows = conn.execute(
        "SELECT role, content FROM conversations WHERE resume_id = ? ORDER BY created_at ASC LIMIT ?",
        (resume_id, limit)
    ).fetchall()
    conn.close()
    return [{"role": row["role"], "content": row["content"]} for row in rows]


def reset_password(username, recovery_key, new_password):
    conn = get_db()
    row = conn.execute(
        "SELECT id, recovery_key FROM users WHERE username = ?",
        (username,)
    ).fetchone()
    if not row:
        conn.close()
        return False
    if row["recovery_key"] != recovery_key:
        conn.close()
        return False
    new_hash = hash_password(new_password)
    conn.execute(
        "UPDATE users SET password_hash = ? WHERE id = ?",
        (new_hash, row["id"])
    )
    conn.commit()
    conn.close()
    return True


def create_hr_job(user_id, title, requirements, salary_range="", city=""):
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO hr_jobs (user_id, title, requirements, salary_range, city) VALUES (?, ?, ?, ?, ?)",
        (user_id, title, requirements, salary_range, city)
    )
    job_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return job_id


def get_hr_jobs(user_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM hr_jobs WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_hr_job(job_id, user_id=None):
    conn = get_db()
    if user_id:
        row = conn.execute("SELECT * FROM hr_jobs WHERE id = ? AND user_id = ?", (job_id, user_id)).fetchone()
    else:
        row = conn.execute("SELECT * FROM hr_jobs WHERE id = ?", (job_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def add_hr_screening(job_id, user_id, filename, content, candidate_name="", phone="", email=""):
    conn = get_db()
    encrypted = encrypt_field(content)
    cursor = conn.execute(
        "INSERT INTO hr_screenings (job_id, user_id, filename, content_encrypted, candidate_name, phone, email) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (job_id, user_id, filename, encrypted, candidate_name, phone, email)
    )
    sid = cursor.lastrowid
    conn.commit()
    conn.close()
    return sid


def update_hr_screening(screening_id, match_score=0, skill_match="", analysis=None, status="pending"):
    conn = get_db()
    conn.execute(
        "UPDATE hr_screenings SET match_score=?, skill_match=?, analysis=?, status=? WHERE id=?",
        (match_score, skill_match, json.dumps(analysis, ensure_ascii=False) if analysis else None, status, screening_id)
    )
    conn.commit()
    conn.close()


def get_hr_screenings(job_id, user_id=None):
    conn = get_db()
    if user_id:
        rows = conn.execute(
            "SELECT id, job_id, user_id, filename, candidate_name, phone, email, match_score, skill_match, analysis, status, sms_sent, sms_content, created_at FROM hr_screenings WHERE job_id = ? AND user_id = ? ORDER BY match_score DESC",
            (job_id, user_id)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, job_id, user_id, filename, candidate_name, phone, email, match_score, skill_match, analysis, status, sms_sent, sms_content, created_at FROM hr_screenings WHERE job_id = ? ORDER BY match_score DESC",
            (job_id,)
        ).fetchall()
    conn.close()
    results = []
    for r in rows:
        d = dict(r)
        if d.get('analysis'):
            try:
                d['analysis'] = json.loads(d['analysis'])
            except Exception:
                pass
        results.append(d)
    return results


def update_screening_sms(screening_id, sms_content):
    conn = get_db()
    conn.execute(
        "UPDATE hr_screenings SET sms_sent=1, sms_content=? WHERE id=?",
        (sms_content, screening_id)
    )
    conn.commit()
    conn.close()


def v2_create_job(user_id, title, description, requirements, salary_range="", city="", ai_generated=False, virtual_interview=False):
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO v2_jobs (user_id, title, description, requirements, salary_range, city, ai_generated, virtual_interview) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (user_id, title, description, requirements, salary_range, city, 1 if ai_generated else 0, 1 if virtual_interview else 0)
    )
    job_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return job_id


def v2_get_jobs(user_id=None, status=None):
    conn = get_db()
    if user_id and status:
        rows = conn.execute("SELECT * FROM v2_jobs WHERE user_id=? AND status=? ORDER BY created_at DESC", (user_id, status)).fetchall()
    elif user_id:
        rows = conn.execute("SELECT * FROM v2_jobs WHERE user_id=? ORDER BY created_at DESC", (user_id,)).fetchall()
    elif status:
        rows = conn.execute("SELECT * FROM v2_jobs WHERE status=? ORDER BY created_at DESC", (status,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM v2_jobs ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def v2_get_job(job_id, user_id=None):
    conn = get_db()
    if user_id:
        row = conn.execute("SELECT * FROM v2_jobs WHERE id=? AND user_id=?", (job_id, user_id)).fetchone()
    else:
        row = conn.execute("SELECT * FROM v2_jobs WHERE id=?", (job_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def v2_update_job(job_id, user_id, **kwargs):
    conn = get_db()
    sets = []
    vals = []
    for k, v in kwargs.items():
        if k in ('title', 'description', 'requirements', 'salary_range', 'city', 'virtual_interview', 'status'):
            sets.append(f"{k}=?")
            vals.append(v)
    if not sets:
        conn.close()
        return
    vals.append(job_id)
    vals.append(user_id)
    conn.execute(f"UPDATE v2_jobs SET {', '.join(sets)} WHERE id=? AND user_id=?", vals)
    conn.commit()
    conn.close()


def v2_create_application(job_id, user_id, resume_id, cover_letter=""):
    conn = get_db()
    try:
        cursor = conn.execute(
            "INSERT INTO v2_applications (job_id, user_id, resume_id, cover_letter) VALUES (?, ?, ?, ?)",
            (job_id, user_id, resume_id, cover_letter)
        )
        app_id = cursor.lastrowid
        conn.commit()
        return app_id
    except sqlite3.IntegrityError:
        conn.close()
        return None
    finally:
        conn.close()


def v2_get_applications_for_job(job_id):
    conn = get_db()
    rows = conn.execute(
        """SELECT a.*, r.filename, r.analysis, r.position, u.username
           FROM v2_applications a
           LEFT JOIN resumes r ON a.resume_id = r.id
           LEFT JOIN users u ON a.user_id = u.id
           WHERE a.job_id = ?
           ORDER BY a.created_at DESC""",
        (job_id,)
    ).fetchall()
    conn.close()
    results = []
    for r in rows:
        d = dict(r)
        if d.get('analysis'):
            try:
                d['analysis'] = json.loads(d['analysis'])
            except Exception:
                pass
        results.append(d)
    return results


def v2_get_applications_for_user(user_id):
    conn = get_db()
    rows = conn.execute(
        """SELECT a.*, j.title as job_title, j.city as job_city, j.salary_range, j.status as job_status, j.virtual_interview
           FROM v2_applications a
           LEFT JOIN v2_jobs j ON a.job_id = j.id
           WHERE a.user_id = ?
           ORDER BY a.created_at DESC""",
        (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def v2_update_application(app_id, **kwargs):
    conn = get_db()
    sets = []
    vals = []
    for k, v in kwargs.items():
        if k in ('status', 'screening_score', 'screening_result', 'interview_status'):
            sets.append(f"{k}=?")
            vals.append(v)
    if not sets:
        conn.close()
        return
    vals.append(app_id)
    conn.execute(f"UPDATE v2_applications SET {', '.join(sets)} WHERE id=?", vals)
    conn.commit()
    conn.close()


def v2_get_application(app_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM v2_applications WHERE id=?", (app_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def v2_check_applied(job_id, user_id):
    conn = get_db()
    row = conn.execute("SELECT id FROM v2_applications WHERE job_id=? AND user_id=?", (job_id, user_id)).fetchone()
    conn.close()
    return row is not None


def v2_save_application_analysis(application_id, resume_id, job_id, analysis):
    conn = get_db()
    conn.execute(
        """INSERT INTO v2_application_analyses (application_id, resume_id, job_id, analysis)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(application_id) DO UPDATE SET analysis=excluded.analysis""",
        (application_id, resume_id, job_id, json.dumps(analysis, ensure_ascii=False) if analysis else None)
    )
    conn.commit()
    conn.close()


def v2_get_application_analysis(application_id):
    conn = get_db()
    row = conn.execute(
        "SELECT analysis FROM v2_application_analyses WHERE application_id=?",
        (application_id,)
    ).fetchone()
    conn.close()
    if row and row["analysis"]:
        try:
            return json.loads(row["analysis"])
        except Exception:
            return None
    return None


def v2_get_application_analysis_by_resume_job(resume_id, job_id):
    conn = get_db()
    row = conn.execute(
        "SELECT analysis FROM v2_application_analyses WHERE resume_id=? AND job_id=?",
        (resume_id, job_id)
    ).fetchone()
    conn.close()
    if row and row["analysis"]:
        try:
            return json.loads(row["analysis"])
        except Exception:
            return None
    return None
