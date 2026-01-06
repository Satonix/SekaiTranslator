from sekai_translator.parsers.registry import get_parser
from sekai_translator.core import Project


def import_file(file_path: str, project: Project):
    parser = get_parser(file_path, project)
    return parser.parse(file_path, project.encoding)
