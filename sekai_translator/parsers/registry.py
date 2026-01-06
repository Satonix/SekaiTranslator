from sekai_translator.parsers.artemis import ArtemisParser


# --------------------------------------------------
# Normalização de idioma
# --------------------------------------------------

LANG_ALIASES = {
    "jp": "ja",
    "jpn": "ja",
    "ja": "ja",

    "en": "en",
    "eng": "en",

    "cn": "cn",
    "zh": "cn",
    "chi": "cn",
}


def normalize_language(lang: str) -> str:
    if not lang:
        return "en"

    lang = lang.lower()
    return LANG_ALIASES.get(lang, lang)


# --------------------------------------------------
# Registry
# --------------------------------------------------

PARSERS = [
    ArtemisParser,
]


def get_parser(file_path, project):
    language = normalize_language(project.language)
    engine = project.engine.lower()

    for parser_cls in PARSERS:
        if parser_cls.engine_name != engine:
            continue

        parser = parser_cls()
        if parser.can_parse(file_path):
            parser.set_language(language)
            return parser

    raise RuntimeError(
        f"Nenhum parser disponível para engine='{engine}' "
        f"e arquivo='{file_path}'"
    )
