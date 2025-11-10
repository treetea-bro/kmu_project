# app.py
import dearpygui.dearpygui as dpg
from returns.result import Failure

from components.codegen import codegen_comp
from components.functions import functions_comp
from components.log import log_comp
from components.nav_bar import navbar_comp
from components.query import query_comp
from finalize import finalize
from initialize import initialize
from playwright_install import ensure_chromium_install
from utils.dpg_ui import log


def main_window():
    with dpg.window(tag="main_window"):
        navbar_comp()
        dpg.add_spacer(height=8)
        query_comp()
        codegen_comp()
        functions_comp()

        dpg.add_spacer(height=8)

        log_comp()


def post_ui_setup():
    match ensure_chromium_install():
        case Failure(e):
            log(str(e))


def main():
    initialize()
    main_window()
    post_ui_setup()
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.set_primary_window("main_window", True)
    dpg.start_dearpygui()

    finalize()


if __name__ == "__main__":
    main()
