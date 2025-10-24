import json
import os
import subprocess
import sys

import dearpygui.dearpygui as dpg

from env import (
    DEFAULT_URL,
    FUNCTIONS_DIR,
    TOOLS_PATH,
)
from utils import log, show_alert


def _get_description_for_function(filename: str) -> str:
    """각 함수 파일 내 첫 번째 주석 줄을 description으로 사용"""
    file_path = os.path.join(FUNCTIONS_DIR, filename)
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            first_line = f.readline().strip()
            if first_line.startswith("#"):
                return first_line.lstrip("#").strip()
    except Exception:
        pass
    return "No description"


def update_tools_py():
    """functions 폴더 내 파일 기준으로 TOOLS.py 재작성"""

    tools = []
    for file in os.listdir(FUNCTIONS_DIR):
        if file.endswith(".py") and file != "tools.py":
            name = file[:-3]
            desc = _get_description_for_function(file)
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": desc,
                        "parameters": {},
                    },
                }
            )

    with open(TOOLS_PATH, "w", encoding="utf-8") as f:
        f.write("# AUTO-GENERATED TOOL DEFINITIONS\n")
        f.write("TOOLS = ")
        json_str = json.dumps(tools, indent=4, ensure_ascii=False)
        # Python dict literal로 변환
        f.write(
            json_str.replace("true", "True")
            .replace("false", "False")
            .replace("null", "None")
        )
        f.write("\n")

    log(f"tools.py 갱신 완료 (total {len(tools)}개 함수)")


def show_save_dialog(code_output: str):
    viewport_w = dpg.get_viewport_width()
    viewport_h = dpg.get_viewport_height()
    win_width, win_height = 450, 280
    pos_x = (viewport_w - win_width) // 2
    pos_y = (viewport_h - win_height) // 2
    tag = f"save_window_{dpg.generate_uuid()}"

    def save_function_callback():
        filename = dpg.get_value("input_filename").strip()
        desc = dpg.get_value("input_desc").strip()

        if not filename or not desc:
            return

        file_path = os.path.join(FUNCTIONS_DIR, f"{filename}.py")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"# {desc}\n")
            f.write(code_output)

        if dpg.does_item_exist(tag):
            dpg.delete_item(tag)

        log(f"함수 저장 완료: {filename}.py ({desc})")

        update_tools_py()

    with dpg.window(
        label="Save Function",
        modal=True,
        no_close=True,
        no_resize=True,
        width=win_width,
        height=win_height,
        pos=[pos_x, pos_y],
        tag=tag,
    ):
        dpg.add_text("생성된 함수를 저장합니다.")
        dpg.add_spacer(height=10)
        dpg.add_text("파일 이름")
        dpg.add_input_text(tag="input_filename", width=-1)
        dpg.add_spacer(height=5)
        dpg.add_text("Description")
        dpg.add_input_text(tag="input_desc", width=-1, multiline=True, height=60)
        dpg.add_spacer(height=10)
        dpg.add_button(label="저장", width=-1, callback=save_function_callback)


def open_playwright_codegen(sender, app_data, user_data):
    url = dpg.get_value("input_url")
    if not url.strip():
        show_alert("입력 오류", "URL을 입력해주세요.")
        return

    log(f"Codegen 시작: {url}")
    log("브라우저 창을 닫으면 코드가 저장됩니다...")

    tmp_path = os.path.join(FUNCTIONS_DIR, "tmp_codegen.py")

    cmd = [
        sys.executable,
        "-m",
        "playwright",
        "codegen",
        url,
        "--browser",
        "chromium",
        "--target",
        "python",
        "--output",
        tmp_path,
    ]
    try:
        subprocess.run(cmd)  # 브라우저 닫힐 때까지 대기
        with open(tmp_path, "r", encoding="utf-8") as f:
            code_output = f.read()
        os.remove(tmp_path)
        show_save_dialog(code_output)
    except Exception as e:
        show_alert("오류", f"open_playwright_codegen 실행 중 오류 발생:\n{e}")


def codegen_comp():
    with dpg.group(tag="content_codegen", show=True):
        with dpg.group(horizontal=True):
            dpg.add_text("URL:")
            dpg.add_input_text(tag="input_url", width=-1, default_value=DEFAULT_URL)
        dpg.add_spacer(height=10)
        dpg.add_button(
            label="Codegen 녹화 시작",
            width=-1,
            height=40,
            callback=open_playwright_codegen,
        )
