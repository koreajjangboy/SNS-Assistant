"""SNS Assistant — Streamlit UI.

실행:
    streamlit run main.py --server.port 8501 --server.address 0.0.0.0
    python main.py            # 위 명령과 동일 (VS Code 'Run Python File' 용)
"""
import html
import json
import logging
import subprocess
import sys
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass

import streamlit as st
import streamlit.components.v1 as components

import config
import gemini_service
import image_service
import page_meta
from gemini_service import GeminiServiceError, GenerationResult

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

# ============================================================
# 디자인 토큰 — docs/design-system.md
# 폰트·Primary·테두리·모서리 기본값은 .streamlit/config.toml 테마에서 적용하고,
# 테마로 표현할 수 없는 값만 아래 CSS 로 적용한다.
# ============================================================
TEXT_COLORS = {  # 강조 / 보조 / 본문
    "light": {"strong": "#374151", "muted": "#9CA3AF", "body": "#6B7280"},
    "dark": {"strong": "#E5E7EB", "muted": "#4B5563", "body": "#6B7280"},
}
TEXT_STYLES = {  # 스타일: (크기px, 굵기, 줄 높이, 색상 역할)
    "metric": (30, 600, "normal", "strong"),
    "title": (18, 500, "28px", "strong"),
    "subtitle": (16, 500, "normal", "muted"),
    "text": (14, 400, "20px", "body"),
    "bold": (14, 700, "normal", "body"),
    "label": (12, 400, "normal", "body"),
}
TOKENS = {  # 모드 공통
    "primary": "#3B82F6",
    "primary-disabled": "#60A5FA",
    "on-primary": "#FFFFFF",
    "shadow-input": "0 1px 2px 0 rgb(0 0 0 / 0.05)",
    "shadow-card": "0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)",
    "shadow-dropdown": "0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)",
}
SURFACE_TOKENS = {  # 라이트 모드 전용 — 컴포넌트의 다크 모드 색상은 Figma 에 없어 Streamlit 기본값을 쓴다
    "surface": "#FFFFFF",
    "surface-muted": "#F9FAFB",
    "surface-disabled": "#F3F4F6",
    "border": "#E5E7EB",
    "border-placeholder": "#9CA3AF",
    "divider": "#F3F4F6",
    "text-strong": "#374151",
    "text-body": "#6B7280",
    "text-disabled": "#9CA3AF",
}

# Streamlit 내부 클래스(st-emotion-cache-*) 대신 data-testid 와 key 로 붙는 st-key-* 클래스만 사용한다.
BUTTONS = ':is([data-testid="stButton"], [data-testid="stDownloadButton"]) button'
FIELDS = ('[data-testid="stTextInputRootElement"], [data-testid="stTextAreaRootElement"], '
          '[data-testid="stSelectbox"] [data-baseweb="select"] > div')
CARD = '[class*="st-key-ds-card"]'

BASE_CSS = f"""
/* ---------- 레이아웃 ---------- */
[data-testid="stMainBlockContainer"] {{ max-width: 1200px; padding: 64px 24px 48px; }}   /* 상단은 Streamlit 툴바 높이 확보 */
hr {{ margin: 24px 0; }}
.ds-header {{ display: flex; flex-direction: column; gap: 4px; margin-bottom: 8px; }}
.ds-card-header {{ display: flex; flex-direction: column; }}
.ds-hashtags {{ display: flex; flex-wrap: wrap; gap: 6px 12px; }}
/* Markdown 요소는 아래 여백을 당겨 쓰므로, 버튼과 붙지 않도록 아래 여백을 준다 */
.ds-tip {{ padding: 8px 12px; border-radius: 8px; border: 1px solid transparent; margin-bottom: 16px; }}
.ds-tip-label {{ font-weight: 500; margin-right: 6px; }}

/* ---------- 버튼 (st.button / st.download_button) ---------- */
{BUTTONS} {{
    min-height: 36px; padding: 8px 16px; border-radius: 8px; border: 1px solid var(--ds-primary);
    box-shadow: var(--ds-shadow-input); transition: box-shadow .15s ease, background-color .15s ease;
}}
{BUTTONS} p {{ font-size: 14px; font-weight: 500; line-height: 20px; }}
{BUTTONS}[data-testid="stBaseButton-primary"],
{BUTTONS}[data-testid="stBaseButton-primary"]:is(:hover, :active, :focus) {{
    background: var(--ds-primary); border-color: var(--ds-primary); color: var(--ds-on-primary);
}}
{BUTTONS}[data-testid="stBaseButton-secondary"],
{BUTTONS}[data-testid="stBaseButton-secondary"]:is(:hover, :active, :focus) {{
    background: transparent; border-color: var(--ds-primary); color: var(--ds-primary);
}}
{BUTTONS}:hover:not(:disabled) {{ box-shadow: var(--ds-shadow-card); }}
{BUTTONS}:active:not(:disabled) {{ box-shadow: none; }}
{BUTTONS}:disabled {{ opacity: 1; cursor: not-allowed; }}
{BUTTONS}[data-testid="stBaseButton-primary"]:disabled {{
    background: var(--ds-primary-disabled); border-color: var(--ds-primary-disabled); color: var(--ds-on-primary);
}}
{BUTTONS}[data-testid="stBaseButton-secondary"]:disabled {{
    background: transparent; border-color: var(--ds-primary-disabled); color: var(--ds-primary-disabled);
}}

/* ---------- 입력창 / 셀렉트 ---------- */
:is({FIELDS}) {{ border-radius: 8px; box-shadow: var(--ds-shadow-input); transition: border-color .15s ease; }}
[data-testid="stSelectbox"] [data-baseweb="select"] > div {{ border-radius: 6px; }}
:is({FIELDS}):focus-within {{ border-color: var(--ds-primary); }}
:is([data-testid="stTextInputRootElement"] input, [data-testid="stTextAreaRootElement"] textarea) {{
    padding: 8px 12px; font-size: 14px; line-height: 20px;
}}
[data-baseweb="popover"] [role="listbox"] {{ border-radius: 6px; box-shadow: var(--ds-shadow-dropdown); }}
[data-baseweb="popover"] [role="option"] {{ padding: 10px 12px; }}

/* ---------- 파일 업로더 ---------- */
[data-testid="stFileUploaderDropzone"] {{
    padding: 24px; border: 1px dashed; border-radius: 8px; transition: border-color .15s ease;
}}
[data-testid="stFileUploaderDropzone"]:is(:hover, :focus-within) {{ border-color: var(--ds-primary); }}

/* ---------- 카드 (st.container(key="ds-card-…")) ---------- */
{CARD} {{ padding: 24px; border-radius: 8px; box-shadow: var(--ds-shadow-card); gap: 16px; }}

/* ---------- 좁은 화면 ---------- */
@media (max-width: 640px) {{
    [data-testid="stMainBlockContainer"] {{ padding: 64px 16px 24px; }}
    {CARD} {{ padding: 16px; }}
    /* 세로로 쌓인 미리보기 그리드의 빈 칸이 여백을 차지하지 않도록 */
    [data-testid="stColumn"]:not(:has([data-testid="stElementContainer"])) {{ display: none; }}
}}
"""

LIGHT_CSS = f"""
{BUTTONS}[data-testid="stBaseButton-secondary"]:hover:not(:disabled) {{ background: var(--ds-surface-muted); }}
:is({FIELDS}) {{ background: var(--ds-surface); border-color: var(--ds-border); }}
:is({FIELDS}) > div {{ background: transparent; }}
:is([data-testid="stTextInputRootElement"] input, [data-testid="stTextAreaRootElement"] textarea) {{
    color: var(--ds-text-strong);
}}
:is([data-testid="stTextInputRootElement"] input, [data-testid="stTextAreaRootElement"] textarea)::placeholder {{
    color: var(--ds-text-body); opacity: 1;
}}
:is([data-testid="stTextInputRootElement"], [data-testid="stTextAreaRootElement"]):has(:disabled) {{
    background: var(--ds-surface-disabled);
}}
:is([data-testid="stTextInputRootElement"] input, [data-testid="stTextAreaRootElement"] textarea):disabled {{
    color: var(--ds-text-disabled); -webkit-text-fill-color: var(--ds-text-disabled);
}}
[data-baseweb="popover"] [role="listbox"] {{ background: var(--ds-surface); border: 1px solid var(--ds-border); }}
[data-testid="stFileUploaderDropzone"] {{ background: var(--ds-surface-muted); border-color: var(--ds-border-placeholder); }}
.ds-tip {{ background: var(--ds-surface-muted); border-color: var(--ds-border); }}
.ds-tip-label {{ color: var(--ds-text-strong); }}
{CARD} {{ background: var(--ds-surface); border-color: var(--ds-border); }}
hr {{ border-color: var(--ds-divider); }}
"""


def _vars(tokens: dict[str, str]) -> str:
    return " ".join(f"--ds-{name}: {value};" for name, value in tokens.items())


def inject_styles() -> None:
    mode = "dark" if st.context.theme.type == "dark" else "light"
    colors = TEXT_COLORS[mode]
    # stMarkdownContainer 로 한정 — Streamlit 의 `… p {font-size: inherit}` 규칙보다 우선하도록
    text_css = "\n".join(
        f'[data-testid="stMarkdownContainer"] .ds-{name} {{ font-size: {size}px; font-weight: {weight}; '
        f"line-height: {lh}; letter-spacing: 0; color: {colors[role]}; margin: 0; white-space: pre-wrap; }}"
        for name, (size, weight, lh, role) in TEXT_STYLES.items()
    )
    tokens = TOKENS | (SURFACE_TOKENS if mode == "light" else {})
    css = f":root {{ {_vars(tokens)} }}\n{text_css}\n{BASE_CSS}\n{LIGHT_CSS if mode == 'light' else ''}"
    st.html(f"<style>{css}</style>")


def ds(text: str, style: str) -> None:
    """디자인 시스템 텍스트 스타일로 출력."""
    st.markdown(f'<p class="ds-{style}">{html.escape(text)}</p>', unsafe_allow_html=True)


@contextmanager
def card(key: str, title: str, subtitle: str | None = None) -> Generator[None]:
    """Figma `Card + Title` — 제목(Title) + 부제(Text), 헤더–본문 16px."""
    with st.container(border=True, key=f"ds-card-{key}"):
        sub = f'<p class="ds-text">{html.escape(subtitle)}</p>' if subtitle else ""
        st.markdown(f'<div class="ds-card-header"><p class="ds-title">{html.escape(title)}</p>{sub}</div>',
                    unsafe_allow_html=True)
        yield


# 게시글 작성 규칙 안내 (gemini_service.SYSTEM_INSTRUCTION 의 이모지 금지·격식체 규칙과 맞춘다)
TONE_TIP = ("게시글은 이모지 없이, 정중한 격식체(~습니다)로 10문장 전후의 적절한 분량으로 작성돼요. "
            "'안녕하세요 여러분' 같은 상투적인 인사나 광고 문구도 넣지 않아요.")
RESULT_NOTE = "이모지 없이 정중한 격식체로 쓴 초안이에요."
LOADING_MESSAGE = "🚀 AI가 SNS 게시글을 생성 중입니다. 잠시만 기다려주세요..."
DONE_MESSAGE = "🎉 게시글 생성이 완료되었습니다!"

# ============================================================
# 복사 버튼 — st.markdown 은 스크립트를 실행하지 않으므로 components.html(iframe)로 만든다.
# iframe 안에서는 페이지 CSS 가 적용되지 않아 Figma Secondary 버튼 스타일을 여기서 다시 정의한다.
# ============================================================
COPY_LABEL = "게시글 복사하기"
COPIED_LABEL = "✅ 복사 완료!"
COPY_FAILED_LABEL = "복사하지 못했어요. 본문을 직접 선택해 복사해 주세요"
COPY_FEEDBACK_MS = 2000
COPY_FRAME_HEIGHT = 52     # 모바일 버튼(44px) + 그림자 여백
_COPY_ICON = ('<svg viewBox="0 -960 960 960" aria-hidden="true"><path d="M360-240q-33 0-56.5-23.5T280-320v-480q0-33 '
              '23.5-56.5T360-880h360q33 0 56.5 23.5T800-800v480q0 33-23.5 56.5T720-240H360Zm0-80h360v-480H360v480ZM200-80'
              'q-33 0-56.5-23.5T120-160v-560h80v560h440v80H200Z"/></svg>')
_COPY_HTML = """<!doctype html>
<html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@500&display=swap" rel="stylesheet">
<style>
  html, body { margin: 0; padding: 2px 3px 6px 1px; background: transparent; }   /* 그림자가 잘리지 않을 만큼만 */
  button {
    display: inline-flex; align-items: center; justify-content: center; gap: 6px; box-sizing: border-box;
    min-height: 36px; padding: 8px 16px; border: 1px solid __PRIMARY__; border-radius: 8px;
    background: transparent; color: __PRIMARY__; font: 500 14px/20px Inter, "Source Sans", sans-serif;
    box-shadow: __SHADOW_INPUT__; cursor: pointer; -webkit-tap-highlight-color: transparent;
    transition: box-shadow .15s ease, background-color .15s ease;
  }
  button:hover { box-shadow: __SHADOW_CARD__; background: __HOVER_BG__; }
  button:active { box-shadow: none; }
  button:focus-visible { outline: 2px solid __PRIMARY__; outline-offset: 2px; }
  svg { width: 18px; height: 18px; fill: currentColor; flex: none; }
  button.done svg { display: none; }   /* '✅ 복사 완료!' 와 아이콘이 겹치지 않도록 */
  /* 좁은 화면(모바일): 터치하기 쉽도록 전체 너비·44px 높이 */
  @media (max-width: 480px) { button { width: 100%; min-height: 44px; } }
</style></head>
<body>
<button id="copy" type="button">__ICON__<span aria-live="polite">__LABEL__</span></button>
<script>
  const text = __TEXT__, labels = __LABELS__;
  const button = document.getElementById("copy"), label = button.querySelector("span");
  // http 로 LAN 주소에 접속하면(비보안 컨텍스트) navigator.clipboard 가 없으므로 execCommand 로 대체한다
  function legacyCopy() {
    const area = document.createElement("textarea");
    area.value = text;
    area.setAttribute("readonly", "");
    area.style.cssText = "position:fixed;top:0;left:0;opacity:0";
    document.body.appendChild(area);
    area.select();
    area.setSelectionRange(0, text.length);
    const ok = document.execCommand("copy");
    area.remove();
    return ok;
  }
  let timer;
  button.addEventListener("click", async () => {
    let ok;
    try { await navigator.clipboard.writeText(text); ok = true; } catch { ok = legacyCopy(); }
    label.textContent = ok ? labels.copied : labels.failed;
    button.classList.add("done");
    clearTimeout(timer);
    timer = setTimeout(() => { label.textContent = labels.idle; button.classList.remove("done"); }, __FEEDBACK_MS__);
  });
</script>
</body></html>"""


def post_text(post: gemini_service.SnsPost) -> str:
    """SNS 에 그대로 붙여 넣을 수 있는 형태 — 본문, 빈 줄, 해시태그."""
    return f"{post.body}\n\n{' '.join(post.hashtags)}"


def copy_button(text: str) -> None:
    """클릭하면 text 를 클립보드에 복사하고 잠시 '복사 완료' 로 바뀌는 버튼."""
    light = st.context.theme.type != "dark"
    replacements = {
        "__PRIMARY__": TOKENS["primary"],
        "__SHADOW_INPUT__": TOKENS["shadow-input"],
        "__SHADOW_CARD__": TOKENS["shadow-card"],
        "__HOVER_BG__": SURFACE_TOKENS["surface-muted"] if light else "transparent",
        "__ICON__": _COPY_ICON,
        "__LABEL__": html.escape(COPY_LABEL),
        "__FEEDBACK_MS__": str(COPY_FEEDBACK_MS),
        # JS 문자열로 안전하게 넣는다 ("</script>" 로 스크립트가 끊기지 않도록 "</" 도 이스케이프)
        "__LABELS__": json.dumps({"idle": COPY_LABEL, "copied": COPIED_LABEL, "failed": COPY_FAILED_LABEL},
                                 ensure_ascii=False).replace("</", "<\\/"),
        "__TEXT__": json.dumps(text, ensure_ascii=False).replace("</", "<\\/"),
    }
    page = _COPY_HTML
    for placeholder, value in replacements.items():
        page = page.replace(placeholder, value)
    components.html(page, height=COPY_FRAME_HEIGHT)


# ============================================================
# 이미지
# ============================================================
@dataclass(frozen=True)
class Crop:
    name: str
    ext: str
    data: bytes              # 다운로드용 인코딩 바이트
    size: tuple[int, int]


@st.cache_data(show_spinner=False, max_entries=128)
def crop_upload(data: bytes, ext: str, ratio: tuple[int, int] | None) -> tuple[bytes, tuple[int, int]]:
    """업로드 이미지를 크롭·인코딩한다. 같은 파일·비율 조합은 재실행 시 캐시를 쓴다."""
    cropped = image_service.center_crop(image_service.load_image(data), ratio)
    return image_service.encode(cropped, ext), cropped.size


def collect_crops(files, ratio: config.AspectRatio) -> list[Crop]:
    crops = []
    for f in files:
        try:
            ext = image_service.extension(f.name)
            data, size = crop_upload(f.getvalue(), ext, ratio.size)
        except image_service.ImageLoadError as e:
            st.error(f"{f.name} — {e}")
            continue
        crops.append(Crop(f.name, ext, data, size))
    return crops


# ============================================================
# 화면 구성
# ============================================================
def render_inputs() -> tuple[list, list[str], config.AspectRatio]:
    left, right = st.columns(2, gap="medium")
    with left, card("upload", "이미지 업로드", "JPG · PNG · WEBP 사진을 여러 장 한 번에 올릴 수 있어요"):
        files = st.file_uploader("이미지 선택", type=list(config.UPLOAD_TYPES),
                                 accept_multiple_files=True, label_visibility="collapsed")
    with right, card("options", "키워드 · 비율", "키워드는 쉼표로 구분하고, 올릴 곳에 맞는 비율을 골라 주세요"):
        raw_keywords = st.text_input("키워드", placeholder="아메리카노, 감성 카페, 주말 여유")
        keywords = [k.strip() for k in raw_keywords.split(",") if k.strip()]
        ratio = st.radio("이미지 비율", config.ASPECT_RATIOS, format_func=lambda r: r.label)
    return files or [], keywords, ratio


def render_previews(crops: list[Crop], ratio: config.AspectRatio) -> None:
    with card("preview", "미리보기", f"{ratio.label} · {len(crops)}장 · 가운데를 기준으로 잘랐어요. 사진마다 따로 내려받을 수 있어요"):
        cols = st.columns(4, gap="medium")
        for i, crop in enumerate(crops):
            with cols[i % 4]:
                st.image(crop.data, width="stretch")
                ds(f"{crop.name} · {crop.size[0]}×{crop.size[1]}px", "label")
                st.download_button(
                    "다운로드", data=crop.data, icon=":material/download:",
                    file_name=image_service.output_filename(crop.name, ratio.slug),
                    mime=image_service.mime_type(crop.ext), key=f"dl-{i}-{crop.name}", width="stretch",
                )


def start_generation() -> None:
    """버튼 on_click — 다음 실행에서 버튼을 '생성 중' 상태로 바꾸고 생성을 시작하도록 표시한다."""
    st.session_state["generating"] = True


def generate(crops: list[Crop], keywords: list[str]) -> tuple[GenerationResult | None, str | None]:
    """스피너와 진행 안내(재시도·대체 모델 전환)를 보여 주며 게시글을 생성한다. 반환: (결과, 오류 문구)."""
    images = [
        image_service.to_model_jpeg(image_service.load_image(c.data), config.MODEL_IMAGE_MAX_SIDE)
        for c in crops[: config.MODEL_MAX_IMAGES]
    ]
    loading = st.empty()   # 생성이 끝나면 스피너와 진행 안내를 한 번에 지운다
    try:
        with loading.container(), st.spinner(LOADING_MESSAGE, show_time=True):
            progress = st.empty()
            return gemini_service.generate_post(images, keywords, on_status=progress.caption), None
    except GeminiServiceError as e:
        return None, str(e)
    finally:
        loading.empty()


def render_result(result: GenerationResult, crops: list[Crop], stale: bool) -> None:
    post = result.post
    if stale:
        st.info("입력이 바뀌었어요. 바뀐 내용으로 다시 쓰려면 '게시글 생성하기'를 눌러 주세요.")
    with card("result", "SNS 게시글", f"해시태그 {len(post.hashtags)}개 · 그대로 복사해서 쓰거나 내 말투로 조금 다듬어 올려 보세요"):
        img_col, text_col = st.columns([1, 2], gap="medium")
        with img_col:
            st.image(crops[0].data, width="stretch")
            if len(crops) > 1:
                ds(f"외 {len(crops) - 1}장", "label")
        with text_col:
            ds(post.body, "text")
            tags = "".join(f'<span class="ds-bold">{html.escape(t)}</span>' for t in post.hashtags)
            st.markdown(f'<div class="ds-hashtags">{tags}</div>', unsafe_allow_html=True)
            copy_button(post_text(post))
            ds(RESULT_NOTE, "label")


def render() -> None:
    # 첫 Streamlit 명령이어야 한다 — 브라우저 탭 제목·파비콘
    st.set_page_config(page_title=config.APP_TITLE, page_icon="✨", layout="wide")
    inject_styles()

    st.markdown(f'<div class="ds-header"><p class="ds-metric">{html.escape(config.APP_TITLE)}</p>'
                f'<p class="ds-subtitle">{html.escape(config.APP_DESCRIPTION)}</p></div>',
                unsafe_allow_html=True)
    if not config.GEMINI_API_KEY:
        st.warning("GEMINI_API_KEY가 설정되지 않아 게시글을 만들 수 없어요. .env 파일에 키를 넣고 앱을 다시 시작해 주세요.")

    files, keywords, ratio = render_inputs()
    crops = collect_crops(files, ratio)
    if crops:
        render_previews(crops, ratio)

    if len(crops) > config.MODEL_MAX_IMAGES:
        ds(f"게시글에는 앞의 {config.MODEL_MAX_IMAGES}장만 반영돼요.", "label")
    signature = (tuple(f.file_id for f in files), ratio.slug, tuple(keywords))
    st.markdown(f'<div class="ds-tip"><p class="ds-text"><span class="ds-tip-label">Tip</span>'
                f'{html.escape(TONE_TIP)}</p></div>', unsafe_allow_html=True)
    # 클릭 즉시 버튼이 '생성 중' 비활성 상태로 바뀌어 눌렸음을 알 수 있고, 중복 요청도 막는다
    generating = st.session_state.get("generating", False)
    st.button("게시글 생성 중…" if generating else "게시글 생성하기", key="generate",
              type="primary", icon=":material/auto_awesome:", on_click=start_generation,
              disabled=generating or not crops or not config.GEMINI_API_KEY,
              help=None if crops else "사진을 1장 이상 올려 주세요")
    if generating:
        st.session_state["generating"] = False   # 생성 중 입력이 바뀌어 중단돼도 버튼이 다시 활성화되도록 먼저 해제
        result, error = generate(crops, keywords)
        if result:
            st.session_state.update(result=result, result_signature=signature, notice=DONE_MESSAGE)
        else:
            st.session_state["notice_error"] = error
        st.rerun()   # 버튼을 다시 활성 상태로 그리고 완료/오류 메시지를 표시

    if notice := st.session_state.pop("notice", None):
        st.success(notice)
    if error := st.session_state.pop("notice_error", None):
        st.error(error)

    result = st.session_state.get("result")
    if result and crops:
        render_result(result, crops, stale=st.session_state.get("result_signature") != signature)


def launch() -> int:
    """`python main.py` 로 실행했을 때 Streamlit 서버를 띄운다."""
    page_meta.ensure_index_meta(config.APP_TITLE, config.APP_DESCRIPTION)   # 서버 시작 전에 적용
    return subprocess.call([
        sys.executable, "-m", "streamlit", "run", __file__,
        "--server.port", str(config.SERVER_PORT), "--server.address", config.SERVER_ADDRESS,
    ])


if __name__ == "__main__":
    from streamlit import runtime

    if runtime.exists():
        # `streamlit run main.py` 로 직접 실행한 경우 — 첫 실행 때 적용 (프로세스당 1회)
        page_meta.ensure_index_meta(config.APP_TITLE, config.APP_DESCRIPTION)
        render()
    else:
        sys.exit(launch())
