LabSmith Control — Windows 打包说明
====================================

1) 安装依赖（在已能运行 labsmith_gui.py 的环境里）:
   pip install pyinstaller pyserial PyQt6 numpy

2) 确保 Python/uProcess_x64/ 目录存在且含 uProcess_x64.pyd（及厂商附带 DLL）。
   spec 会自动把整包 uProcess_x64 打进 exe。

3) 在 Python 目录执行:
   cd Python
   pyinstaller --noconfirm packaging/LabSmithControl.spec

4) 输出:
   Python/dist/LabSmithControl.exe   （无控制台窗口）

5) 日志目录:
   与 exe 同级的 logs/OUTPUT.txt
   若安装到 Program Files 等只读位置，请设置环境变量:
   LABSMITH_DATA_DIR=C:\Users\你\AppData\Local\LabSmithControl
   再启动 exe，日志会写到该目录下的 logs/。

6) 自定义图标:
   将 icon.ico 放在 packaging/ 下，编辑 LabSmithControl.spec 取消注释 icon= 那一行。

7) macOS:
   在同一 spec 上通常需去掉 console=False 或改用 .app 流程；建议在 Mac 上单独用 pyinstaller
   生成 --windowed 的 .app，并处理代码签名（未签名可能被 Gatekeeper 拦截）。
