from typing import List

from PySide6.QtCore import (
    Qt,
    QAbstractTableModel,
    QModelIndex,
    Signal,
)
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QTableView, QHeaderView

from sekai_translator.core import TranslationEntry, TranslationStatus


# ============================================================
# MODEL
# ============================================================

class TranslationTableModel(QAbstractTableModel):

    advance_requested = Signal(int)

    HEADERS = ["#", "Original", "Tradução"]

    def __init__(self, entries: List[TranslationEntry]):
        super().__init__()

        self.all_entries = entries
        self.entries = [
            e for e in entries
            if e.context.get("is_translatable", False)
        ]

    # ---------------- Qt basics ----------------

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self.entries)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self.HEADERS)

    # ---------------- Data ----------------

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        entry = self.entries[index.row()]
        col = index.column()

        if role == Qt.DisplayRole:
            if col == 0:
                if entry.qa_issues:
                    if any(i.level == "error" for i in entry.qa_issues):
                        return f"❌ {index.row() + 1}"
                    return f"⚠️ {index.row() + 1}"
                return index.row() + 1

            if col == 1:
                return entry.original

            if col == 2:
                return entry.translation

        if role == Qt.ToolTipRole and entry.qa_issues:
            return "\n".join(
                f"{'❌' if i.level == 'error' else '⚠️'} {i.message}"
                for i in entry.qa_issues
            )

        if role == Qt.BackgroundRole:
            return {
                TranslationStatus.UNTRANSLATED: QColor("#2a2a2a"),
                TranslationStatus.IN_PROGRESS: QColor("#3a331a"),
                TranslationStatus.TRANSLATED: QColor("#1f3a24"),
                TranslationStatus.REVIEWED: QColor("#1f2f3a"),
            }.get(entry.status)

        if role == Qt.FontRole and entry.status == TranslationStatus.UNTRANSLATED:
            font = QFont()
            font.setItalic(True)
            return font

        if role == Qt.TextAlignmentRole and col == 0:
            return Qt.AlignLeft | Qt.AlignVCenter

        return None

    # ---------------- Editing ----------------

    def setData(self, index, value, role=Qt.EditRole):
        if not index.isValid():
            return False

        if index.column() == 2 and role == Qt.EditRole:
            entry = self.entries[index.row()]
            entry.translation = value

            self.dataChanged.emit(
                self.index(index.row(), 0),
                self.index(index.row(), self.columnCount() - 1),
            )

            # 🔥 ENTER = próxima linha
            self.advance_requested.emit(index.row())
            return True

        return False

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags

        flags = Qt.ItemIsSelectable | Qt.ItemIsEnabled
        if index.column() == 2:
            flags |= Qt.ItemIsEditable

        return flags

    # ---------------- Refresh (RESTAURADO) ----------------

    def refresh(self):
        self.beginResetModel()
        self.entries = [
            e for e in self.all_entries
            if e.context.get("is_translatable", False)
        ]
        self.endResetModel()


# ============================================================
# VIEW
# ============================================================

class TranslationTableView(QTableView):

    def __init__(self):
        super().__init__()

        self.setSelectionBehavior(QTableView.SelectRows)
        self.setSelectionMode(QTableView.ExtendedSelection)
        self.setShowGrid(False)
        self.setWordWrap(False)

        self.verticalHeader().setVisible(False)

        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)

        self.setEditTriggers(
            QTableView.DoubleClicked
            | QTableView.EditKeyPressed
            | QTableView.AnyKeyPressed
        )
