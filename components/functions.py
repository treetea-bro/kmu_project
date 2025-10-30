import os
import subprocess
import sys

import dearpygui.dearpygui as dpg

from components.codegen import update_tools_py
from env import (
    FUNCTIONS_DIR,
    TOOLS_PATH,
)
from utils import log, show_alert


def load_tools():
    """tools.py를 파싱해서 현재 등록된 TOOLS를 반환"""
    if not os.path.exists(TOOLS_PATH):
        return []

    try:
        content = open(TOOLS_PATH, "r", encoding="utf-8").read()
        local_vars = {}
        exec(content, {}, local_vars)
        return local_vars.get("TOOLS", [])
    except Exception:
        return []


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
            log(f"저장 완료: {filename} 파일의 내용이 수정되었습니다.")
        except Exception as e:
            log(f"저장 실패: 파일 내용 수정 중 오류 발생:\n{e}")

    with dpg.window(
        label=f"{filename}",
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
            readonly=False,
            width=-1,
            height=win_height - 100,
        )
        dpg.add_spacer(height=10)

        with dpg.group(horizontal=True):
            dpg.add_button(label="저장", width=120, callback=save_code)
            dpg.add_button(label="닫기", width=120, callback=close_preview)


def refresh_function_list():
    dpg.delete_item("functions_group", children_only=True)

    tools = load_tools()
    if not tools:
        dpg.add_text("아직 생성된 함수가 없습니다.", parent="functions_group")
        return

    for item in tools:
        func = item["function"]
        name = func["name"]
        desc = func["description"]
        file_path = os.path.join(FUNCTIONS_DIR, f"{name}.py")

        def make_run_callback(f=file_path, func_name=name):
            def _run():
                log(f"{func_name}.py 실행")
                try:
                    process = subprocess.Popen(
                        [sys.executable, f],
                        stdout=sys.stdout,
                        stderr=sys.stderr,
                        text=True,
                        # start_new_session=True,
                    )

                    def read_output():
                        _ = process.communicate()

                    import threading

                    threading.Thread(target=read_output, daemon=True).start()

                except Exception as e:
                    show_alert("실행 오류", f"{func_name}.py 실행 중 오류 발생:\n{e}")

            return _run

        def make_delete_callback(f=file_path, func_name=name):
            def _delete():
                def confirm_delete():
                    try:
                        os.remove(f)
                        log(f"{func_name}.py 삭제 완료")
                        update_tools_py()
                        refresh_function_list()
                    except Exception as e:
                        show_alert("삭제 오류", f"{func_name}.py 삭제 실패:\n{e}")
                    dpg.delete_item(confirm_tag)

                # 확인 팝업
                viewport_w = dpg.get_viewport_width()
                viewport_h = dpg.get_viewport_height()
                win_width, win_height = 320, 150
                pos_x = (viewport_w - win_width) // 2
                pos_y = (viewport_h - win_height) // 2
                confirm_tag = f"confirm_delete_{dpg.generate_uuid()}"

                with dpg.window(
                    label="삭제 확인",
                    modal=True,
                    no_resize=True,
                    width=win_width,
                    height=win_height,
                    pos=[pos_x, pos_y],
                    tag=confirm_tag,
                ):
                    dpg.add_text(f"정말 {func_name}.py 파일을 삭제하시겠습니까?")
                    dpg.add_spacer(height=10)
                    with dpg.group(horizontal=True):
                        dpg.add_button(
                            label="삭제",
                            width=120,
                            callback=lambda: confirm_delete(),
                        )
                        dpg.add_button(
                            label="취소",
                            width=120,
                            callback=lambda: dpg.delete_item(confirm_tag),
                        )

            return _delete

        def make_preview_callback(f=f"{name}.py"):
            return lambda: show_code_preview(f)

        with dpg.child_window(parent="functions_group", height=90):
            with dpg.table(
                header_row=False, resizable=False, policy=dpg.mvTable_SizingStretchProp
            ):
                dpg.add_table_column()
                dpg.add_table_column(width_fixed=True, init_width_or_weight=90)
                dpg.add_table_column(width_fixed=True, init_width_or_weight=90)

                with dpg.table_row():
                    dpg.add_button(
                        label=f"{name}",
                        width=-1,
                        callback=make_preview_callback(),
                    )
                    dpg.add_button(
                        label="실행",
                        width=80,
                        callback=make_run_callback(),
                    )
                    dpg.add_button(
                        label="삭제",
                        width=80,
                        callback=make_delete_callback(),
                    )

            dpg.add_text(f"설명: {desc}")
            dpg.add_spacer(height=5)


def functions_comp():
    with dpg.group(tag="content_functions", show=False):
        dpg.add_text("저장된 함수 목록")
        dpg.add_child_window(tag="functions_scroll")
        with dpg.group(tag="functions_group", parent="functions_scroll"):
            dpg.add_text("아직 생성된 함수가 없습니다.")
