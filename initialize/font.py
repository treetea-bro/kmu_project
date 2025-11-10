# font.py
import urllib.request
from pathlib import Path

import dearpygui.dearpygui as dpg
from returns.result import Failure, Result, Success

from env import FONT_DIR, FONT_PATH, FONT_URL
from errors import FontApplyError, FontDownloadError


def download_korean_font(retry: int = 3) -> Result[str, Exception]:
    """한글 폰트를 확보 (이미 있으면 통과, 없으면 다운로드)"""
    Path(FONT_DIR).mkdir(parents=True, exist_ok=True)

    for _ in range(retry):
        try:
            if not Path(FONT_PATH).exists():
                urllib.request.urlretrieve(FONT_URL, FONT_PATH)
            return Success("한글 폰트 확보 완료")
        except Exception as e:
            last_error = e

    return Failure(FontDownloadError("한글 폰트 다운로드 실패", last_error))


def apply_korean_font(_: str) -> Result[str, Exception]:
    """DearPyGui에 한글 폰트를 적용"""
    try:
        with dpg.font_registry():
            with dpg.font(str(FONT_PATH), 16) as kor_font:
                dpg.add_font_range_hint(dpg.mvFontRangeHint_Korean)
            dpg.bind_font(kor_font)
        return Success("한글 폰트 적용 완료")
    except Exception as e:
        return Failure(FontApplyError("한글 폰트 적용 실패", e))


def ensure_korean_font() -> Result[str, Exception]:
    """DearPyGui에 한글 폰트를 적용"""
    return download_korean_font(3).bind(apply_korean_font)
