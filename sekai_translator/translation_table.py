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
# Helpers (VISUAL ONLY)
# ============================================================

def clean_engine_syntax(text: str) -> str:
    if not text:
        return ""

    t = text.strip()

    if t.startswith("[[") and t.endswith("]]"):
        return t[2:-2]

    if t.startswith('"') and t.endswith('"'):
        return t[1:-1]

    return t


# ============================================================
# MODEL
# ============================================================

class TranslationTableModel(QAbstractTableModel):

    advance_requested = Signal(int)

    BASE_HEADERS = ["#", "Original", "Tradução"]

    def __init__(self, entries: List[TranslationEntry]):
        super().__init__()

        self.all_entries = entries
        self.entries = [
            e for e in entries
            if e.context.get("is_translatable", False)
        ]

        # 🔑 Só ativa se houver speaker (KiriKiri)
        self.has_speaker = any(
            e.context.get("speaker") for e in self.entries
        )

    # ---------------- Headers ----------------

    @property
    def headers(self):
        if self.has_speaker:
            return ["#", "Personagem", "Original", "Tradução"]
        return self.BASE_HEADERS

    # ---------------- Qt basics ----------------

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self.entries)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self.headers)

    def headerData(self, section, orientation, role):
        if (
            orientation == Qt.Horizontal
            and role == Qt.DisplayRole
            and section < len(self.headers)
        ):
            return self.headers[section]
        return None

    # ---------------- Data ----------------

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        entry = self.entries[index.row()]
        col = index.column()

        # ---------------- Display ----------------
        if role == Qt.DisplayRole:

            # #
            if col == 0:
                if entry.qa_issues:
                    if any(i.level == "error" for i in entry.qa_issues):
                        return f"❌ {index.row() + 1}"
                    return f"⚠️ {index.row() + 1}"
                return index.row() + 1

            # Personagem (KiriKiri)
            if self.has_speaker:
                if col == 1:
                    return entry.context.get("speaker", "") or ""
                col -= 1

            # Original
            if col == 1:
                return clean_engine_syntax(entry.original)

            # Tradução
            if col == 2:
                return clean_engine_syntax(entry.translation)

        # ---------------- Tooltip QA ----------------
        if role == Qt.ToolTipRole and entry.qa_issues:
            return "\n".join(
                f"{'❌' if i.level == 'error' else '⚠️'} {i.message}"
                for i in entry.qa_issues
            )

        # ---------------- Background ----------------
        if role == Qt.BackgroundRole:
            return {
                TranslationStatus.UNTRANSLATED: QColor("#2a2a2a"),
                TranslationStatus.IN_PROGRESS: QColor("#3a331a"),
                TranslationStatus.TRANSLATED: QColor("#1f3a24"),
                TranslationStatus.REVIEWED: QColor("#1f2f3a"),
            }.get(entry.status)

        # ---------------- Font ----------------
        if role == Qt.FontRole:
            font = QFont()
            if entry.status == TranslationStatus.UNTRANSLATED:
                font.setItalic(True)
            if self.has_speaker and index.column() == 1:
                font.setBold(True)
            return font

        return None

    # ---------------- Editing ----------------

    def setData(self, index, value, role=Qt.EditRole):
        if not index.isValid():
            return False

        col = index.column()
        if self.has_speaker:
            col -= 1

        # Tradução
        if col == 2 and role == Qt.EditRole:
            entry = self.entries[index.row()]
            entry.translation = value

            self.dataChanged.emit(
                self.index(index.row(), 0),
                self.index(index.row(), self.columnCount() - 1),
            )

            self.advance_requested.emit(index.row())
            return True

        return False

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags

        flags = Qt.ItemIsSelectable | Qt.ItemIsEnabled

        col = index.column()
        if self.has_speaker:
            col -= 1

        if col == 2:
            flags |= Qt.ItemIsEditable

        return flags

    # ---------------- Refresh ----------------

    def refresh(self):
        self.beginResetModel()

        self.entries = [
            e for e in self.all_entries
            if e.context.get("is_translatable", False)
        ]

        self.has_speaker = any(
            e.context.get("speaker") for e in self.entries
        )

        self.endResetModel()


# ============================================================
# VIEW
# ============================================================

class TranslationTableView(QTableView):

    def apply_layout(self, has_speaker: bool):
        header = self.horizontalHeader()

        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)

        if has_speaker:
            header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(2, QHeaderView.Stretch)
            header.setSectionResizeMode(3, QHeaderView.Stretch)
        else:
            header.setSectionResizeMode(1, QHeaderView.Stretch)
            header.setSectionResizeMode(2, QHeaderView.Stretch)

    def __init__(self):
        super().__init__()

        self.setSelectionBehavior(QTableView.SelectRows)
        self.setSelectionMode(QTableView.ExtendedSelection)
        self.setShowGrid(False)
        self.setWordWrap(False)

        self.verticalHeader().setVisible(False)

        self.setEditTriggers(
            QTableView.DoubleClicked
            | QTableView.EditKeyPressed
            | QTableView.AnyKeyPressed
        )
