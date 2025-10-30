import dearpygui.dearpygui as dpg

from components.functions import refresh_function_list
from config import cfg, toggle_theme


def on_tab_change(sender, app_data, user_data):
    tag = dpg.get_item_alias(app_data)
    for content_tag in ["content_codegen", "content_query", "content_functions"]:
        dpg.configure_item(content_tag, show=False)
    if tag == "tab_functions":
        dpg.configure_item("log", show=False)
        refresh_function_list()
    else:
        dpg.configure_item("log", show=True)
    dpg.configure_item(f"content_{tag.split('_')[1]}", show=True)


def navbar_comp():
    with dpg.table(
        header_row=False, resizable=False, policy=dpg.mvTable_SizingStretchProp
    ):
        dpg.add_table_column(width_stretch=True)
        dpg.add_table_column(width_fixed=True)
        with dpg.table_row():
            with dpg.tab_bar(tag="top_tabbar", callback=on_tab_change):
                dpg.add_tab(label="프롬프트", tag="tab_query")
                dpg.add_tab(label="함수 생성", tag="tab_codegen")
                dpg.add_tab(label="함수 리스트", tag="tab_functions")

            initial_color = "어둡게" if cfg["theme"] == "light" else "밝게"
            dpg.add_button(
                label=initial_color,
                width=80,
                callback=toggle_theme,
            )
