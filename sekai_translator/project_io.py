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
    """
    Converte o nome do projeto em um slug seguro para pasta.
    """
    name = name.lower().strip()
    name = re.sub(r"[^\w\s-]", "", name)
    name = re.sub(r"[\s_-]+", "-", name)
    return name


def unique_slug(base_slug: str) -> str:
    """
    Garante que o slug seja único dentro da pasta de projetos.
    """
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
    """
    Diretório legado baseado em ID (projetos antigos).
    """
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
    """
    Cria um novo projeto usando SLUG como nome da pasta.
    """
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

    # slug não é obrigatório, mas é MUITO útil
    project.slug = slug  # type: ignore[attr-defined]

    save_project(project)
    return project


def save_project(project: Project):
    """
    Salva o projeto em disco.
    Usa slug se existir, senão fallback para ID (legado).
    """
    _ensure_dirs()

    slug = getattr(project, "slug", None)

    if slug:
        project_dir = _project_dir_from_slug(slug)
    else:
        project_dir = _project_dir_legacy(project.id)

    project_dir.mkdir(exist_ok=True)

    path = project_dir / "project.json"
    project.project_path = str(path)

    data = project.to_dict()

    # persiste slug no JSON se existir
    if slug:
        data["slug"] = slug

    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2,
        )


def load_project(project_path: str) -> Project:
    """
    Carrega projeto (novo ou legado).
    """
    with open(project_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    project = Project.from_dict(data)
    project.project_path = project_path

    # restaura slug se existir
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
    """
    Renomeia apenas o NOME LÓGICO do projeto.
    (não renomeia a pasta automaticamente)
    """
    project.name = new_name
    save_project(project)


def delete_project(project: Project):
    """
    Remove a pasta do projeto (slug ou legado).
    """
    slug = getattr(project, "slug", None)

    if slug:
        project_dir = _project_dir_from_slug(slug)
    else:
        project_dir = _project_dir_legacy(project.id)

    if project_dir.exists():
        shutil.rmtree(project_dir)


def list_projects() -> list[Project]:
    """
    Lista todos os projetos (slug e legado).
    """
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
