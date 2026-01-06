from PySide6.QtCore import Qt, Signal, QEvent
from PySide6.QtGui import QTextOption
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPlainTextEdit,
    QMessageBox,
)

from sekai_translator.status_service import StatusService
from sekai_translator.undo_stack import UndoAction, CompositeUndoAction
from sekai_translator.core import TranslationStatus


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
        layout.addWidget(self.translation_edit)

        self.translation_edit.installEventFilter(self)

    # -------------------------------------------------
    # API pública
    # -------------------------------------------------

    def set_entries(self, entries: list):
        self._entries = entries

        self.original_edit.setPlainText(
            "\n\n".join(e.original for e in entries)
        )

        if len(entries) == 1:
            self.translation_edit.setPlainText(entries[0].translation or "")
        else:
            self.translation_edit.clear()

    # -------------------------------------------------
    # ENTER / SHIFT+ENTER
    # -------------------------------------------------

    def eventFilter(self, obj, event):
        if obj is self.translation_edit and event.type() == QEvent.KeyPress:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                if event.modifiers() & Qt.ShiftModifier:
                    return False
                self._commit_translation()
                return True
            elif event.key() == Qt.Key_Up and event.modifiers() & Qt.ControlModifier:
                self.request_prev.emit()
                return True

        return super().eventFilter(obj, event)

    # -------------------------------------------------
    # Commit DEFINITIVO (single + batch + undo correto)
    # -------------------------------------------------

    def _commit_translation(self):
        if not self._entries:
            return

        raw_text = self.translation_edit.toPlainText().strip()
        if not raw_text:
            return

        entries = self._entries
        blocks = [b.strip() for b in raw_text.split("\n\n") if b.strip()]

        # 🔒 proteção contra sobrescrita em batch
        if len(entries) > 1 and any(e.translation for e in entries):
            QMessageBox.warning(
                self,
                "Tradução em lote",
                "Uma ou mais linhas já possuem tradução.\n"
                "Operação cancelada para evitar sobrescrita.",
            )
            return

        # -----------------------------
        # Determina texto por entry
        # -----------------------------
        texts_per_entry: list[str] = []

        if len(entries) == 1:
            texts_per_entry = [raw_text]

        elif len(blocks) == 1:
            texts_per_entry = [blocks[0]] * len(entries)

        elif len(blocks) == len(entries):
            texts_per_entry = blocks

        else:
            QMessageBox.warning(
                self,
                "Tradução em lote",
                f"Número de blocos ({len(blocks)}) não corresponde "
                f"ao número de linhas selecionadas ({len(entries)}).",
            )
            return

        # -----------------------------
        # Cria Undo COMPLETO
        # -----------------------------
        undo_actions = []

        for entry, new_text in zip(entries, texts_per_entry):
            old_text = entry.translation

            old_status = entry.status
            new_status = (
                TranslationStatus.TRANSLATED
                if new_text.strip()
                else TranslationStatus.UNTRANSLATED
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

        # 🔒 batch = 1 undo
        self.project.undo_stack.push(
            CompositeUndoAction(undo_actions)
        )

        # -----------------------------
        # Aplica commit real
        # -----------------------------
        for entry, text in zip(entries, texts_per_entry):
            StatusService.on_translation_committed(entry, text)

        self.entry_changed.emit()
        self.request_next.emit()
