"""End-to-end demo driver: launch labsmith_gui with the mock driver, then
click through Connect -> Load demo JSON -> Run flow automatically so a screen
recorder can capture a clean happy-path run.

Usage:
    python3 dev_tools/demo_orchestrator.py

Timeline (approximate):
    t+0.5s   enter COM3 into the port combo
    t+1.2s   click Connect (synchronous connect via LABSMITH_SYNC_CONNECT=1)
    t+3.0s   switch to Flow Designer tab and load demo_scenario_fast.json
    t+4.0s   click Run flow
    ~30s     flow completes
    +3s     click Disconnect
    +2s     close the window (exits the app)
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PYTHON_ROOT = os.path.abspath(os.path.join(HERE, ".."))
TEST_DATA = os.path.join(PYTHON_ROOT, "test_data")
DEMO_JSON = os.path.join(TEST_DATA, "demo_scenario_fast.json")

if HERE not in sys.path:
    sys.path.insert(0, HERE)
if PYTHON_ROOT not in sys.path:
    sys.path.insert(0, PYTHON_ROOT)

# Force the in-process (synchronous) connect path so we don't have to babysit
# a QThread from the orchestrator. The mock InitConnection is instantaneous.
os.environ["LABSMITH_SYNC_CONNECT"] = "1"

import mock_driver
mock_driver.install()

from PyQt6 import QtCore, QtWidgets

import labsmith_gui


# ---- Overlay banner so the recorder shows which step is firing ----------

class _StatusOverlay(QtWidgets.QLabel):
    def __init__(self, parent):
        super().__init__(parent)
        self.setStyleSheet(
            "background-color: rgba(20, 120, 220, 220);"
            "color: white;"
            "font: bold 16pt 'Menlo', monospace;"
            "padding: 8px 18px;"
            "border-radius: 10px;"
        )
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.hide()

    def flash(self, text, ms=2500):
        self.setText(text)
        self.adjustSize()
        # top-right corner of the parent
        p = self.parent()
        margin = 24
        x = p.width() - self.width() - margin
        y = margin
        self.move(x, y)
        self.show()
        self.raise_()
        QtCore.QTimer.singleShot(ms, self.hide)


def run():
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("LabSmith Control — Mock demo")
    app.setWindowIcon(labsmith_gui.build_app_icon())
    labsmith_gui.apply_app_theme(app)
    labsmith_gui.apply_modern_stylesheet(app)
    win = labsmith_gui.MainWindow()
    win.resize(1400, 900)
    # Centre on the primary screen so the ffmpeg avfoundation capture (which
    # always grabs the main display) sees a predictably framed window.
    screen = QtWidgets.QApplication.primaryScreen().availableGeometry()
    win.move(
        screen.x() + (screen.width() - 1400) // 2,
        screen.y() + max(0, (screen.height() - 900) // 2),
    )
    win.show()
    win.raise_()
    win.activateWindow()

    overlay = _StatusOverlay(win)

    # -- Step 1: type a COM port --------------------------------------------
    def step_enter_port():
        overlay.flash("① Selecting COM3 (mock)")
        win.port_combo.setEditText("COM3")

    # -- Step 2: click Connect ---------------------------------------------
    def step_connect():
        overlay.flash("② Connect board")
        win.connect_btn.click()

    # -- Step 3: patch file-dialog + load JSON ------------------------------
    def step_load_flow():
        overlay.flash("③ Load demo flow JSON")
        win.tabs.setCurrentIndex(1)  # Flow Designer tab
        QtWidgets.QFileDialog.getOpenFileName = staticmethod(
            lambda *a, **kw: (DEMO_JSON, "JSON files (*.json)")
        )
        win.load_flow_btn.click()

    # -- Step 4: click Run --------------------------------------------------
    def step_run_flow():
        overlay.flash("④ Run flow — watch the steps turn green")
        # Pre-answer any validation confirmation dialog with "Yes"
        QtWidgets.QMessageBox.question = staticmethod(
            lambda *a, **kw: QtWidgets.QMessageBox.StandardButton.Yes
        )
        QtWidgets.QMessageBox.warning = staticmethod(
            lambda *a, **kw: QtWidgets.QMessageBox.StandardButton.Ok
        )
        QtWidgets.QMessageBox.information = staticmethod(
            lambda *a, **kw: QtWidgets.QMessageBox.StandardButton.Ok
        )
        win.run_flow_btn.click()

    # -- Step 5: disconnect and exit ---------------------------------------
    def step_disconnect_and_exit():
        overlay.flash("⑤ Flow complete — disconnect & exit", ms=2500)
        try:
            win.disconnect_btn.click()
        except Exception:
            pass
        QtCore.QTimer.singleShot(2500, app.quit)

    # Sanity log: how long do we think the flow will take?
    with open(DEMO_JSON) as f:
        demo = json.load(f)
    est_wait = sum(s.get("seconds", 0.0) for s in demo["steps"] if s.get("type") == "Wait")
    est_move = sum(
        s.get("volume", 0.0) / max(s.get("flowrate", 1.0), 0.001) * 60.0 / 4.0
        for s in demo["steps"] if s.get("type") == "Move syringe"
    )
    total_flow = est_wait + est_move + 1.0
    print(f"[orchestrator] estimated flow duration ~ {total_flow:.1f}s")

    QtCore.QTimer.singleShot(800, step_enter_port)
    QtCore.QTimer.singleShot(1800, step_connect)
    QtCore.QTimer.singleShot(3200, step_load_flow)
    QtCore.QTimer.singleShot(4500, step_run_flow)
    QtCore.QTimer.singleShot(int((4500 + total_flow * 1000) + 1500), step_disconnect_and_exit)

    sys.exit(app.exec())


if __name__ == "__main__":
    run()
