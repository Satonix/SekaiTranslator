from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Any

from sekai_translator.undo_stack import UndoStack


class TranslationStatus(str, Enum):
    UNTRANSLATED = "untranslated"
    IN_PROGRESS = "in_progress"
    TRANSLATED = "translated"
    REVIEWED = "reviewed"


@dataclass
class TranslationEntry:
    entry_id: str
    original: str
    translation: str = ""
    status: TranslationStatus = TranslationStatus.UNTRANSLATED
    context: Dict[str, Any] = field(default_factory=dict)
    qa_issues: List[Any] = field(default_factory=list)


class Project:
    def __init__(
        self,
        id: str,
        name: str,
        root_path: str,
        encoding: str = "utf-8",
        language: str = "en",
        engine: str = "artemis",  # 👈 NOVO
    ):
        self.id = id
        self.name = name
        self.root_path = root_path
        self.encoding = encoding
        self.language = language
        self.engine = engine

        self.files: Dict[str, List[TranslationEntry]] = {}
        self.entry_index: Dict[str, TranslationEntry] = {}

        self.undo_stack = UndoStack()
        self.project_path: str | None = None

    # --------------------------------------------------

    def index_entries(self):
        self.entry_index.clear()
        for entries in self.files.values():
            for e in entries:
                self.entry_index[e.entry_id] = e

    # --------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "root_path": self.root_path,
            "encoding": self.encoding,
            "language": self.language,
            "engine": self.engine,  # 👈
            "files": {
                path: [e.__dict__ for e in entries]
                for path, entries in self.files.items()
            },
        }

    @staticmethod
    def from_dict(data: dict) -> "Project":
        project = Project(
            id=data["id"],
            name=data.get("name", "Projeto"),
            root_path=data["root_path"],
            encoding=data.get("encoding", "utf-8"),
            language=data.get("language", "en"),
            engine=data.get("engine", "artemis"),  # 👈 fallback
        )

        for path, entries in data.get("files", {}).items():
            project.files[path] = [
                TranslationEntry(**e) for e in entries
            ]

        project.index_entries()
        return project
