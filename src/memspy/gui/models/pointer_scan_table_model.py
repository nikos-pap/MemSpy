from typing import Any

from PyQt6.QtCore import QModelIndex, Qt, QObject, QAbstractTableModel

from memspy.utils.types import PointerItem


class PointerScanTableModel(QAbstractTableModel):
    """
    Generic table model for pointer scan results.

    - Data is stored as a list of rows, where each row is a sequence of values.
    - Column headers are provided by a list of strings.
    - Optionally, a parallel list of "pointer objects" is kept so you can
      retrieve the underlying object for a given row.
    """

    def __init__(
        self,
        headers: list[str] | None = None,
        rows: list[Any] | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._headers: list[str] = list(headers) if headers is not None else []
        self._rows: list[Any] = list(rows) if rows is not None else []
        # Parallel storage for your PointerItem (or similar) objects
        self._pointer_items: list[PointerItem] = []

    # ----- Qt model interface -----

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # type: ignore[override]
        if parent.isValid():
            return 0
        return len(self._rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # type: ignore[override]
        if parent.isValid():
            return 0
        return len(self._headers)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:  # type: ignore[override]
        if not index.isValid():
            return None

        row = index.row()
        col = index.column()

        if not (0 <= row < len(self._rows)):
            return None
        if not (0 <= col < len(self._headers)):
            return None

        value = self._rows[row][col]

        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            return value

        return None

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:  # type: ignore[override]
        if role != Qt.ItemDataRole.DisplayRole:
            return None

        if orientation == Qt.Orientation.Horizontal:
            if 0 <= section < len(self._headers):
                return self._headers[section]
            return None

        # simple 1-based row numbering
        if orientation == Qt.Orientation.Vertical:
            return section + 1

        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:  # type: ignore[override]
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags

        base_flags = Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
        # If you want editable cells later, OR with ItemIsEditable here.
        return base_flags

    # ----- Public API for generic tabular data -----

    # def set_headers(self, headers: Sequence[str]) -> None:
    #     """
    #     Replace all column headers and clear data/objects.
    #     """
    #     self.beginResetModel()
    #     self._headers = list(headers)
    #     self._rows.clear()
    #     self._pointer_items.clear()
    #     self.endResetModel()

    # def set_rows(self, rows: list[Sequence[Any]]) -> None:
    #     """
    #     Replace all row data. Pointer objects are discarded.
    #     """
    #     self.beginResetModel()
    #     self._rows = list(rows)
    #     self._pointer_items = [None] * len(self._rows)
    #     self.endResetModel()

    def clear(self) -> None:
        """
        Remove all data while keeping headers.
        """
        self.beginResetModel()
        self._rows.clear()
        self._pointer_items.clear()
        self.endResetModel()

    # ----- PointerItem-aware API -----

    def set_pointer_items(self, items: list[PointerItem]) -> None:
        """
        Configure headers and rows from a sequence of PointerItem-like objects.

        Expected attributes on each item:
            - start:  base address
            - offsets: sequence[int]
            - target: target address
            - value: current value (any type)
        """
        # Determine max number of offsets across this scan
        max_offsets = 0
        for obj in items:
            offsets = getattr(obj, "offsets", [])
            try:
                length = len(offsets)
            except TypeError:
                length = 0
            if length > max_offsets:
                max_offsets = length

        # Build headers: Base, Offset 0..N-1, Target, Value
        headers: list[str] = ["Base"]
        for i in range(max_offsets):
            headers.append(f"Offset {i}")
        headers.append("Target")
        headers.append("Value")

        self.beginResetModel()
        self._headers = headers
        self._pointer_items = list(items)
        self._rows = []

        for pointer in self._pointer_items:
            row: list[PointerItem] = []

            # Base address
            row.append(pointer.start)

            # Offsets (padded/truncated to max_offsets)
            offsets_seq = pointer.offsets
            if len(offsets_seq) < max_offsets:
                offsets_seq.extend([None] * (max_offsets - len(offsets_seq)))
            else:
                offsets_seq = offsets_seq[:max_offsets]
            row.extend(offsets_seq)

            # Target address and value
            row.append(pointer.target)
            row.append(pointer.value)

            self._rows.append(row)

        self.endResetModel()

    def append_pointer_item(self, item: PointerItem) -> None:
        """
        Append a single PointerItem-like object as a new row.

        Assumes headers are already configured by set_pointer_items().
        If headers are empty, they are derived from this single item.
        """
        # If headers are not yet pointer-style, derive them from this one item.
        if not self._headers:
            offsets = getattr(item, "offsets", [])
            try:
                max_offsets = len(offsets)
            except TypeError:
                max_offsets = 0

            headers: list[str] = ["Base"]
            for i in range(max_offsets):
                headers.append(f"Offset {i}")
            headers.append("Target")
            headers.append("Value")
            self._headers = headers

        # Current number of offset columns encoded in headers:
        # H = 1 (Base) + K (offsets) + 1 (Target) + 1 (Value) => K = H - 3
        offset_count = max(0, len(self._headers) - 3)

        insert_at = len(self._rows)
        self.beginInsertRows(QModelIndex(), insert_at, insert_at)

        self._pointer_items.append(item)

        row: list[PointerItem] = []
        row.append(getattr(item, "start", None))

        offsets_seq = list(getattr(item, "offsets", []))
        if len(offsets_seq) < offset_count:
            offsets_seq.extend([None] * (offset_count - len(offsets_seq)))
        else:
            offsets_seq = offsets_seq[:offset_count]
        row.extend(offsets_seq)

        row.append(getattr(item, "target", None))
        row.append(getattr(item, "value", None))

        self._rows.append(row)

        self.endInsertRows()

    def pointer_item_at(self, row_index: int) -> PointerItem | None:
        """
        Retrieve the underlying PointerItem-like object for a row.
        """
        if 0 <= row_index < len(self._pointer_items):
            return self._pointer_items[row_index]
        return None

    def update_pointer_value(self, row_index: int, value: PointerItem) -> None:
        """
        Update only the value column for an existing row and keep
        the underlying PointerItem in sync.
        """
        if not (0 <= row_index < len(self._rows)):
            return

        if not self._headers:
            return

        value_col = len(self._headers) - 1  # last column is Value

        # Update the row data
        row_list = list(self._rows[row_index])
        if value_col >= len(row_list):
            return

        row_list[value_col] = value
        self._rows[row_index] = row_list

        # Update the underlying object if available
        if 0 <= row_index < len(self._pointer_items):
            obj = self._pointer_items[row_index]
            if obj is not None:
                try:
                    setattr(obj, "value", value)
                except Exception:
                    # If the object doesn't support assignment, just ignore.
                    pass

        # Notify views
        idx = self.index(row_index, value_col)
        self.dataChanged.emit(
            idx,
            idx,
            [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole],
        )
