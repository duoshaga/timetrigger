# 定时提醒

一个使用 PyQt6 编写的工作日定时提醒小工具。

## 功能

- 周一到周五按自定义时间提醒，精确到分钟。
- 配置文件与程序或 exe 在同一个目录，文件名为 `reminder_times.txt`。
- 第一行是提醒时间，格式示例: `10:00|11:15|14:15`。
- 第二行开始是提醒内容，可以在主窗口中编辑。
- 主窗口和托盘右键菜单可以开启或暂停提醒。
- 主窗口点击系统自带的 X 按钮时最小化到托盘。
- 托盘图标右键菜单可以退出程序。
- 托盘图标右键菜单可以开启或关闭开机自启动。
- 提醒窗口会保持在其他窗口上方，直到点击提醒窗口的 X 按钮关闭。

## 运行

```powershell
python -m pip install -r requirements.txt
python main.py
```

第一次运行会自动创建 `reminder_times.txt` 和 `reminder_enabled.txt`。

配置文件示例:

```text
10:00|11:15|14:15
该休息一下了。
```

## 打包为 exe

可使用 PyInstaller:

```powershell
python -m pip install pyinstaller
.\build_exe.ps1
```

打包完成后，程序位于 `dist_final\TimeTrigger.exe`，配置文件 `reminder_times.txt` 会复制到同目录。

脚本会先在 Windows 临时目录中完成 PyInstaller 构建，再复制回项目目录。这样可以避开部分磁盘环境中 PyInstaller 写入 exe 资源时的“拒绝访问”问题，同时保留程序启动所需的 manifest。
