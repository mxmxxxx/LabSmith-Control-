import sys
import os
import time
import math
from PyQt6 import QtWidgets, QtCore, QtGui

from LabsmithBoard import LabsmithBoard


class ArrowEdge(QtWidgets.QGraphicsPathItem):
    """Directed edge with arrow head between two node items."""

    def __init__(self, src_item: QtWidgets.QGraphicsItem, dst_item: QtWidgets.QGraphicsItem):
        super().__init__()
        self.src_item = src_item
        self.dst_item = dst_item
        pen = QtGui.QPen(QtGui.QColor("white"))
        pen.setWidth(2)
        self.setPen(pen)
        self.setZValue(-1)  # draw under nodes
        self.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.update_positions()

    def update_positions(self):
        p1 = self.src_item.sceneBoundingRect().center()
        p2 = self.dst_item.sceneBoundingRect().center()

        path = QtGui.QPainterPath(p1)
        path.lineTo(p2)
        self.setPath(path)

        # Arrow head at p2
        line_vec = QtCore.QLineF(p1, p2)
        angle = line_vec.angle()  # degrees
        arrow_size = 10.0

        # Two points for arrowhead
        angle1 = math.radians(angle + 150)
        angle2 = math.radians(angle - 150)
        p3 = QtCore.QPointF(
            p2.x() + arrow_size * math.cos(angle1),
            p2.y() - arrow_size * math.sin(angle1),
        )
        p4 = QtCore.QPointF(
            p2.x() + arrow_size * math.cos(angle2),
            p2.y() - arrow_size * math.sin(angle2),
        )

        arrow_path = QtGui.QPainterPath(p2)
        arrow_path.lineTo(p3)
        arrow_path.moveTo(p2)
        arrow_path.lineTo(p4)

        full_path = QtGui.QPainterPath()
        full_path.addPath(path)
        full_path.addPath(arrow_path)
        self.setPath(full_path)


class LogWatcher(QtCore.QObject):
    """Watch OUTPUT.txt and emit new lines to the UI."""
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
        self.setWindowTitle("LabSmith Control UI (PyQt6)")
        self.resize(1000, 600)

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

        # ===== Manual control tab =====
        # Top connection section
        conn_layout = QtWidgets.QHBoxLayout()
        self.manual_layout.addLayout(conn_layout)

        conn_layout.addWidget(QtWidgets.QLabel("COM Port (integer):"))
        self.port_edit = QtWidgets.QLineEdit()
        self.port_edit.setPlaceholderText("e.g. 3")
        self.port_edit.setFixedWidth(80)
        conn_layout.addWidget(self.port_edit)

        self.connect_btn = QtWidgets.QPushButton("Connect Board")
        self.disconnect_btn = QtWidgets.QPushButton("Disconnect")
        self.disconnect_btn.setEnabled(False)
        conn_layout.addWidget(self.connect_btn)
        conn_layout.addWidget(self.disconnect_btn)
        conn_layout.addStretch()

        # Middle splitter: left = controls, right = log
        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        self.manual_layout.addWidget(splitter, 1)

        left_widget = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left_widget)
        splitter.addWidget(left_widget)

        right_widget = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_widget)
        splitter.addWidget(right_widget)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        # Syringe control
        syringe_group = QtWidgets.QGroupBox("Syringe Control")
        left_layout.addWidget(syringe_group)
        s_layout = QtWidgets.QGridLayout(syringe_group)

        s_layout.addWidget(QtWidgets.QLabel("Syringe name:"), 0, 0)
        self.syringe_combo = QtWidgets.QComboBox()
        s_layout.addWidget(self.syringe_combo, 0, 1, 1, 3)

        s_layout.addWidget(QtWidgets.QLabel("Flowrate (ul/min):"), 1, 0)
        self.flowrate_edit = QtWidgets.QLineEdit()
        self.flowrate_edit.setPlaceholderText("e.g. 100")
        s_layout.addWidget(self.flowrate_edit, 1, 1)

        s_layout.addWidget(QtWidgets.QLabel("Volume (ul):"), 1, 2)
        self.volume_edit = QtWidgets.QLineEdit()
        self.volume_edit.setPlaceholderText("e.g. 10")
        s_layout.addWidget(self.volume_edit, 1, 3)

        self.move_btn = QtWidgets.QPushButton("Execute Move")
        self.stop_board_btn = QtWidgets.QPushButton("StopBoard")
        s_layout.addWidget(self.move_btn, 2, 0, 1, 2)
        s_layout.addWidget(self.stop_board_btn, 2, 2, 1, 2)

        # Manifold control
        manifold_group = QtWidgets.QGroupBox("Manifold Control (4VM)")
        left_layout.addWidget(manifold_group)
        m_layout = QtWidgets.QGridLayout(manifold_group)

        m_layout.addWidget(QtWidgets.QLabel("Manifold name:"), 0, 0)
        self.manifold_combo = QtWidgets.QComboBox()
        m_layout.addWidget(self.manifold_combo, 0, 1, 1, 3)

        self.v1_spin = QtWidgets.QSpinBox()
        self.v2_spin = QtWidgets.QSpinBox()
        self.v3_spin = QtWidgets.QSpinBox()
        self.v4_spin = QtWidgets.QSpinBox()
        for idx, spin in enumerate([self.v1_spin, self.v2_spin, self.v3_spin, self.v4_spin], start=1):
            spin.setRange(0, 1)
            m_layout.addWidget(QtWidgets.QLabel(f"V{idx}:"), 1, (idx - 1) * 2)
            m_layout.addWidget(spin, 1, (idx - 1) * 2 + 1)

        self.switch_btn = QtWidgets.QPushButton("Switch valves")
        m_layout.addWidget(self.switch_btn, 2, 0, 1, 4)

        left_layout.addStretch()

        # Log area
        right_layout.addWidget(QtWidgets.QLabel("Output log (OUTPUT.txt):"))
        self.log_edit = QtWidgets.QPlainTextEdit()
        self.log_edit.setReadOnly(True)
        right_layout.addWidget(self.log_edit, 1)

        # Log watcher
        self.log_watcher = LogWatcher(os.path.join(os.getcwd(), "OUTPUT.txt"))
        self.log_watcher.new_line.connect(self._append_log)
        self.log_watcher.start()

        # Signal connections
        self.connect_btn.clicked.connect(self._on_connect)
        self.disconnect_btn.clicked.connect(self._on_disconnect)
        self.move_btn.clicked.connect(self._on_move)
        self.stop_board_btn.clicked.connect(self._on_stop_board)
        self.switch_btn.clicked.connect(self._on_switch)

        # ===== Flow designer tab =====
        self._init_flow_designer()

        # Data for flow designer
        self.flow_steps = []  # list of dicts

        # ===== Flow graph tab =====
        self._init_flow_graph()
        self.graph_nodes = []  # list of dicts with "type", params, "item"
        self.graph_edges = []  # list of ArrowEdge

    # Log
    def _append_log(self, line: str):
        self.log_edit.appendPlainText(line)
        self.log_edit.verticalScrollBar().setValue(self.log_edit.verticalScrollBar().maximum())

    # Connect / disconnect
    def _on_connect(self):
        if self._board is not None:
            QtWidgets.QMessageBox.information(self, "Info", "Already connected.")
            return
        text = self.port_edit.text().strip()
        if not text.isdigit():
            QtWidgets.QMessageBox.warning(self, "Error", "Please enter an integer COM port number, e.g. 3.")
            return
        port = int(text)
        try:
            self._board = LabsmithBoard(port)
        except Exception as e:
            self._board = None
            QtWidgets.QMessageBox.critical(self, "Connection failed", f"Error creating LabsmithBoard:\n{e}")
            return

        # Populate device names
        try:
            self.syringe_combo.clear()
            self.manifold_combo.clear()
            if self._board.SPS01 is not None:
                for dev in self._board.SPS01:
                    if dev is not None:
                        self.syringe_combo.addItem(str(dev.name))
            if self._board.C4VM is not None:
                for dev in self._board.C4VM:
                    if dev is not None:
                        self.manifold_combo.addItem(str(dev.name))
        except Exception:
            # Ignore errors when populating combo boxes to keep UI alive
            pass

        self.connect_btn.setEnabled(False)
        self.disconnect_btn.setEnabled(True)

    def _on_disconnect(self):
        if self._board is None:
            return
        try:
            msg = self._board.Disconnect()
            self._append_log(str(msg))
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Disconnect error", f"Error while disconnecting:\n{e}")
        finally:
            self._board = None
            self.connect_btn.setEnabled(True)
            self.disconnect_btn.setEnabled(False)

    # Syringe actions
    def _on_move(self):
        if self._board is None:
            QtWidgets.QMessageBox.warning(self, "Not connected", "Please connect the board first.")
            return
        name = self.syringe_combo.currentText().strip()
        if not name:
            QtWidgets.QMessageBox.warning(self, "Error", "No syringe name available.")
            return
        try:
            flow = float(self.flowrate_edit.text().strip())
            vol = float(self.volume_edit.text().strip())
        except ValueError:
            QtWidgets.QMessageBox.warning(self, "Input error", "Flowrate and volume must be numeric.")
            return
        try:
            self._board.Move(name, flow, vol)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Execution error", f"Error calling Move:\n{e}")

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
        name = self.manifold_combo.currentText().strip()
        if not name:
            QtWidgets.QMessageBox.warning(self, "Error", "No manifold name available.")
            return
        v1 = self.v1_spin.value()
        v2 = self.v2_spin.value()
        v3 = self.v3_spin.value()
        v4 = self.v4_spin.value()
        try:
            idx = self._board.FindIndexM(name)
            dev = self._board.C4VM[idx]
            dev.SwitchValves(v1, v2, v3, v4)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Execution error", f"Error switching valves:\n{e}")

    # ===== Flow designer methods =====
    def _init_flow_designer(self):
        """Build the linear flow editor UI."""
        # Layout: left = available components, center = steps table, right = parameter editor
        container = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(container)
        self.flow_layout.addWidget(container)

        # Left: components list
        left_box = QtWidgets.QGroupBox("Components")
        left_layout = QtWidgets.QVBoxLayout(left_box)
        self.flow_components_list = QtWidgets.QListWidget()
        self.flow_components_list.addItems(
            ["Move syringe", "Wait", "Switch valves", "Stop board"]
        )
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

    def _on_add_step(self):
        row = self.flow_table.rowCount()
        selected_items = self.flow_components_list.selectedItems()
        if not selected_items:
            return
        step_type = selected_items[0].text()

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

    def _on_run_flow(self):
        if self._board is None:
            QtWidgets.QMessageBox.warning(self, "Not connected", "Please connect the board first.")
            return
        if not self.flow_steps:
            QtWidgets.QMessageBox.information(self, "No steps", "Please add at least one step.")
            return

        for idx, step in enumerate(self.flow_steps, start=1):
            t = step.get("type")
            QtWidgets.QApplication.processEvents()
            try:
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
                        time.sleep(sec)
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
            except Exception as e:
                QtWidgets.QMessageBox.critical(
                    self,
                    "Execution error",
                    f"Error executing step {idx} ({t}):\n{e}",
                )
                break

    # ===== Flow graph (visual flowchart) =====
    def _init_flow_graph(self):
        """Simple visual flowchart: nodes with automatic sequential connections."""
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
        left_layout.addWidget(self.graph_components_list)
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
        self.graph_view = QtWidgets.QGraphicsView(self.graph_scene)
        self.graph_view.setRenderHints(
            QtGui.QPainter.RenderHint.Antialiasing
            | QtGui.QPainter.RenderHint.TextAntialiasing
        )
        center_layout.addWidget(self.graph_view)

        # Bottom controls
        ctrl_layout = QtWidgets.QHBoxLayout()
        self.graph_run_btn = QtWidgets.QPushButton("Run graph")
        ctrl_layout.addStretch()
        ctrl_layout.addWidget(self.graph_run_btn)
        center_layout.addLayout(ctrl_layout)

        layout.addWidget(left_box, 1)
        layout.addWidget(center_box, 4)

        # Signals
        self.graph_add_btn.clicked.connect(self._on_graph_add_node)
        self.graph_edit_btn.clicked.connect(self._on_graph_edit_node)
        self.graph_delete_edge_btn.clicked.connect(self._on_graph_delete_edge)
        self.graph_clear_btn.clicked.connect(self._on_graph_clear)
        self.graph_run_btn.clicked.connect(self._on_graph_run)
        # When items move in the scene, recompute edges so lines follow nodes
        self.graph_scene.changed.connect(self._update_graph_edges)

    def _on_graph_add_node(self):
        selected = self.graph_components_list.selectedItems()
        if not selected:
            return
        step_type = selected[0].text()
        # Reuse default step structures from flow designer
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
            step = {"type": "Stop board"}

        # Create graphics node
        index = len(self.graph_nodes)
        node_width, node_height = 150, 50
        x = 0
        y = index * (node_height + 20)
        rect_item = self.graph_scene.addRect(
            0,
            0,
            node_width,
            node_height,
            pen=QtGui.QPen(QtGui.QColor("white")),
            brush=QtGui.QBrush(QtGui.QColor(60, 60, 60)),
        )
        rect_item.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        rect_item.setFlag(
            QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True
        )
        rect_item.setPos(x, y)

        label = self.graph_scene.addSimpleText(step_type)
        label.setBrush(QtGui.QBrush(QtGui.QColor("white")))
        label.setParentItem(rect_item)
        label_rect = label.boundingRect()
        label.setPos(
            (node_width - label_rect.width()) / 2,
            (node_height - label_rect.height()) / 2,
        )

        step["item"] = rect_item
        self.graph_nodes.append(step)
        self._update_graph_edges()

    def _update_graph_edges(self):
        # Remove old edges
        for edge in self.graph_edges:
            self.graph_scene.removeItem(edge)
        self.graph_edges.clear()

        # Draw simple sequential connections as directed arrows
        for i in range(len(self.graph_nodes) - 1):
            item1 = self.graph_nodes[i]["item"]
            item2 = self.graph_nodes[i + 1]["item"]
            edge = ArrowEdge(item1, item2)
            self.graph_scene.addItem(edge)
            self.graph_edges.append(edge)

    def _on_graph_delete_edge(self):
        """Delete currently selected connection line."""
        selected_items = self.graph_scene.selectedItems()
        if not selected_items:
            return
        for item in selected_items:
            if isinstance(item, ArrowEdge):
                if item in self.graph_edges:
                    self.graph_edges.remove(item)
                self.graph_scene.removeItem(item)

    def _on_graph_edit_node(self):
        selected_items = self.graph_scene.selectedItems()
        if not selected_items:
            return
        item = selected_items[0]
        node = None
        for n in self.graph_nodes:
            if n.get("item") is item:
                node = n
                break
        if node is None:
            return

        dlg = StepParamDialog(self, self._board, node)
        if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            # Optionally update label with more info
            item: QtWidgets.QGraphicsRectItem = node["item"]
            # Remove old child texts
            for child in item.childItems():
                self.graph_scene.removeItem(child)
            text = self._describe_step(node)
            label = self.graph_scene.addSimpleText(text if text else node["type"])
            label.setBrush(QtGui.QBrush(QtGui.QColor("white")))
            label.setParentItem(item)
            label_rect = label.boundingRect()
            rect = item.rect()
            label.setPos(
                (rect.width() - label_rect.width()) / 2,
                (rect.height() - label_rect.height()) / 2,
            )

    def _on_graph_clear(self):
        self.graph_scene.clear()
        self.graph_nodes.clear()
        self.graph_edges.clear()

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

        for idx, step in enumerate(self.graph_nodes, start=1):
            t = step.get("type")
            QtWidgets.QApplication.processEvents()
            try:
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
                        time.sleep(sec)
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
            except Exception as e:
                QtWidgets.QMessageBox.critical(
                    self,
                    "Execution error",
                    f"Error executing node {idx} ({t}):\n{e}",
                )
                break


class StepParamDialog(QtWidgets.QDialog):
    """Dialog to edit parameters of a flow step / graph node."""

    def __init__(self, parent, board: LabsmithBoard | None, step: dict):
        super().__init__(parent)
        self.setWindowTitle("Edit node parameters")
        self._board = board
        self._step = step

        layout = QtWidgets.QFormLayout(self)
        t = step.get("type")

        if t == "Move syringe":
            self.syringe_combo = QtWidgets.QComboBox()
            names = []
            if self._board is not None and getattr(self._board, "SPS01", None) is not None:
                for dev in self._board.SPS01:
                    if dev is not None:
                        names.append(str(dev.name))
            self.syringe_combo.addItems(names)
            if step.get("syringe") and step["syringe"] in names:
                self.syringe_combo.setCurrentText(step["syringe"])

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
            names = []
            if self._board is not None and getattr(self._board, "C4VM", None) is not None:
                for dev in self._board.C4VM:
                    if dev is not None:
                        names.append(str(dev.name))
            self.manifold_combo.addItems(names)
            if step.get("manifold") and step["manifold"] in names:
                self.manifold_combo.setCurrentText(step["manifold"])

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
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

