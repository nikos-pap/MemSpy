import os

import psutil
from PyQt6.QtCore import pyqtSignal, Qt, QPoint
from PyQt6.QtWidgets import QWidget, QTableView, QPushButton, QHBoxLayout, QVBoxLayout, QMenu, QDialog

from memspy.gui.models.pointer_scan_table_model import PointerScanTableModel
from memspy.gui.widgets.dialogs.pointer_scan_dialog import PointerScanConfigDialog
from memspy.utils.types import PointerScanParameters, PointerItem, ModuleInfo


def list_modules_for_pid(pid: int) -> list[ModuleInfo]:
    p = psutil.Process(int(pid))
    mods = set()  # path -> [min_start, max_end]
    main_name = os.path.basename(p.exe())
    print(main_name)

    result = []

    for m in p.memory_maps(grouped=False):
        path = os.path.basename(m.path) or ""
        if not path:
            continue
        # keep it "module-ish"; drop this filter if you want every mapped file
        if not path.lower().endswith((".dll", ".exe")):
            continue
        # print(dir(m), m.count, m.index, m.perms, m.rss)
        if path in mods:
            continue

        mods.add(path)

        start, end = int(m.addr, 16), int(m.addr, 16) + m.rss
        start_s, end_s = str(start), str(end)

        if main_name == path:
            result.insert(0, ModuleInfo(path, start, end))
        else:
            result.append(ModuleInfo(path, start, end))

    result[1:] = sorted(result[1:], key=lambda item: item.name)

    return result


class PointerScanTableWidget(QWidget):
    """
    Self-contained widget that shows the pointer-scan result table
    and exposes a 'Pointer scan...' button to open the configuration dialog.

    This widget:
      - does NOT know about your process object / PID
      - does NOT implement the scan
      - ONLY emits pointerScanRequested(parameters) when the user
        configures a scan and confirms in the popup.
      - Provides a context menu to request insert/update operations,
        which you can handle in your own code.
    """

    # You connect this to your real scan backend in your app.
    pointerScanRequested = pyqtSignal(PointerScanParameters)

    # Context-menu driven actions (you decide what to do when they fire)
    rowInsertRequested = pyqtSignal()
    rowValueUpdateRequested = pyqtSignal(int)  # row index

    def __init__(
        self,
        parent: QWidget | None = None,
        headers: list[str] | None = None,
        pid: int | None = None
    ) -> None:
        super().__init__(parent)

        # ---- store data needed for dialog ----
        # self._type_list: list[Any] = list(type_list) if type_list is not None else []
        # self._module_list: list[str] = list(module_list) if module_list is not None else []
        self.pid = pid
        # ---- table ----
        self._table_view = QTableView(self)
        self._model = PointerScanTableModel(headers=headers, parent=self)
        self._table_view.setModel(self._model)
        self._configure_view()

        # ---- top bar with button ----
        self._scan_button = QPushButton("Pointer scan...", self)
        self._scan_button.clicked.connect(self._open_scan_dialog)

        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)
        top_bar.addStretch(1)
        top_bar.addWidget(self._scan_button, 0, Qt.AlignmentFlag.AlignRight)

        # ---- main layout ----
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        layout.addLayout(top_bar)
        layout.addWidget(self._table_view)

    # -------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------

    def _configure_view(self) -> None:
        self._table_view.setSortingEnabled(True)
        self._table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self._table_view.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self._table_view.horizontalHeader().setStretchLastSection(True)

        # Right-click popup
        self._table_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table_view.customContextMenuRequested.connect(self._show_context_menu)

    def _show_context_menu(self, pos: QPoint) -> None:
        """
        Simple context menu that lets you request:
          - inserting a new row
          - updating the value of the clicked row

        The widget itself does not perform these operations; it emits
        signals that your code can handle.
        """
        index = self._table_view.indexAt(pos)

        menu = QMenu(self)
        insert_action = menu.addAction("Insert pointer row")
        update_action = menu.addAction("Update value in row")

        if not index.isValid():
            update_action.setEnabled(False)

        global_pos = self._table_view.viewport().mapToGlobal(pos)
        chosen = menu.exec(global_pos)

        if chosen is insert_action:
            self.rowInsertRequested.emit()
        elif chosen is update_action and index.isValid():
            self.rowValueUpdateRequested.emit(index.row())

    def _open_scan_dialog(self) -> None:
        """
        Opens the PointerScanConfigDialog, and if the user confirms,
        emits pointerScanRequested with the chosen parameters.

        On each open, it fetches module names as follows:
          - if self._module_list is non-empty, use that
          - otherwise, if HARD_CODED_PID > 0, call list_modules_for_pid(HARD_CODED_PID)
          - otherwise, leave it empty and the dialog will just have "<none>"
        """
        # start from any explicit list you might have set
        # module_list: list[str] = list(self._module_list)

        # if nothing was set explicitly, fetch from the hardcoded PID
        module_list = list_modules_for_pid(self.pid)

        dlg = PointerScanConfigDialog(
            parent=self,
            module_list=module_list,
        )

        if dlg.exec() == QDialog.DialogCode.Accepted:
            params = dlg.parameters()
            print(params)
            self.pointerScanRequested.emit(params)

    # -------------------------------------------------------
    # Public API
    # -------------------------------------------------------

    def model(self) -> PointerScanTableModel:
        return self._model

    # ----- generic tabular API (still available) -----

    # def set_headers(self, headers: Sequence[str]) -> None:
    #     self._model.set_headers(headers)

    # def set_rows(self, rows: list[Sequence[Any]]) -> None:
    #     self._model.set_rows(rows)

    def clear_rows(self) -> None:
        self._model.clear()

    # ----- pointer-aware API -----

    def set_pointer_items(self, items: list[PointerItem]) -> None:
        """
        Configure the table from a sequence of PointerItem-like objects.
        """
        self._model.set_pointer_items(items)

    def append_pointer_item(self, item: PointerItem) -> None:
        """
        Append a single PointerItem-like object as a new row.
        """
        self._model.append_pointer_item(item)

    def pointer_item_at(self, row_index: int) -> PointerItem | None:
        """
        Access the underlying PointerItem-like object for a given row.
        """
        return self._model.pointer_item_at(row_index)

    def update_pointer_value(self, row_index: int, value: PointerItem) -> None:
        """
        Update only the value cell for a given row and keep the object in sync.
        """
        self._model.update_pointer_value(row_index, value)


    def set_module_list(self, module_list: list[str]) -> None:
        """
        Update available target modules for the scan dialog.
        """
        self._module_list = list(module_list)
