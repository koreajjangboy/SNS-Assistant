"""링크 공유 미리보기용 메타 태그 — Streamlit 이 제공하는 index.html 을 패치한다.

카카오톡 등 링크 미리보기 크롤러는 JavaScript 를 실행하지 않고 HTML 원문의 <title> 과 Open Graph 태그만 읽는다.
Streamlit 의 index.html 에는 `<title>Streamlit</title>` 이 고정되어 있고 st.set_page_config() 로는 바뀌지 않으므로,
설치된 Streamlit 패키지의 index.html 을 직접 수정한다.

- 멱등: 추가한 태그는 표식 주석으로 감싸 두고, 다시 실행하면 그 블록만 교체한다. 내용이 같으면 파일을 쓰지 않는다.
- Streamlit 을 업그레이드하면 index.html 이 원래대로 돌아가므로, 앱을 실행할 때마다 확인한다.
- 파일을 쓸 수 없어도 앱 실행은 막지 않는다 (경고 로그만 남긴다).
"""
import html
import logging
import re
from functools import cache
from pathlib import Path

import streamlit

logger = logging.getLogger(__name__)

INDEX_HTML = Path(streamlit.__file__).parent / "static" / "index.html"
_BEGIN, _END = "<!-- sns-assistant:meta -->", "<!-- /sns-assistant:meta -->"
_BLOCK = re.compile(re.escape(_BEGIN) + r".*?" + re.escape(_END), re.DOTALL)
_TITLE = re.compile(r"<title>.*?</title>", re.DOTALL)


def _meta_block(title: str, description: str) -> str:
    t, d = html.escape(title, quote=True), html.escape(description, quote=True)
    return "".join((
        _BEGIN,
        f'<meta name="description" content="{d}" />',
        '<meta property="og:type" content="website" />',
        f'<meta property="og:site_name" content="{t}" />',
        f'<meta property="og:title" content="{t}" />',
        f'<meta property="og:description" content="{d}" />',
        '<meta name="twitter:card" content="summary" />',
        f'<meta name="twitter:title" content="{t}" />',
        f'<meta name="twitter:description" content="{d}" />',
        _END,
    ))


def patched_html(source: str, title: str, description: str) -> str:
    """index.html 원문에 제목과 메타 태그를 적용한 결과."""
    result = _TITLE.sub(f"<title>{html.escape(title)}</title>", source, count=1)
    block = _meta_block(title, description)
    if _BLOCK.search(result):
        return _BLOCK.sub(lambda _: block, result, count=1)
    return result.replace("</head>", block + "</head>", 1)


@cache
def ensure_index_meta(title: str, description: str) -> bool:
    """index.html 이 원하는 메타 태그를 갖도록 한다 (프로세스당 1회). 변경했으면 True."""
    try:
        source = INDEX_HTML.read_text(encoding="utf-8")
        updated = patched_html(source, title, description)
        if updated == source:
            return False
        INDEX_HTML.write_text(updated, encoding="utf-8")
    except OSError as e:
        logger.warning("링크 미리보기 메타 태그를 적용하지 못했습니다 (%s): %s", INDEX_HTML, e)
        return False
    logger.info("index.html 에 링크 미리보기 메타 태그를 적용했습니다: %s", INDEX_HTML)
    return True
