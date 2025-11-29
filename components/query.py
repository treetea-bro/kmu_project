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
        return []

    try:
        spec = importlib.util.spec_from_file_location("tools", tools_path)
        if spec is None or spec.loader is None:
            return []

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return getattr(module, "TOOLS", [])
    except Exception as e:
        log(f"tools.py 로드 중 오류: {e}")
        return []


def run_script(file_path: str, args: dict):
    """
    별도 쓰레드에서 subprocess로 파이썬 스크립트 실행
    args 딕셔너리가 있으면 --key value 형태로 변환하여 전달
    """

    def _run():
        try:
            cmd = [sys.executable, file_path]

            if args:
                for key, value in args.items():
                    cmd.append(f"--{key}")
                    cmd.append(str(value))

            log(f"명령어 실행: {' '.join(cmd)}")

            process = subprocess.Popen(
                cmd,
                stdout=sys.stdout,
                stderr=sys.stderr,
                text=True,
                encoding="utf-8",
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
        show_alert("입력 오류", "프롬프트를 입력해주세요.")
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
                        "당신은 사용자의 요청을 수행하기 위해 적절한 함수를 선택하고 "
                        "필요한 매개변수(parameter)를 정확히 추출하여 호출해야 합니다."
                    ),
                },
                {"role": "user", "content": query_text},
            ],
            tools=tools,
        )

        message = response.get("message", {})
        tool_calls = message.get("tool_calls")

        if not tool_calls:
            log(f"LLM 응답: {message.get('content', '')}")
            log("⚠️ 함수 호출이 감지되지 않았습니다.")
            return

        for tool_call in tool_calls:
            fn_name = tool_call.function.name
            arguments = tool_call.function.arguments  # Dict 형태

            log(f"함수 호출 감지: {fn_name}")
            log(f"인자: {arguments}")

            file_path = os.path.join("functions", f"{fn_name}.py")

            if os.path.exists(file_path):
                run_script(file_path, arguments)
            else:
                log(f"⚠️ 실행 파일을 찾을 수 없습니다: {file_path}")

    except Exception as e:
        log(f"LLM 실행 중 오류 발생: {e}")


stt(run_query)


def query_comp():
    with dpg.group(tag="content_query", show=True):
        with dpg.group(horizontal=True):
            dpg.add_text("모델 선택:")
            dpg.add_combo(
                items=[
                    "qwen2.5:7b",
                    "qwen2.5-coder:7b",
                    "llama3.1:8b",
                ],
                default_value="qwen2.5:7b",
                width=-1,
                tag="model_selector",
            )
        dpg.add_spacer(height=10)
        with dpg.group(horizontal=True):
            dpg.add_text("프롬프트:")
            dpg.add_input_text(
                tag="input_query",
                width=-1,
                on_enter=True,
                callback=lambda: run_query(dpg.get_value("input_query")),
            )
        dpg.add_spacer(height=10)
        dpg.add_button(
            label="실행",
            width=-1,
            height=40,
            callback=lambda: run_query(dpg.get_value("input_query")),
        )
