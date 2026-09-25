"""Pillow 기반 이미지 처리 — 로드, 센터 크롭, 형식 변환, Gemini 전송용 축소."""
import io
from pathlib import Path
from typing import BinaryIO

from PIL import Image, ImageOps, UnidentifiedImageError

# 확장자 → (Pillow 저장 포맷, MIME)
FORMATS: dict[str, tuple[str, str]] = {
    "jpg": ("JPEG", "image/jpeg"),
    "jpeg": ("JPEG", "image/jpeg"),
    "png": ("PNG", "image/png"),
    "webp": ("WEBP", "image/webp"),
}
# 포맷별로 그대로 저장할 수 있는 모드 — 그 외 모드는 저장 전에 변환한다
_SAVE_MODES = {"JPEG": {"RGB", "L"}, "PNG": {"RGB", "RGBA", "L", "LA", "P"}, "WEBP": {"RGB", "RGBA"}}


class ImageLoadError(ValueError):
    """이미지로 열 수 없는 파일."""


def extension(filename: str) -> str:
    """지원 확장자(소문자, 점 제외). 지원하지 않으면 ImageLoadError."""
    ext = Path(filename).suffix.lower().lstrip(".")
    if ext not in FORMATS:
        raise ImageLoadError("지원하지 않는 형식이에요. JPG · PNG · WEBP 파일을 올려 주세요.")
    return ext


def load_image(source: bytes | BinaryIO) -> Image.Image:
    """이미지를 열고 EXIF 회전 정보(휴대폰 사진)를 반영한다."""
    try:
        img = Image.open(io.BytesIO(source) if isinstance(source, bytes) else source)
        img = ImageOps.exif_transpose(img)
        img.load()
    except Image.DecompressionBombError as e:
        raise ImageLoadError("해상도가 너무 커서 열 수 없어요.") from e
    except (UnidentifiedImageError, OSError) as e:
        raise ImageLoadError("이미지 파일이 아니거나 손상된 파일이에요.") from e
    return img


def center_crop(img: Image.Image, ratio: tuple[int, int] | None) -> Image.Image:
    """목표 비율에서 가능한 가장 큰 영역을 이미지 중앙에서 잘라낸다. ratio 가 None 이면 원본 그대로."""
    if ratio is None:
        return img
    w, h = img.size
    rw, rh = ratio
    if w * rh > h * rw:                      # 원본이 더 넓음 → 좌우를 자름
        new_w = round(h * rw / rh)
        left = (w - new_w) // 2
        return img.crop((left, 0, left + new_w, h))
    new_h = round(w * rh / rw)               # 원본이 더 높음 → 위아래를 자름
    top = (h - new_h) // 2
    return img.crop((0, top, w, top + new_h))


def _to_savable(img: Image.Image, fmt: str) -> Image.Image:
    if img.mode in _SAVE_MODES[fmt]:
        return img
    has_alpha = img.mode in ("RGBA", "LA", "PA") or (img.mode == "P" and "transparency" in img.info)
    return img.convert("RGBA" if has_alpha and fmt != "JPEG" else "RGB")


def encode(img: Image.Image, ext: str) -> bytes:
    """확장자에 맞는 포맷으로 인코딩한 바이트 (다운로드용)."""
    fmt = FORMATS[ext][0]
    buf = io.BytesIO()
    options = {"quality": 95} if fmt in ("JPEG", "WEBP") else {}
    _to_savable(img, fmt).save(buf, format=fmt, **options)
    return buf.getvalue()


def mime_type(ext: str) -> str:
    return FORMATS[ext][1]


def output_filename(filename: str, suffix: str) -> str:
    """`photo.jpg` + `4x5` → `photo_4x5.jpg`"""
    path = Path(filename)
    return f"{path.stem}_{suffix}{path.suffix.lower()}"


def to_model_jpeg(img: Image.Image, max_side: int) -> bytes:
    """Gemini 전송용 — 긴 변을 max_side 이하로 줄인 JPEG 바이트."""
    small = img.copy()
    small.thumbnail((max_side, max_side))
    buf = io.BytesIO()
    _to_savable(small, "JPEG").save(buf, format="JPEG", quality=85)
    return buf.getvalue()
