import dearpygui.dearpygui as dpg

from utils import log, show_alert


def run_query():
    query_text = dpg.get_value("input_query")
    model_name = dpg.get_value("model_selector")
    if not query_text.strip():
        show_alert("입력 오류", "Query를 입력해주세요.")
        return
    log(f"선택된 모델: {model_name}")
    log(f"입력된 Query: {query_text}")
    log("실행되었습니다.")


def query_comp():
    with dpg.group(tag="content_query", show=False):
        with dpg.group(horizontal=True):
            dpg.add_text("모델 선택:")
            dpg.add_combo(
                items=["llama4:16x17b", "mistral-small3.2:24b"],
                default_value="llama4:16x17b",
                width=-1,
                tag="model_selector",
            )
        dpg.add_spacer(height=10)
        with dpg.group(horizontal=True):
            dpg.add_text("Query:")
            dpg.add_input_text(
                tag="input_query", width=-1, on_enter=True, callback=run_query
            )
        dpg.add_spacer(height=10)
        dpg.add_button(label="실행", width=-1, height=40, callback=run_query)
