import subprocess
import sys
from pathlib import Path

from returns.result import Failure, Result, Success

from errors import ChromiumInstallError


def get_playwright_cache_dir() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library/Caches/ms-playwright"
    elif sys.platform == "win32":
        return Path.home() / "AppData/Local/ms-playwright"
    else:
        return Path.home() / ".cache/ms-playwright"


def ensure_chromium_install() -> Result[str, Exception]:
    base = get_playwright_cache_dir()
    try:
        next(base.glob("chromium-*"))
    except Exception:
        try:
            subprocess.run(
                ["uv", "run", "playwright", "install", "chromium"], check=True
            )
            return Success("Chromium 설치 완료")
        except Exception as e:
            return Failure(ChromiumInstallError("Chromium 설치 중 오류 발생", e))
