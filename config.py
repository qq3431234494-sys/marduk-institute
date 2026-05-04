import os
from dotenv import load_dotenv

load_dotenv()


def _set_key(env_path, key, value):
    lines = []
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    found = False
    for i, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[i] = f"{key}={value}\n"
            found = True
            break
    if not found:
        lines.append(f"{key}={value}\n")
    with open(env_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)


DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"

DATABASE_PATH = os.path.join(os.path.dirname(__file__), "data", "resumes.db")

BACKUP_DIR = os.path.join(os.path.dirname(__file__), "data", "backups")
BACKUP_FILES_DIR = os.path.join(BACKUP_DIR, "files")
BACKUP_PAYLOADS_DIR = os.path.join(BACKUP_DIR, "payloads")

MAX_UPLOAD_SIZE = 10 * 1024 * 1024

JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "")
if not JWT_SECRET_KEY:
    JWT_SECRET_KEY = os.urandom(32).hex()
    _env_path = os.path.join(os.path.dirname(__file__), ".env")
    _set_key(_env_path, "JWT_SECRET_KEY", JWT_SECRET_KEY)

ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY", "")
if not ENCRYPTION_KEY:
    from cryptography.fernet import Fernet
    ENCRYPTION_KEY = Fernet.generate_key().decode()
    _env_path = os.path.join(os.path.dirname(__file__), ".env")
    _set_key(_env_path, "ENCRYPTION_KEY", ENCRYPTION_KEY)

ALLOWED_MIME_TYPES = {
    'text/plain',
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
}

RATE_LIMIT_DEFAULT = "120/minute"
RATE_LIMIT_UPLOAD = "5/minute"
RATE_LIMIT_CHAT = "30/minute"
