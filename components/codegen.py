import json
import os
import re
import subprocess
import sys

import dearpygui.dearpygui as dpg

from env import (
    DEFAULT_URL,
    FUNCTIONS_DIR,
    TOOLS_PATH,
)
from utils.dpg_ui import log, show_alert

# --- Helper Functions for File I/O ---


def _get_description_for_function(filename: str) -> str:
    """각 함수 파일 내 첫 번째 주석 줄을 description으로 사용"""
    file_path = os.path.join(FUNCTIONS_DIR, filename)
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            first_line = f.readline().strip()
            if first_line.startswith("#"):
                # 파일에서 읽은 설명을 반환 (실제로는 add_tools_py에서 사용되지 않음. UI에서 받은 desc 사용)
                return first_line.lstrip("#").strip()
    except Exception:
        pass
    return "No description"


def load_existing_tools() -> list:
    """tools.py에서 현재 정의된 도구 목록을 로드"""
    if not os.path.exists(TOOLS_PATH):
        return []

    try:
        with open(TOOLS_PATH, "r", encoding="utf-8") as f:
            content = f.read()

        # 간단한 파싱을 위해 exec 사용 (보안상 로컬 환경에서만 권장)
        local_vars = {}
        exec(content, {}, local_vars)
        return local_vars.get("TOOLS", [])
    except Exception as e:
        log(f"기존 tools.py 로드 실패: {e}")
        return []


def save_tools_list(tools_list: list):
    """도구 리스트를 tools.py에 저장"""
    with open(TOOLS_PATH, "w", encoding="utf-8") as f:
        f.write("# AUTO-GENERATED TOOL DEFINITIONS\n")
        f.write("TOOLS = ")
        json_str = json.dumps(tools_list, indent=4, ensure_ascii=False)
        # Python 문법에 맞게 변환
        f.write(
            json_str.replace("true", "True")
            .replace("false", "False")
            .replace("null", "None")
        )
        f.write("\n")


def add_tools_py(filename, name, schema, desc):  # desc 인자 추가
    # 1. 기존 도구 로드
    current_tools = load_existing_tools()

    # 2. 중복 제거 (이미 같은 이름이 있다면 삭제 후 갱신)
    current_tools = [t for t in current_tools if t["function"]["name"] != name]

    # 3. 새 도구 추가
    new_tool = {
        "type": "function",
        "function": {
            "name": name,
            "description": desc,  # UI에서 받은 desc 사용
            "parameters": schema,
        },
    }
    current_tools.append(new_tool)

    # 4. 저장
    save_tools_list(current_tools)
    log(f"tools.py 갱신 완료 (총 {len(current_tools)} 함수)")


def params_to_schema(params):
    """UI 파라미터를 JSON Schema로 변환"""
    properties = {}
    required = []

    for p in params:
        var = p["variable"]
        desc = p["desc"]
        typ = p["type"]

        if typ == "문자열":
            t = "string"
        else:
            t = "number"

        properties[var] = {"type": t, "description": desc}
        required.append(var)

    return {"type": "object", "properties": properties, "required": required}


# --- UI & Logic ---


def save_function_to_file(code_output: str):
    """
    모달 창 없이, UI에서 입력받은 함수명과 설명으로 파일을 저장하고 tools.py를 갱신합니다.
    """

    # 1. UI에서 값 가져오기
    filename = dpg.get_value("input_filename").strip()
    desc = dpg.get_value("input_desc").strip()

    if not filename or not desc:
        show_alert("오류", "함수명과 설명을 모두 입력해주세요.")
        return

    # 2. Playwright keepalive 및 run 정의 수정 (기존과 동일)
    code_output = re.sub(r"^\s*page\d*\.close\(\)", "", code_output, flags=re.M)

    def insert_keepalive(match: re.Match) -> str:
        return (
            "    # Keep browser open loop\n"
            "    while True:\n"
            "        try:\n"
            "            page.wait_for_timeout(1000)\n"
            "        except Exception:\n"
            "            break\n\n"
            "    context.close()"
        )

    code_output = re.sub(
        r"^([ \t]*)context\.close\(\)",
        insert_keepalive,
        code_output,
        count=1,
        flags=re.M,
    )

    # 3. 파라미터를 run 함수 정의에 주입 (기존과 동일)
    current_params = get_all_params()

    def inject_params_into_code(code_output, params):
        sig_params = ", ".join(
            f"{p['variable']}: {'str' if p['type'] == '문자열' else 'int'}"
            for p in params
        )
        if sig_params:
            sig_params = ", " + sig_params

        new_code = re.sub(
            r"def run\(playwright: Playwright\)",
            f"def run(playwright: Playwright{sig_params})",
            code_output,
            count=1,
        )
        return new_code

    new_code_output = inject_params_into_code(code_output, current_params)

    # 4. argparse를 사용하는 main 블록 생성기
    def generate_main_block(params):
        lines = [
            "",
            'if __name__ == "__main__":',
            "    import argparse",
            "    from playwright.sync_api import sync_playwright # main 블록에서 import 필요",
            "    parser = argparse.ArgumentParser()",
        ]

        # UI에서 설정한 파라미터들을 argparse 인자로 추가
        arg_list = []
        for p in params:
            var_name = p["variable"]
            p_type = "str" if p["type"] == "문자열" else "int"

            lines.append(
                f'    parser.add_argument("--{var_name}", type=str, required=True, help="{p["desc"]}")'
            )  # 모든 인자를 str로 받도록 통일 (실행 시 타입 변환은 파이썬 코드가 처리하도록)
            arg_list.append(f"{var_name}=args.{var_name}")

        lines.append("    args = parser.parse_args()")
        lines.append("")

        # run 함수 호출부 구성
        args_str = ", ".join(arg_list)
        if args_str:
            args_str = ", " + args_str

        lines.append("    with sync_playwright() as playwright:")
        lines.append(f"        run(playwright{args_str})")

        return "\n".join(lines)

    # 5. 기존 Playwright 실행 블록 제거
    def remove_sync_playwright_block(code_output: str) -> str:
        """기존 Playwright 생성 코드 (with sync_playwright() as playwright: run(playwright)) 제거"""
        # with sync_playwright() 로 시작하고 run(playwright)로 끝나는 블록을 제거
        pattern = re.compile(
            r"^([ \t]*with sync_playwright\(\) as playwright:\s*\n[ \t]*run\(playwright\)[ \t]*\n?)$",
            re.MULTILINE | re.DOTALL,
        )
        cleaned_output = pattern.sub("", code_output).strip()
        return cleaned_output

    # 6. 파일 저장 및 tools.py 갱신
    schema = params_to_schema(current_params)
    main_block = generate_main_block(current_params)

    if not os.path.exists(FUNCTIONS_DIR):
        os.makedirs(FUNCTIONS_DIR)

    file_path = os.path.join(FUNCTIONS_DIR, f"{filename}.py")
    final_code_body = remove_sync_playwright_block(new_code_output)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"# {desc}\n")
        f.write("import time\n")
        # final_code_body에는 Playwright import가 포함되어 있어야 함
        f.write(final_code_body)
        f.write(main_block)  # argparse가 포함된 실행 블록 작성

    add_tools_py(file_path, filename, schema, desc)  # desc도 함께 전달

    log(f"함수 저장 완료: {filename}.py")


def show_save_dialog(code_output: str):
    """
    모달 창을 제거하고 save_function_to_file을 직접 호출하도록 수정
    """
    save_function_to_file(code_output)


def open_playwright_codegen(sender, app_data, user_data):
    # ... (기존과 동일) ...
    url = dpg.get_value("input_url")
    filename = dpg.get_value("input_filename").strip()
    desc = dpg.get_value("input_desc").strip()

    if not url.strip():
        show_alert("입력 오류", "URL을 입력해주세요.")
        return

    if not filename or not desc:
        show_alert("입력 오류", "함수명과 설명을 모두 입력해주세요.")
        return

    # 파라미터 유효성 검사 (기존과 동일)
    params = get_all_params()
    for p in params:
        if not p["variable"].strip():
            show_alert("입력 오류", "파라미터 변수명을 입력하세요.")
            return
        if not p["desc"].strip():
            show_alert("입력 오류", "파라미터 설명을 입력하세요.")
            return

    log(f"함수 기록 시작: {url}")
    log("브라우저 창을 닫으면 코드가 저장됩니다...")

    tmp_path = os.path.join(FUNCTIONS_DIR, "tmp_codegen.py")

    cmd = [
        sys.executable,
        "-m",
        "playwright",
        "codegen",
        url,
        "--target",
        "python",
        "--output",
        tmp_path,
    ]

    # 비동기로 실행하지 않고 subprocess.run으로 블로킹해야 codegen 종료 후 로직이 실행됨
    try:
        subprocess.run(cmd)
        if os.path.exists(tmp_path):
            with open(tmp_path, "r", encoding="utf-8") as f:
                code_output = f.read()
            os.remove(tmp_path)
            # 녹화된 코드를 바로 저장 로직으로 전달
            show_save_dialog(code_output)
        else:
            log("codegen이 코드를 생성하지 않고 종료되었습니다.")
    except Exception as e:
        show_alert("오류", f"open_playwright_codegen 실행 중 오류 발생:\n{e}")


# ... (Dynamic Parameter Row Logic - 변경 없음) ...
# delete_row_callback, add_param_row, get_all_params는 변경 없음

# --- codegen_comp 수정 ---


def codegen_comp():
    global param_rows  # 전역 변수 초기화 방지
    param_rows = []

    with dpg.group(tag="content_codegen", show=False):
        # 1. URL 입력
        with dpg.group(horizontal=True):
            dpg.add_text("URL:")
            dpg.add_input_text(tag="input_url", width=-1, default_value=DEFAULT_URL)
        dpg.add_spacer(height=10)

        with dpg.group(horizontal=True):
            dpg.add_text("함수명:")
            dpg.add_input_text(tag="input_filename", width=-1)
        dpg.add_spacer(height=5)

        with dpg.group(horizontal=True):
            dpg.add_text("설명:")
            dpg.add_input_text(
                tag="input_desc",
                hint="함수가 수행하는 역할에 대한 자세한 설명",
                width=-1,
                multiline=True,
                height=60,
            )
        dpg.add_spacer(height=10)

        # 4. 파라미터 입력 (기존과 동일)
        dpg.add_text("추가 파라미터 (선택)", color=(100, 200, 255))
        dpg.add_group(tag="params_container")
        dpg.add_button(
            label="+ 파라미터 추가",
            callback=lambda: add_param_row("params_container"),
            width=-1,
        )
        dpg.add_spacer(height=15)

        # 5. 녹화 버튼 (기존과 동일)
        dpg.add_button(
            label="함수 녹화 시작 (Playwright)",
            width=-1,
            height=40,
            callback=open_playwright_codegen,
        )


# get_all_params, delete_row_callback, add_param_row 등의 함수는 상단에 있으므로 변경 없이 동작합니다.

# --- Dynamic Parameter Row Logic ---

param_rows = []


def delete_row_callback(sender, app_data, user_data):
    row_id = user_data
    if dpg.does_item_exist(row_id):
        dpg.delete_item(row_id)
    if row_id in param_rows:
        param_rows.remove(row_id)


def add_param_row(parent: str):
    row_id = f"param_row_{dpg.generate_uuid()}"
    param_rows.append(row_id)

    with dpg.group(horizontal=True, parent=parent, tag=row_id):
        t_type = f"param_type_{row_id}"
        t_var = f"param_variable_{row_id}"
        t_desc = f"param_desc_{row_id}"

        with dpg.table(
            header_row=False, resizable=False, policy=dpg.mvTable_SizingStretchProp
        ):
            dpg.add_table_column(width_fixed=True, init_width_or_weight=90)
            dpg.add_table_column(width_fixed=True, init_width_or_weight=100)
            dpg.add_table_column()
            dpg.add_table_column(width_fixed=True, init_width_or_weight=70)

            with dpg.table_row():
                dpg.add_combo(
                    tag=t_type,
                    items=["문자열", "숫자"],
                    default_value="문자열",
                    width=90,
                )
                dpg.add_input_text(tag=t_var, hint="변수명", width=-1)
                dpg.add_input_text(tag=t_desc, hint="설명", width=-1)
                dpg.add_button(
                    label="삭제",
                    width=70,
                    callback=delete_row_callback,
                    user_data=row_id,
                )


def get_all_params():
    results = []
    for row_id in list(param_rows):
        t_type = f"param_type_{row_id}"
        t_var = f"param_variable_{row_id}"
        t_desc = f"param_desc_{row_id}"

        if not dpg.does_item_exist(t_var):
            continue

        try:
            p_type = dpg.get_value(t_type)
            p_var = dpg.get_value(t_var).strip()
            p_desc = dpg.get_value(t_desc).strip()
            results.append(
                {"type": p_type, "variable": p_var, "desc": p_desc, "row_id": row_id}
            )
        except:
            continue
    return results
