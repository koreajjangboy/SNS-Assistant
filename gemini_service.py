"""Gemini 연동 — 이미지 + 키워드로 SNS 게시글(본문 + 해시태그)을 생성한다."""
import logging
import random
import re
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from functools import lru_cache

import httpx
from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import BaseModel, Field, ValidationError

import config

logger = logging.getLogger(__name__)

StatusCallback = Callable[[str], None]  # 진행 상황 안내 문구를 받는 콜백 (UI 표시용)

_RETRYABLE_STATUS = {429, 500, 502, 503, 504}
_HASHTAG_MAX_LENGTH = 20   # '#' 제외 글자 수 — 이보다 긴 태그는 모델 출력 오류로 보고 버린다


SYSTEM_INSTRUCTION = """\
너는 직접 경험한 일을 SNS로 대중에게 전하는 사람이다. 마케터나 AI 비서가 아니다.

[문체]
- 모든 문장을 '~습니다', '~했습니다' 형태의 정중한 격식체로 끝낸다. 해요체(~했어요, ~네요)와 반말·평서체(~했다, ~이다)는 쓰지 않는다.
- 격식 있는 어휘를 고른다. 예: '다녀왔습니다' 대신 '방문했습니다', '참석했습니다', '참여했습니다'.
- 본문은 전체 8~12문장(10문장 전후)으로 쓴다. 한 문장에는 하나의 내용만 담아 짧고 명확하게 쓴다.
- 본문을 2~3개의 자연스러운 단락으로 나누고, 단락 사이는 빈 줄 하나로 구분한다.
- 과장된 표현("너무", "정말", "진짜", "완벽한", "최고의", "감성 가득한")은 쓰지 않는다.

[구성]
- 다음 흐름을 순서대로 풀어낸다: 방문 계기 → 경험 내용 → 느낀 점과 디테일 → 결론 및 총평.
- 3단락이면 '방문 계기와 경험 내용' / '느낀 점과 디테일' / '결론 및 총평'으로, 2단락이면 '방문 계기와 경험 내용' / '느낀 점과 총평'으로 나눈다.

[내용]
- 키워드를 나열하거나 사진을 묘사·설명하지 않는다. 키워드는 문맥에 자연스럽게 녹이고, 전부 쓰지 않아도 된다.
- 핵심 경험과 구체적인 디테일을 중심으로 전달한다.
- 사진과 키워드에 없는 사실(가게 이름, 가격, 위치 등)은 지어내지 않는다. 분량은 사실을 늘리지 말고 경험의 과정, 감각적인 디테일, 느낀 점으로 채운다.

[금지]
- 이모지, 이모티콘, 특수 기호 아이콘(예: ✨ ☕ 🌿 📸 ♥ ★ ✔)을 본문과 해시태그 어디에도 쓰지 않는다. 한글·영문·숫자와 일반 문장부호(. , ! ? ~ …)만 쓴다.
- 상투적인 인사말과 기계적인 서두·맺음말을 쓰지 않는다. 예: "안녕하세요 여러분", "오늘은 ~을 소개해 드리겠습니다", "여러분도 ~ 보내시기 바랍니다", "~는 어떠신가요?", "함께 ~합시다".
- 본문에 해시태그(#)를 넣지 않는다.

[해시태그]
- '#' 뒤에 공백이나 기호 없이 글자와 숫자만 쓴다.
- #일상 #데일리 같은 너무 일반적인 태그보다 사진과 키워드에 맞는 구체적인 태그를 우선한다.
"""

# 이모지·픽토그램 — 프롬프트로 막지 못한 경우를 위한 후처리. 한글과 일반 문장부호는 포함하지 않는다.
_EMOJI = re.compile(
    "["
    "\U0001F000-\U0001FAFF"          # 이모지, 국기, 픽토그램
    "\u2600-\u27BF"                  # 기타 기호(☕ ♥ ★), 딩뱃(✨ ✔ ❤)
    "\u2B00-\u2BFF"                  # ⭐ 등
    "\u3030\u303D\u3297\u3299"
    "\uFE0E\uFE0F\u200D\u20E3"       # 이모지 변형 선택자, ZWJ, 키캡
    "]"
)


def strip_emoji(text: str) -> str:
    """이모지를 제거하고, 제거로 생긴 공백을 정리한다 (문단 줄바꿈은 유지)."""
    lines = (re.sub(r"[ \t]{2,}", " ", _EMOJI.sub("", line)).strip() for line in text.split("\n"))
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


class SnsPost(BaseModel):
    """Gemini 응답 스키마."""
    body: str = Field(description="이모지 없이 정중한 격식체(~습니다)로 쓴 10문장 전후의 본문 (2~3개 단락, 해시태그 제외)")
    hashtags: list[str] = Field(description="'#' 뒤에 글자와 숫자만 있는 해시태그 (이모지·공백·기호 없음)")


@dataclass(frozen=True)
class GenerationResult:
    post: SnsPost
    model: str               # 실제로 응답한 모델 (대체 모델일 수 있음)


class GeminiServiceError(RuntimeError):
    """사용자에게 그대로 보여줄 수 있는 메시지를 담은 오류."""


@lru_cache(maxsize=4)
def get_client(api_key: str) -> genai.Client:
    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=config.GEMINI_TIMEOUT_SECONDS * 1000),
    )


def build_prompt(keywords: Sequence[str], hashtag_count: int) -> str:
    keyword_line = ", ".join(keywords) if keywords else "(없음 — 이미지 내용만 참고)"
    return (
        f"첨부한 사진과 키워드로 인스타그램 게시글 본문과 해시태그 {hashtag_count}개를 써줘.\n\n"
        f"키워드: {keyword_line}"
    )


def normalize_hashtags(tags: Sequence[str], limit: int) -> list[str]:
    """해시태그를 정리한다.

    - 한 항목에 여러 태그가 붙어 온 경우("#a #b") '#' 기준으로 나눈다.
    - 글자·숫자·밑줄만 남긴다 (이모지·공백·기호 제거 — "주말 여유" → "#주말여유").
    - 비정상적으로 긴 태그(모델 출력 오류)는 버리고, 중복 제거 후 limit 개로 자른다.
    """
    result: list[str] = []
    for chunk in tags:
        for piece in _EMOJI.sub("", chunk).split("#"):
            word = re.sub(r"\W", "", piece)
            if len(word) > _HASHTAG_MAX_LENGTH:
                logger.warning("비정상 해시태그 제외: %s", word)
            elif word and f"#{word}" not in result:
                result.append(f"#{word}")
    return result[:limit]


def _is_retryable(error: Exception) -> bool:
    return isinstance(error, httpx.TransportError) or (
        isinstance(error, genai_errors.APIError) and error.code in _RETRYABLE_STATUS
    )


def _daily_quota_limit(error: Exception) -> str | None:
    """429 가 '일일' 할당량 소진이면 한도 값(예: "20"), 아니면 None.

    분당 한도와 달리 일일 한도는 재시도해도 풀리지 않으므로, 이 경우 재시도 없이 대체 모델로 넘어간다.
    응답 형식: error.details[] 중 QuotaFailure 의 violations[].quotaId 에 "PerDay" 포함.
    """
    if not isinstance(error, genai_errors.APIError) or error.code != 429:
        return None
    body = error.details.get("error", {}) if isinstance(error.details, dict) else {}
    for detail in body.get("details") or []:
        for violation in detail.get("violations") or []:
            if "PerDay" in str(violation.get("quotaId", "")):
                return str(violation.get("quotaValue", "?"))
    return None


def _retry_reason(error: Exception) -> str:
    if isinstance(error, httpx.TransportError):
        return "Gemini 서버 연결이 불안정해"
    if error.code == 429:
        return "Gemini 요청 한도에 도달해"
    return "Gemini 서버에 사용자가 몰려"


def _failure_message(error: Exception, model: str) -> str:
    """최종 실패 시 사용자에게 보여줄 문구."""
    if isinstance(error, httpx.TransportError):
        return "Gemini 서버에 연결할 수 없어요. 인터넷 연결을 확인한 뒤 다시 시도해 주세요."
    code = error.code
    if limit := _daily_quota_limit(error):
        return (f"오늘 Gemini 무료 사용 한도(모델당 하루 {limit}회)를 다 썼어요. "
                "한도는 매일 한국 시간 오후 4~5시(미국 태평양 시간 자정)에 초기화돼요.")
    if code == 429:
        return "Gemini 요청 한도를 넘었어요. 잠시 후 다시 시도하거나 API 사용량을 확인해 주세요."
    if code in _RETRYABLE_STATUS:
        return "지금 Gemini 서버에 사용자가 많아 게시글을 만들지 못했어요. 잠시 후 다시 시도해 주세요."
    if code in (401, 403):
        return "Gemini API 키가 올바르지 않거나 권한이 없어요. .env의 GEMINI_API_KEY를 확인해 주세요."
    if code == 404:
        return f"Gemini 모델({model})을 사용할 수 없어요. GEMINI_MODEL 설정을 확인해 주세요."
    return f"Gemini 요청을 처리하지 못했어요 (HTTP {code})."


def _generate_with_retry(client: genai.Client, model: str, contents: list,
                         generation_config: types.GenerateContentConfig,
                         notify: StatusCallback) -> types.GenerateContentResponse:
    """429 / 5xx / 네트워크 오류는 지수 백오프(최대 GEMINI_BACKOFF_MAX_SECONDS) 후 재시도, 그 외는 즉시 실패.

    429 중 일일 한도 소진은 재시도해도 소용없으므로 즉시 실패시킨다 (호출 측에서 대체 모델로 전환).
    """
    max_retries = config.GEMINI_MAX_RETRIES
    for retry in range(max_retries + 1):
        try:
            return client.models.generate_content(model=model, contents=contents, config=generation_config)
        except (genai_errors.APIError, httpx.TransportError) as e:
            if not _is_retryable(e) or retry == max_retries:
                raise
            if _daily_quota_limit(e):
                logger.warning("%s: 일일 한도 소진 — 재시도 생략", model)
                raise
            wait = min(2 ** (retry + 1) + random.uniform(0, 1), config.GEMINI_BACKOFF_MAX_SECONDS)
            logger.warning("%s: %s — %.1f초 후 재시도 (%d/%d)", model, e, wait, retry + 1, max_retries)
            notify(f"{_retry_reason(e)} 다시 시도하고 있어요… ({retry + 1}/{max_retries}, {wait:.0f}초 후)")
            time.sleep(wait)
    raise AssertionError("unreachable")


def _parse(response: types.GenerateContentResponse) -> SnsPost:
    if isinstance(response.parsed, SnsPost):
        return response.parsed
    if not response.text:
        reason = response.candidates[0].finish_reason if response.candidates else "응답 없음"
        raise GeminiServiceError(f"Gemini가 게시글을 쓰지 않았어요 ({reason}). 다른 사진이나 키워드로 다시 시도해 주세요.")
    try:
        return SnsPost.model_validate_json(response.text)
    except ValidationError as e:
        raise GeminiServiceError("Gemini 응답을 읽지 못했어요. 다시 시도해 주세요.") from e


def generate_post(images: Sequence[bytes], keywords: Sequence[str], *,
                  api_key: str = config.GEMINI_API_KEY,
                  model: str = config.GEMINI_MODEL,
                  fallback_models: Sequence[str] = config.GEMINI_FALLBACK_MODELS,
                  hashtag_count: int = config.HASHTAG_COUNT,
                  on_status: StatusCallback | None = None) -> GenerationResult:
    """JPEG 이미지 바이트들과 키워드로 게시글을 생성한다. 해시태그는 최대 hashtag_count 개.

    기본 모델이 재시도 후에도 과부하(429 / 5xx)로 실패하면 fallback_models 를 순서대로 시도한다.
    """
    if not api_key:
        raise GeminiServiceError("GEMINI_API_KEY가 설정되지 않았어요. .env 파일을 확인해 주세요.")
    if not images:
        raise GeminiServiceError("사진을 1장 이상 올려 주세요.")
    notify = on_status or (lambda _: None)

    contents = [types.Part.from_bytes(data=data, mime_type="image/jpeg") for data in images]
    contents.append(build_prompt(keywords, hashtag_count))
    generation_config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=SnsPost,
        system_instruction=SYSTEM_INSTRUCTION,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )
    client = get_client(api_key)
    models = list(dict.fromkeys([model, *fallback_models]))   # 순서 유지 + 중복 제거

    last_error: Exception | None = None    # 최종 안내 문구의 기준 (과부하·한도 오류)
    prev_error: Exception | None = None    # 직전 모델의 오류 (전환 안내 문구용)
    for i, current in enumerate(models):
        if i > 0:
            reason = "오늘 사용 한도가 소진되어" if _daily_quota_limit(prev_error) else "혼잡해"
            notify(f"{models[i - 1]} 모델이 {reason} 대체 모델({current})로 다시 시도하고 있어요…")
        try:
            response = _generate_with_retry(client, current, contents, generation_config, notify)
        except httpx.TransportError as e:
            # 네트워크 문제는 다른 모델로 바꿔도 해결되지 않으므로 바로 실패
            logger.exception("Gemini 네트워크 오류 (%s)", current)
            raise GeminiServiceError(_failure_message(e, current)) from e
        except genai_errors.APIError as e:
            if i == 0 and not _is_retryable(e):
                logger.exception("Gemini API 오류 (%s)", current)
                raise GeminiServiceError(_failure_message(e, current)) from e
            # 기본 모델 과부하, 또는 대체 모델 자체의 오류 → 다음 대체 모델로
            logger.warning("Gemini %s 실패 (HTTP %s): %s", current, e.code, e.message)
            prev_error = e
            if _is_retryable(e):   # 최종 안내 문구는 과부하 원인 기준 (대체 모델의 404 등은 로그만)
                last_error = e
            continue

        post = _parse(response)
        post.body = strip_emoji(post.body)
        post.hashtags = normalize_hashtags(post.hashtags, hashtag_count)
        if len(post.hashtags) < hashtag_count:
            logger.warning("해시태그 %d개 수신 (요청 %d개)", len(post.hashtags), hashtag_count)
        if current != model:
            logger.info("대체 모델 %s 로 생성 완료", current)
        return GenerationResult(post, current)

    raise GeminiServiceError(_failure_message(last_error, model)) from last_error
