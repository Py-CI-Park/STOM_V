"""ChatGPT OAuth Proxy - 상수 정의 (Newsletter_AI 이식, STOM 격리판).

Newsletter_AI processors/chatgpt_oauth/constants.py 를 STOM용으로 적응.
핵심 적응:
  - 토큰 경로는 Newsletter_AI와 동일한 기존 파일을 재사용한다
    (`~/.config/newsletter-ai/chatgpt_auth.json`). 사용자가 이미 로그인했으므로
    재로그인 없이 그대로 쓴다.
  - 프록시 포트 기본값을 STOM 전용 18761로 둔다 (Newsletter_AI의 18741과 충돌 회피).
    STOM_AILOOP_PROXY_PORT 환경변수로 오버라이드 가능.
"""

import os
from pathlib import Path

# =============================================================================
# OAuth 설정
# =============================================================================

OAUTH_CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"

OAUTH_AUTHORIZE_URL = "https://auth.openai.com/oauth/authorize"
OAUTH_TOKEN_URL = "https://auth.openai.com/oauth/token"

OAUTH_CALLBACK_HOST = "localhost"
OAUTH_CALLBACK_PORT = 1455
OAUTH_CALLBACK_PATH = "/auth/callback"
OAUTH_REDIRECT_URI = f"http://{OAUTH_CALLBACK_HOST}:{OAUTH_CALLBACK_PORT}{OAUTH_CALLBACK_PATH}"

OAUTH_SCOPE = "openid profile email offline_access"

# =============================================================================
# ChatGPT API 설정
# =============================================================================

CHATGPT_API_BASE = "https://chatgpt.com/backend-api"
CHATGPT_RESPONSES_URL = f"{CHATGPT_API_BASE}/codex/responses"

# =============================================================================
# 프록시 서버 설정
# =============================================================================

PROXY_HOST = "127.0.0.1"

# STOM 전용 기본 포트 (Newsletter_AI 18741과 충돌 회피). env로 오버라이드.
DEFAULT_PROXY_PORT = 18761
PROXY_PORT = int(os.getenv("STOM_AILOOP_PROXY_PORT", str(DEFAULT_PROXY_PORT)))
PROXY_BASE_URL = f"http://{PROXY_HOST}:{PROXY_PORT}/v1"

PROXY_OPENAI_API_KEY_PLACEHOLDER = "chatgpt-oauth-placeholder"

# =============================================================================
# 토큰 저장 설정
# =============================================================================

# 토큰 파일은 Newsletter_AI 로그인 결과를 재사용한다 (재로그인 불필요).
# STOM_AILOOP_TOKEN_DIR 로 오버라이드 가능하나, 기본은 기존 newsletter-ai 경로.
_NEWSLETTER_APP_NAME = "newsletter-ai"
_default_config_dir = Path.home() / ".config" / _NEWSLETTER_APP_NAME
TOKEN_DIR = Path(os.getenv("STOM_AILOOP_TOKEN_DIR", str(_default_config_dir)))
TOKEN_FILE = TOKEN_DIR / "chatgpt_auth.json"

# 토큰 파일 권한 (Unix 전용, Windows에서는 무시)
TOKEN_FILE_PERMISSION = 0o600

# 토큰 갱신 여유 시간 (초) - 만료 N초 전에 미리 갱신
TOKEN_REFRESH_MARGIN_SECONDS = 300  # 5분

# =============================================================================
# 모델 매핑
# =============================================================================

# OpenAI Chat Completions 모델명 -> ChatGPT Codex 호환 모델명
MODEL_MAPPING = {
    "gpt-5.5": "gpt-5.5",
    "gpt-5.5-mini": "gpt-5.5-mini",
    "gpt-5.4": "gpt-5.4",
    "gpt-5.4-mini": "gpt-5.4-mini",
    "gpt-5.3-codex": "gpt-5.3-codex",
    "gpt-5.3-codex-spark": "gpt-5.3-codex-spark",
    "gpt-5.2": "gpt-5.2",
    "gpt-5.2-codex": "gpt-5.2-codex",
    "gpt-5.1": "gpt-5.1",
    "gpt-5.1-codex-max": "gpt-5.1-codex-max",
    "gpt-5.1-codex-mini": "gpt-5.1-codex-mini",
    # Codex CLI 표기 -> bare codex 모델명 정규화
    "openai-codex/gpt-5.5": "gpt-5.5",
    "openai-codex/gpt-5.5-mini": "gpt-5.5-mini",
    "openai-codex/gpt-5.4": "gpt-5.4",
    "openai-codex/gpt-5.4-mini": "gpt-5.4-mini",
    "openai-codex/gpt-5.3-codex": "gpt-5.3-codex",
    "openai-codex/gpt-5.3-codex-spark": "gpt-5.3-codex-spark",
    "openai-codex/gpt-5.2": "gpt-5.2",
    "openai-codex/gpt-5.2-codex": "gpt-5.2-codex",
    "openai-codex/gpt-5.1": "gpt-5.1",
    "openai-codex/gpt-5.1-codex-max": "gpt-5.1-codex-max",
    "openai-codex/gpt-5.1-codex-mini": "gpt-5.1-codex-mini",
    # codex endpoint 미지원/불확실 모델 -> fallback
    "gpt-5.5-pro": "gpt-5.5-mini",
    "gpt-5.5-thinking": "gpt-5.5-mini",
    "gpt-5.5-nano": "gpt-5.5-mini",
    "gpt-5.4-pro": "gpt-5.4-mini",
    "gpt-5.4-thinking": "gpt-5.4-mini",
    "gpt-5.4-nano": "gpt-5.4-mini",
    "gpt-5-mini": "gpt-5.5-mini",
    "gpt-5-nano": "gpt-5.5-mini",
    "o3": "gpt-5.5-mini",
    "o3-mini": "gpt-5.5-mini",
    # 레거시 OpenAI 모델 -> fallback
    "gpt-4o": "gpt-5.5-mini",
    "gpt-4o-mini": "gpt-5.5-mini",
    "gpt-4o-2024-08-06": "gpt-5.5-mini",
    "gpt-4-turbo": "gpt-5.5-mini",
    "gpt-4-turbo-preview": "gpt-5.5-mini",
    "gpt-4": "gpt-5.5-mini",
    "gpt-3.5-turbo": "gpt-5.5-mini",
    "o4-mini": "gpt-5.5-mini",
    "o1": "gpt-5.5-mini",
    "o1-mini": "gpt-5.5-mini",
}

# ChatGPT OAuth 사용 시 기본 모델
DEFAULT_MODEL = "gpt-5.5"

# =============================================================================
# 환경변수 이름
# =============================================================================

ENV_AUTH_MODE = "STOM_AILOOP_OPENAI_AUTH_MODE"
ENV_AUTH_MODE_VALUE = "chatgpt_oauth"

# 타임아웃 설정
REQUEST_TIMEOUT_SECONDS = 300  # 5분
PROXY_STARTUP_TIMEOUT_SECONDS = 10

# =============================================================================
# 로깅
# =============================================================================

# 토큰 마스킹: 로그에 출력할 때 앞 N자만 표시
TOKEN_LOG_MASK_LENGTH = 8


def get_oauth_callback_port() -> int:
    return OAUTH_CALLBACK_PORT


def get_oauth_redirect_uri() -> str:
    return f"http://{OAUTH_CALLBACK_HOST}:{get_oauth_callback_port()}{OAUTH_CALLBACK_PATH}"


def get_proxy_port() -> int:
    return int(os.getenv("STOM_AILOOP_PROXY_PORT", str(PROXY_PORT)))


def get_proxy_base_url() -> str:
    return f"http://{PROXY_HOST}:{get_proxy_port()}/v1"
