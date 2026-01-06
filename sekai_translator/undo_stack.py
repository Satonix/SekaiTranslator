from dataclasses import dataclass
from typing import Any, List


@dataclass
class UndoAction:
    entry_id: str
    field: str
    old_value: Any
    new_value: Any


@dataclass
class CompositeUndoAction:
    actions: List[UndoAction]


class UndoStack:
    def __init__(self):
        self._undo: List[Any] = []
        self._redo: List[Any] = []

    # --------------------------------------------------

    def push(self, action: Any):
        self._undo.append(action)
        self._redo.clear()

    def can_undo(self) -> bool:
        return bool(self._undo)

    def can_redo(self) -> bool:
        return bool(self._redo)

    # --------------------------------------------------

    def undo(self, project):
        if not self._undo:
            return

        action = self._undo.pop()
        self._apply(project, action, undo=True)
        self._redo.append(action)

    def redo(self, project):
        if not self._redo:
            return

        action = self._redo.pop()
        self._apply(project, action, undo=False)
        self._undo.append(action)

    # --------------------------------------------------

    def _apply(self, project, action, undo: bool):
        if isinstance(action, CompositeUndoAction):
            actions = reversed(action.actions) if undo else action.actions
            for a in actions:
                self._apply_single(project, a, undo)
        else:
            self._apply_single(project, action, undo)

    def _apply_single(self, project, action: UndoAction, undo: bool):
        entry = project.entry_index.get(action.entry_id)
        if not entry:
            return

        value = action.old_value if undo else action.new_value
        setattr(entry, action.field, value)

    # --------------------------------------------------

    def clear(self):
        self._undo.clear()
        self._redo.clear()
