import sys
from pathlib import Path


def get_playwright_cache_dir() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library/Caches/ms-playwright"
    elif sys.platform == "win32":
        return Path.home() / "AppData/Local/ms-playwright"
    else:
        return Path.home() / ".cache/ms-playwright"


print(get_playwright_cache_dir())
