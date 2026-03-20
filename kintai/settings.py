# kintai/settings.py
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()  # .env ファイルを読み込む

BASE_DIR = Path(__file__).resolve().parent.parent

# ── セキュリティ ──────────────────────────────────────────
SECRET_KEY = os.environ.get("SECRET_KEY", "insecure-dev-key-change-this")
DEBUG      = os.environ.get("DEBUG", "True") == "True"
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")

# ── アプリ ────────────────────────────────────────────────
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "attendance",               # 自分で作ったアプリ
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "kintai.urls"

# ── テンプレート ──────────────────────────────────────────
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                # ↓ 自作の context_processor（後で作る）
                "attendance.context_processors.global_context",
            ],
        },
    },
]

# ── データベース（PostgreSQL）────────────────────────────
DATABASES = {
    "default": {
        "ENGINE":   "django.db.backends.postgresql",
        "NAME":     os.environ.get("DB_NAME",     "kintai_db"),
        "USER":     os.environ.get("DB_USER",     "kintai_user"),
        "PASSWORD": os.environ.get("DB_PASSWORD", "kintai_pass"),
        "HOST":     os.environ.get("DB_HOST",     "localhost"),
        "PORT":     os.environ.get("DB_PORT",     "5432"),
    }
}

# ── 静的ファイル ──────────────────────────────────────────
STATIC_URL  = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"   # 本番用（collectstatic の出力先）

# ── メディアファイル ──────────────────────────────────────
MEDIA_URL  = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ── 言語・タイムゾーン ────────────────────────────────────
LANGUAGE_CODE = "ja"
TIME_ZONE     = "Asia/Tokyo"
USE_I18N      = True
USE_TZ        = True

# ── 認証設定 ──────────────────────────────────────────────
LOGIN_URL           = "/login/"
# LOGIN_REDIRECT_URL  = "/"
LOGIN_REDIRECT_URL  = "/admin-login/"
LOGOUT_REDIRECT_URL = "/login/"

# ── セッション ────────────────────────────────────────────
SESSION_COOKIE_AGE     = 60 * 60 * 8   # 8 時間
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# ── その他 ────────────────────────────────────────────────
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGGING = {
    "version":            1,
    "disable_existing_loggers": False,

    # ── フォーマット ──────────────────────────────────────
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name} {message}",
            "style":  "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style":  "{",
        },
    },

    # ── ハンドラ ──────────────────────────────────────────
    "handlers": {
        # コンソール出力（開発時）
        "console": {
            "class":     "logging.StreamHandler",
            "formatter": "simple",
        },
        # ファイル出力（本番）
        "file": {
            "class":     "logging.handlers.RotatingFileHandler",
            "filename":  "/var/log/kintai/app.log",
            "maxBytes":  10 * 1024 * 1024,   # 10MB でローテート
            "backupCount": 5,
            "formatter": "verbose",
        },
        # エラーのみ別ファイルに保存
        "error_file": {
            "class":     "logging.handlers.RotatingFileHandler",
            "filename":  "/var/log/kintai/error.log",
            "level":     "ERROR",
            "maxBytes":  5 * 1024 * 1024,
            "backupCount": 3,
            "formatter": "verbose",
        },
    },

    # ── ロガー ────────────────────────────────────────────
    "loggers": {
        "django": {
            "handlers": ["console", "file"],
            "level":    "INFO",
            "propagate": True,
        },
        "django.request": {
            "handlers": ["error_file"],
            "level":    "ERROR",
            "propagate": False,
        },
        "attendance": {   # 自作アプリのロガー
            "handlers": ["console", "file"],
            "level":    "DEBUG",
            "propagate": False,
        },
    },
}