from pathlib import Path

APP_TITLE = "Function Generation to Action Execution"
VIEWPORT_WIDTH = 800
VIEWPORT_HEIGHT = 600
DEFAULT_URL = "https://naver.com"

APP_DIR = Path(__file__).parent

FONT_DIR = APP_DIR / "fonts"
FONT_PATH = FONT_DIR / "NanumGothic.ttf"
FONT_URL = "https://fonts.gstatic.com/ea/nanumgothic/v5/NanumGothic-Regular.ttf"

CONFIG_DIR = APP_DIR
CONFIG_PATH = CONFIG_DIR / "config.json"

FUNCTIONS_DIR = APP_DIR / "functions"

AUDIOS_DIR = APP_DIR / "audios"

TOOLS_DIR = APP_DIR
TOOLS_PATH = TOOLS_DIR / "tools.py"
