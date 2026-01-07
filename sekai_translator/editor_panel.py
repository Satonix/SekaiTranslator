from PySide6.QtCore import Qt, Signal, QEvent
from PySide6.QtGui import QTextOption, QTextCursor
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPlainTextEdit,
    QMessageBox,
)

import re

from sekai_translator.status_service import StatusService
from sekai_translator.undo_stack import UndoAction, CompositeUndoAction
from sekai_translator.core import TranslationStatus


NUMBER_PREFIX_RE = re.compile(r"^\[\d+\]\s*")


class EditorPanel(QWidget):

    entry_changed = Signal()
    request_next = Signal()
    request_prev = Signal()

    def __init__(self, project):
        super().__init__()

        self.project = project
        self._entries: list = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        # -----------------------------
        # Original
        # -----------------------------
        layout.addWidget(QLabel("Original"))

        self.original_edit = QPlainTextEdit()
        self.original_edit.setReadOnly(True)
        self.original_edit.setMaximumHeight(160)
        self.original_edit.setWordWrapMode(QTextOption.WordWrap)
        layout.addWidget(self.original_edit)

        # -----------------------------
        # Tradução
        # -----------------------------
        layout.addWidget(QLabel("Tradução"))

        self.translation_edit = QPlainTextEdit()
        self.translation_edit.setWordWrapMode(QTextOption.WordWrap)
        self.translation_edit.setUndoRedoEnabled(False)
        layout.addWidget(self.translation_edit)

        self.translation_edit.installEventFilter(self)

    # -------------------------------------------------
    # Helpers (APENAS VISUAL)
    # -------------------------------------------------

    def _clean_engine_syntax(self, text: str) -> str:
        """
        Remove APENAS delimitadores externos de engine.
        USADO SOMENTE PARA EXIBIÇÃO.
        """
        if not text:
            return ""

        t = text.strip()

        if t.startswith("[[") and t.endswith("]]"):
            return t[2:-2]

        if t.startswith('"') and t.endswith('"'):
            return t[1:-1]

        return t

    # -------------------------------------------------
    # API pública
    # -------------------------------------------------

    def set_entries(self, entries: list):
        self._entries = entries

        # ORIGINAL
        if len(entries) == 1:
            self.original_edit.setPlainText(
                self._clean_engine_syntax(entries[0].original)
            )
        else:
            self.original_edit.setPlainText(
                "\n\n".join(
                    f"[{i}] {self._clean_engine_syntax(e.original)}"
                    for i, e in enumerate(entries, start=1)
                )
            )

        # TRADUÇÃO (visual limpa)
        if len(entries) == 1:
            self.translation_edit.setPlainText(
                self._clean_engine_syntax(entries[0].translation or "")
            )
            self.translation_edit.selectAll()
        else:
            self.translation_edit.setPlainText(
                "\n\n".join(
                    f"[{i}] {self._clean_engine_syntax(e.translation or '')}"
                    for i, e in enumerate(entries, start=1)
                )
            )

        self._ensure_cursor_after_prefix()
        self.translation_edit.setFocus()

    # -------------------------------------------------
    # EVENT FILTER
    # -------------------------------------------------

    def eventFilter(self, obj, event):
        if obj is self.translation_edit:

            if event.type() in (QEvent.MouseButtonRelease, QEvent.FocusIn):
                self._ensure_cursor_after_prefix()
                return False

            if event.type() == QEvent.KeyPress:
                key = event.key()
                mods = event.modifiers()

                cursor = self.translation_edit.textCursor()
                block = cursor.block()
                text = block.text()

                m = NUMBER_PREFIX_RE.match(text)
                min_pos = m.end() if m else 0
                pos = cursor.positionInBlock()

                # Shift + Enter → próxima entry
                if key in (Qt.Key_Return, Qt.Key_Enter) and mods & Qt.ShiftModifier:
                    self._jump_to_next_entry(cursor)
                    return True

                # Proteção do prefixo
                if pos < min_pos:
                    self._ensure_cursor_after_prefix()
                    return True

                if key == Qt.Key_Backspace and pos <= min_pos:
                    return True
                if key == Qt.Key_Delete and pos < min_pos:
                    return True

                # Enter → commit
                if key in (Qt.Key_Return, Qt.Key_Enter):
                    self._commit_translation()
                    return True

                # Undo / Redo globais
                if key == Qt.Key_Z and mods & Qt.ControlModifier:
                    self._call_main_window("undo")
                    return True
                if key == Qt.Key_Y and mods & Qt.ControlModifier:
                    self._call_main_window("redo")
                    return True

                # Ctrl + ↑
                if key == Qt.Key_Up and mods & Qt.ControlModifier:
                    self.request_prev.emit()
                    return True

        return super().eventFilter(obj, event)

    # -------------------------------------------------
    # Cursor helpers
    # -------------------------------------------------

    def _ensure_cursor_after_prefix(self):
        cursor = self.translation_edit.textCursor()
        block = cursor.block()
        text = block.text()

        m = NUMBER_PREFIX_RE.match(text)
        if not m:
            return

        min_pos = block.position() + m.end()
        if cursor.position() < min_pos:
            cursor.setPosition(min_pos)
            self.translation_edit.setTextCursor(cursor)

    def _jump_to_next_entry(self, cursor: QTextCursor):
        if not self._entries or len(self._entries) <= 1:
            return

        block_index = cursor.blockNumber()
        entry_index = block_index // 2
        next_index = entry_index + 1

        if next_index >= len(self._entries):
            return

        target_block = self.translation_edit.document().findBlockByNumber(
            next_index * 2
        )

        if not target_block.isValid():
            return

        text = target_block.text()
        m = NUMBER_PREFIX_RE.match(text)
        pos = target_block.position() + (m.end() if m else 0)

        cursor.setPosition(pos)
        self.translation_edit.setTextCursor(cursor)

    def _call_main_window(self, method: str):
        win = self.window()
        if win and hasattr(win, method):
            getattr(win, method)()

    # -------------------------------------------------
    # Commit FINAL (CORRETO)
    # -------------------------------------------------

    def _commit_translation(self):
        if not self._entries:
            return

        raw = self.translation_edit.toPlainText()
        if not raw.strip():
            return

        def clean(text: str) -> str:
            # 🔒 REMOVE SOMENTE O PREFIXO [n]
            return NUMBER_PREFIX_RE.sub("", text).strip()

        entries = self._entries

        blocks = [
            clean(b)
            for b in raw.split("\n\n")
            if clean(b)
        ]

        if len(entries) > 1 and any(e.translation for e in entries):
            QMessageBox.warning(
                self,
                "Tradução em lote",
                "Uma ou mais linhas já possuem tradução.\n"
                "Operação cancelada para evitar sobrescrita.",
            )
            return

        if len(entries) == 1:
            texts = [clean(raw)]
        elif len(blocks) == 1:
            texts = [blocks[0]] * len(entries)
        elif len(blocks) == len(entries):
            texts = blocks
        else:
            QMessageBox.warning(
                self,
                "Tradução em lote",
                "Número de blocos não corresponde às linhas selecionadas.",
            )
            return

        undo_actions = []

        for entry, new_text in zip(entries, texts):
            old_text = entry.translation
            old_status = entry.status

            new_status = (
                TranslationStatus.TRANSLATED
                if new_text else TranslationStatus.UNTRANSLATED
            )

            if old_text == new_text and old_status == new_status:
                continue

            undo_actions.append(
                UndoAction(
                    entry_id=entry.entry_id,
                    field="translation",
                    old_value=old_text,
                    new_value=new_text,
                )
            )
            undo_actions.append(
                UndoAction(
                    entry_id=entry.entry_id,
                    field="status",
                    old_value=old_status,
                    new_value=new_status,
                )
            )

        if not undo_actions:
            return

        self.project.undo_stack.push(
            CompositeUndoAction(undo_actions)
        )

        for entry, text in zip(entries, texts):
            StatusService.on_translation_committed(entry, text)

        self.entry_changed.emit()
        self.request_next.emit()
