import sys
import os
import time
import math
import itertools
from typing import Callable, Optional
from PyQt6 import QtWidgets, QtCore, QtGui
try:
    from serial.tools import list_ports
except Exception:
    list_ports = None

from LabsmithBoard import LabsmithBoard
from output_log import log_directory, output_txt_path


def parse_com_port_to_int(text_or_device: Optional[str]) -> Optional[int]:
    """Accept '3', 'COM3', 'COM13', or 'COM3 - USB Serial …' → int for LabsmithBoard."""
    if text_or_device is None:
        return None
    s = str(text_or_device).strip()
    if not s or s.lower().startswith("install"):
        return None
    if " - " in s:
        s = s.split(" - ", 1)[0].strip()
    u = s.upper()
    if u.startswith("COM"):
        tail = u[3:]
        if tail.isdigit():
            return int(tail)
    if s.isdigit():
        return int(s)
    return None


def interruptible_sleep(seconds: float) -> None:
    """Sleep while processing Qt events so spinners/animations stay alive."""
    if seconds <= 0:
        return
    end = time.monotonic() + seconds
    while True:
        rem = end - time.monotonic()
        if rem <= 0:
            break
        QtWidgets.QApplication.processEvents()
        time.sleep(min(0.08, rem))


ACCENT = QtGui.QColor(0, 168, 232)  # modern cyan


class ArcSpinnerWidget(QtWidgets.QWidget):
    """Small rotating arc — loading indicator (no external assets)."""

    def __init__(self, size: int = 24, parent=None):
        super().__init__(parent)
        self._angle = 0
        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._tick)
        self.setFixedSize(size, size)

    def _tick(self):
        self._angle = (self._angle + 22) % 360
        self.update()

    def start(self):
        self._timer.start(35)
        self.show()

    def stop(self):
        self._timer.stop()
        self.hide()

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        cx, cy = self.width() / 2, self.height() / 2
        p.translate(cx, cy)
        p.rotate(self._angle)
        pen = QtGui.QPen(ACCENT, 3)
        pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        r = min(cx, cy) - 4
        rect = QtCore.QRectF(-r, -r, 2 * r, 2 * r)
        p.drawArc(rect, 45 * 16, 280 * 16)
        p.end()


class ConnectWorker(QtCore.QObject):
    """Try LabsmithBoard on a worker thread so the UI spinner can animate.

    Note: If uProcess/COM is not thread-safe on your setup and you see crashes,
    report it — we can fall back to synchronous connect on the GUI thread.
    """

    finished = QtCore.pyqtSignal(object, str)

    def __init__(self, port: int, parent=None):
        super().__init__(parent)
        self._port = port

    @QtCore.pyqtSlot()
    def work(self):
        board = None
        err = ""
        try:
            b = LabsmithBoard(self._port)
            if getattr(b, "isConnected", False):
                board = b
            else:
                try:
                    b.Disconnect()
                except Exception:
                    pass
                err = "Not connected, check COM port"
        except Exception as e:
            err = str(e)
        self.finished.emit(board, err)


def build_app_icon() -> QtGui.QIcon:
    """Programmatic app / window icon (no external .ico file required)."""
    size = 256
    pix = QtGui.QPixmap(size, size)
    pix.fill(QtCore.Qt.GlobalColor.transparent)
    p = QtGui.QPainter(pix)
    p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
    g = QtGui.QLinearGradient(40, 40, size - 40, size - 40)
    g.setColorAt(0, ACCENT)
    g.setColorAt(1, QtGui.QColor(88, 86, 214))
    p.setBrush(g)
    p.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 60), 3))
    p.drawRoundedRect(36, 36, size - 72, size - 72, 52, 52)
    # Simple “L” + fluid curve (lab / flow motif)
    line_pen = QtGui.QPen(QtGui.QColor(255, 255, 255), 10)
    line_pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
    p.setPen(line_pen)
    p.drawLine(88, 188, 88, 88)
    p.drawLine(88, 88, 148, 88)
    p.setBrush(QtGui.QColor(255, 255, 255, 220))
    p.setPen(QtCore.Qt.PenStyle.NoPen)
    p.drawEllipse(158, 72, 28, 28)
    p.end()
    ico = QtGui.QIcon()
    for px in (16, 24, 32, 48, 64, 128, 256):
        ico.addPixmap(pix.scaled(px, px, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation))
    return ico


def apply_app_theme(app: QtWidgets.QApplication):
    """Dark Fusion + modern palette."""
    app.setStyle("Fusion")
    pal = QtGui.QPalette()
    base = QtGui.QColor(24, 24, 30)
    alt = QtGui.QColor(34, 34, 42)
    text = QtGui.QColor(235, 235, 240)
    pal.setColor(QtGui.QPalette.ColorRole.Window, base)
    pal.setColor(QtGui.QPalette.ColorRole.WindowText, text)
    pal.setColor(QtGui.QPalette.ColorRole.Base, alt)
    pal.setColor(QtGui.QPalette.ColorRole.AlternateBase, base)
    pal.setColor(QtGui.QPalette.ColorRole.Text, text)
    pal.setColor(QtGui.QPalette.ColorRole.Button, QtGui.QColor(48, 48, 58))
    pal.setColor(QtGui.QPalette.ColorRole.ButtonText, text)
    pal.setColor(QtGui.QPalette.ColorRole.Highlight, ACCENT)
    pal.setColor(QtGui.QPalette.ColorRole.HighlightedText, QtGui.QColor(255, 255, 255))
    pal.setColor(QtGui.QPalette.ColorRole.ToolTipBase, alt)
    pal.setColor(QtGui.QPalette.ColorRole.ToolTipText, text)
    app.setPalette(pal)
    f = app.font()
    f.setPointSize(max(9, f.pointSize()))
    app.setFont(f)


def apply_modern_stylesheet(app: QtWidgets.QApplication):
    """Rounded controls, spacing, sliders — works with Fusion dark palette."""
    app.setStyleSheet(
        """
        QMainWindow, QDialog { background-color: #18181e; }
        QGroupBox {
            font-weight: 600;
            font-size: 11pt;
            border: 1px solid #3a3a48;
            border-radius: 12px;
            margin-top: 14px;
            padding: 16px 12px 12px 12px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 14px;
            padding: 0 8px;
            color: #e8e8ef;
        }
        QPushButton {
            background-color: #3d3d4c;
            color: #f0f0f5;
            border: none;
            border-radius: 10px;
            padding: 9px 18px;
            min-height: 22px;
            font-weight: 500;
        }
        QPushButton:hover { background-color: #4d4d5e; }
        QPushButton:pressed { background-color: #0088c0; }
        QPushButton:disabled { background-color: #2a2a32; color: #666; }
        QLineEdit, QSpinBox, QDoubleSpinBox {
            border: 1px solid #3a3a48;
            border-radius: 10px;
            padding: 6px 10px;
            min-height: 22px;
            background-color: #22222a;
            selection-background-color: #00a8e8;
        }
        QComboBox {
            border: 1px solid #3a3a48;
            border-radius: 10px;
            padding: 6px 10px;
            padding-right: 30px;
            min-height: 22px;
            background-color: #22222a;
            selection-background-color: #00a8e8;
        }
        QComboBox::drop-down {
            subcontrol-origin: padding;
            subcontrol-position: center right;
            width: 26px;
            border: none;
        }
        QComboBox QAbstractItemView {
            border: 1px solid #3a3a48;
            border-radius: 8px;
            background-color: #22222a;
            selection-background-color: #00a8e8;
        }
        QTabWidget::pane {
            border: 1px solid #3a3a48;
            border-radius: 10px;
            top: -1px;
            padding: 4px;
        }
        QTabBar::tab {
            background-color: #2a2a34;
            color: #b0b0bc;
            padding: 10px 22px;
            margin-right: 4px;
            border-top-left-radius: 10px;
            border-top-right-radius: 10px;
            min-width: 72px;
        }
        QTabBar::tab:selected {
            background-color: #00a8e8;
            color: #ffffff;
            font-weight: 600;
        }
        QTabBar::tab:hover:!selected { background-color: #353542; color: #e0e0e8; }
        QSlider::groove:horizontal {
            height: 8px;
            background: #2e2e38;
            border-radius: 4px;
            border: 1px solid #3a3a48;
        }
        QSlider::sub-page:horizontal {
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #0090c8, stop:1 #00c8f0);
            border-radius: 4px;
        }
        QSlider::handle:horizontal {
            width: 20px;
            height: 20px;
            margin: -7px 0;
            background: #ffffff;
            border: 2px solid #00a8e8;
            border-radius: 10px;
        }
        QSlider::handle:horizontal:hover { background: #e8f8ff; }
        QPlainTextEdit {
            border: 1px solid #3a3a48;
            border-radius: 10px;
            background-color: #121218;
            padding: 8px;
            font-family: "Cascadia Mono", "Consolas", "Courier New", monospace;
            font-size: 10pt;
        }
        QSplitter::handle:horizontal { width: 4px; background: #2a2a34; }
        QSplitter::handle:horizontal:hover { background: #00a8e8; }
        QStatusBar { background: #1a1a22; border-top: 1px solid #3a3a48; }
        QTableWidget {
            gridline-color: #3a3a48;
            border: 1px solid #3a3a48;
            border-radius: 8px;
            background-color: #1c1c24;
        }
        QHeaderView::section {
            background-color: #2a2a34;
            padding: 6px;
            border: none;
            border-bottom: 2px solid #00a8e8;
        }
        QListWidget {
            border: 1px solid #3a3a48;
            border-radius: 10px;
            background-color: #1c1c24;
            padding: 4px;
        }
        QListWidget::item:selected { background-color: #00a8e8; color: #fff; border-radius: 6px; }
        QLabel#hintLabel { color: #888898; font-size: 9pt; }
        QMenuBar {
            background-color: #1c1c24;
            border-bottom: 1px solid #3a3a48;
            padding: 2px 4px;
            spacing: 6px;
        }
        QMenuBar::item {
            padding: 6px 14px;
            border-radius: 6px;
        }
        QMenuBar::item:selected {
            background-color: #00a8e8;
            color: #ffffff;
        }
        QMenu {
            background-color: #22222a;
            border: 1px solid #3a3a48;
            border-radius: 8px;
            padding: 4px;
        }
        QMenu::item { padding: 8px 28px 8px 12px; border-radius: 6px; }
        QMenu::item:selected { background-color: #00a8e8; color: #ffffff; }
        QPushButton#primaryButton {
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #00b4f0, stop:1 #0088c8);
            color: #ffffff;
            font-weight: 600;
        }
        QPushButton#primaryButton:hover {
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #33c8ff, stop:1 #00a8e8);
        }
        QPushButton#primaryButton:pressed { background-color: #006a94; }
        QPushButton#primaryButton:disabled {
            background: #2a3a42;
            color: #666;
        }
        QToolButton {
            background-color: #2e2e38;
            border: 1px solid #3a3a48;
            border-radius: 8px;
            padding: 6px 10px;
        }
        QToolButton:hover { background-color: #3d3d4c; border-color: #00a8e8; }
        QScrollArea { background: transparent; border: none; }
        QScrollBar:vertical {
            background: #1a1a22;
            width: 12px;
            margin: 4px 2px 4px 0;
            border-radius: 6px;
        }
        QScrollBar::handle:vertical {
            background: #3d3d4c;
            min-height: 32px;
            border-radius: 6px;
        }
        QScrollBar::handle:vertical:hover { background: #00a8e8; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        QScrollBar:horizontal {
            background: #1a1a22;
            height: 12px;
            margin: 0 4px 2px 4px;
            border-radius: 6px;
        }
        QScrollBar::handle:horizontal {
            background: #3d3d4c;
            min-width: 32px;
            border-radius: 6px;
        }
        QScrollBar::handle:horizontal:hover { background: #00a8e8; }
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
        """
    )


def _wire_slider_spin(
    slider: QtWidgets.QSlider,
    spin: QtWidgets.QDoubleSpinBox,
    slider_max: int,
    spin_max: float,
):
    """Two-way sync: slider 0..slider_max ↔ spin (same numeric range for slider portion)."""

    def on_slider(v: int):
        spin.blockSignals(True)
        spin.setValue(float(v))
        spin.blockSignals(False)

    def on_spin(v: float):
        slider.blockSignals(True)
        slider.setValue(int(round(min(v, float(slider_max)))))
        slider.blockSignals(False)

    slider.setRange(0, slider_max)
    slider.valueChanged.connect(on_slider)
    spin.valueChanged.connect(on_spin)
    on_spin(spin.value())


class GraphNodeItem(QtWidgets.QGraphicsRectItem):
    """Movable flow node; notifies when position changes for edge refresh."""

    def __init__(
        self,
        rect: QtCore.QRectF,
        on_moved: Optional[Callable[[], None]] = None,
    ):
        super().__init__(rect)
        self._on_moved = on_moved
        self.setZValue(1)
        self.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)

    def itemChange(self, change, value):
        if (
            change == QtWidgets.QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged
            and self._on_moved is not None
        ):
            self._on_moved()
        return super().itemChange(change, value)


def _graph_item_to_node_rect(item: Optional[QtWidgets.QGraphicsItem]) -> Optional[GraphNodeItem]:
    """Walk parents until we find the flow node rectangle."""
    while item is not None:
        if isinstance(item, GraphNodeItem):
            return item
        item = item.parentItem()
    return None


class NodePortItem(QtWidgets.QGraphicsEllipseItem):
    """Connection anchor on a flow node: input (left) or output (right)."""

    def __init__(self, parent_node: GraphNodeItem, port_type: str):
        super().__init__(-5, -5, 10, 10, parent_node)
        self.port_type = port_type  # "in" | "out"
        self.setBrush(QtGui.QBrush(QtGui.QColor("#00a8e8")))
        self.setPen(QtGui.QPen(QtGui.QColor("white"), 1))
        self.setZValue(25)
        self.setAcceptHoverEvents(True)
        self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.CrossCursor))
        tip = "Drag from a right port to a left port on another node to connect."
        if port_type == "in":
            tip = "Incoming connection (drop here)."
        elif port_type == "out":
            tip = "Drag to another node’s left port to connect."
        self.setToolTip(tip)


class FlowChartView(QtWidgets.QGraphicsView):
    """Canvas: Ctrl+wheel zoom, rubber-band select, drag from out-port to in-port."""

    connectionRequested = QtCore.pyqtSignal(object, object)

    def __init__(self, scene: QtWidgets.QGraphicsScene):
        super().__init__(scene)
        self.setViewportUpdateMode(
            QtWidgets.QGraphicsView.ViewportUpdateMode.SmartViewportUpdate
        )
        self.setDragMode(QtWidgets.QGraphicsView.DragMode.RubberBandDrag)
        self.setMouseTracking(True)
        self._connecting = False
        self._src_rect: Optional[GraphNodeItem] = None
        self._temp_path: Optional[QtWidgets.QGraphicsPathItem] = None

    def _pick_port_at(self, scene_pos: QtCore.QPointF) -> Optional[NodePortItem]:
        """Area pick in scene coords — more stable than single-point itemAt under zoom/overlap."""
        sc = self.scene()
        if sc is None:
            return None
        r = QtCore.QRectF(scene_pos.x() - 8, scene_pos.y() - 8, 16, 16)
        items = sc.items(
            r,
            QtCore.Qt.ItemSelectionMode.IntersectsItemShape,
            QtCore.Qt.SortOrder.DescendingOrder,
        )
        for it in items:
            if isinstance(it, NodePortItem):
                return it
            p = it.parentItem()
            while p is not None:
                if isinstance(p, NodePortItem):
                    return p
                p = p.parentItem()
        return None

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            sp = self.mapToScene(event.pos())
            port = self._pick_port_at(sp)
            if isinstance(port, NodePortItem) and port.port_type == "out":
                parent = port.parentItem()
                if isinstance(parent, GraphNodeItem):
                    self._connecting = True
                    self._src_rect = parent
                    self._temp_path = QtWidgets.QGraphicsPathItem()
                    pen = QtGui.QPen(QtGui.QColor("#7dd8f0"), 2, QtCore.Qt.PenStyle.DashLine)
                    self._temp_path.setPen(pen)
                    self._temp_path.setZValue(50)
                    sc = self.scene()
                    if sc is not None:
                        sc.addItem(self._temp_path)
                    self._update_temp_connection(sp)
                    event.accept()
                    return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._connecting and self._temp_path is not None:
            sp = self.mapToScene(event.pos())
            self._update_temp_connection(sp)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if (
            self._connecting
            and event.button() == QtCore.Qt.MouseButton.LeftButton
        ):
            sp = self.mapToScene(event.pos())
            port = self._pick_port_at(sp)
            dst_rect: Optional[GraphNodeItem] = None
            if isinstance(port, NodePortItem) and port.port_type == "in":
                p = port.parentItem()
                if isinstance(p, GraphNodeItem):
                    dst_rect = p
            if (
                self._src_rect is not None
                and dst_rect is not None
                and dst_rect is not self._src_rect
            ):
                self.connectionRequested.emit(self._src_rect, dst_rect)
            if self._temp_path is not None:
                sc = self.scene()
                if sc is not None:
                    sc.removeItem(self._temp_path)
                self._temp_path = None
            self._connecting = False
            self._src_rect = None
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _update_temp_connection(self, mouse_scene_pos: QtCore.QPointF) -> None:
        if self._temp_path is None or self._src_rect is None:
            return
        out_ports = [
            ch
            for ch in self._src_rect.childItems()
            if isinstance(ch, NodePortItem) and ch.port_type == "out"
        ]
        if not out_ports:
            return
        src_pos = out_ports[0].sceneBoundingRect().center()
        dx = mouse_scene_pos.x() - src_pos.x()
        off = max(40.0, min(abs(dx) * 0.35, 140.0))
        c1 = QtCore.QPointF(src_pos.x() + off, src_pos.y())
        c2 = QtCore.QPointF(mouse_scene_pos.x() - off, mouse_scene_pos.y())
        path = QtGui.QPainterPath(src_pos)
        path.cubicTo(c1, c2, mouse_scene_pos)
        self._temp_path.setPath(path)

    def wheelEvent(self, event):
        if event.modifiers() == QtCore.Qt.KeyboardModifier.ControlModifier:
            fac = 1.12 if event.angleDelta().y() > 0 else 1 / 1.12
            self.scale(fac, fac)
            event.accept()
            return
        super().wheelEvent(event)


class ArrowEdge(QtWidgets.QGraphicsPathItem):
    """Bezier edge from source out-port to destination in-port, with arrow head and wide hit shape."""

    def __init__(self, src_node: dict, dst_node: dict):
        super().__init__()
        self._src_node = src_node
        self._dst_node = dst_node
        self._arrow_color = QtGui.QColor(220, 245, 255)
        pen = QtGui.QPen(self._arrow_color)
        pen.setWidth(2)
        pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(QtCore.Qt.PenJoinStyle.RoundJoin)
        self.setPen(pen)
        self.setBrush(QtGui.QBrush(self._arrow_color))
        self.setZValue(0)
        self.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.update_positions()

    def cleanup(self) -> None:
        pass

    def update_positions(self):
        op = self._src_node.get("out_port")
        ip = self._dst_node.get("in_port")
        if op is None or ip is None:
            self.prepareGeometryChange()
            self.setPath(QtGui.QPainterPath())
            return
        p1 = op.sceneBoundingRect().center()
        p2 = ip.sceneBoundingRect().center()
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        dist = math.hypot(dx, dy)
        if dist < 1e-6:
            self.prepareGeometryChange()
            self.setPath(QtGui.QPainterPath())
            return

        off = max(40.0, min(abs(dx) * 0.35, 140.0))
        c1 = QtCore.QPointF(p1.x() + off, p1.y())
        c2 = QtCore.QPointF(p2.x() - off, p2.y())

        curve = QtGui.QPainterPath(p1)
        curve.cubicTo(c1, c2, p2)

        # Tangent at end: proportional to p2 - c2 (Bezier derivative at t=1)
        tx = p2.x() - c2.x()
        ty = p2.y() - c2.y()
        tlen = math.hypot(tx, ty)
        if tlen < 1e-6:
            tx, ty = dx / dist, dy / dist
            tlen = 1.0
        ux, uy = tx / tlen, ty / tlen
        px, py = -uy, ux

        arrow_len = float(min(24.0, max(14.0, dist * 0.14), dist * 0.4))
        wing = arrow_len * 0.65

        tip = QtCore.QPointF(p2.x(), p2.y())
        base = QtCore.QPointF(tip.x() - ux * arrow_len, tip.y() - uy * arrow_len)
        left = QtCore.QPointF(base.x() + px * wing, base.y() + py * wing)
        right = QtCore.QPointF(base.x() - px * wing, base.y() - py * wing)

        head = QtGui.QPainterPath()
        head.moveTo(tip)
        head.lineTo(left)
        head.lineTo(right)
        head.closeSubpath()

        full_path = QtGui.QPainterPath()
        full_path.addPath(curve)
        full_path.addPath(head)

        self.prepareGeometryChange()
        self.setPath(full_path)

    def shape(self) -> QtGui.QPainterPath:
        stroker = QtGui.QPainterPathStroker()
        stroker.setWidth(14)
        stroker.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
        stroker.setJoinStyle(QtCore.Qt.PenJoinStyle.RoundJoin)
        return stroker.createStroke(self.path())

    def refresh_geometry(self):
        """Update path when endpoints move (no scene item churn)."""
        self.update_positions()


class LogWatcher(QtCore.QObject):
    """Watch logs/OUTPUT.txt and emit new lines to the UI."""
    new_line = QtCore.pyqtSignal(str)

    def __init__(self, path: str, parent=None):
        super().__init__(parent)
        self._path = path
        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._check_file)
        self._pos = 0

    def start(self, interval_ms: int = 500):
        self._timer.start(interval_ms)

    def _check_file(self):
        if not os.path.exists(self._path):
            return
        try:
            with open(self._path, "r", encoding="utf-8", errors="ignore") as f:
                f.seek(self._pos)
                data = f.read()
                self._pos = f.tell()
        except OSError:
            return

        if data:
            for line in data.splitlines():
                self.new_line.emit(line)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LabSmith Control")
        self.setWindowIcon(build_app_icon())
        self.resize(1100, 720)
        self.statusBar().setSizeGripEnabled(True)

        self._busy_depth = 0
        self._connect_in_progress = False
        self._connect_thread: QtCore.QThread | None = None
        self._connect_worker: ConnectWorker | None = None

        busy_wrap = QtWidgets.QWidget()
        busy_lay = QtWidgets.QHBoxLayout(busy_wrap)
        busy_lay.setContentsMargins(12, 0, 8, 0)
        busy_lay.setSpacing(8)
        self._busy_spinner = ArcSpinnerWidget(26)
        self._busy_label = QtWidgets.QLabel()
        self._busy_label.setStyleSheet("color: #7dd8f0; font-weight: 600;")
        self._busy_label.hide()
        busy_lay.addWidget(self._busy_spinner)
        busy_lay.addWidget(self._busy_label)
        self.statusBar().addPermanentWidget(busy_wrap)
        self._busy_spinner.hide()

        self._settings = QtCore.QSettings("LabSmith", "LabSmithControl")
        geom = self._settings.value("geometry")
        if geom is not None:
            self.restoreGeometry(geom)

        self._board: LabsmithBoard | None = None

        central = QtWidgets.QWidget(self)
        self.setCentralWidget(central)

        main_layout = QtWidgets.QVBoxLayout(central)

        # Tabs: Manual control + Flow designer
        self.tabs = QtWidgets.QTabWidget()
        main_layout.addWidget(self.tabs)

        manual_tab = QtWidgets.QWidget()
        self.manual_layout = QtWidgets.QVBoxLayout(manual_tab)
        self.tabs.addTab(manual_tab, "Manual Control")

        flow_tab = QtWidgets.QWidget()
        self.flow_layout = QtWidgets.QVBoxLayout(flow_tab)
        self.tabs.addTab(flow_tab, "Flow Designer")

        graph_tab = QtWidgets.QWidget()
        self.graph_layout = QtWidgets.QVBoxLayout(graph_tab)
        self.tabs.addTab(graph_tab, "Flow Graph")

        bus_tab = QtWidgets.QWidget()
        bus_layout = QtWidgets.QVBoxLayout(bus_tab)
        self.bus_text = QtWidgets.QPlainTextEdit()
        self.bus_text.setReadOnly(True)
        self.bus_text.setPlaceholderText(
            "C4AM / C4PM / CEP01 devices appear here after connect (parsed from CmdCreateDeviceList)."
        )
        self.bus_text.setMaximumBlockCount(4000)
        bus_layout.addWidget(self.bus_text, 1)
        bus_btn_row = QtWidgets.QHBoxLayout()
        self.bus_refresh_btn = QtWidgets.QPushButton("Refresh status")
        self.bus_stop_extras_btn = QtWidgets.QPushButton("Stop C4AM / C4PM / CEP01")
        bus_btn_row.addWidget(self.bus_refresh_btn)
        bus_btn_row.addWidget(self.bus_stop_extras_btn)
        bus_btn_row.addStretch()
        bus_layout.addLayout(bus_btn_row)
        self.tabs.addTab(bus_tab, "Bus modules")

        # ===== Manual control tab =====
        # Top connection section
        conn_layout = QtWidgets.QHBoxLayout()
        self.manual_layout.addLayout(conn_layout)

        conn_layout.addWidget(QtWidgets.QLabel("COM Port:"))
        self.port_combo = QtWidgets.QComboBox()
        self.port_combo.setEditable(True)
        self.port_combo.setFixedWidth(220)
        le = self.port_combo.lineEdit()
        if le is not None:
            le.setPlaceholderText("Pick from list or type COM# (e.g. 3)")
        conn_layout.addWidget(self.port_combo)

        self.refresh_ports_btn = QtWidgets.QPushButton("Refresh Ports")
        self.auto_detect_btn = QtWidgets.QPushButton("Auto Detect")
        conn_layout.addWidget(self.refresh_ports_btn)
        conn_layout.addWidget(self.auto_detect_btn)
        self.refresh_ports_btn.setToolTip("Rescan serial ports (requires pyserial).")
        self.auto_detect_btn.setToolTip("Try each COM port until the board connects.")

        self.connect_btn = QtWidgets.QPushButton("Connect Board")
        self.connect_btn.setObjectName("primaryButton")
        self.disconnect_btn = QtWidgets.QPushButton("Disconnect")
        self.disconnect_btn.setEnabled(False)
        conn_layout.addWidget(self.connect_btn)
        conn_layout.addWidget(self.disconnect_btn)

        self.conn_badge = QtWidgets.QLabel()
        self.conn_badge.setMinimumWidth(140)
        self._refresh_conn_badge()
        conn_layout.addWidget(self.conn_badge)
        conn_layout.addStretch()

        # Middle splitter: left = controls, right = log
        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        self.manual_layout.addWidget(splitter, 1)

        left_widget = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 10, 0)
        left_widget.setMinimumWidth(340)
        left_widget.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred,
            QtWidgets.QSizePolicy.Policy.Minimum,
        )
        # Tall control column scrolls; connection bar + log stay fixed beside it.
        self.manual_left_scroll = QtWidgets.QScrollArea()
        self.manual_left_scroll.setWidgetResizable(True)
        self.manual_left_scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.manual_left_scroll.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.manual_left_scroll.setVerticalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.manual_left_scroll.setWidget(left_widget)
        splitter.addWidget(self.manual_left_scroll)

        right_widget = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_widget)
        splitter.addWidget(right_widget)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([650, 420])

        # Syringe control
        self.syringe_group = QtWidgets.QGroupBox("Syringe Control")
        left_layout.addWidget(self.syringe_group)
        s_layout = QtWidgets.QGridLayout(self.syringe_group)

        s_layout.addWidget(QtWidgets.QLabel("Syringe name:"), 0, 0)
        self.syringe_combo = QtWidgets.QComboBox()
        s_layout.addWidget(self.syringe_combo, 0, 1, 1, 3)

        self.syringe_info_label = QtWidgets.QLabel("—")
        self.syringe_info_label.setWordWrap(True)
        self.syringe_info_label.setStyleSheet("color: #a8a8b8; font-size: 10pt;")
        s_layout.addWidget(self.syringe_info_label, 1, 0, 1, 4)

        s_layout.addWidget(QtWidgets.QLabel("Flowrate (µL/min):"), 2, 0)
        self.flowrate_spin = QtWidgets.QDoubleSpinBox()
        self.flowrate_spin.setRange(0.0, 10000.0)
        self.flowrate_spin.setSingleStep(1.0)
        self.flowrate_spin.setDecimals(2)
        self.flowrate_spin.setValue(100.0)
        self.flowrate_spin.setToolTip(
            "Device min/max applied after connect (matches uProcess flow limits)."
        )
        s_layout.addWidget(self.flowrate_spin, 2, 1)
        self.flowrate_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.flowrate_slider.setToolTip("Quick adjust within device range (capped for UI).")
        s_layout.addWidget(self.flowrate_slider, 3, 0, 1, 4)
        _wire_slider_spin(self.flowrate_slider, self.flowrate_spin, 1000, 10000.0)

        s_layout.addWidget(QtWidgets.QLabel("Volume (µL):"), 4, 0)
        self.volume_spin = QtWidgets.QDoubleSpinBox()
        self.volume_spin.setRange(0.0, 100000.0)
        self.volume_spin.setSingleStep(0.5)
        self.volume_spin.setDecimals(2)
        self.volume_spin.setValue(10.0)
        self.volume_spin.setToolTip("Target volume; max stroke from device after connect.")
        s_layout.addWidget(self.volume_spin, 4, 1)
        self.volume_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.volume_slider.setToolTip("Quick adjust 0–500 µL (or device max if lower).")
        s_layout.addWidget(self.volume_slider, 5, 0, 1, 4)
        _wire_slider_spin(self.volume_slider, self.volume_spin, 500, 100000.0)

        self.move_btn = QtWidgets.QPushButton("Execute Move")
        self.stop_syringe_btn = QtWidgets.QPushButton("Stop this syringe")
        self.stop_syringe_btn.setToolTip("CmdStop on selected pump only (uProcess red stop per device).")
        self.stop_board_btn = QtWidgets.QPushButton("StopBoard")
        s_layout.addWidget(self.move_btn, 6, 0, 1, 1)
        s_layout.addWidget(self.stop_syringe_btn, 6, 1, 1, 1)
        s_layout.addWidget(self.stop_board_btn, 6, 2, 1, 2)

        self.monitor_status_cb = QtWidgets.QCheckBox("Live status (≈4 Hz)")
        self.monitor_status_cb.setToolTip(
            "Poll uProcess status: volume, online, moving, stall; manifold valves."
        )
        s_layout.addWidget(self.monitor_status_cb, 7, 0, 1, 1)
        self.syringe_status_label = QtWidgets.QLabel("—")
        self.syringe_status_label.setWordWrap(True)
        self.syringe_status_label.setStyleSheet("color: #c8c8d8; font-size: 9pt;")
        s_layout.addWidget(self.syringe_status_label, 7, 1, 1, 3)

        self.syringe_adv_group = QtWidgets.QGroupBox(
            "Syringe advanced — microstep & 16-bit position (uProcess API)"
        )
        left_layout.addWidget(self.syringe_adv_group)
        ag = QtWidgets.QGridLayout(self.syringe_adv_group)
        ag.addWidget(QtWidgets.QLabel("Microstep direction:"), 0, 0)
        self.micro_dir_combo = QtWidgets.QComboBox()
        self.micro_dir_combo.addItem("Pull in (into syringe)", False)
        self.micro_dir_combo.addItem("Push out (dispense)", True)
        self.micro_dir_combo.setToolTip("CmdSetStepDirection — then repeated CmdMicrostep.")
        ag.addWidget(self.micro_dir_combo, 0, 1)
        ag.addWidget(QtWidgets.QLabel("Step count:"), 0, 2)
        self.microstep_count_spin = QtWidgets.QSpinBox()
        self.microstep_count_spin.setRange(1, 20000)
        self.microstep_count_spin.setValue(10)
        ag.addWidget(self.microstep_count_spin, 0, 3)
        self.microstep_run_btn = QtWidgets.QPushButton("Run microsteps → CmdStop (release windings)")
        self.microstep_run_btn.setToolTip(
            "Calls CmdSetStepDirection, CmdMicrostep ×N, then CmdStop (required to idle motor)."
        )
        ag.addWidget(self.microstep_run_btn, 1, 0, 1, 4)
        ag.addWidget(
            QtWidgets.QLabel("Motor position 0–65535 (CmdMoveToPosition, not µL):"), 2, 0, 1, 2
        )
        self.position16_spin = QtWidgets.QSpinBox()
        self.position16_spin.setRange(0, 65535)
        ag.addWidget(self.position16_spin, 2, 2)
        self.move_position_btn = QtWidgets.QPushButton("CmdMoveToPosition")
        self.move_position_btn.setToolTip("16-bit encoder/position target per uProcess binding.")
        ag.addWidget(self.move_position_btn, 2, 3)

        # Manifold control
        self.manifold_group = QtWidgets.QGroupBox("Manifold Control (4VM)")
        left_layout.addWidget(self.manifold_group)
        m_layout = QtWidgets.QGridLayout(self.manifold_group)

        m_layout.addWidget(QtWidgets.QLabel("Manifold name:"), 0, 0)
        self.manifold_combo = QtWidgets.QComboBox()
        m_layout.addWidget(self.manifold_combo, 0, 1, 1, 3)

        self.manifold_info_label = QtWidgets.QLabel("—")
        self.manifold_info_label.setWordWrap(True)
        self.manifold_info_label.setStyleSheet("color: #a8a8b8; font-size: 10pt;")
        m_layout.addWidget(self.manifold_info_label, 1, 0, 1, 4)

        self.v1_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.v2_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.v3_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.v4_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        # One slider per row — four in a single grid row were ~80px wide each and often
        # unusable in the narrow left column (hard to drag / no hit target).
        for idx, sl in enumerate(
            [self.v1_slider, self.v2_slider, self.v3_slider, self.v4_slider], start=1
        ):
            sl.setRange(0, 1)
            sl.setSingleStep(1)
            sl.setPageStep(1)
            sl.setTracking(True)
            sl.setMaximumHeight(32)
            sl.setMinimumWidth(200)
            sl.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Expanding,
                QtWidgets.QSizePolicy.Policy.Fixed,
            )
            sl.setToolTip(
                f"V{idx} quick: 0/1 passed to CmdSetValves (0=no change, 1=position A). "
                f"For codes 2=closed, 3=B use “4VM native” below."
            )
            row = 1 + idx
            m_layout.addWidget(QtWidgets.QLabel(f"V{idx}:"), row, 0)
            m_layout.addWidget(sl, row, 1, 1, 3)

        self.switch_btn = QtWidgets.QPushButton("Switch valves")
        m_layout.addWidget(self.switch_btn, 6, 0, 1, 4)

        self.manifold_status_label = QtWidgets.QLabel("—")
        self.manifold_status_label.setWordWrap(True)
        self.manifold_status_label.setStyleSheet("color: #c8c8d8; font-size: 9pt;")
        m_layout.addWidget(self.manifold_status_label, 7, 0, 1, 4)

        self.manifold_adv_group = QtWidgets.QGroupBox(
            "4VM native — CmdSetValves / CmdSetValveMotion"
        )
        left_layout.addWidget(self.manifold_adv_group)
        mg = QtWidgets.QGridLayout(self.manifold_adv_group)
        mg.addWidget(
            QtWidgets.QLabel(
                "CmdSetValves codes: 0=no change, 1=position A, 2=closed, 3=position B"
            ),
            0,
            0,
            1,
            8,
        )
        self.native_v_spins = []
        for i in range(4):
            sp = QtWidgets.QSpinBox()
            sp.setRange(0, 3)
            sp.setValue(0)
            self.native_v_spins.append(sp)
            mg.addWidget(QtWidgets.QLabel(f"V{i + 1}:"), 1, i * 2)
            mg.addWidget(sp, 1, i * 2 + 1)
        self.native_valves_btn = QtWidgets.QPushButton("Apply CmdSetValves (native 0–3)")
        mg.addWidget(self.native_valves_btn, 2, 0, 1, 8)
        mg.addWidget(QtWidgets.QLabel("CmdSetValveMotion — valve #"), 3, 0)
        self.motion_valve_spin = QtWidgets.QSpinBox()
        self.motion_valve_spin.setRange(1, 4)
        self.motion_valve_spin.setValue(1)
        mg.addWidget(self.motion_valve_spin, 3, 1)
        mg.addWidget(QtWidgets.QLabel("motion code"), 3, 2)
        self.motion_code_spin = QtWidgets.QSpinBox()
        self.motion_code_spin.setRange(0, 3)
        self.motion_code_spin.setValue(1)
        mg.addWidget(self.motion_code_spin, 3, 3)
        self.motion_one_btn = QtWidgets.QPushButton("Apply single-valve motion")
        mg.addWidget(self.motion_one_btn, 4, 0, 1, 8)

        # Log area
        log_header = QtWidgets.QHBoxLayout()
        log_header.addWidget(
            QtWidgets.QLabel(f"Output log ({os.path.join('logs', 'OUTPUT.txt')}):")
        )
        log_header.addStretch()
        self.open_logs_btn = QtWidgets.QPushButton("Open logs folder")
        self.open_logs_btn.setToolTip("Reveal Python/logs in your file manager.")
        log_header.addWidget(self.open_logs_btn)
        self.clear_log_btn = QtWidgets.QPushButton("Clear log")
        self.clear_log_btn.setToolTip(
            "Clear on-screen log only (does not delete the file under Python/logs/)."
        )
        log_header.addWidget(self.clear_log_btn)
        right_layout.addLayout(log_header)
        self.log_edit = QtWidgets.QPlainTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setPlaceholderText("Hardware and script messages appear here…")
        self.log_edit.setMaximumBlockCount(8000)
        right_layout.addWidget(self.log_edit, 1)

        # Log watcher
        self.log_watcher = LogWatcher(output_txt_path())
        self.log_watcher.new_line.connect(self._append_log)
        self.log_watcher.start()

        # Signal connections
        self.connect_btn.clicked.connect(self._on_connect)
        self.disconnect_btn.clicked.connect(self._on_disconnect)
        self.refresh_ports_btn.clicked.connect(self._refresh_serial_ports)
        self.auto_detect_btn.clicked.connect(self._on_auto_detect)
        self.move_btn.clicked.connect(self._on_move)
        self.stop_syringe_btn.clicked.connect(self._on_stop_syringe)
        self.stop_board_btn.clicked.connect(self._on_stop_board)
        self.switch_btn.clicked.connect(self._on_switch)
        self.clear_log_btn.clicked.connect(self.log_edit.clear)
        self.open_logs_btn.clicked.connect(self._open_logs_folder)

        self._setup_menubar()

        self.syringe_combo.currentIndexChanged.connect(self._on_syringe_selection_changed)
        self.manifold_combo.currentIndexChanged.connect(self._on_manifold_selection_changed)
        self.monitor_status_cb.toggled.connect(self._on_monitor_toggled)
        self._status_timer = QtCore.QTimer(self)
        self._status_timer.setInterval(250)
        self._status_timer.timeout.connect(self._refresh_live_hardware_status)
        self.microstep_run_btn.clicked.connect(self._on_microstep_run)
        self.move_position_btn.clicked.connect(self._on_move_to_position16)
        self.native_valves_btn.clicked.connect(self._on_native_cmd_set_valves)
        self.motion_one_btn.clicked.connect(self._on_cmd_set_valve_motion)
        self.bus_refresh_btn.clicked.connect(self._refresh_bus_modules_panel)
        self.bus_stop_extras_btn.clicked.connect(self._on_stop_bus_extra_modules)

        # ===== Flow designer tab =====
        self._init_flow_designer()

        # Data for flow designer
        self.flow_steps = []  # list of dicts

        # ===== Flow graph tab =====
        self.graph_nodes = []  # list of dicts with "type", params, "item", ports, incoming/outgoing, label_item
        self.graph_edges = []  # list of {"id", "src", "dst", "item": ArrowEdge}
        self._graph_edge_counter = itertools.count(1)
        self._init_flow_graph()
        self._graph_refresh_nodes_bar()

        # Initial serial scan
        self._refresh_serial_ports()
        self._restore_session_prefs()
        self._sync_connection_ui()
        self._update_status_bar()

    def _setup_menubar(self):
        mb = self.menuBar()
        file_m = mb.addMenu("&File")
        act_logs = QtGui.QAction("Open &logs folder", self)
        act_logs.setShortcut("Ctrl+Shift+O")
        act_logs.triggered.connect(self._open_logs_folder)
        file_m.addAction(act_logs)
        file_m.addSeparator()
        act_quit = QtGui.QAction("E&xit", self)
        act_quit.setShortcut("Ctrl+Q")
        act_quit.triggered.connect(self.close)
        file_m.addAction(act_quit)

        view_m = mb.addMenu("&View")
        act_clear = QtGui.QAction("&Clear log view", self)
        act_clear.setShortcut("Ctrl+L")
        act_clear.triggered.connect(self.log_edit.clear)
        view_m.addAction(act_clear)
        act_ports = QtGui.QAction("&Refresh serial ports", self)
        act_ports.setShortcut("F5")
        act_ports.triggered.connect(self._refresh_serial_ports)
        view_m.addAction(act_ports)

        help_m = mb.addMenu("&Help")
        act_about = QtGui.QAction("&About LabSmith Control", self)
        act_about.triggered.connect(self._show_about)
        help_m.addAction(act_about)

    def closeEvent(self, event):
        self._settings.setValue("geometry", self.saveGeometry())
        self._settings.setValue("last_tab", self.tabs.currentIndex())
        le = self.port_combo.lineEdit()
        if le is not None:
            self._settings.setValue("last_com_text", self.port_combo.currentText().strip())
        super().closeEvent(event)

    def _open_logs_folder(self):
        path = log_directory()
        url = QtCore.QUrl.fromLocalFile(path)
        if not QtGui.QDesktopServices.openUrl(url):
            QtWidgets.QMessageBox.warning(
                self, "Open folder", f"Could not open:\n{path}"
            )

    def _show_about(self):
        QtWidgets.QMessageBox.about(
            self,
            "About LabSmith Control",
            "LabSmith Control\n\n"
            "PyQt6 desktop UI for LabSmith uProcess hardware.\n"
            "Session logs: Python/logs/OUTPUT.txt\n\n"
            "Shortcuts:\n"
            "  Ctrl+L          Clear log view\n"
            "  F5              Refresh serial ports\n"
            "  Ctrl+Shift+O    Open logs folder\n"
            "  Ctrl+Q          Exit",
        )

    def _restore_session_prefs(self):
        last = self._settings.value("last_com_text", "")
        le = self.port_combo.lineEdit()
        if le is not None and last:
            self.port_combo.setEditText(str(last))
        try:
            ti = int(self._settings.value("last_tab", 0) or 0)
        except (TypeError, ValueError):
            ti = 0
        if 0 <= ti < self.tabs.count():
            self.tabs.setCurrentIndex(ti)

    def _save_last_com_pref(self):
        le = self.port_combo.lineEdit()
        if le is not None:
            self._settings.setValue("last_com_text", self.port_combo.currentText().strip())

    def _begin_busy(self, message: str = ""):
        self._busy_depth += 1
        if self._busy_depth == 1:
            self._busy_spinner.start()
            if message.strip():
                self._busy_label.setText(message)
                self._busy_label.show()
            else:
                self._busy_label.hide()
        elif message.strip():
            self._set_busy_message(message)

    def _end_busy(self):
        if self._busy_depth > 0:
            self._busy_depth -= 1
        if self._busy_depth == 0:
            self._busy_spinner.stop()
            self._busy_label.hide()
            self._busy_label.clear()

    def _set_busy_message(self, message: str):
        self._busy_label.setText(message)
        self._busy_label.setVisible(bool(message and str(message).strip()))

    def _refresh_conn_badge(self):
        ok = self._board is not None and getattr(self._board, "isConnected", False)
        partial = self._board is not None and not ok
        if ok:
            self.conn_badge.setText("  ● Connected  ")
            self.conn_badge.setStyleSheet(
                "QLabel { padding: 6px 14px; border-radius: 16px; font-weight: 700; "
                "font-size: 10pt; background-color: #143d2a; color: #6ee7b7; "
                "border: 1px solid #2d6b4a; }"
            )
        elif partial:
            self.conn_badge.setText("  ○ No link  ")
            self.conn_badge.setStyleSheet(
                "QLabel { padding: 6px 14px; border-radius: 16px; font-weight: 700; "
                "font-size: 10pt; background-color: #3d3514; color: #f0d060; "
                "border: 1px solid #6b5a2d; }"
            )
        else:
            self.conn_badge.setText("  ○ Offline  ")
            self.conn_badge.setStyleSheet(
                "QLabel { padding: 6px 14px; border-radius: 16px; font-weight: 700; "
                "font-size: 10pt; background-color: #352830; color: #d0a0a8; "
                "border: 1px solid #5a3a40; }"
            )

    def _on_flow_table_double_clicked(self, row: int, _col: int):
        if row < 0 or row >= len(self.flow_steps):
            return
        self.flow_table.selectRow(row)
        step = self.flow_steps[row]
        dlg = StepParamDialog(self, self._board, step)
        if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self._refresh_flow_row(row)
            self._build_param_editor_for_step(step)

    # Log
    def _append_log(self, line: str):
        self.log_edit.appendPlainText(line)
        sb = self.log_edit.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _sync_connection_ui(self):
        """COM row follows link state; hardware *actions* only when connected.

        Do not disable entire QGroupBoxes when offline — that greys out all child
        combos/spins and feels like “nothing is selectable”. Offline editing of
        flow parameters and control presets stays usable.
        """
        has_board = self._board is not None
        ok = has_board and getattr(self._board, "isConnected", False)
        if not ok:
            self._status_timer.stop()
            self.monitor_status_cb.blockSignals(True)
            self.monitor_status_cb.setChecked(False)
            self.monitor_status_cb.blockSignals(False)
        busy_conn = self._connect_in_progress
        # COM: editable while disconnected; block during background connect attempt.
        self.port_combo.setEnabled(not ok and not busy_conn)
        self.refresh_ports_btn.setEnabled(not ok and not busy_conn)
        self.auto_detect_btn.setEnabled(not ok and not busy_conn)
        self.connect_btn.setEnabled(not ok and not busy_conn)
        self.disconnect_btn.setEnabled(ok)
        # Hardware commands only when uProcess link is up.
        for w in (
            self.move_btn,
            self.stop_syringe_btn,
            self.stop_board_btn,
            self.switch_btn,
            self.microstep_run_btn,
            self.move_position_btn,
            self.native_valves_btn,
            self.motion_one_btn,
        ):
            w.setEnabled(ok)
        self.monitor_status_cb.setEnabled(ok)
        self.bus_refresh_btn.setEnabled(ok)
        self.bus_stop_extras_btn.setEnabled(ok)
        self.run_flow_btn.setEnabled(ok)
        self.graph_run_btn.setEnabled(ok)
        self._refresh_conn_badge()

    def _update_status_bar(self):
        if self._board is None or not getattr(self._board, "isConnected", False):
            hint = (
                "Disconnected — type COM# or Refresh/Auto Detect (needs pyserial)."
                if list_ports is not None
                else "Disconnected — type COM# in the port box, or: pip install pyserial"
            )
            self.statusBar().showMessage(hint)
            return
        dev = self.port_combo.currentData() or ""
        n_s = (
            len(self._board.SPS01)
            if getattr(self._board, "SPS01", None) is not None
            else 0
        )
        n_m = (
            len(self._board.C4VM)
            if getattr(self._board, "C4VM", None) is not None
            else 0
        )
        n_am = (
            len(self._board.C4AM)
            if getattr(self._board, "C4AM", None) is not None
            else 0
        )
        n_pm = (
            len(self._board.C4PM)
            if getattr(self._board, "C4PM", None) is not None
            else 0
        )
        n_ep = (
            len(self._board.CEP01)
            if getattr(self._board, "CEP01", None) is not None
            else 0
        )
        self.statusBar().showMessage(
            f"Connected · {dev} · SPS:{n_s} 4VM:{n_m} · C4AM:{n_am} C4PM:{n_pm} CEP01:{n_ep}"
        )

    def _schedule_graph_edge_positions(self):
        """Keep arrows glued to nodes while dragging."""
        for rec in self.graph_edges:
            rec["item"].refresh_geometry()

    def _graph_node_dict_from_rect(self, rect_item: GraphNodeItem) -> Optional[dict]:
        for n in self.graph_nodes:
            if n.get("item") is rect_item:
                return n
        return None

    def _graph_remove_edge_record(self, rec: dict) -> None:
        """Remove one edge from scene, graph_edges, and node incoming/outgoing lists."""
        if rec not in self.graph_edges:
            return
        s, d = rec["src"], rec["dst"]
        if rec in s.get("outgoing", []):
            s["outgoing"].remove(rec)
        if rec in d.get("incoming", []):
            d["incoming"].remove(rec)
        rec["item"].cleanup()
        self.graph_scene.removeItem(rec["item"])
        self.graph_edges.remove(rec)

    def _graph_create_edge(self, src_node: dict, dst_node: dict) -> None:
        """Single-chain mode: at most one out per node, one in per node; new wire replaces old."""
        if src_node is dst_node:
            return
        for r in list(src_node.get("outgoing", [])):
            self._graph_remove_edge_record(r)
        for r in list(dst_node.get("incoming", [])):
            self._graph_remove_edge_record(r)
        edge = ArrowEdge(src_node, dst_node)
        self.graph_scene.addItem(edge)
        rec = {
            "id": next(self._graph_edge_counter),
            "src": src_node,
            "dst": dst_node,
            "item": edge,
        }
        src_node.setdefault("outgoing", []).append(rec)
        dst_node.setdefault("incoming", []).append(rec)
        self.graph_edges.append(rec)

    def _on_graph_connection_requested(self, src_rect: GraphNodeItem, dst_rect: GraphNodeItem):
        src_n = self._graph_node_dict_from_rect(src_rect)
        dst_n = self._graph_node_dict_from_rect(dst_rect)
        if src_n is None or dst_n is None:
            return
        self._graph_create_edge(src_n, dst_n)

    def _validate_graph_for_run(self) -> None:
        """Raise ValueError with a readable message if the graph cannot run as a single chain."""
        nodes = self.graph_nodes
        if not nodes:
            raise ValueError("No nodes to run.")
        for n in nodes:
            ni = len(n.get("incoming", []))
            no = len(n.get("outgoing", []))
            if ni > 1:
                raise ValueError(
                    "A node has more than one incoming connection. "
                    "Single-chain mode allows at most one wire into each node — delete extras."
                )
            if no > 1:
                raise ValueError(
                    "A node has more than one outgoing connection. "
                    "Single-chain mode allows at most one wire from each node."
                )
        n = len(nodes)
        m = len(self.graph_edges)
        if n == 1:
            return
        if m == 0:
            raise ValueError(
                "You have multiple nodes but no connections. "
                "Drag from a right (out) port to a left (in) port to form one chain."
            )
        starts = [x for x in nodes if len(x.get("incoming", [])) == 0]
        if len(starts) != 1:
            raise ValueError(
                f"Need exactly one start node (no incoming wire); found {len(starts)}."
            )
        ends = [x for x in nodes if len(x.get("outgoing", [])) == 0]
        if len(ends) != 1:
            raise ValueError(
                f"Need exactly one end node (no outgoing wire); found {len(ends)}."
            )
        if m != n - 1:
            raise ValueError(
                f"For {n} nodes in one chain, expect {n - 1} connection(s); found {m}."
            )

    def _get_graph_execution_order(self) -> list:
        """Topological order along explicit edges (single chain after validation)."""
        nodes = self.graph_nodes
        if not nodes:
            return []
        node_set = set(nodes)
        indeg = {id(n): 0 for n in nodes}
        outgoing = {id(n): [] for n in nodes}
        for rec in self.graph_edges:
            s, d = rec["src"], rec["dst"]
            if s not in node_set or d not in node_set:
                continue
            outgoing[id(s)].append(d)
            indeg[id(d)] += 1
        queue = [n for n in nodes if indeg[id(n)] == 0]
        order = []
        while queue:
            n = queue.pop(0)
            order.append(n)
            for nxt in outgoing[id(n)]:
                indeg[id(nxt)] -= 1
                if indeg[id(nxt)] == 0:
                    queue.append(nxt)
        if len(order) != len(nodes):
            raise ValueError(
                "The graph has a cycle or a disconnected island. "
                "Use a single chain: one start → … → one end, with no loops."
            )
        return order

    def _graph_fit_view(self):
        self.graph_view.resetTransform()
        br = self.graph_scene.itemsBoundingRect()
        if br.isValid() and not br.isEmpty():
            self.graph_view.fitInView(
                br.adjusted(-48, -48, 48, 48),
                QtCore.Qt.AspectRatioMode.KeepAspectRatio,
            )

    # Connect / disconnect
    def _on_connect(self):
        if self._board is not None:
            QtWidgets.QMessageBox.information(self, "Info", "Already connected.")
            return
        if self._connect_in_progress:
            return

        port = self._get_selected_port_number()
        if port is None:
            QtWidgets.QMessageBox.warning(
                self, "Error", "Please select a COM port first."
            )
            return

        self._connect_in_progress = True
        self._begin_busy("Connecting to hardware…")
        self._sync_connection_ui()

        self._connect_thread = QtCore.QThread(self)
        self._connect_worker = ConnectWorker(port)
        self._connect_worker.moveToThread(self._connect_thread)
        self._connect_thread.started.connect(self._connect_worker.work)
        self._connect_worker.finished.connect(self._on_connect_worker_finished)
        self._connect_thread.start()

    def _on_connect_worker_finished(self, board, err: str):
        self._end_busy()
        self._connect_in_progress = False
        if self._connect_thread is not None:
            self._connect_thread.quit()
            self._connect_thread.wait(8000)
            self._connect_thread.deleteLater()
            self._connect_thread = None
        if self._connect_worker is not None:
            self._connect_worker.deleteLater()
        self._connect_worker = None

        if board is not None:
            self._board = board
            self._populate_device_names()
            self._refresh_bus_modules_panel()
            self._save_last_com_pref()
        elif err:
            self._board = None
            QtWidgets.QMessageBox.critical(
                self, "Connection failed", f"Error creating LabsmithBoard:\n{err}"
            )

        self._sync_connection_ui()
        self._update_status_bar()

    def _on_disconnect(self):
        if self._board is None:
            return
        try:
            msg = self._board.Disconnect()
            self._append_log(str(msg))
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Disconnect error", f"Error while disconnecting:\n{e}")
        finally:
            self._status_timer.stop()
            self.monitor_status_cb.setChecked(False)
            self._board = None
            self.syringe_combo.clear()
            self.manifold_combo.clear()
            self.syringe_info_label.setText("—")
            self.manifold_info_label.setText("—")
            self.syringe_status_label.setText("—")
            self.manifold_status_label.setText("—")
            self.bus_text.clear()
            self._sync_connection_ui()
            self._update_status_bar()

    def _refresh_serial_ports(self):
        """Populate COM port combo from system serial ports."""
        current_data = self.port_combo.currentData()
        typed = self.port_combo.currentText().strip()
        self.port_combo.clear()
        if list_ports is None:
            le = self.port_combo.lineEdit()
            if le is not None:
                le.setPlaceholderText(
                    "No port list — type COM number (e.g. 3) or pip install pyserial"
                )
            if typed:
                self.port_combo.setEditText(typed)
            self.statusBar().showMessage(
                "Install pyserial to list ports: pip install pyserial",
                8000,
            )
            return

        ports = sorted(list_ports.comports(), key=lambda p: p.device)
        for p in ports:
            label = f"{p.device} - {p.description}"
            self.port_combo.addItem(label, p.device)

        if current_data:
            idx = self.port_combo.findData(current_data)
            if idx >= 0:
                self.port_combo.setCurrentIndex(idx)
            elif typed:
                self.port_combo.setEditText(typed)
        elif typed:
            self.port_combo.setEditText(typed)

    def _get_selected_port_number(self):
        """Convert selected COMx to integer x used by LabsmithBoard."""
        device = self.port_combo.currentData()
        port = parse_com_port_to_int(device) if device else None
        if port is not None:
            return port
        return parse_com_port_to_int(self.port_combo.currentText())

    def _try_connect_port(self, port_num: int):
        """Try creating board on a specific port; return board or None."""
        try:
            candidate = LabsmithBoard(port_num)
            if getattr(candidate, "isConnected", False):
                return candidate
            # Not connected according to board flag, close if possible
            try:
                candidate.Disconnect()
            except Exception:
                pass
            return None
        except Exception:
            return None

    def _on_auto_detect(self):
        """Try each COM port and connect to the first valid LabSmith board."""
        if self._board is not None:
            QtWidgets.QMessageBox.information(
                self, "Info", "Already connected. Disconnect first if needed."
            )
            return

        if list_ports is None:
            QtWidgets.QMessageBox.information(
                self,
                "Auto Detect",
                "Port scanning needs pyserial:\n  pip install pyserial\n\n"
                "Until then, type the COM number (e.g. 3) in the port box and click Connect Board.",
            )
            return

        self._refresh_serial_ports()
        if self.port_combo.count() == 0:
            QtWidgets.QMessageBox.warning(
                self, "No ports", "No serial ports found on this computer."
            )
            return

        self._begin_busy("Auto-detecting…")
        try:
            n = self.port_combo.count()
            for i in range(n):
                self.port_combo.setCurrentIndex(i)
                port_num = self._get_selected_port_number()
                if port_num is None:
                    continue
                self._set_busy_message(f"Trying COM{port_num}… ({i + 1}/{n})")
                QtWidgets.QApplication.processEvents()
                board = self._try_connect_port(port_num)
                if board is not None:
                    self._board = board
                    self._populate_device_names()
                    self._refresh_bus_modules_panel()
                    self._save_last_com_pref()
                    self._sync_connection_ui()
                    self._update_status_bar()
                    QtWidgets.QMessageBox.information(
                        self,
                        "Auto Detect",
                        f"Connected successfully on COM{port_num}.",
                    )
                    return

            QtWidgets.QMessageBox.warning(
                self,
                "Auto Detect",
                "No valid LabSmith board found on available COM ports.",
            )
        finally:
            self._end_busy()

    def _populate_device_names(self):
        """Populate syringe and manifold combo boxes from connected board."""
        try:
            self.syringe_combo.clear()
            self.manifold_combo.clear()
            if self._board.SPS01 is not None:
                for dev in self._board.SPS01:
                    if dev is not None:
                        addr = getattr(dev, "address", None)
                        label = (
                            f"{dev.name} (Addr {addr})"
                            if addr is not None and str(addr) != ""
                            else str(dev.name)
                        )
                        self.syringe_combo.addItem(label, dev.name)
            if self._board.C4VM is not None:
                for dev in self._board.C4VM:
                    if dev is not None:
                        addr = getattr(dev, "address", None)
                        label = (
                            f"{dev.name} (Addr {addr})"
                            if addr is not None and str(addr) != ""
                            else str(dev.name)
                        )
                        self.manifold_combo.addItem(label, dev.name)
        except Exception:
            pass
        self._on_syringe_selection_changed()
        self._on_manifold_selection_changed()

    def _syringe_logical_name(self) -> str:
        data = self.syringe_combo.currentData()
        if data is not None and str(data).strip() != "":
            return str(data).strip()
        return self.syringe_combo.currentText().strip()

    def _manifold_logical_name(self) -> str:
        data = self.manifold_combo.currentData()
        if data is not None and str(data).strip() != "":
            return str(data).strip()
        return self.manifold_combo.currentText().strip()

    def _current_syringe(self):
        if self._board is None or not getattr(self._board, "isConnected", False):
            return None
        name = self._syringe_logical_name()
        if not name:
            return None
        try:
            idx = self._board.FindIndexS(name)
            return self._board.SPS01[idx]
        except Exception:
            return None

    def _current_manifold(self):
        if self._board is None or not getattr(self._board, "isConnected", False):
            return None
        name = self._manifold_logical_name()
        if not name:
            return None
        try:
            idx = self._board.FindIndexM(name)
            return self._board.C4VM[idx]
        except Exception:
            return None

    def _apply_syringe_hw_ranges(self, s):
        """Clamp flow / volume widgets to uProcess-reported limits (like uProcess speed bar)."""
        try:
            mn = float(s.minFlowrate)
            mx = float(s.maxFlowrate)
            if mx <= mn:
                mx = mn + 1e-6
            self.flowrate_spin.setRange(mn, mx)
            cur = self.flowrate_spin.value()
            if cur < mn:
                self.flowrate_spin.setValue(mn)
            elif cur > mx:
                self.flowrate_spin.setValue(mx)
            sl_max = int(min(1000, max(1, round(mx))))
            self.flowrate_slider.blockSignals(True)
            self.flowrate_slider.setRange(0, sl_max)
            fv = self.flowrate_spin.value()
            self.flowrate_slider.setValue(int(round(min(max(fv, mn), float(sl_max)))))
            self.flowrate_slider.blockSignals(False)

            maxv = max(0.0, float(s.maxVolume))
            self.volume_spin.setRange(0.0, maxv)
            vc = self.volume_spin.value()
            if vc > maxv:
                self.volume_spin.setValue(maxv)
            self.volume_slider.blockSignals(True)
            if maxv <= 0:
                self.volume_slider.setRange(0, 0)
                self.volume_slider.setValue(0)
            else:
                vs_cap = int(min(500, max(1, round(maxv))))
                self.volume_slider.setRange(0, vs_cap)
                self.volume_slider.setValue(int(round(min(vc, float(vs_cap)))))
            self.volume_slider.blockSignals(False)
        except Exception:
            pass

    def _on_syringe_selection_changed(self):
        s = self._current_syringe()
        if s is None:
            self.syringe_info_label.setText("—")
            return
        try:
            self._apply_syringe_hw_ranges(s)
            self.syringe_info_label.setText(
                f"Diameter: {s.diameter} · Max stroke: {float(s.maxVolume):.4g} µL · "
                f"Flow limits: {float(s.minFlowrate):.4g}–{float(s.maxFlowrate):.4g} µL/min"
            )
        except Exception:
            self.syringe_info_label.setText(str(getattr(s, "name", "?")))

    def _on_manifold_selection_changed(self):
        m = self._current_manifold()
        if m is None:
            self.manifold_info_label.setText("—")
            return
        addr = getattr(m, "address", None)
        self.manifold_info_label.setText(
            f"4VM · Addr {addr}" if addr is not None else f"4VM · {m.name}"
        )

    def _on_monitor_toggled(self, on: bool):
        if on:
            self._refresh_live_hardware_status()
            self._status_timer.start()
        else:
            self._status_timer.stop()

    def _refresh_live_hardware_status(self):
        if self._board is None or not getattr(self._board, "isConnected", False):
            return
        s = self._current_syringe()
        if s is not None:
            try:
                s.UpdateStatus()
                vol = getattr(s, "volume_ul", None)
                vol_s = f"{vol:.3f}" if vol is not None else "—"
                self.syringe_status_label.setText(
                    f"Online: {s.FlagIsOnline} · Moving: {s.FlagIsMoving} · Done: {s.FlagIsDone} · "
                    f"Stalled: {s.FlagIsStalled} · In/Out: {s.FlagIsMovingIn}/{s.FlagIsMovingOut} · "
                    f"Vol µL: {vol_s}"
                )
            except Exception as e:
                self.syringe_status_label.setText(f"Syringe status: {e}")
        else:
            self.syringe_status_label.setText("—")

        m = self._current_manifold()
        if m is not None:
            try:
                m.UpdateStatus()
                miss = getattr(m, "V_missing", []) or []
                vst = getattr(m, "V_status", []) or []
                miss_bits = []
                for i in range(4):
                    mis = miss[i] if i < len(miss) else False
                    miss_bits.append(f"V{i + 1}{' (missing)' if mis else ''}")
                vs_bits = []
                for i in range(4):
                    vs_bits.append(str(vst[i]) if i < len(vst) and vst[i] is not None else "?")
                stuck = getattr(m, "FlagIsStuck", False)
                self.manifold_status_label.setText(
                    f"Online: {m.FlagIsOnline} · Done: {m.FlagIsDone} · Moving: {m.FlagIsMoving} · "
                    f"Stuck: {stuck} · "
                    f"{', '.join(miss_bits)} · Status: [{', '.join(vs_bits)}]"
                )
            except Exception as e:
                self.manifold_status_label.setText(f"Manifold status: {e}")
        else:
            self.manifold_status_label.setText("—")

    # Syringe actions
    def _on_move(self):
        if self._board is None:
            QtWidgets.QMessageBox.warning(self, "Not connected", "Please connect the board first.")
            return
        name = self._syringe_logical_name()
        if not name:
            QtWidgets.QMessageBox.warning(self, "Error", "No syringe name available.")
            return
        flow = self.flowrate_spin.value()
        vol = self.volume_spin.value()
        try:
            self._board.Move(name, flow, vol)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Execution error", f"Error calling Move:\n{e}")

    def _on_stop_syringe(self):
        if self._board is None:
            return
        s = self._current_syringe()
        if s is None:
            QtWidgets.QMessageBox.warning(self, "Error", "Select a valid syringe.")
            return
        try:
            s.Stop()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Execution error", f"Error stopping syringe:\n{e}")

    def _on_stop_board(self):
        if self._board is None:
            return
        try:
            self._board.StopBoard()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Execution error", f"Error calling StopBoard:\n{e}")

    # Manifold actions
    def _on_switch(self):
        if self._board is None:
            QtWidgets.QMessageBox.warning(self, "Not connected", "Please connect the board first.")
            return
        name = self._manifold_logical_name()
        if not name:
            QtWidgets.QMessageBox.warning(self, "Error", "No manifold name available.")
            return
        v1 = self.v1_slider.value()
        v2 = self.v2_slider.value()
        v3 = self.v3_slider.value()
        v4 = self.v4_slider.value()
        try:
            idx = self._board.FindIndexM(name)
            dev = self._board.C4VM[idx]
            dev.SwitchValves(v1, v2, v3, v4)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Execution error", f"Error switching valves:\n{e}")

    def _on_microstep_run(self):
        s = self._current_syringe()
        if s is None:
            QtWidgets.QMessageBox.warning(self, "Error", "Select a syringe.")
            return
        push = bool(self.micro_dir_combo.currentData())
        n = self.microstep_count_spin.value()
        try:
            if not s.BeginManualMicrostep(push):
                QtWidgets.QMessageBox.warning(
                    self, "Microstep", "CmdSetStepDirection returned false."
                )
                return
            s.MicrostepRepeat(n)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Microstep", str(e))
        finally:
            try:
                s.Stop()
            except Exception:
                pass

    def _on_move_to_position16(self):
        s = self._current_syringe()
        if s is None:
            QtWidgets.QMessageBox.warning(self, "Error", "Select a syringe.")
            return
        pos = self.position16_spin.value()
        try:
            ok = s.MoveToPosition16(pos)
            if not ok:
                QtWidgets.QMessageBox.warning(
                    self, "Position", "CmdMoveToPosition returned false."
                )
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Position", str(e))

    def _on_native_cmd_set_valves(self):
        m = self._current_manifold()
        if m is None:
            QtWidgets.QMessageBox.warning(self, "Error", "Select a manifold.")
            return
        v = [sp.value() for sp in self.native_v_spins]
        try:
            m.SetValvesNative(v[0], v[1], v[2], v[3])
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Native valves", str(e))

    def _on_cmd_set_valve_motion(self):
        m = self._current_manifold()
        if m is None:
            QtWidgets.QMessageBox.warning(self, "Error", "Select a manifold.")
            return
        vi = self.motion_valve_spin.value()
        code = self.motion_code_spin.value()
        try:
            ok = m.SetSingleValveMotion(vi, code)
            if not ok:
                QtWidgets.QMessageBox.warning(
                    self, "Valve motion", "CmdSetValveMotion returned false."
                )
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Valve motion", str(e))

    def _refresh_bus_modules_panel(self):
        self.bus_text.clear()
        if self._board is None or not getattr(self._board, "isConnected", False):
            self.bus_text.setPlainText("Not connected.")
            return
        lines = []
        for label, arr in (
            ("C4AM (analog)", getattr(self._board, "C4AM", None)),
            ("C4PM (power)", getattr(self._board, "C4PM", None)),
            ("CEP01", getattr(self._board, "CEP01", None)),
        ):
            if arr is None or len(arr) == 0:
                lines.append(f"{label}: (none)")
                continue
            lines.append(f"{label}:")
            for i in range(len(arr)):
                d = arr[i]
                try:
                    d.UpdateStatus()
                    on = getattr(d, "FlagIsOnline", "?")
                    dn = getattr(d, "FlagIsDone", "?")
                    lines.append(
                        f"  [{i}] {getattr(d, 'name', '?')}  Addr {getattr(d, 'address', '?')}  "
                        f"Online={on} Done={dn}"
                    )
                except Exception as e:
                    lines.append(f"  [{i}] (read error: {e})")
        self.bus_text.setPlainText("\n".join(lines))

    def _on_stop_bus_extra_modules(self):
        if self._board is None:
            return
        for arr_name in ("C4AM", "C4PM", "CEP01"):
            arr = getattr(self._board, arr_name, None)
            if arr is None:
                continue
            for i in range(len(arr)):
                try:
                    arr[i].Stop()
                except Exception:
                    pass
        self._refresh_bus_modules_panel()

    # ===== Flow designer methods =====
    def _init_flow_designer(self):
        """Build the linear flow editor UI."""
        # Layout: left = available components, center = steps table, right = parameter editor
        container = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(container)
        container.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.MinimumExpanding,
            QtWidgets.QSizePolicy.Policy.MinimumExpanding,
        )
        container.setMinimumHeight(360)
        flow_scroll = QtWidgets.QScrollArea()
        flow_scroll.setWidgetResizable(True)
        flow_scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        flow_scroll.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        flow_scroll.setVerticalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        flow_scroll.setWidget(container)
        self.flow_layout.addWidget(flow_scroll)

        # Left: components list
        left_box = QtWidgets.QGroupBox("Components")
        left_layout = QtWidgets.QVBoxLayout(left_box)
        self.flow_components_list = QtWidgets.QListWidget()
        self.flow_components_list.addItems(
            ["Move syringe", "Wait", "Switch valves", "Stop board"]
        )
        if self.flow_components_list.count() > 0:
            self.flow_components_list.setCurrentRow(0)
        left_layout.addWidget(self.flow_components_list)
        self.add_step_btn = QtWidgets.QPushButton("Add selected")
        left_layout.addWidget(self.add_step_btn)
        left_layout.addStretch()

        # Center: steps table
        center_box = QtWidgets.QGroupBox("Flow steps (executed from top to bottom)")
        center_layout = QtWidgets.QVBoxLayout(center_box)
        self.flow_table = QtWidgets.QTableWidget(0, 3)
        self.flow_table.setHorizontalHeaderLabels(["#", "Type", "Details"])
        self.flow_table.horizontalHeader().setStretchLastSection(True)
        self.flow_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.flow_table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        center_layout.addWidget(self.flow_table)
        fd_hint = QtWidgets.QLabel("Double-click a step row to open the parameter editor.")
        fd_hint.setObjectName("hintLabel")
        center_layout.addWidget(fd_hint)

        btn_layout = QtWidgets.QHBoxLayout()
        self.remove_step_btn = QtWidgets.QPushButton("Remove step")
        self.run_flow_btn = QtWidgets.QPushButton("Run flow")
        btn_layout.addWidget(self.remove_step_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.run_flow_btn)
        center_layout.addLayout(btn_layout)

        # Right: parameter editor
        right_box = QtWidgets.QGroupBox("Step parameters")
        right_layout = QtWidgets.QVBoxLayout(right_box)
        self.param_container = QtWidgets.QWidget()
        self.param_layout = QtWidgets.QFormLayout(self.param_container)
        right_layout.addWidget(self.param_container)
        right_layout.addStretch()

        # Add three panels to main layout
        layout.addWidget(left_box, 1)
        layout.addWidget(center_box, 2)
        layout.addWidget(right_box, 2)

        # Connections
        self.add_step_btn.clicked.connect(self._on_add_step)
        self.remove_step_btn.clicked.connect(self._on_remove_step)
        self.run_flow_btn.clicked.connect(self._on_run_flow)
        self.flow_table.selectionModel().selectionChanged.connect(self._on_flow_selection_changed)
        self.flow_table.cellDoubleClicked.connect(self._on_flow_table_double_clicked)

    def _flow_selected_component_text(self) -> Optional[str]:
        lst = self.flow_components_list
        for it in lst.selectedItems():
            return it.text()
        r = lst.currentRow()
        if r < 0 and lst.count() > 0:
            lst.setCurrentRow(0)
            r = 0
        if 0 <= r < lst.count():
            item = lst.item(r)
            return item.text() if item is not None else None
        return None

    def _on_add_step(self):
        row = self.flow_table.rowCount()
        step_type = self._flow_selected_component_text()
        if not step_type:
            QtWidgets.QMessageBox.information(
                self,
                "Add step",
                "请在左侧列表中选择一种步骤类型（或点击列表第一项后再试）。",
            )
            return

        # Default step dict
        if step_type == "Move syringe":
            step = {
                "type": "Move syringe",
                "syringe": "",
                "flowrate": 100.0,
                "volume": 10.0,
            }
        elif step_type == "Wait":
            step = {
                "type": "Wait",
                "seconds": 1.0,
            }
        elif step_type == "Switch valves":
            step = {
                "type": "Switch valves",
                "manifold": "",
                "v1": 0,
                "v2": 0,
                "v3": 0,
                "v4": 0,
            }
        else:
            step = {
                "type": "Stop board",
            }

        self.flow_steps.append(step)
        self.flow_table.insertRow(row)
        self._refresh_flow_row(row)
        self.flow_table.selectRow(row)

    def _on_remove_step(self):
        row = self.flow_table.currentRow()
        if row < 0 or row >= len(self.flow_steps):
            QtWidgets.QMessageBox.information(
                self, "Remove step", "请先在表格中选中要删除的一行。"
            )
            return
        self.flow_table.removeRow(row)
        del self.flow_steps[row]
        # Renumber remaining rows
        for r in range(self.flow_table.rowCount()):
            item = self.flow_table.item(r, 0)
            if item is not None:
                item.setText(str(r + 1))
        self._clear_param_editor()

    def _refresh_flow_row(self, row: int):
        if row < 0 or row >= len(self.flow_steps):
            return
        step = self.flow_steps[row]
        num_item = QtWidgets.QTableWidgetItem(str(row + 1))
        num_item.setFlags(num_item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
        type_item = QtWidgets.QTableWidgetItem(step["type"])
        type_item.setFlags(type_item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
        details_item = QtWidgets.QTableWidgetItem(self._describe_step(step))
        details_item.setFlags(details_item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
        self.flow_table.setItem(row, 0, num_item)
        self.flow_table.setItem(row, 1, type_item)
        self.flow_table.setItem(row, 2, details_item)

    def _describe_step(self, step: dict) -> str:
        t = step.get("type")
        if t == "Move syringe":
            return f"{step.get('syringe', '')}: {step.get('flowrate', '')} ul/min, {step.get('volume', '')} ul"
        if t == "Wait":
            return f"Wait {step.get('seconds', '')} s"
        if t == "Switch valves":
            return f"{step.get('manifold', '')}: V=({step.get('v1', 0)},{step.get('v2', 0)},{step.get('v3', 0)},{step.get('v4', 0)})"
        if t == "Stop board":
            return "Stop board"
        return ""

    def _clear_param_editor(self):
        while self.param_layout.count():
            item = self.param_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def _on_flow_selection_changed(self, *_):
        row = self.flow_table.currentRow()
        if row < 0 or row >= len(self.flow_steps):
            self._clear_param_editor()
            return
        step = self.flow_steps[row]
        self._build_param_editor_for_step(step)

    def _build_param_editor_for_step(self, step: dict):
        self._clear_param_editor()
        t = step.get("type")

        if t == "Move syringe":
            # Syringe name
            syringe_combo = QtWidgets.QComboBox()
            names = []
            if self._board is not None and getattr(self._board, "SPS01", None) is not None:
                for dev in self._board.SPS01:
                    if dev is not None:
                        names.append(str(dev.name))
            syringe_combo.addItems(names)
            if step.get("syringe") and step["syringe"] in names:
                syringe_combo.setCurrentText(step["syringe"])
            syringe_combo.currentTextChanged.connect(
                lambda text: self._update_move_step("syringe", text)
            )

            # Flowrate
            flow_edit = QtWidgets.QLineEdit(str(step.get("flowrate", 100.0)))
            flow_edit.editingFinished.connect(
                lambda fe=flow_edit: self._update_move_step("flowrate", fe.text())
            )

            # Volume
            vol_edit = QtWidgets.QLineEdit(str(step.get("volume", 10.0)))
            vol_edit.editingFinished.connect(
                lambda ve=vol_edit: self._update_move_step("volume", ve.text())
            )

            self.param_layout.addRow("Syringe name:", syringe_combo)
            self.param_layout.addRow("Flowrate (ul/min):", flow_edit)
            self.param_layout.addRow("Volume (ul):", vol_edit)

        elif t == "Wait":
            sec_edit = QtWidgets.QLineEdit(str(step.get("seconds", 1.0)))
            sec_edit.editingFinished.connect(
                lambda se=sec_edit: self._update_wait_step(se.text())
            )
            self.param_layout.addRow("Seconds:", sec_edit)

        elif t == "Switch valves":
            manifold_combo = QtWidgets.QComboBox()
            names = []
            if self._board is not None and getattr(self._board, "C4VM", None) is not None:
                for dev in self._board.C4VM:
                    if dev is not None:
                        names.append(str(dev.name))
            manifold_combo.addItems(names)
            if step.get("manifold") and step["manifold"] in names:
                manifold_combo.setCurrentText(step["manifold"])
            manifold_combo.currentTextChanged.connect(
                lambda text: self._update_switch_step("manifold", text)
            )

            v1_spin = QtWidgets.QSpinBox()
            v2_spin = QtWidgets.QSpinBox()
            v3_spin = QtWidgets.QSpinBox()
            v4_spin = QtWidgets.QSpinBox()
            for spin, key in [
                (v1_spin, "v1"),
                (v2_spin, "v2"),
                (v3_spin, "v3"),
                (v4_spin, "v4"),
            ]:
                spin.setRange(0, 1)
                spin.setValue(int(step.get(key, 0)))
                spin.valueChanged.connect(
                    lambda val, k=key: self._update_switch_step(k, val)
                )

            self.param_layout.addRow("Manifold name:", manifold_combo)
            self.param_layout.addRow("V1:", v1_spin)
            self.param_layout.addRow("V2:", v2_spin)
            self.param_layout.addRow("V3:", v3_spin)
            self.param_layout.addRow("V4:", v4_spin)

        else:
            info = QtWidgets.QLabel("Stop board: call StopBoard() when reaching this step.")
            self.param_layout.addRow(info)

    def _update_move_step(self, field: str, value):
        row = self.flow_table.currentRow()
        if row < 0 or row >= len(self.flow_steps):
            return
        step = self.flow_steps[row]
        if field in ("flowrate", "volume"):
            try:
                step[field] = float(value)
            except ValueError:
                return
        else:
            step[field] = value
        self._refresh_flow_row(row)

    def _update_wait_step(self, value):
        row = self.flow_table.currentRow()
        if row < 0 or row >= len(self.flow_steps):
            return
        step = self.flow_steps[row]
        try:
            step["seconds"] = float(value)
        except ValueError:
            return
        self._refresh_flow_row(row)

    def _update_switch_step(self, field: str, value):
        row = self.flow_table.currentRow()
        if row < 0 or row >= len(self.flow_steps):
            return
        step = self.flow_steps[row]
        if field in ("v1", "v2", "v3", "v4"):
            step[field] = int(value)
        else:
            step[field] = value
        self._refresh_flow_row(row)

    def _execute_one_flow_step(self, step: dict) -> None:
        """Run one step dict on the connected board; raises on invalid config or hardware error."""
        if self._board is None:
            raise RuntimeError("Board not connected.")
        t = step.get("type")
        if t == "Move syringe":
            name = step.get("syringe", "")
            flow = float(step.get("flowrate", 0.0))
            vol = float(step.get("volume", 0.0))
            if not name:
                raise ValueError("Syringe name is empty.")
            self._board.Move(name, flow, vol)
        elif t == "Wait":
            sec = float(step.get("seconds", 0.0))
            if sec > 0:
                interruptible_sleep(sec)
        elif t == "Switch valves":
            name = step.get("manifold", "")
            if not name:
                raise ValueError("Manifold name is empty.")
            idx_m = self._board.FindIndexM(name)
            dev = self._board.C4VM[idx_m]
            dev.SwitchValves(
                int(step.get("v1", 0)),
                int(step.get("v2", 0)),
                int(step.get("v3", 0)),
                int(step.get("v4", 0)),
            )
        elif t == "Stop board":
            self._board.StopBoard()
        else:
            raise ValueError(f"Unknown step type: {t!r}")

    def _on_run_flow(self):
        if self._board is None:
            QtWidgets.QMessageBox.warning(self, "Not connected", "Please connect the board first.")
            return
        if not self.flow_steps:
            QtWidgets.QMessageBox.information(self, "No steps", "Please add at least one step.")
            return

        n = len(self.flow_steps)
        self._begin_busy("Running flow…")
        try:
            for idx, step in enumerate(self.flow_steps, start=1):
                t = step.get("type")
                self._set_busy_message(f"Flow {idx}/{n}: {t}…")
                QtWidgets.QApplication.processEvents()
                try:
                    self._execute_one_flow_step(step)
                except Exception as e:
                    QtWidgets.QMessageBox.critical(
                        self,
                        "Execution error",
                        f"Error executing step {idx} ({t}):\n{e}",
                    )
                    break
        finally:
            self._end_busy()

    # ===== Flow graph (visual flowchart) =====
    def _init_flow_graph(self):
        """Visual flowchart: explicit edges (drag right port → left port)."""
        container = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(container)
        self.graph_layout.addWidget(container)

        # Left: components
        left_box = QtWidgets.QGroupBox("Components")
        left_layout = QtWidgets.QVBoxLayout(left_box)
        self.graph_components_list = QtWidgets.QListWidget()
        self.graph_components_list.addItems(
            ["Move syringe", "Wait", "Switch valves", "Stop board"]
        )
        if self.graph_components_list.count() > 0:
            self.graph_components_list.setCurrentRow(0)
        left_layout.addWidget(self.graph_components_list)
        self.graph_components_list.setToolTip(
            "Left-click a module type to add a node to the canvas (same as Add node)."
        )

        bar_box = QtWidgets.QGroupBox("Nodes on canvas")
        bar_layout_outer = QtWidgets.QVBoxLayout(bar_box)
        self.graph_nodes_bar_inner = QtWidgets.QWidget()
        self.graph_nodes_bar_layout = QtWidgets.QVBoxLayout(self.graph_nodes_bar_inner)
        self.graph_nodes_bar_layout.setContentsMargins(4, 4, 4, 4)
        self.graph_nodes_bar_layout.setSpacing(4)
        bar_scroll = QtWidgets.QScrollArea()
        bar_scroll.setWidgetResizable(True)
        bar_scroll.setWidget(self.graph_nodes_bar_inner)
        bar_scroll.setMaximumHeight(140)
        bar_scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        bar_scroll.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        bar_layout_outer.addWidget(bar_scroll)
        left_layout.addWidget(bar_box)

        self.graph_add_btn = QtWidgets.QPushButton("Add node")
        self.graph_edit_btn = QtWidgets.QPushButton("Edit selected node")
        self.graph_delete_edge_btn = QtWidgets.QPushButton("Delete selected connection")
        self.graph_clear_btn = QtWidgets.QPushButton("Clear all")
        left_layout.addWidget(self.graph_add_btn)
        left_layout.addWidget(self.graph_edit_btn)
        left_layout.addWidget(self.graph_delete_edge_btn)
        left_layout.addWidget(self.graph_clear_btn)
        left_layout.addStretch()

        # Center: graphics scene/view
        center_box = QtWidgets.QGroupBox("Flow chart")
        center_layout = QtWidgets.QVBoxLayout(center_box)
        self.graph_scene = QtWidgets.QGraphicsScene()
        self.graph_view = FlowChartView(self.graph_scene)
        tip = QtWidgets.QLabel(
            "Tip: Ctrl+wheel zoom. Drag out→in to wire. Single-chain only: one in / one out per node, "
            "one start and one end; new wire replaces an old one on those ports. Run validates then executes."
        )
        tip.setStyleSheet("color: palette(mid); font-size: 11px;")
        center_layout.addWidget(tip)
        center_layout.addWidget(self.graph_view)

        # Bottom controls
        ctrl_layout = QtWidgets.QHBoxLayout()
        self.graph_fit_btn = QtWidgets.QPushButton("Fit view")
        self.graph_fit_btn.setToolTip("Reset zoom and frame all nodes.")
        self.graph_run_btn = QtWidgets.QPushButton("Run graph")
        self.graph_run_btn.setObjectName("primaryButton")
        ctrl_layout.addWidget(self.graph_fit_btn)
        ctrl_layout.addStretch()
        ctrl_layout.addWidget(self.graph_run_btn)
        center_layout.addLayout(ctrl_layout)

        layout.addWidget(left_box, 1)
        layout.addWidget(center_box, 4)

        # Signals
        self.graph_add_btn.clicked.connect(self._on_graph_add_node)
        self.graph_components_list.itemClicked.connect(self._on_graph_component_item_clicked)
        self.graph_edit_btn.clicked.connect(self._on_graph_edit_node)
        self.graph_delete_edge_btn.clicked.connect(self._on_graph_delete_edge)
        self.graph_clear_btn.clicked.connect(self._on_graph_clear)
        self.graph_run_btn.clicked.connect(self._on_graph_run)
        self.graph_fit_btn.clicked.connect(self._graph_fit_view)
        self.graph_view.connectionRequested.connect(self._on_graph_connection_requested)

    def _graph_selected_component_text(self) -> Optional[str]:
        lst = self.graph_components_list
        for it in lst.selectedItems():
            return it.text()
        r = lst.currentRow()
        if r < 0 and lst.count() > 0:
            lst.setCurrentRow(0)
            r = 0
        if 0 <= r < lst.count():
            item = lst.item(r)
            return item.text() if item is not None else None
        return None

    def _graph_step_for_graphics_item(self, item):
        """Map click on node rect or its child label to the step dict."""
        while item is not None:
            for n in self.graph_nodes:
                if n.get("item") is item:
                    return n
            item = item.parentItem()
        return None

    def _on_graph_component_item_clicked(self, item: QtWidgets.QListWidgetItem):
        """Left-click a module type in the list → add that node to the canvas."""
        t = item.text().strip() if item is not None else ""
        if t:
            self._graph_add_node_from_type(t)

    def _graph_step_dict_for_type(self, step_type: str) -> dict:
        """Default step payload for a graph node type (same as flow designer)."""
        if step_type == "Move syringe":
            return {
                "type": "Move syringe",
                "syringe": "",
                "flowrate": 100.0,
                "volume": 10.0,
            }
        if step_type == "Wait":
            return {
                "type": "Wait",
                "seconds": 1.0,
            }
        if step_type == "Switch valves":
            return {
                "type": "Switch valves",
                "manifold": "",
                "v1": 0,
                "v2": 0,
                "v3": 0,
                "v4": 0,
            }
        return {"type": "Stop board"}

    def _graph_add_node_from_type(self, step_type: str) -> None:
        if not step_type:
            return
        step = self._graph_step_dict_for_type(step_type)

        index = len(self.graph_nodes)
        node_width, node_height = 150, 50
        x = 0
        y = index * (node_height + 20)
        rect_item = GraphNodeItem(
            QtCore.QRectF(0, 0, node_width, node_height),
            on_moved=self._schedule_graph_edge_positions,
        )
        rect_item.setPen(QtGui.QPen(ACCENT, 2))
        rect_item.setBrush(QtGui.QBrush(QtGui.QColor(40, 42, 54)))
        self.graph_scene.addItem(rect_item)
        rect_item.setPos(x, y)

        label = self.graph_scene.addSimpleText(step_type)
        label.setBrush(QtGui.QBrush(QtGui.QColor("white")))
        label.setParentItem(rect_item)
        label.setAcceptedMouseButtons(QtCore.Qt.MouseButton.NoButton)
        label_rect = label.boundingRect()
        label.setPos(
            (node_width - label_rect.width()) / 2,
            (node_height - label_rect.height()) / 2,
        )

        cy = node_height / 2
        step["in_port"] = NodePortItem(rect_item, "in")
        step["in_port"].setPos(0, cy)
        step["out_port"] = NodePortItem(rect_item, "out")
        step["out_port"].setPos(node_width, cy)
        step["incoming"] = []
        step["outgoing"] = []
        step["label_item"] = label

        step["item"] = rect_item
        self.graph_nodes.append(step)
        self._graph_refresh_nodes_bar()

    def _graph_refresh_nodes_bar(self) -> None:
        """Rebuild the left-panel list of canvas nodes with Delete buttons."""
        lay = self.graph_nodes_bar_layout
        while lay.count():
            item = lay.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        if not self.graph_nodes:
            hint = QtWidgets.QLabel("No nodes yet — click a module above.")
            hint.setStyleSheet("color: #888898; font-size: 10pt;")
            hint.setWordWrap(True)
            lay.addWidget(hint)
            return

        for i, n in enumerate(self.graph_nodes):
            row = QtWidgets.QWidget()
            h = QtWidgets.QHBoxLayout(row)
            h.setContentsMargins(0, 0, 0, 0)
            title = n.get("type", "?")
            lbl = QtWidgets.QLabel(f"{i + 1}. {title}")
            lbl.setStyleSheet("color: #d0d0dc;")
            del_btn = QtWidgets.QPushButton("Delete")
            del_btn.setFixedWidth(72)
            del_btn.setToolTip("Remove this node from the canvas (and its wires).")
            del_btn.clicked.connect(
                lambda _checked=False, node=n: self._graph_delete_node(node)
            )
            h.addWidget(lbl, 1)
            h.addWidget(del_btn)
            lay.addWidget(row)

    def _graph_delete_node(self, node: dict) -> None:
        """Remove a node and any edges touching it."""
        if node not in self.graph_nodes:
            return
        seen: set[int] = set()
        for r in list(node.get("incoming", [])) + list(node.get("outgoing", [])):
            rid = id(r)
            if rid in seen:
                continue
            seen.add(rid)
            self._graph_remove_edge_record(r)
        self.graph_scene.removeItem(node["item"])
        self.graph_nodes.remove(node)
        self._graph_refresh_nodes_bar()

    def _on_graph_add_node(self):
        step_type = self._graph_selected_component_text()
        if not step_type:
            QtWidgets.QMessageBox.information(
                self,
                "Add node",
                "请在左侧列表中选择一种节点类型（或点击列表第一项后再试）。",
            )
            return
        self._graph_add_node_from_type(step_type)

    def _on_graph_delete_edge(self):
        """Delete currently selected connection line."""
        selected_items = self.graph_scene.selectedItems()
        if not selected_items:
            QtWidgets.QMessageBox.information(
                self,
                "Delete connection",
                "请在画布上点击选中一条连接线（箭头），再按此按钮删除。",
            )
            return
        for item in selected_items:
            if isinstance(item, ArrowEdge):
                for rec in list(self.graph_edges):
                    if rec["item"] is item:
                        self._graph_remove_edge_record(rec)
                        break

    def _on_graph_edit_node(self):
        selected_items = self.graph_scene.selectedItems()
        if not selected_items:
            QtWidgets.QMessageBox.information(
                self,
                "Edit node",
                "请先在画布上点击选中一个流程节点（方框），再编辑参数。",
            )
            return
        item = selected_items[0]
        node = self._graph_step_for_graphics_item(item)
        if node is None:
            QtWidgets.QMessageBox.information(
                self,
                "Edit node",
                "当前选中项不是流程节点。请点击节点方框（或空白处取消选中后重试）。",
            )
            return

        dlg = StepParamDialog(self, self._board, node)
        if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            item: QtWidgets.QGraphicsRectItem = node["item"]
            old_lbl = node.get("label_item")
            if old_lbl is not None:
                self.graph_scene.removeItem(old_lbl)
            text = self._describe_step(node)
            label = self.graph_scene.addSimpleText(text if text else node["type"])
            label.setBrush(QtGui.QBrush(QtGui.QColor("white")))
            label.setParentItem(item)
            label.setAcceptedMouseButtons(QtCore.Qt.MouseButton.NoButton)
            label_rect = label.boundingRect()
            rect = item.rect()
            label.setPos(
                (rect.width() - label_rect.width()) / 2,
                (rect.height() - label_rect.height()) / 2,
            )
            node["label_item"] = label

    def _on_graph_clear(self):
        self.graph_edges.clear()
        self.graph_scene.clear()
        self.graph_nodes.clear()
        self._graph_refresh_nodes_bar()

    def _on_graph_run(self):
        if self._board is None:
            QtWidgets.QMessageBox.warning(
                self, "Not connected", "Please connect the board first."
            )
            return
        if not self.graph_nodes:
            QtWidgets.QMessageBox.information(
                self, "No nodes", "Please add at least one node."
            )
            return
        try:
            self._validate_graph_for_run()
            exec_order = self._get_graph_execution_order()
        except ValueError as e:
            QtWidgets.QMessageBox.warning(self, "Graph error", str(e))
            return

        n = len(exec_order)
        self._begin_busy("Running graph…")
        try:
            for idx, step in enumerate(exec_order, start=1):
                t = step.get("type")
                self._set_busy_message(f"Graph {idx}/{n}: {t}…")
                QtWidgets.QApplication.processEvents()
                try:
                    self._execute_one_flow_step(step)
                except Exception as e:
                    QtWidgets.QMessageBox.critical(
                        self,
                        "Execution error",
                        f"Error executing node {idx} ({t}):\n{e}",
                    )
                    break
        finally:
            self._end_busy()


class StepParamDialog(QtWidgets.QDialog):
    """Dialog to edit parameters of a flow step / graph node."""

    def __init__(self, parent, board: LabsmithBoard | None, step: dict):
        super().__init__(parent)
        self.setWindowTitle("Edit node parameters")
        self.setWindowIcon(build_app_icon())
        self._board = board
        self._step = step

        layout = QtWidgets.QFormLayout(self)
        t = step.get("type")

        if t == "Move syringe":
            self.syringe_combo = QtWidgets.QComboBox()
            self.syringe_combo.setEditable(True)
            le = self.syringe_combo.lineEdit()
            if le is not None:
                le.setPlaceholderText("Device name (type or pick after connect)")
            names = []
            if self._board is not None and getattr(self._board, "SPS01", None) is not None:
                for dev in self._board.SPS01:
                    if dev is not None:
                        names.append(str(dev.name))
            self.syringe_combo.addItems(names)
            cur = (step.get("syringe") or "").strip()
            if cur:
                if cur in names:
                    self.syringe_combo.setCurrentText(cur)
                else:
                    self.syringe_combo.setEditText(cur)

            self.flow_edit = QtWidgets.QLineEdit(str(step.get("flowrate", 100.0)))
            self.vol_edit = QtWidgets.QLineEdit(str(step.get("volume", 10.0)))

            layout.addRow("Syringe name:", self.syringe_combo)
            layout.addRow("Flowrate (ul/min):", self.flow_edit)
            layout.addRow("Volume (ul):", self.vol_edit)

        elif t == "Wait":
            self.sec_edit = QtWidgets.QLineEdit(str(step.get("seconds", 1.0)))
            layout.addRow("Seconds:", self.sec_edit)

        elif t == "Switch valves":
            self.manifold_combo = QtWidgets.QComboBox()
            self.manifold_combo.setEditable(True)
            lem = self.manifold_combo.lineEdit()
            if lem is not None:
                lem.setPlaceholderText("Manifold name (type or pick after connect)")
            names = []
            if self._board is not None and getattr(self._board, "C4VM", None) is not None:
                for dev in self._board.C4VM:
                    if dev is not None:
                        names.append(str(dev.name))
            self.manifold_combo.addItems(names)
            curm = (step.get("manifold") or "").strip()
            if curm:
                if curm in names:
                    self.manifold_combo.setCurrentText(curm)
                else:
                    self.manifold_combo.setEditText(curm)

            self.v1_spin = QtWidgets.QSpinBox()
            self.v2_spin = QtWidgets.QSpinBox()
            self.v3_spin = QtWidgets.QSpinBox()
            self.v4_spin = QtWidgets.QSpinBox()
            for spin, key in [
                (self.v1_spin, "v1"),
                (self.v2_spin, "v2"),
                (self.v3_spin, "v3"),
                (self.v4_spin, "v4"),
            ]:
                spin.setRange(0, 1)
                spin.setValue(int(step.get(key, 0)))

            layout.addRow("Manifold name:", self.manifold_combo)
            layout.addRow("V1:", self.v1_spin)
            layout.addRow("V2:", self.v2_spin)
            layout.addRow("V3:", self.v3_spin)
            layout.addRow("V4:", self.v4_spin)

        else:
            info = QtWidgets.QLabel("Stop board: no parameters.")
            layout.addRow(info)

        btn_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addRow(btn_box)

    def accept(self):
        t = self._step.get("type")
        try:
            if t == "Move syringe":
                self._step["syringe"] = self.syringe_combo.currentText().strip()
                self._step["flowrate"] = float(self.flow_edit.text().strip())
                self._step["volume"] = float(self.vol_edit.text().strip())
            elif t == "Wait":
                self._step["seconds"] = float(self.sec_edit.text().strip())
            elif t == "Switch valves":
                self._step["manifold"] = self.manifold_combo.currentText().strip()
                self._step["v1"] = int(self.v1_spin.value())
                self._step["v2"] = int(self.v2_spin.value())
                self._step["v3"] = int(self.v3_spin.value())
                self._step["v4"] = int(self.v4_spin.value())
        except ValueError:
            QtWidgets.QMessageBox.warning(
                self, "Input error", "Please enter valid numeric values."
            )
            return
        super().accept()


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("LabSmith Control")
    app.setWindowIcon(build_app_icon())
    apply_app_theme(app)
    apply_modern_stylesheet(app)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

