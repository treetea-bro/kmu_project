from pathlib import Path

import dearpygui.dearpygui as dpg
from dearpygui_ext.themes import create_theme_imgui_dark, create_theme_imgui_light
from returns.result import Failure

from config import cfg
from env import (
    APP_TITLE,
    FUNCTIONS_DIR,
    TOOLS_DIR,
    TOOLS_PATH,
    VIEWPORT_HEIGHT,
    VIEWPORT_WIDTH,
)
from initialize.font import ensure_korean_font


def ensure_functions():
    Path(FUNCTIONS_DIR).mkdir(parents=True, exist_ok=True)


def ensure_tools():
    Path(TOOLS_DIR).mkdir(parents=True, exist_ok=True)
    if not TOOLS_PATH.exists():
        with open(TOOLS_PATH, "w", encoding="utf-8") as f:
            f.write("# AUTO-GENERATED TOOL DEFINITIONS\nTOOLS = []\n")


def init_theme():
    if cfg["theme"] == "light":
        dpg.bind_theme(create_theme_imgui_light())
    else:
        dpg.bind_theme(create_theme_imgui_dark())


def initialize():
    dpg.create_context()
    dpg.create_viewport(title=APP_TITLE, width=VIEWPORT_WIDTH, height=VIEWPORT_HEIGHT)
    ensure_functions()
    ensure_tools()
    match ensure_korean_font():
        case Failure(e):
            raise e

    init_theme()
