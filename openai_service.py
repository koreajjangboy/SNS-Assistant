"""ChatGPT(OpenAI) 연동 — Gemini 와 같은 프롬프트·응답 스키마로 SNS 게시글(본문 + 해시태그)을 생성한다.

결과를 Gemini 와 나란히 비교할 수 있도록 시스템 프롬프트, 사용자 프롬프트, 응답 스키마(SnsPost),
후처리(이모지 제거·해시태그 정리)는 gemini_service 의 것을 그대로 쓴다.
"""
import base64
import logging
from collections.abc import Sequence
from functools import lru_cache

import openai
from openai import OpenAI

import config
from gemini_service import SYSTEM_INSTRUCTION, GenerationResult, SnsPost, build_prompt, normalize_hashtags, strip_emoji

logger = logging.getLogger(__name__)


class OpenAIServiceError(RuntimeError):
    """사용자에게 그대로 보여줄 수 있는 메시지를 담은 오류."""


@lru_cache(maxsize=4)
def get_client(api_key: str) -> OpenAI:
    # 429 / 5xx / 연결 오류는 SDK 가 지수 백오프로 자동 재시도한다
    return OpenAI(api_key=api_key, timeout=config.OPENAI_TIMEOUT_SECONDS, max_retries=config.OPENAI_MAX_RETRIES)


def _image_part(data: bytes) -> dict:
    """JPEG 바이트 → Chat Completions 멀티모달 입력 (base64 data URL)."""
    encoded = base64.b64encode(data).decode("ascii")
    return {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded}"}}


def _failure_message(error: openai.APIError, model: str) -> str:
    """최종 실패 시 사용자에게 보여줄 문구."""
    if isinstance(error, openai.APITimeoutError):
        return "ChatGPT 응답이 너무 오래 걸려 중단했어요. 잠시 후 다시 시도해 주세요."
    if isinstance(error, openai.APIConnectionError):
        return "OpenAI 서버에 연결할 수 없어요. 인터넷 연결을 확인한 뒤 다시 시도해 주세요."
    if isinstance(error, openai.RateLimitError):
        if error.code == "insufficient_quota":
            return "OpenAI 크레딧(사용 한도)이 소진됐어요. OpenAI 결제·사용량 설정을 확인해 주세요."
        return "ChatGPT 요청 한도를 넘었어요. 잠시 후 다시 시도해 주세요."
    if isinstance(error, (openai.AuthenticationError, openai.PermissionDeniedError)):
        return "OpenAI API 키가 올바르지 않거나 권한이 없어요. .env의 OPENAI_API_KEY를 확인해 주세요."
    if isinstance(error, openai.NotFoundError):
        return f"ChatGPT 모델({model})을 사용할 수 없어요. OPENAI_MODEL_NAME 설정을 확인해 주세요."
    if isinstance(error, openai.APIStatusError) and error.status_code >= 500:
        return "지금 OpenAI 서버에 사용자가 많아 게시글을 만들지 못했어요. 잠시 후 다시 시도해 주세요."
    status = getattr(error, "status_code", "?")
    return f"ChatGPT 요청을 처리하지 못했어요 (HTTP {status})."


def generate_post(images: Sequence[bytes], keywords: Sequence[str], *,
                  api_key: str = config.OPENAI_API_KEY,
                  model: str = config.OPENAI_MODEL_NAME,
                  hashtag_count: int = config.HASHTAG_COUNT) -> GenerationResult:
    """JPEG 이미지 바이트들과 키워드로 게시글을 생성한다. 해시태그는 최대 hashtag_count 개."""
    if not api_key:
        raise OpenAIServiceError("OPENAI_API_KEY가 설정되지 않았어요. .env 파일을 확인해 주세요.")
    if not images:
        raise OpenAIServiceError("사진을 1장 이상 올려 주세요.")

    user_content = [*(_image_part(data) for data in images),
                    {"type": "text", "text": build_prompt(keywords, hashtag_count)}]
    try:
        completion = get_client(api_key).chat.completions.parse(
            model=model,
            messages=[{"role": "system", "content": SYSTEM_INSTRUCTION},
                      {"role": "user", "content": user_content}],
            response_format=SnsPost,
        )
    except (openai.LengthFinishReasonError, openai.ContentFilterFinishReasonError) as e:
        logger.warning("ChatGPT 응답 중단 (%s): %s", model, e)
        raise OpenAIServiceError("ChatGPT가 게시글을 끝까지 쓰지 못했어요. 다른 사진이나 키워드로 다시 시도해 주세요.") from e
    except openai.APIError as e:
        logger.exception("OpenAI API 오류 (%s)", model)
        raise OpenAIServiceError(_failure_message(e, model)) from e

    message = completion.choices[0].message
    if message.refusal or message.parsed is None:
        logger.warning("ChatGPT 응답 거절/해석 실패 (%s): %s", model, message.refusal)
        raise OpenAIServiceError("ChatGPT가 게시글을 쓰지 않았어요. 다른 사진이나 키워드로 다시 시도해 주세요.")

    post: SnsPost = message.parsed
    post.body = strip_emoji(post.body)
    post.hashtags = normalize_hashtags(post.hashtags, hashtag_count)
    if len(post.hashtags) < hashtag_count:
        logger.warning("ChatGPT 해시태그 %d개 수신 (요청 %d개)", len(post.hashtags), hashtag_count)
    return GenerationResult(post, completion.model)
