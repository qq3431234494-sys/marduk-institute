import sys
import os
import threading
import webview

IS_FROZEN = getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

if IS_FROZEN:
    BUNDLE_DIR = sys._MEIPASS
    EXE_DIR = os.path.dirname(sys.executable)
else:
    BUNDLE_DIR = os.path.dirname(os.path.abspath(__file__))
    EXE_DIR = os.path.dirname(BUNDLE_DIR)

PROJECT_DIR = EXE_DIR


def start_flask():
    os.chdir(PROJECT_DIR)
    sys.path.insert(0, BUNDLE_DIR if IS_FROZEN else PROJECT_DIR)

    env_path = os.path.join(PROJECT_DIR, '.env')
    if not os.path.exists(env_path):
        with open(env_path, 'w', encoding='utf-8') as f:
            f.write('DEEPSEEK_API_KEY=\n')

    from dotenv import load_dotenv
    load_dotenv(env_path)

    data_dir = os.path.join(PROJECT_DIR, 'data')
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(os.path.join(data_dir, 'backups', 'files'), exist_ok=True)
    os.makedirs(os.path.join(data_dir, 'backups', 'payloads'), exist_ok=True)

    os.environ['DATABASE_PATH'] = os.path.join(data_dir, 'resumes.db')
    os.environ['BACKUP_DIR'] = os.path.join(data_dir, 'backups')
    os.environ['BACKUP_FILES_DIR'] = os.path.join(data_dir, 'backups', 'files')
    os.environ['BACKUP_PAYLOADS_DIR'] = os.path.join(data_dir, 'backups', 'payloads')

    if IS_FROZEN:
        import config
        config.DATABASE_PATH = os.path.join(data_dir, 'resumes.db')
        config.BACKUP_DIR = os.path.join(data_dir, 'backups')
        config.BACKUP_FILES_DIR = os.path.join(data_dir, 'backups', 'files')
        config.BACKUP_PAYLOADS_DIR = os.path.join(data_dir, 'backups', 'payloads')

        template_dir = os.path.join(BUNDLE_DIR, 'templates')
        static_dir = os.path.join(BUNDLE_DIR, 'static')
        if os.path.exists(template_dir):
            os.environ['FLASK_TEMPLATE_DIR'] = template_dir
        if os.path.exists(static_dir):
            os.environ['FLASK_STATIC_DIR'] = static_dir

    from app import app

    if IS_FROZEN:
        template_dir = os.environ.get('FLASK_TEMPLATE_DIR')
        static_dir = os.environ.get('FLASK_STATIC_DIR')
        if template_dir and os.path.exists(template_dir):
            app.template_folder = template_dir
        if static_dir and os.path.exists(static_dir):
            app.static_folder = static_dir

    from db import init_db
    init_db()

    app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)


def main():
    print("=" * 50)
    print("  MARDUK INSTITUTE - Desktop Application")
    print("=" * 50)
    print(f"  Project Dir: {PROJECT_DIR}")
    print(f"  Bundle Dir:  {BUNDLE_DIR}")
    print(f"  Frozen:      {IS_FROZEN}")
    print("=" * 50)

    flask_thread = threading.Thread(target=start_flask, daemon=True)
    flask_thread.start()

    import time
    time.sleep(2.0)

    window = webview.create_window(
        'MARDUK INSTITUTE',
        'http://127.0.0.1:5000',
        width=1280,
        height=800,
        min_size=(768, 600),
        text_select=True
    )

    def on_closing():
        os._exit(0)

    window.events.closing += on_closing
    webview.start()


if __name__ == '__main__':
    main()
