from sekai_translator.parsers.registry import get_parser
from sekai_translator.core import Project


def export_translated_file(
    source_file: str,
    entries,
    project: Project,
    suffix: str = ".pt",
):
    parser = get_parser(source_file, project)
    return parser.rebuild(
        source_file,
        entries,
        project.encoding,
        suffix,
    )
