import dearpygui.dearpygui as dpg

from config import cfg, save_config


def finalize():
    dpg.destroy_context()
    save_config(cfg)
