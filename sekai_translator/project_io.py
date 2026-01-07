import json
import uuid
import shutil
import os
import re
from pathlib import Path

from sekai_translator.core import Project


# ============================================================
# Diretórios da aplicação
# ============================================================

APP_DIR = Path(os.getenv("LOCALAPPDATA", Path.home())) / "SekaiTranslator"
PROJECTS_DIR = APP_DIR / "projects"


# ============================================================
# Utils
# ============================================================

def slugify(name: str) -> str:
    name = name.lower().strip()
    name = re.sub(r"[^\w\s-]", "", name)
    name = re.sub(r"[\s_-]+", "-", name)
    return name


def unique_slug(base_slug: str) -> str:
    slug = base_slug
    i = 1
    while (PROJECTS_DIR / slug).exists():
        slug = f"{base_slug}-{i}"
        i += 1
    return slug


def _ensure_dirs():
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)


def _project_dir_from_slug(slug: str) -> Path:
    return PROJECTS_DIR / slug


def _project_dir_legacy(project_id: str) -> Path:
    return PROJECTS_DIR / project_id


# ============================================================
# Create / Load / Save
# ============================================================

def create_project(
    name: str,
    root_path: str,
    encoding: str = "utf-8",
    language: str = "en",
    engine: str = "artemis",
) -> Project:
    _ensure_dirs()

    project_id = uuid.uuid4().hex[:8]
    base_slug = slugify(name)
    slug = unique_slug(base_slug)

    project = Project(
        id=project_id,
        name=name,
        root_path=root_path,
        encoding=encoding,
        language=language,
        engine=engine,
    )

    project.slug = slug  # type: ignore[attr-defined]

    save_project(project)
    return project


def save_project(project: Project):
    """
    Salvamento seguro:
    - backup automático (.bak)
    - escrita atômica (.tmp → .json)
    """
    _ensure_dirs()

    slug = getattr(project, "slug", None)
    project_dir = (
        _project_dir_from_slug(slug)
        if slug
        else _project_dir_legacy(project.id)
    )

    project_dir.mkdir(exist_ok=True)

    path = project_dir / "project.json"
    tmp_path = project_dir / "project.json.tmp"
    bak_path = project_dir / "project.json.bak"

    project.project_path = str(path)

    data = project.to_dict()
    if slug:
        data["slug"] = slug

    # 1️⃣ escreve no arquivo temporário
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # 2️⃣ cria backup se o arquivo já existir
    if path.exists():
        shutil.copy2(path, bak_path)

    # 3️⃣ substitui o arquivo real de forma atômica
    os.replace(tmp_path, path)


def load_project(project_path: str) -> Project:
    with open(project_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    project = Project.from_dict(data)
    project.project_path = project_path

    slug = data.get("slug")
    if slug:
        project.slug = slug  # type: ignore[attr-defined]

    project.index_entries()
    project.rebuild_all_file_status()

    return project


# ============================================================
# Management
# ============================================================

def rename_project(project: Project, new_name: str):
    project.name = new_name
    save_project(project)


def delete_project(project: Project):
    slug = getattr(project, "slug", None)
    project_dir = (
        _project_dir_from_slug(slug)
        if slug
        else _project_dir_legacy(project.id)
    )

    if project_dir.exists():
        shutil.rmtree(project_dir)


def list_projects() -> list[Project]:
    _ensure_dirs()

    projects: list[Project] = []

    for project_dir in PROJECTS_DIR.iterdir():
        path = project_dir / "project.json"
        if not path.exists():
            continue

        try:
            project = load_project(str(path))
            projects.append(project)
        except Exception:
            pass

    return projects
