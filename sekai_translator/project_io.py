import json
import uuid
import shutil
from pathlib import Path

from sekai_translator.core import Project


import os
from pathlib import Path

APP_DIR = Path(os.getenv("LOCALAPPDATA", Path.home())) / "SekaiTranslator"
PROJECTS_DIR = APP_DIR / "projects"



def _ensure_dirs():
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)


def _project_dir(project_id: str) -> Path:
    return PROJECTS_DIR / project_id


# ============================================================
# Create / Load / Save
# ============================================================

def create_project(
    name: str,
    root_path: str,
    encoding: str = "utf-8",
    language: str = "en",
    engine: str = "artemis",  # 👈
) -> Project:
    _ensure_dirs()

    project_id = uuid.uuid4().hex[:8]
    project = Project(
        id=project_id,
        name=name,
        root_path=root_path,
        encoding=encoding,
        language=language,
        engine=engine,  # 👈
    )

    save_project(project)
    return project


def save_project(project: Project):
    _ensure_dirs()

    project_dir = _project_dir(project.id)
    project_dir.mkdir(exist_ok=True)

    path = project_dir / "project.json"
    project.project_path = str(path)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(project.to_dict(), f, ensure_ascii=False, indent=2)


def load_project(project_path: str) -> Project:
    with open(project_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    project = Project.from_dict(data)
    project.project_path = project_path
    return project


# ============================================================
# Management
# ============================================================

def rename_project(project: Project, new_name: str):
    project.name = new_name
    save_project(project)


def delete_project(project: Project):
    project_dir = _project_dir(project.id)
    if project_dir.exists():
        shutil.rmtree(project_dir)


def list_projects() -> list[Project]:
    _ensure_dirs()

    projects = []
    for project_dir in PROJECTS_DIR.iterdir():
        path = project_dir / "project.json"
        if not path.exists():
            continue
        try:
            projects.append(load_project(str(path)))
        except Exception:
            pass

    return projects
