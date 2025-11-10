import platform

import dearpygui.dearpygui as dpg

from utils.dpg_ui import log


def log_comp():
    with dpg.group(tag="log", show=True):
        dpg.add_text("실행 로그")
        dpg.add_child_window(tag="log_scroll")
        with dpg.group(tag="log_group", parent="log_scroll"):
            log(f"OS: {platform.system()}")
            log(f"Python: {platform.python_version()}")
