"""SNS Assistant UI 프로토타입 — SNS-Assistant.ipynb Cell 5 에서 자동 생성된다 (직접 수정 시 덮어써짐)."""
import html
import io
from pathlib import Path

import streamlit as st
from PIL import Image, ImageOps, UnidentifiedImageError

st.set_page_config(page_title="SNS Assistant", page_icon="📸", layout="wide")

# ---------- 디자인 토큰 (docs/design-system.md) ----------
PALETTE = {  # 텍스트 색상: 강조 / 보조 / 본문
    "light": {"strong": "#374151", "muted": "#9CA3AF", "body": "#6B7280"},
    "dark":  {"strong": "#E5E7EB", "muted": "#4B5563", "body": "#6B7280"},
}
c = PALETTE.get(st.context.theme.type or "light", PALETTE["light"])

st.markdown(f"""
<style>
.ds-metric   {{ font-size: 30px; font-weight: 600; line-height: normal; color: {c["strong"]}; margin: 0; }}
.ds-title    {{ font-size: 18px; font-weight: 500; line-height: 28px;   color: {c["strong"]}; margin: 0; }}
.ds-subtitle {{ font-size: 16px; font-weight: 500; line-height: normal; color: {c["muted"]};  margin: 0; }}
.ds-text     {{ font-size: 14px; font-weight: 400; line-height: 20px;   color: {c["body"]};   margin: 0; white-space: pre-wrap; }}
.ds-bold     {{ font-size: 14px; font-weight: 700; line-height: normal; color: {c["body"]}; }}
.ds-label    {{ font-size: 12px; font-weight: 400; line-height: normal; color: {c["body"]};   margin: 0; }}
</style>
""", unsafe_allow_html=True)


def ds(text: str, style: str) -> None:
    """디자인 시스템 텍스트 스타일(metric/title/subtitle/text/bold/label)로 출력."""
    st.markdown(f'<p class="ds-{style}">{html.escape(text)}</p>', unsafe_allow_html=True)


# ---------- 이미지 처리 ----------
RATIOS = {  # 라벨: (가로, 세로) — None 이면 원본 유지
    "1:1 (인스타그램 피드 / 정방형)": (1, 1),
    "9:16 (인스타 리얼스 / 틱톡 / 유튜브 쇼츠)": (9, 16),
    "4:5 (인스타그램 세로 피드)": (4, 5),
    "16:9 (가로형 / X / 페이스북)": (16, 9),
    "원본 비율 유지": None,
}
FORMATS = {  # 확장자: (Pillow 포맷, MIME)
    "jpg": ("JPEG", "image/jpeg"), "jpeg": ("JPEG", "image/jpeg"),
    "png": ("PNG", "image/png"),   "webp": ("WEBP", "image/webp"),
}


def center_crop(img: Image.Image, ratio: tuple[int, int] | None) -> Image.Image:
    """목표 비율에서 가능한 가장 큰 영역을 이미지 중앙에서 잘라낸다."""
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


def encode(img: Image.Image, ext: str) -> bytes:
    fmt, _ = FORMATS[ext]
    if fmt == "JPEG" and img.mode != "RGB":  # JPEG 는 투명도(RGBA/P)를 저장할 수 없음
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format=fmt, **({"quality": 95} if fmt in ("JPEG", "WEBP") else {}))
    return buf.getvalue()


def mock_post(keywords: list[str]) -> dict:
    """Gemini 연동 전 레이아웃 확인용 Mock 게시글 — 해시태그는 정확히 5개."""
    topic = ", ".join(keywords) if keywords else "오늘의 순간"
    body = (f"{topic} 🌿\n\n"
            "바쁜 일상 속에서 잠시 멈춰 나만의 시간을 즐겨봤어요.\n"
            "작은 여유가 하루를 더 특별하게 만들어 주네요 ✨\n\n"
            "(※ Mock 데이터 — 실제 Gemini 연동 전 예시 문구입니다)")
    tags = []
    for t in [k.replace(" ", "") for k in keywords] + ["일상", "데일리", "소통", "오늘의기록", "인스타그램"]:
        tag = "#" + t.lstrip("#")
        if t and tag not in tags:
            tags.append(tag)
    return {"body": body, "hashtags": tags[:5]}


# ---------- 헤더 ----------
ds("SNS Assistant", "metric")
ds("이미지와 키워드로 SNS 게시글을 자동으로 작성합니다", "subtitle")
st.divider()

# ---------- 입력 영역 ----------
left, right = st.columns(2, gap="large")
with left:
    ds("1. 이미지 업로드", "title")
    files = st.file_uploader("이미지 선택 (여러 장 가능)", type=list(FORMATS),
                             accept_multiple_files=True)
with right:
    ds("2. 키워드 입력", "title")
    raw_kw = st.text_input("키워드 (쉼표로 구분)", placeholder="아메리카노, 감성 카페, 주말 여유")
    keywords = [k.strip() for k in raw_kw.split(",") if k.strip()]
    if keywords:
        ds("입력된 키워드: " + " · ".join(keywords), "label")

    ds("3. 이미지 비율", "title")
    ratio_label = st.radio("SNS 권장 비율", list(RATIOS), label_visibility="collapsed")

# ---------- 크롭 미리보기 + 다운로드 ----------
crops = []  # (파일명, 크롭 이미지, 확장자)
for f in files or []:
    try:
        img = ImageOps.exif_transpose(Image.open(f))   # 휴대폰 사진 회전 정보 반영
    except UnidentifiedImageError:
        st.error(f"❌ 이미지를 열 수 없습니다: {f.name}")
        continue
    ext = Path(f.name).suffix.lower().lstrip(".")
    crops.append((f.name, center_crop(img, RATIOS[ratio_label]), ext))

if crops:
    st.divider()
    ds(f"미리보기 · {ratio_label} · {len(crops)}장", "title")
    slug = ratio_label.split(" ")[0].replace(":", "x") if RATIOS[ratio_label] else "original"
    cols = st.columns(4)
    for i, (name, img, ext) in enumerate(crops):
        with cols[i % 4]:
            st.image(img, width="stretch")
            ds(f"{name} · {img.width}×{img.height}px", "label")
            st.download_button("⬇️ 다운로드", data=encode(img, ext),
                               file_name=f"{Path(name).stem}_{slug}.{ext}",
                               mime=FORMATS[ext][1], key=f"dl-{i}-{name}", width="stretch")

# ---------- 액션 영역 ----------
st.divider()
if st.button("게시글 생성하기", type="primary", disabled=not crops,
             help=None if crops else "이미지를 1장 이상 업로드하세요"):
    st.session_state["post"] = mock_post(keywords)

# ---------- 결과 출력 영역 ----------
post = st.session_state.get("post")
if post and crops:
    ds("생성 결과", "title")
    img_col, card_col = st.columns([1, 2], gap="large")
    with img_col:
        st.image(crops[0][1], width="stretch")
        if len(crops) > 1:
            ds(f"외 {len(crops) - 1}장", "label")
    with card_col:
        with st.container(border=True):
            ds("SNS 게시글", "title")
            ds(post["body"], "text")
            st.markdown(" ".join(f'<span class="ds-bold">{html.escape(t)}</span>'
                                 for t in post["hashtags"]), unsafe_allow_html=True)
            ds(f"해시태그 {len(post['hashtags'])}개 · Mock 데이터", "label")
