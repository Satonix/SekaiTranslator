from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from sekai_translator.core import Project, TranslationStatus


# ============================================================
# Build project status (dados em memória)
# ============================================================

def build_project_status(project: Project) -> dict:
    """
    Constrói um dicionário com o status do projeto,
    seguro para uso externo (site, dashboard, etc).
    """
    files_status: dict[str, dict] = {}

    total = translated = reviewed = 0

    for path, entries in project.files.items():
        translatable = [
            e for e in entries
            if e.context.get("is_translatable")
        ]

        if not translatable:
            continue

        file_total = len(translatable)
        file_translated = len([
            e for e in translatable
            if e.status == TranslationStatus.TRANSLATED
        ])
        file_reviewed = len([
            e for e in translatable
            if e.status == TranslationStatus.REVIEWED
        ])

        files_status[Path(path).name] = {
            "total": file_total,
            "translated": file_translated,
            "reviewed": file_reviewed,
            "progress": round(
                (file_translated / file_total) * 100, 1
            ) if file_total else 0,
        }

        total += file_total
        translated += file_translated
        reviewed += file_reviewed

    untranslated = total - translated - reviewed

    return {
        "project_id": project.id,
        "slug": getattr(project, "slug", None),
        "name": project.name,
        "engine": project.engine,
        "language": project.language,
        "updated_at": datetime.now(timezone.utc).isoformat(),

        "stats": {
            "total_entries": total,
            "translated": translated,
            "reviewed": reviewed,
            "untranslated": untranslated,
            "progress": round(
                (translated / total) * 100, 1
            ) if total else 0,
        },

        "files": files_status,
    }


# ============================================================
# Export helper (arquivo JSON)
# ============================================================

def export_project_status(
    project: Project,
    output_path: str | None = None,
) -> str:
    """
    Gera o project_status.json no disco.

    Se output_path não for informado,
    o arquivo será salvo na pasta do projeto.
    """
    status = build_project_status(project)

    if not output_path:
        if not project.project_path:
            raise RuntimeError(
                "Projeto ainda não foi salvo em disco."
            )
        base_dir = Path(project.project_path).parent
        output_path = str(base_dir / "project_status.json")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(
            status,
            f,
            ensure_ascii=False,
            indent=2,
        )

    return output_path
