# query.py
import importlib.util
import os
import subprocess
import sys
import threading

import dearpygui.dearpygui as dpg
import ollama

from utils.dpg_ui import log, show_alert
from utils.stt import stt


def load_tools():
    """tools.py를 안전하게 동적 import해서 TOOLS 리스트 반환"""
    tools_path = os.path.join(os.getcwd(), "tools.py")
    if not os.path.exists(tools_path):
        raise FileNotFoundError(f"tools.py 파일을 찾을 수 없습니다: {tools_path}")

    spec = importlib.util.spec_from_file_location("tools", tools_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"tools.py 모듈 로드 실패: {tools_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, "TOOLS", [])


def run_script_async(file_path: str):
    """별도 쓰레드에서 subprocess로 파이썬 스크립트 실행 (비블로킹)"""

    def _run():
        try:
            process = subprocess.Popen(
                [sys.executable, file_path],
                stdout=sys.stdout,
                stderr=sys.stderr,
                text=True,
                # start_new_session=True,
            )

            def read_output():
                _ = process.communicate()

            threading.Thread(target=read_output, daemon=True).start()

        except Exception as e:
            log(f"실행 오류: {e}")

    threading.Thread(target=_run, daemon=True).start()


def run_query(query_text: str):
    model_name = dpg.get_value("model_selector")

    if not query_text.strip():
        show_alert("입력 오류", "Query를 입력해주세요.")
        return

    log(f"선택된 모델: {model_name}")
    log(f"입력된 프롬프트: {query_text}")
    log("LLM Function-Calling 실행 중...")

    try:
        tools = load_tools()

        response = ollama.chat(
            model=model_name,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "당신은 절대로 자연어로 답변하지 말고 "
                        "반드시 제공된 함수 중 하나를 호출해야 합니다."
                    ),
                },
                {"role": "user", "content": query_text},
            ],
            tools=tools,
            think=False,
            keep_alive="1h",
        )

        message = response.get("message", {})
        toll_calls = message.get("tool_calls")
        if not toll_calls:
            log("⚠️ 함수 호출이 감지되지 않았습니다.")
            return

        log(toll_calls)
        for toll_call in toll_calls:
            fn_name = toll_call.function.name
            # args = toll_call.function.arguments
            file_path = os.path.join("functions", f"{fn_name}.py")

            if os.path.exists(file_path):
                log(f"{fn_name}.py 실행 시작")
                run_script_async(file_path)
            else:
                log(f"⚠️ 파일을 찾을 수 없습니다: {file_path}")

    except Exception as e:
        log(f"LLM 실행 중 오류 발생: {e}")


stt(run_query)


def query_comp():
    with dpg.group(tag="content_query", show=True):
        with dpg.group(horizontal=True):
            dpg.add_text("모델 선택:")
            dpg.add_combo(
                items=["qwen2.5:7b", "qwen3:4b", "qwen3:14b"],
                default_value="qwen2.5:7b",
                width=-1,
                tag="model_selector",
            )
        dpg.add_spacer(height=10)
        with dpg.group(horizontal=True):
            dpg.add_text("프롬프트:")
            dpg.add_input_text(
                tag="input_query", width=-1, on_enter=True, callback=run_query
            )
        dpg.add_spacer(height=10)
        dpg.add_button(
            label="실행",
            width=-1,
            height=40,
            callback=lambda: run_query(dpg.get_value("input_query")),
        )
