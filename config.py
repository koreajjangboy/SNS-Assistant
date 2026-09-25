"""애플리케이션 설정 — `.env` 로드, 환경 변수, 공통 상수."""
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

# 실제 환경 변수가 이미 있으면 그 값을 우선한다 (배포 환경에서 .env 없이 주입 가능)
load_dotenv(BASE_DIR / ".env", encoding="utf-8")


def _env(name: str, default: str = "") -> str:
    """환경 변수 값. `.env` 템플릿의 `your_...` 자리표시자는 미설정으로 취급한다."""
    value = (os.getenv(name) or "").strip()
    return default if not value or value.startswith("your_") else value


# ---------- Gemini ----------
GEMINI_API_KEY = _env("GEMINI_API_KEY")
GEMINI_MODEL = _env("GEMINI_MODEL", "gemini-3.8-flash")  # gemini-2.5-flash 는 신규 키에서 404
# 기본 모델이 재시도 후에도 과부하(429/5xx)면 순서대로 호출할 대체 모델 (쉼표 구분으로 재정의 가능)
GEMINI_FALLBACK_MODELS = tuple(
    m.strip() for m in _env("GEMINI_FALLBACK_MODELS", "gemini-3.6-flash").split(",") if m.strip()
)
GEMINI_MAX_RETRIES = 5           # 모델당 재시도 횟수 (첫 호출 제외) — 429 / 5xx / 네트워크 오류
GEMINI_BACKOFF_MAX_SECONDS = 15  # 지수 백오프 대기 상한 (2 → 4 → 8 → 15 → 15초)
GEMINI_TIMEOUT_SECONDS = 60      # 요청 1회당 제한 시간

# ---------- 게시글 ----------
HASHTAG_COUNT = 5                # 결과 카드에 표시할 해시태그 수

# ---------- 이미지 ----------
UPLOAD_TYPES = ("jpg", "jpeg", "png", "webp")
MODEL_MAX_IMAGES = 10            # Gemini 에 보내는 최대 이미지 수
MODEL_IMAGE_MAX_SIDE = 1024      # Gemini 전송 전 긴 변 축소 기준(px) — 토큰·전송량 절감


@dataclass(frozen=True)
class AspectRatio:
    label: str
    size: tuple[int, int] | None   # (가로, 세로). None 이면 원본 비율 유지
    slug: str                       # 다운로드 파일명 접미사


ASPECT_RATIOS: tuple[AspectRatio, ...] = (
    AspectRatio("1:1 (인스타그램 피드 / 정방형)", (1, 1), "1x1"),
    AspectRatio("9:16 (인스타 리얼스 / 틱톡 / 유튜브 쇼츠)", (9, 16), "9x16"),
    AspectRatio("4:5 (인스타그램 세로 피드)", (4, 5), "4x5"),
    AspectRatio("16:9 (가로형 / X / 페이스북)", (16, 9), "16x9"),
    AspectRatio("원본 비율 유지", None, "original"),
)

# ---------- 서버 ----------
SERVER_PORT = 8501
SERVER_ADDRESS = "0.0.0.0"       # 같은 네트워크의 다른 기기에서 접속 허용
