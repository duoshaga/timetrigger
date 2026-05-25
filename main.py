import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QAction, QCloseEvent, QFont
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QStyle,
    QSystemTrayIcon,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


CONFIG_NAME = "reminder_times.txt"
DEFAULT_TIMES = "10:00|11:15|14:15"
DEFAULT_MESSAGE = "该休息一下了。"
TIME_PATTERN = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")


@dataclass
class ReminderConfig:
    times: list[str]
    message: str


def app_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def config_path() -> str:
    return os.path.join(app_dir(), CONFIG_NAME)


def ensure_config() -> None:
    path = config_path()
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as file:
            file.write(f"{DEFAULT_TIMES}\n{DEFAULT_MESSAGE}")


def parse_times(raw_text: str) -> list[str]:
    parts = [item.strip() for item in raw_text.replace("\n", "|").split("|")]
    times = []
    invalid = []

    for item in parts:
        if not item:
            continue
        if TIME_PATTERN.match(item):
            times.append(item)
        else:
            invalid.append(item)

    if invalid:
        raise ValueError("时间格式不正确: " + ", ".join(invalid))

    return sorted(set(times))


def read_config() -> ReminderConfig:
    with open(config_path(), "r", encoding="utf-8") as file:
        lines = file.read().splitlines()

    time_line = lines[0].strip() if lines else DEFAULT_TIMES
    message = "\n".join(lines[1:]).strip() if len(lines) > 1 else DEFAULT_MESSAGE
    return ReminderConfig(parse_times(time_line or DEFAULT_TIMES), message or DEFAULT_MESSAGE)


def write_config(config: ReminderConfig) -> None:
    with open(config_path(), "w", encoding="utf-8") as file:
        file.write("|".join(config.times))
        file.write("\n")
        file.write(config.message)


class ReminderDialog(QDialog):
    def __init__(
        self,
        reminder_time: str,
        reminder_message: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("定时提醒")
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setModal(False)
        self.resize(420, 240)

        title = QLabel("到提醒时间了")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        time_label = QLabel(f"提醒时间: {reminder_time}")
        time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        message = QLabel(reminder_message)
        message.setWordWrap(True)
        message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message.setStyleSheet("font-size: 16px; color: #222;")

        hint = QLabel("关闭这个窗口前，它会保持在其他窗口上方。")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet("color: #555;")

        layout = QVBoxLayout()
        layout.addStretch(1)
        layout.addWidget(title)
        layout.addWidget(time_label)
        layout.addWidget(message)
        layout.addWidget(hint)
        layout.addStretch(1)
        self.setLayout(layout)

        self._raise_timer = QTimer(self)
        self._raise_timer.timeout.connect(self.bring_to_front)
        self._raise_timer.start(1000)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.bring_to_front()

    def bring_to_front(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("定时提醒")
        self.resize(500, 330)

        self._exiting = False
        self._triggered_keys: set[str] = set()
        self._active_dialogs: list[ReminderDialog] = []

        ensure_config()
        self.config = read_config()
        self.tray_icon = self.create_tray_icon()

        self.time_input = QLineEdit()
        self.time_input.setPlaceholderText("例如: 10:00|11:15|14:15")
        self.time_input.setText("|".join(self.config.times))

        self.message_input = QTextEdit()
        self.message_input.setPlaceholderText("填写提醒弹窗中显示的内容")
        self.message_input.setPlainText(self.config.message)
        self.message_input.setMinimumHeight(90)

        save_button = QPushButton("保存")
        save_button.clicked.connect(self.save_config)

        reload_button = QPushButton("重新读取配置")
        reload_button.clicked.connect(self.reload_config)

        button_row = QHBoxLayout()
        button_row.addWidget(save_button)
        button_row.addWidget(reload_button)

        description = QLabel(
            f"配置文件与程序同目录: {CONFIG_NAME}\n"
            "第一行填写提醒时间，例如: 10:00|11:15|14:15\n"
            "第二行开始填写提醒内容。"
        )
        description.setWordWrap(True)

        content_label = QLabel("提醒内容")

        layout = QVBoxLayout()
        layout.addWidget(description)
        layout.addWidget(self.time_input)
        layout.addWidget(content_label)
        layout.addWidget(self.message_input)
        layout.addLayout(button_row)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_reminders)
        self.timer.start(1000)

    def create_tray_icon(self) -> QSystemTrayIcon:
        tray = QSystemTrayIcon(self)
        icon = self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        tray.setIcon(icon)
        tray.setToolTip("定时提醒")

        menu = QMenu()
        show_action = QAction("打开主窗口", self)
        show_action.triggered.connect(self.show_from_tray)
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.exit_app)
        menu.addAction(show_action)
        menu.addSeparator()
        menu.addAction(exit_action)

        tray.setContextMenu(menu)
        tray.activated.connect(self.on_tray_activated)
        tray.show()
        return tray

    def save_config(self) -> None:
        try:
            times = parse_times(self.time_input.text())
        except ValueError as error:
            QMessageBox.warning(self, "保存失败", str(error))
            return

        message = self.message_input.toPlainText().strip()
        if not times:
            QMessageBox.warning(self, "保存失败", "请至少填写一个提醒时间。")
            return
        if not message:
            QMessageBox.warning(self, "保存失败", "请填写提醒内容。")
            return

        self.config = ReminderConfig(times, message)
        write_config(self.config)
        self.time_input.setText("|".join(times))
        QMessageBox.information(self, "已保存", "提醒时间和内容已更新。")

    def reload_config(self) -> None:
        try:
            self.config = read_config()
        except ValueError as error:
            QMessageBox.warning(self, "读取失败", str(error))
            return

        self.time_input.setText("|".join(self.config.times))
        self.message_input.setPlainText(self.config.message)
        QMessageBox.information(self, "已读取", "已从同目录配置文件重新读取提醒配置。")

    def check_reminders(self) -> None:
        now = datetime.now()
        today_prefix = now.strftime("%Y-%m-%d")

        if now.weekday() >= 5:
            self._clear_old_trigger_keys(today_prefix)
            return

        current_time = now.strftime("%H:%M")
        key = f"{today_prefix} {current_time}"

        if current_time in self.config.times and key not in self._triggered_keys:
            self._triggered_keys.add(key)
            self.show_reminder(current_time)

        self._clear_old_trigger_keys(today_prefix)

    def _clear_old_trigger_keys(self, today_prefix: str) -> None:
        self._triggered_keys = {
            key for key in self._triggered_keys if key.startswith(today_prefix)
        }

    def show_reminder(self, reminder_time: str) -> None:
        dialog = ReminderDialog(reminder_time, self.config.message)
        dialog.destroyed.connect(lambda: self._remove_closed_dialog(dialog))
        self._active_dialogs.append(dialog)
        dialog.show()

    def _remove_closed_dialog(self, dialog: ReminderDialog) -> None:
        if dialog in self._active_dialogs:
            self._active_dialogs.remove(dialog)

    def show_from_tray(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show_from_tray()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._exiting:
            event.accept()
            return

        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "定时提醒仍在运行",
            "需要退出时，请右键托盘图标选择“退出”。",
            QSystemTrayIcon.MessageIcon.Information,
            2500,
        )

    def exit_app(self) -> None:
        self._exiting = True
        self.tray_icon.hide()
        QApplication.instance().quit()


def main() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(None, "无法启动", "当前系统没有可用的托盘区域。")
        return 1

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
