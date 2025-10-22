import urllib.request
from pathlib import Path

import dearpygui.dearpygui as dpg
from returns.pipeline import pipe
from returns.result import Failure, Result, Success

from env import FONT_DIR, FONT_PATH, FONT_URL
from errors import FontApplyError, FontDownloadError


def ensure_korean_font(retry=3) -> Result[str, Exception]:
    Path(FONT_DIR).mkdir(parents=True, exist_ok=True)
    error = None
    for _ in range(retry):
        try:
            if not Path(FONT_PATH).exists():
                urllib.request.urlretrieve(FONT_URL, FONT_PATH)
            return Success("한글 폰트 확보 완료")
        except Exception as e:
            error = e
    return Failure(FontDownloadError("한글 폰트 다운로드 실패", error))


def apply_korean_font() -> Result[str, Exception]:
    def _apply_korean_font(result) -> Result[str, Exception]:
        match result:
            case Failure(e):
                return Failure(e)
        try:
            with dpg.font_registry():
                with dpg.font(str(FONT_PATH), 16) as kor_font:
                    dpg.add_font_range_hint(dpg.mvFontRangeHint_Korean)
                dpg.bind_font(kor_font)
                return Success("한글 폰트 적용 완료")
        except Exception as e:
            return Failure(FontApplyError("한글 폰트 적용 실패", e))

    return pipe(ensure_korean_font, _apply_korean_font)(3)
