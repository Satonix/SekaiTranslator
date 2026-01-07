from pathlib import Path
from typing import List

from sekai_translator.core import TranslationEntry, TranslationStatus
from sekai_translator.parsers.base import BaseParser


class ArtemisParser(BaseParser):
    engine_name = "artemis"

    def can_parse(self, file_path: str) -> bool:
        return file_path.lower().endswith(".ast")

    # --------------------------------------------------

    def parse(self, file_path: str, encoding: str) -> List[TranslationEntry]:
        if not self.language:
            raise RuntimeError("Idioma não definido no parser Artemis")

        lines = Path(file_path).read_text(
            encoding=encoding, errors="ignore"
        ).splitlines()

        entries: List[TranslationEntry] = []

        inside_block = False
        inside_text = False
        inside_lang = False

        block_depth = 0
        text_depth = 0
        lang_depth = 0

        for ln, line in enumerate(lines, start=1):
            stripped = line.strip()

            if not inside_block and stripped.startswith("block_") and stripped.endswith("{"):
                inside_block = True
                block_depth = 1
                entries.append(self._raw(line, ln))
                continue

            if inside_block:
                block_depth += stripped.count("{")
                block_depth -= stripped.count("}")

                if not inside_text and stripped.startswith("text ="):
                    inside_text = True
                    text_depth = 1
                    entries.append(self._raw(line, ln))
                    continue

                if inside_text:
                    text_depth += stripped.count("{")
                    text_depth -= stripped.count("}")

                    if (
                        not inside_lang
                        and stripped.replace(" ", "").startswith(f"{self.language}=")
                        and stripped.endswith("{")
                    ):
                        inside_lang = True
                        lang_depth = 1
                        entries.append(self._raw(line, ln))
                        continue

                    if inside_lang:
                        lang_depth += stripped.count("{")
                        lang_depth -= stripped.count("}")

                        if lang_depth == 0:
                            inside_lang = False
                            entries.append(self._raw(line, ln))
                            continue

                        raw = line.rstrip().rstrip(",")

                        wrapper = None
                        text = None

                        if '[["' in raw and '"]]' in raw:
                            wrapper = "lua_long_string_quoted"
                            start = raw.find('[["') + 3
                            end = raw.rfind('"]]')
                            text = raw[start:end]

                        elif '[[' in raw and ']]' in raw:
                            wrapper = "lua_long_string"
                            start = raw.find('[[') + 2
                            end = raw.rfind(']]')
                            text = raw[start:end]

                        elif '"' in raw:
                            wrapper = "lua_string"
                            start = raw.find('"') + 1
                            end = raw.rfind('"')
                            text = raw[start:end]

                        if text is not None:
                            start_idx = line.find(text)
                            end_idx = start_idx + len(text)

                            entries.append(
                                TranslationEntry(
                                    entry_id=str(ln),
                                    original=text,
                                    translation="",
                                    status=TranslationStatus.UNTRANSLATED,
                                    context={
                                        "raw_line": line,
                                        "prefix": line[:start_idx],
                                        "suffix": line[end_idx:],
                                        "wrapper": wrapper,
                                        "is_translatable": True,
                                        "language": self.language,
                                        "line_number": ln,
                                    },
                                )
                            )
                            continue

                        entries.append(self._raw(line, ln))
                        continue

                    if text_depth == 0:
                        inside_text = False
                        entries.append(self._raw(line, ln))
                        continue

                    entries.append(self._raw(line, ln))
                    continue

                if block_depth == 0:
                    inside_block = False
                    entries.append(self._raw(line, ln))
                    continue

                entries.append(self._raw(line, ln))
                continue

            entries.append(self._raw(line, ln))

        return entries

    # --------------------------------------------------

    def rebuild(self, source_file, entries, encoding, suffix):
        from pathlib import Path

        src = Path(source_file)
        out = src.with_name(f"{src.stem}{suffix}{src.suffix}")

        output = []

        for e in entries:
            ctx = e.context

            if not ctx.get("is_translatable"):
                output.append(ctx["raw_line"])
                continue

            text = e.translation or e.original
            prefix = ctx["prefix"]
            suffix = ctx["suffix"]

            rebuilt = text

            # ==================================================
            # CASO EXATO: linha original era [["texto"]]
            # ==================================================
            if (
                prefix.rstrip().endswith("[[")
                and suffix.lstrip().startswith("]]")
                and not prefix.rstrip().endswith('"')
                and not suffix.lstrip().startswith('"')
            ):
                t = text.strip()
                if not (t.startswith('"') and t.endswith('"')):
                    rebuilt = f'"{t}"'
                else:
                    rebuilt = t

            output.append(f"{prefix}{rebuilt}{suffix}")

        out.write_text("\n".join(output), encoding=encoding)
        return out


    # --------------------------------------------------

    def _raw(self, line: str, ln: int) -> TranslationEntry:
        return TranslationEntry(
            entry_id=str(ln),
            original="",
            translation="",
            status=TranslationStatus.UNTRANSLATED,
            context={
                "raw_line": line,
                "is_translatable": False,
                "line_number": ln,
            },
        )
