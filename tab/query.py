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
