import json
import os
import platform
import subprocess
import sys

import dearpygui.dearpygui as dpg
from dearpygui_ext.themes import create_theme_imgui_dark, create_theme_imgui_light
from returns.result import Failure

from config import (
    APP_TITLE,
    CONFIG_PATH,
    DEFAULT_URL,
    FUNCTIONS_DIR,
    TOOLS_PATH,
)
from font import apply_korean_font
from playwright_install import ensure_chromium_install


def log(msg: str):
    dpg.add_text(msg, parent="log_group")


def show_alert(title: str, message: str):
    viewport_w = dpg.get_viewport_width()
    viewport_h = dpg.get_viewport_height()
    win_width, win_height = 340, 140
    pos_x = (viewport_w - win_width) // 2
    pos_y = (viewport_h - win_height) // 2
    tag = f"alert_window_{dpg.generate_uuid()}"

    def close_alert():
        if dpg.does_item_exist(tag):
            dpg.delete_item(tag)

    with dpg.window(
        label=title,
        modal=True,
        no_close=False,
        no_resize=True,
        width=win_width,
        height=win_height,
        pos=[pos_x, pos_y],
        tag=tag,
    ):
        dpg.add_text(message, wrap=win_width - 40)
        dpg.add_spacer(height=10)
        dpg.add_button(label="확인", width=-1, callback=close_alert)


# -------------------------------------------------
# 함수 파일 / tools.py 관리
# -------------------------------------------------
def ensure_tools():
    os.makedirs(FUNCTIONS_DIR, exist_ok=True)
    if not os.path.exists(TOOLS_PATH):
        with open(TOOLS_PATH, "w", encoding="utf-8") as f:
            f.write("# AUTO-GENERATED TOOL DEFINITIONS\nTOOLS = []\n")


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

    log(f"🔧 tools.py 갱신 완료 ({len(tools)}개 함수)")


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


# -------------------------------------------------
# 코드 미리보기 팝업
# -------------------------------------------------
def show_code_preview(filename: str):
    file_path = os.path.join(FUNCTIONS_DIR, filename)
    if not os.path.exists(file_path):
        show_alert("오류", f"파일을 찾을 수 없습니다:\n{filename}")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        code = f.read()

    viewport_w = dpg.get_viewport_width()
    viewport_h = dpg.get_viewport_height()
    win_width, win_height = 600, 500
    pos_x = (viewport_w - win_width) // 2
    pos_y = (viewport_h - win_height) // 2
    tag = f"preview_window_{dpg.generate_uuid()}"

    def close_preview():
        if dpg.does_item_exist(tag):
            dpg.delete_item(tag)

    with dpg.window(
        label=f"📄 {filename}",
        modal=True,
        no_close=False,
        width=win_width,
        height=win_height,
        pos=[pos_x, pos_y],
        tag=tag,
    ):
        dpg.add_input_text(
            default_value=code, multiline=True, readonly=True, width=-1, height=-1
        )
        dpg.add_spacer(height=10)
        dpg.add_button(label="닫기", width=-1, callback=close_preview)


# -------------------------------------------------
# Functions 탭 갱신
# -------------------------------------------------
def refresh_function_list():
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
        file_path = os.path.join(FUNCTIONS_DIR, f"{name}.py")

        # ▶ 실행 콜백
        def make_run_callback(f=file_path, func_name=name):
            def _run():
                log(f"▶ {func_name}.py 실행 중...")
                try:
                    result = subprocess.run(
                        [sys.executable, f],
                        capture_output=True,
                        text=True,
                    )
                    if result.stdout.strip():
                        log(f"✅ 출력:\n{result.stdout.strip()}")
                    if result.stderr.strip():
                        log(f"⚠️ 오류:\n{result.stderr.strip()}")
                except Exception as e:
                    show_alert("실행 오류", f"{func_name}.py 실행 중 오류 발생:\n{e}")

            return _run

        # 🗑️ 삭제 콜백
        def make_delete_callback(f=file_path, func_name=name):
            def _delete():
                def confirm_delete():
                    try:
                        os.remove(f)
                        log(f"🗑️ {func_name}.py 삭제 완료")
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

        # 💡 table 레이아웃: 이름 버튼 + 실행 + 삭제
        with dpg.group(parent="functions_group"):
            with dpg.table(
                header_row=False, resizable=False, policy=dpg.mvTable_SizingStretchProp
            ):
                dpg.add_table_column()  # 이름 버튼 (가변폭)
                dpg.add_table_column(
                    width_fixed=True, init_width_or_weight=90
                )  # 실행 버튼
                dpg.add_table_column(
                    width_fixed=True, init_width_or_weight=90
                )  # 삭제 버튼

                with dpg.table_row():
                    dpg.add_button(
                        label=f"🧩 {name}",
                        width=-1,
                        callback=make_preview_callback(),
                    )
                    dpg.add_button(
                        label="▶ 실행",
                        width=80,
                        callback=make_run_callback(),
                    )
                    dpg.add_button(
                        label="🗑️ 삭제",
                        width=80,
                        callback=make_delete_callback(),
                    )

            dpg.add_text(f"설명: {desc}")
            dpg.add_spacer(height=5)


# -------------------------------------------------
# Codegen → 파일 저장
# -------------------------------------------------
def open_playwright_codegen(sender, app_data, user_data):
    url = dpg.get_value("input_url")
    if not url.strip():
        show_alert("입력 오류", "URL을 입력해주세요.")
        return

    log(f"🧭 Codegen 시작: {url}")
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

        if not os.path.exists(tmp_path):
            show_alert("오류", "Codegen 결과 파일이 생성되지 않았습니다.")
            return

        with open(tmp_path, "r", encoding="utf-8") as f:
            code_output = f.read()

        if not code_output.strip():
            show_alert("경고", "Codegen 결과가 비어 있습니다.")
            return

        show_save_dialog(code_output)
        os.remove(tmp_path)

    except Exception as e:
        show_alert("오류", f"실행 중 오류 발생:\n{e}")


# -------------------------------------------------
# 저장 팝업
# -------------------------------------------------
def show_save_dialog(code_output: str):
    viewport_w = dpg.get_viewport_width()
    viewport_h = dpg.get_viewport_height()
    win_width, win_height = 360, 200
    pos_x = (viewport_w - win_width) // 2
    pos_y = (viewport_h - win_height) // 2
    tag = f"save_window_{dpg.generate_uuid()}"

    def save_function_callback():
        filename = dpg.get_value("input_filename").strip()
        desc = dpg.get_value("input_desc").strip()

        if not filename:
            show_alert("입력 오류", "파일 이름을 입력해주세요.")
            return

        file_path = os.path.join(FUNCTIONS_DIR, f"{filename}.py")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"# {desc}\n")
            f.write(code_output)

        if dpg.does_item_exist(tag):
            dpg.delete_item(tag)

        log(f"💾 저장 완료: {filename}.py ({desc})")

        # 🔧 tools.py 갱신
        update_tools_py()
        refresh_function_list()

    with dpg.window(
        label="Save Function",
        modal=True,
        no_close=False,
        no_resize=True,
        width=win_width,
        height=win_height,
        pos=[pos_x, pos_y],
        tag=tag,
    ):
        dpg.add_text("생성된 함수를 저장합니다.")
        dpg.add_spacer(height=10)
        dpg.add_text("파일 이름:")
        dpg.add_input_text(tag="input_filename", width=-1)
        dpg.add_spacer(height=5)
        dpg.add_text("Description:")
        dpg.add_input_text(tag="input_desc", width=-1, multiline=True, height=60)
        dpg.add_spacer(height=10)
        dpg.add_button(label="저장", width=-1, callback=save_function_callback)


# -------------------------------------------------
# 테마 / 설정
# -------------------------------------------------
def load_config() -> dict:
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"theme": "dark"}


def save_config(data: dict):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def toggle_theme(sender, app_data, user_data):
    current = user_data["theme"]
    if current == "dark":
        new_theme = create_theme_imgui_light()
        user_data["theme"] = "light"
        dpg.configure_item(sender, label="Dark")
    else:
        new_theme = create_theme_imgui_dark()
        user_data["theme"] = "dark"
        dpg.configure_item(sender, label="Light")
    dpg.bind_theme(new_theme)
    save_config({"theme": user_data["theme"]})


# -------------------------------------------------
# 메인 GUI
# -------------------------------------------------
def main():
    ensure_tools()
    dpg.create_context()

    match apply_korean_font(dpg):
        case Failure(e):
            raise e

    cfg = load_config()
    theme_state = {"theme": cfg.get("theme", "dark")}
    if theme_state["theme"] == "light":
        dpg.bind_theme(create_theme_imgui_light())
    else:
        dpg.bind_theme(create_theme_imgui_dark())

    dpg.create_viewport(title=APP_TITLE, width=800, height=600)

    def run_query():
        query_text = dpg.get_value("input_query")
        model_name = dpg.get_value("model_selector")
        if not query_text.strip():
            show_alert("입력 오류", "Query를 입력해주세요.")
            return
        log(f"선택된 모델: {model_name}")
        log(f"입력된 Query: {query_text}")
        log("실행되었습니다.")

    def on_tab_change(sender, app_data, user_data):
        tag = dpg.get_item_alias(app_data)
        for content_tag in ["content_codegen", "content_query", "content_functions"]:
            dpg.configure_item(content_tag, show=False)
        dpg.configure_item(f"content_{tag.split('_')[1]}", show=True)
        if tag == "tab_functions":
            refresh_function_list()

    with dpg.window(tag="main_window"):
        with dpg.table(
            header_row=False, resizable=False, policy=dpg.mvTable_SizingStretchProp
        ):
            dpg.add_table_column(width_stretch=True)
            dpg.add_table_column(width_fixed=True)

            with dpg.table_row():
                with dpg.tab_bar(tag="top_tabbar", callback=on_tab_change):
                    dpg.add_tab(label="Codegen", tag="tab_codegen")
                    dpg.add_tab(label="Functions", tag="tab_functions")
                    dpg.add_tab(label="User Query", tag="tab_query")

                initial_label = "Dark" if theme_state["theme"] == "light" else "Light"
                dpg.add_button(
                    label=initial_label,
                    width=80,
                    callback=toggle_theme,
                    user_data=theme_state,
                )

        dpg.add_spacer(height=8)

        with dpg.child_window(tag="content_area", auto_resize_y=True):
            # Codegen 탭
            with dpg.group(tag="content_codegen", show=True):
                with dpg.group(horizontal=True):
                    dpg.add_text("URL:")
                    dpg.add_input_text(
                        tag="input_url", width=-1, default_value=DEFAULT_URL
                    )
                dpg.add_spacer(height=10)
                dpg.add_button(
                    label="Codegen 녹화 시작",
                    width=-1,
                    height=40,
                    callback=open_playwright_codegen,
                )

            # Functions 탭
            with dpg.group(tag="content_functions", show=False):
                dpg.add_text("저장된 함수 목록")
                dpg.add_child_window(
                    tag="functions_scroll", autosize_x=True, autosize_y=True
                )
                with dpg.group(tag="functions_group", parent="functions_scroll"):
                    dpg.add_text("아직 생성된 함수가 없습니다.")

            # User Query 탭
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

        dpg.add_spacer(height=8)
        dpg.add_text("실행 로그")
        dpg.add_child_window(tag="log_scroll")
        with dpg.group(tag="log_group", parent="log_scroll"):
            log(f"OS: {platform.system()}")
            log(f"Python: {platform.python_version()}")

    match ensure_chromium_install():
        case Failure(e):
            log(e)

    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.set_primary_window("main_window", True)
    dpg.start_dearpygui()
    dpg.destroy_context()


if __name__ == "__main__":
    main()
