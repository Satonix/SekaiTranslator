from PySide6.QtCore import Qt, Signal, QEvent
from PySide6.QtGui import QTextOption, QFont
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPlainTextEdit,
    QMessageBox,
    QHBoxLayout,
    QStyle,
)

from sekai_translator.status_service import StatusService
from sekai_translator.undo_stack import UndoAction, CompositeUndoAction
from sekai_translator.core import TranslationStatus


MAX_NAME_LEN = 14


class EditorPanel(QWidget):

    entry_changed = Signal()
    request_next = Signal()
    request_prev = Signal()

    def __init__(self, project):
        super().__init__()

        self.project = project
        self._entries: list = []
        self._rows: list[int] = []

        mono = QFont("Consolas")
        mono.setStyleHint(QFont.Monospace)

        root = QVBoxLayout(self)
        root.setContentsMargins(6, 4, 6, 4)
        root.setSpacing(4)

        # ================= ORIGINAL =================
        root.addWidget(QLabel("Original"))

        original_row = QHBoxLayout()
        original_row.setSpacing(0)

        self.meta_original = self._create_meta(mono)
        original_row.addWidget(self.meta_original)

        self.original_edit = QPlainTextEdit()
        self.original_edit.setFont(mono)
        self.original_edit.setReadOnly(True)
        self.original_edit.setWordWrapMode(QTextOption.NoWrap)
        self.original_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.original_edit.document().setDocumentMargin(0)
        self.original_edit.setStyleSheet("QPlainTextEdit { border: none; }")

        original_row.addWidget(self.original_edit)
        root.addLayout(original_row)

        # ================= TRADUÇÃO =================
        root.addWidget(QLabel("Tradução"))

        translation_row = QHBoxLayout()
        translation_row.setSpacing(0)

        self.meta_translation = self._create_meta(mono)
        translation_row.addWidget(self.meta_translation)

        self.translation_edit = QPlainTextEdit()
        self.translation_edit.setFont(mono)
        self.translation_edit.setUndoRedoEnabled(False)
        self.translation_edit.setWordWrapMode(QTextOption.NoWrap)
        self.translation_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.translation_edit.document().setDocumentMargin(0)
        self.translation_edit.setStyleSheet("QPlainTextEdit { border: none; }")

        translation_row.addWidget(self.translation_edit)
        root.addLayout(translation_row)

        # Scroll sync
        self.original_edit.verticalScrollBar().valueChanged.connect(
            self.meta_original.verticalScrollBar().setValue
        )
        self.translation_edit.verticalScrollBar().valueChanged.connect(
            self.meta_translation.verticalScrollBar().setValue
        )

        self.translation_edit.installEventFilter(self)

    # ================= META =================

    def _create_meta(self, font: QFont) -> QPlainTextEdit:
        meta = QPlainTextEdit()
        meta.setFont(font)
        meta.setReadOnly(True)
        meta.setFixedWidth(120)
        meta.setFocusPolicy(Qt.NoFocus)
        meta.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        meta.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        meta.setWordWrapMode(QTextOption.NoWrap)
        meta.document().setDocumentMargin(0)

        opt = meta.document().defaultTextOption()
        opt.setAlignment(Qt.AlignRight)
        meta.document().setDefaultTextOption(opt)

        scrollbar_width = self.style().pixelMetric(QStyle.PM_ScrollBarExtent)

        meta.setStyleSheet(f"""
        QPlainTextEdit {{
            border: none;
            background: transparent;
            padding: 2px {6 + scrollbar_width}px 2px 2px;
            color: #9ca3af;
        }}
        """)

        return meta

    # ================= API =================

    def set_entries(self, entries: list, rows: list[int]):
        self._entries = entries
        self._rows = rows
        is_batch = len(entries) > 1

        # -------- ORIGINAL --------
        self.original_edit.setPlainText(
            "\n".join(e.original or "" for e in entries)
            if is_batch else entries[0].original or ""
        )

        # -------- META (EXATAMENTE IGUAL À TABELA) --------
        def truncate(name: str) -> str:
            if not name:
                return ""
            return name if len(name) <= MAX_NAME_LEN else name[: MAX_NAME_LEN - 1] + "…"

        meta_lines = []
        for row, entry in zip(rows, entries):
            number = row + 1  # tabela é 1-based visualmente
            speaker = truncate(entry.context.get("speaker"))
            meta_lines.append(
                f"{number}. {speaker}" if speaker else f"{number}."
            )

        meta_text = "\n".join(meta_lines)

        self.meta_original.setPlainText(meta_text)
        self.meta_translation.setPlainText(meta_text)

        # -------- TRANSLATION --------
        self.translation_edit.setPlainText(
            "\n".join(e.translation or "" for e in entries)
            if is_batch else entries[0].translation or ""
        )

        if not is_batch:
            self.translation_edit.selectAll()

        self.translation_edit.setFocus()

    # ================= EVENT FILTER =================

    def eventFilter(self, obj, event):
        if obj is self.translation_edit and event.type() == QEvent.KeyPress:
            key = event.key()
            mods = event.modifiers()
            is_batch = len(self._entries) > 1
            cursor = self.translation_edit.textCursor()

            if is_batch and key in (Qt.Key_Return, Qt.Key_Enter) and mods & Qt.ShiftModifier:
                self._jump(cursor, +1)
                return True

            if is_batch and key == Qt.Key_Down and cursor.atBlockEnd():
                self._jump(cursor, +1)
                return True

            if is_batch and key == Qt.Key_Up and cursor.atBlockStart():
                self._jump(cursor, -1)
                return True

            if key in (Qt.Key_Return, Qt.Key_Enter) and not mods:
                self._commit_translation()
                return True

        return super().eventFilter(obj, event)

    # ================= NAV =================

    def _jump(self, cursor, delta: int):
        block = cursor.block()
        target = block.next() if delta > 0 else block.previous()
        if target.isValid():
            cursor.setPosition(target.position())
            self.translation_edit.setTextCursor(cursor)

    # ================= COMMIT =================

    def _commit_translation(self):
        lines = [l.rstrip() for l in self.translation_edit.toPlainText().splitlines()]

        if len(lines) != len(self._entries):
            QMessageBox.warning(
                self,
                "Tradução em lote",
                "Número de linhas não corresponde às entradas.",
            )
            return

        undo_actions = []

        for entry, new_text in zip(self._entries, lines):
            if entry.translation == new_text:
                continue

            undo_actions.append(
                UndoAction(
                    entry_id=entry.entry_id,
                    field="translation",
                    old_value=entry.translation,
                    new_value=new_text,
                )
            )
            undo_actions.append(
                UndoAction(
                    entry_id=entry.entry_id,
                    field="status",
                    old_value=entry.status,
                    new_value=TranslationStatus.TRANSLATED,
                )
            )

        if not undo_actions:
            return

        self.project.undo_stack.push(
            CompositeUndoAction(undo_actions)
        )

        for entry, text in zip(self._entries, lines):
            StatusService.on_translation_committed(entry, text)

        self.entry_changed.emit()
        self.request_next.emit()
