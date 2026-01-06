class BaseParser:
    engine_name = "base"

    def __init__(self):
        self.language = None

    def set_language(self, language: str):
        self.language = language

    def can_parse(self, file_path: str) -> bool:
        raise NotImplementedError

    def parse(self, file_path: str, encoding: str):
        raise NotImplementedError

    def rebuild(self, source_file, entries, encoding, suffix):
        raise NotImplementedError
