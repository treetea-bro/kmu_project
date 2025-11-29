import json
import os
import subprocess
import sys
import threading

import dearpygui.dearpygui as dpg

from env import (
    FUNCTIONS_DIR,
    TOOLS_PATH,
)
from utils.dpg_ui import log, show_alert


def load_tools():
    """tools.py 파싱"""
    if not os.path.exists(TOOLS_PATH):
        return []
    try:
        content = open(TOOLS_PATH, "r", encoding="utf-8").read()
        local_vars = {}
        exec(content, {}, local_vars)
        return local_vars.get("TOOLS", [])
    except Exception:
        return []


def save_tools_list_direct(tools_list: list):
    """tools.py 저장 (삭제 시 사용)"""
    with open(TOOLS_PATH, "w", encoding="utf-8") as f:
        f.write("# AUTO-GENERATED TOOL DEFINITIONS\n")
        f.write("TOOLS = ")
        json_str = json.dumps(tools_list, indent=4, ensure_ascii=False)
        f.write(
            json_str.replace("true", "True")
            .replace("false", "False")
            .replace("null", "None")
        )
        f.write("\n")


def show_code_preview(filename: str):
    file_path = os.path.join(FUNCTIONS_DIR, filename)
    if not os.path.exists(file_path):
        show_alert("오류", f"파일을 찾을 수 없습니다:\n{filename}")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        code = f.read()

    viewport_w = dpg.get_viewport_width()
    viewport_h = dpg.get_viewport_height()
    win_width, win_height = 800, 600
    pos_x = (viewport_w - win_width) // 2
    pos_y = (viewport_h - win_height) // 2
    tag = f"preview_window_{dpg.generate_uuid()}"
    input_tag = f"code_input_{dpg.generate_uuid()}"

    def close_preview():
        if dpg.does_item_exist(tag):
            dpg.delete_item(tag)

    def save_code():
        new_code = dpg.get_value(input_tag)
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_code)
            log(f"저장 완료: {filename} 내용 수정됨.")
        except Exception as e:
            log(f"저장 실패: {e}")

    with dpg.window(
        label=f"Preview: {filename}",
        modal=True,
        no_close=False,
        width=win_width,
        height=win_height,
        pos=[pos_x, pos_y],
        tag=tag,
    ):
        dpg.add_input_text(
            tag=input_tag,
            default_value=code,
            multiline=True,
            width=-1,
            height=win_height - 100,
        )
        dpg.add_spacer(height=10)
        with dpg.group(horizontal=True):
            dpg.add_button(label="저장 (Overwrite)", width=120, callback=save_code)
            dpg.add_button(label="닫기", width=120, callback=close_preview)


def refresh_function_list():
    """functions_group 태그 내부를 비우고 다시 그립니다. 인자 입력 UI 추가"""
    if not dpg.does_item_exist("functions_group"):
        return

    dpg.delete_item("functions_group", children_only=True)

    tools = load_tools()
    if not tools:
        dpg.add_text("아직 생성된 함수가 없습니다.", parent="functions_group")
        return

    for item in tools:
        func = item["function"]
        name = func["name"]
        desc = func["description"]
        params_schema = func["parameters"].get("properties", {})  # 파라미터 스키마

        file_path = os.path.join(FUNCTIONS_DIR, f"{name}.py")
        item_id = dpg.generate_uuid()  # 이 항목 전체를 위한 고유 ID

        def make_run_callback(
            f_path=file_path, f_name=name, p_schema=params_schema, item_tag=item_id
        ):
            # 런타임에 UI에서 인자 값을 읽는 함수
            def get_runtime_args():
                args = {}
                for var_name in p_schema.keys():
                    tag = f"input_arg_{f_name}_{var_name}_{item_tag}"
                    if dpg.does_item_exist(tag):
                        value = dpg.get_value(tag)
                        if value is None or (
                            isinstance(value, str) and not value.strip()
                        ):
                            # 필수 인수가 비어있으면 경고
                            show_alert(
                                "입력 오류",
                                f"함수 '{f_name}'의 필수 인자 '{var_name}' 값을 입력해주세요.",
                            )
                            return None  # 실행 중단

                        # 타입 변환 (argparse가 기대하는 str 형태로 전달)
                        args[var_name] = str(value)
                return args

            def _run():
                args = get_runtime_args()
                if args is None:
                    return

                log(f"실행 중: {f_name}.py (인자: {args})")
                if not os.path.exists(f_path):
                    show_alert("오류", f"파일이 존재하지 않습니다: {f_path}")
                    return

                def run_process():
                    try:
                        cmd = [sys.executable, f_path]

                        # 인자를 커맨드라인 아규먼트로 추가
                        for key, value in args.items():
                            cmd.append(f"--{key}")
                            cmd.append(value)  # 값은 이미 str로 변환됨

                        process = subprocess.Popen(
                            cmd,
                            stdout=sys.stdout,
                            stderr=sys.stderr,
                            text=True,
                        )
                        process.communicate()  # 프로세스가 끝날 때까지 대기
                        log(f"{f_name}.py 실행 종료")
                    except Exception as e:
                        show_alert("실행 오류", str(e))

                threading.Thread(target=run_process, daemon=True).start()

            return _run

        # 삭제 콜백 (변경 없음)
        def make_delete_callback(f_path=file_path, f_name=name):
            # ... (기존 make_delete_callback 로직 유지) ...

            # --- (내부 함수 do_real_delete, UI 로직) ---
            def _delete():
                # 확인 팝업
                confirm_tag = f"confirm_delete_{dpg.generate_uuid()}"

                def do_real_delete(sender, app_data, user_data):
                    dpg.delete_item(confirm_tag)
                    try:
                        # 1. 파일 삭제
                        if os.path.exists(f_path):
                            os.remove(f_path)

                        # 2. tools.py 갱신
                        current_tools = load_tools()
                        new_tools = [
                            t for t in current_tools if t["function"]["name"] != f_name
                        ]
                        save_tools_list_direct(new_tools)

                        log(f"삭제 완료: {f_name}")
                        refresh_function_list()  # 목록 갱신

                    except Exception as e:
                        show_alert("삭제 실패", str(e))

                viewport_w = dpg.get_viewport_width()
                viewport_h = dpg.get_viewport_height()
                win_width, win_height = 300, 130
                pos_x = (viewport_w - win_width) // 2
                pos_y = (viewport_h - win_height) // 2

                with dpg.window(
                    label="삭제 확인",
                    modal=True,
                    no_resize=True,
                    width=win_width,
                    height=win_height,
                    pos=[pos_x, pos_y],
                    tag=confirm_tag,
                ):
                    dpg.add_text(f"'{f_name}' 함수를 삭제하시겠습니까?")
                    dpg.add_spacer(height=10)
                    with dpg.group(horizontal=True):
                        dpg.add_button(label="삭제", width=100, callback=do_real_delete)
                        dpg.add_button(
                            label="취소",
                            width=100,
                            callback=lambda: dpg.delete_item(confirm_tag),
                        )

            return _delete

        # 미리보기 콜백 (변경 없음)
        def make_preview_callback(f_name=f"{name}.py"):
            return lambda: show_code_preview(f_name)

        # ------------------------------------------------------------------
        # UI Structure Reverted to Original Style
        # ------------------------------------------------------------------
        with dpg.group(
            parent="functions_group",
        ):  # height=None으로 유연하게 조정
            # 1. 함수 이름 및 버튼 행
            with dpg.table(
                header_row=False, resizable=False, policy=dpg.mvTable_SizingStretchProp
            ):
                dpg.add_table_column()
                dpg.add_table_column(width_fixed=True, init_width_or_weight=90)

                with dpg.table_row():
                    dpg.add_button(
                        label=f"{name}",
                        width=-1,
                        callback=make_preview_callback(),
                    )
                    dpg.add_button(
                        label="삭제",
                        width=80,
                        callback=make_delete_callback(),
                    )

            dpg.add_text(f"설명: {desc}", wrap=0)
            if params_schema:
                with dpg.group(tag=f"param_input_group_{item_id}"):
                    for var_name, p_details in params_schema.items():
                        p_type = p_details.get("type", "string")
                        p_desc = p_details.get("description", "인자 설명")

                        input_tag = f"input_arg_{name}_{var_name}_{item_id}"

                        dpg.add_text(f"{var_name} ({p_type}): {p_desc}")

                        input_type = dpg.mvInputText
                        if p_type == "number":
                            input_type = dpg.mvInputInt  # 정수 입력 위젯 사용

                        # 텍스트 또는 숫자 입력
                        dpg.add_input_text(
                            tag=input_tag,
                            hint="값 입력 (필수)",
                            width=-1,
                            on_enter=True,  # 엔터 입력 시 실행 트리거
                            callback=make_run_callback(),
                        )
                    dpg.add_spacer(height=5)

                    dpg.add_button(
                        label=f"{name} 실행",
                        width=-1,
                        height=30,
                        callback=make_run_callback(),
                        user_data=item_id,
                    )
            else:
                # 파라미터가 없으면 바로 실행 버튼 배치
                dpg.add_button(
                    label=f"{name} 실행",
                    width=-1,
                    height=30,
                    callback=make_run_callback(),
                    user_data=item_id,
                )

            dpg.add_spacer(height=5)
            dpg.add_separator()
            dpg.add_spacer(height=5)


def functions_comp():
    """functions_comp는 UI를 구성하고, 탭 활성화 시 목록을 로드합니다."""
    with dpg.group(tag="content_functions", show=False):
        dpg.add_text("저장된 함수 목록")
        dpg.add_child_window(tag="functions_scroll")
        with dpg.group(tag="functions_group", parent="functions_scroll"):
            dpg.add_text("목록을 로딩합니다...", tag="initial_loading_text")
