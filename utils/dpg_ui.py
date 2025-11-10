import dearpygui.dearpygui as dpg


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
