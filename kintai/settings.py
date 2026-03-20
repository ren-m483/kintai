# kintai/settings.py
import os
import dj_database_url
from pathlib import Path
from dotenv import load_dotenv


load_dotenv()  # .env ファイルを読み込む

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-insecure-key")
DEBUG      = os.environ.get("DEBUG", "True") == "True"
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")

# ── INSTALLED_APPS ─────────────────────────────────────
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "attendance",
]

# ── MIDDLEWARE（whitenoise を追加） ──────────────────────
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",   # ← 追加（2番目に置く）
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "kintai.urls"

# ── データベース ──────────────────────────────────────────
# DATABASE_URL環境変数があれば（本番）それを使う、なければローカルの PostgreSQL
DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            ssl_require=True,
        )
    }
else:
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

# ── 本番セキュリティ設定 ──────────────────────────────────
if not DEBUG:
    SECURE_SSL_REDIRECT             = True
    SESSION_COOKIE_SECURE           = True
    CSRF_COOKIE_SECURE              = True
    SECURE_HSTS_SECONDS             = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS  = True
    SECURE_HSTS_PRELOAD             = True
    SECURE_CONTENT_TYPE_NOSNIFF     = True
    X_FRAME_OPTIONS                 = "DENY"


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

# settings.py の LOGGING を以下に差し替え

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name} {message}",
            "style":  "{",
        },
    },
    "handlers": {
        "console": {
            "class":     "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level":    "INFO",
            "propagate": True,
        },
        "django.request": {
            "handlers":  ["console"],
            "level":     "ERROR",
            "propagate": False,
        },
        "attendance": {
            "handlers":  ["console"],
            "level":     "INFO",
            "propagate": False,
        },
    },
}