import json
import os

import dearpygui.dearpygui as dpg
from dearpygui_ext.themes import create_theme_imgui_dark, create_theme_imgui_light
from returns.result import Failure, Result, Success

from env import (
    CONFIG_PATH,
)
from errors import ConfigLoadError, ConfigSaveError


def load_config() -> dict:
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            raise ConfigLoadError("설정 파일을 불러오는 중 오류가 발생했습니다.", e)

    default_config = {
        "theme": "dark",
    }
    return default_config


cfg = load_config()


def save_config(data: dict) -> Result[str, Exception]:
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            return Success("설정 파일이 성공적으로 저장되었습니다.")
    except Exception as e:
        return Failure(
            ConfigSaveError("설정 파일을 저장하는 중 오류가 발생했습니다.", e)
        )


def toggle_theme(sender):
    if cfg["theme"] == "dark":
        dpg.bind_theme(create_theme_imgui_light())
        dpg.configure_item(sender, label="Dark")
        cfg["theme"] = "light"
    else:
        dpg.bind_theme(create_theme_imgui_dark())
        dpg.configure_item(sender, label="Light")
        cfg["theme"] = "dark"
