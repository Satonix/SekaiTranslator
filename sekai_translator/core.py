from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Any

from sekai_translator.undo_stack import UndoStack


# ============================================================
# Translation Status
# ============================================================

class TranslationStatus(str, Enum):
    UNTRANSLATED = "untranslated"
    IN_PROGRESS = "in_progress"
    TRANSLATED = "translated"
    REVIEWED = "reviewed"  # mantido por compatibilidade, não usado no progresso


# ============================================================
# Translation Entry
# ============================================================

@dataclass
class TranslationEntry:
    entry_id: str
    original: str
    translation: str = ""
    status: TranslationStatus = TranslationStatus.UNTRANSLATED
    context: Dict[str, Any] = field(default_factory=dict)
    qa_issues: List[Any] = field(default_factory=list)


# ============================================================
# Project
# ============================================================

class Project:
    def __init__(
        self,
        id: str,
        name: str,
        root_path: str,
        encoding: str = "utf-8",
        language: str = "en",
        engine: str = "artemis",
    ):
        self.id = id
        self.name = name
        self.root_path = root_path
        self.encoding = encoding
        self.language = language
        self.engine = engine

        # file_path -> List[TranslationEntry]
        self.files: Dict[str, List[TranslationEntry]] = {}

        # entry_id -> TranslationEntry
        self.entry_index: Dict[str, TranslationEntry] = {}

        # file_path -> bool (tem alguma linha traduzida?)
        self.file_status_cache: Dict[str, bool] = {}

        self.undo_stack = UndoStack()
        self.project_path: str | None = None

    # --------------------------------------------------
    # Indexação (usar APENAS após import/load)
    # --------------------------------------------------

    def index_entries(self):
        self.entry_index.clear()
        for entries in self.files.values():
            for e in entries:
                self.entry_index[e.entry_id] = e

    # --------------------------------------------------
    # Cache de status por arquivo (TreeView)
    # --------------------------------------------------

    def update_file_status(self, path: str):
        """
        Atualiza o cache indicando se o arquivo possui
        pelo menos uma linha traduzida.
        """
        entries = self.files.get(path)
        if not entries:
            self.file_status_cache[path] = False
            return

        self.file_status_cache[path] = any(
            e.status == TranslationStatus.TRANSLATED
            for e in entries
        )

    def rebuild_all_file_status(self):
        """
        Recalcula o cache inteiro.
        Usar apenas ao carregar projeto.
        """
        self.file_status_cache.clear()
        for path in self.files:
            self.update_file_status(path)

    # --------------------------------------------------
    # Progresso por arquivo (NOVO)
    # --------------------------------------------------

    def file_progress(self, path: str) -> int:
        """
        Retorna o progresso do arquivo em porcentagem (0–100),
        considerando APENAS linhas traduzíveis e status TRANSLATED.
        """
        entries = self.files.get(path)
        if not entries:
            return 0

        translatable = [
            e for e in entries
            if e.context.get("is_translatable")
        ]

        if not translatable:
            return 0

        translated = len([
            e for e in translatable
            if e.status == TranslationStatus.TRANSLATED
        ])

        return int((translated / len(translatable)) * 100)

    # --------------------------------------------------
    # Persistência
    # --------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "root_path": self.root_path,
            "encoding": self.encoding,
            "language": self.language,
            "engine": self.engine,
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
            engine=data.get("engine", "artemis"),
        )

        for path, entries in data.get("files", {}).items():
            project.files[path] = [
                TranslationEntry(**e) for e in entries
            ]

        project.index_entries()
        project.rebuild_all_file_status()
        return project
