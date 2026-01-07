from pathlib import Path
from typing import List

from sekai_translator.core import TranslationEntry, TranslationStatus
from sekai_translator.parsers.base import BaseParser


class SiglusParser(BaseParser):
    engine_name = "siglus"

    # --------------------------------------------------

    def can_parse(self, file_path: str) -> bool:
        return file_path.lower().endswith(".txt")

    # --------------------------------------------------
    # PARSE
    # --------------------------------------------------

    def parse(self, file_path: str, encoding: str) -> List[TranslationEntry]:
        lines = Path(file_path).read_text(
            encoding=encoding, errors="ignore"
        ).splitlines()

        entries: List[TranslationEntry] = []
        i = 0

        while i < len(lines) - 1:
            line_a = lines[i]
            line_b = lines[i + 1]

            # precisa ser par ○ / ●
            if not (line_a.startswith("○") and line_b.startswith("●")):
                entries.append(self._raw(line_a, i + 1))
                i += 1
                continue

            id_end = line_a.find("○", 1)
            if id_end == -1:
                entries.append(self._raw(line_a, i + 1))
                i += 1
                continue

            raw_text = line_a[id_end + 1 :].strip()

            # ---------------------------------
            # DETECÇÃO DE FALA (aspas)
            # ---------------------------------
            has_quotes = (
                (raw_text.startswith("“") and raw_text.endswith("”"))
                or (raw_text.startswith('"') and raw_text.endswith('"'))
            )

            # ---------------------------------
            # Se NÃO for fala → esconder
            # ---------------------------------
            if not has_quotes:
                entries.append(self._raw(line_a, i + 1))
                entries.append(self._raw(line_b, i + 2))
                i += 2
                continue

            # remove aspas
            prefix_extra = raw_text[0]
            suffix_extra = raw_text[-1]
            text = raw_text[1:-1]

            if not text.strip():
                entries.append(self._raw(line_a, i + 1))
                entries.append(self._raw(line_b, i + 2))
                i += 2
                continue

            entries.append(
                TranslationEntry(
                    entry_id=str(i),
                    original=text,
                    translation="",
                    status=TranslationStatus.UNTRANSLATED,
                    context={
                        "prefix_a": line_a[: id_end + 1] + prefix_extra,
                        "prefix_b": line_b[: id_end + 1] + prefix_extra,
                        "suffix": suffix_extra,
                        "is_translatable": True,
                        "line_number": i + 1,
                    },
                )
            )

            i += 2

        # sobra de linha
        if i < len(lines):
            entries.append(self._raw(lines[i], i + 1))

        return entries

    # --------------------------------------------------
    # REBUILD
    # --------------------------------------------------

    def rebuild(self, source_file, entries, encoding, suffix):
        src = Path(source_file)
        out = src.with_name(f"{src.stem}{suffix}{src.suffix}")

        output: List[str] = []

        for e in entries:
            ctx = e.context

            if not ctx.get("is_translatable"):
                output.append(ctx["raw_line"])
                continue

            text = e.translation or e.original
            output.append(f'{ctx["prefix_a"]}{text}{ctx["suffix"]}')
            output.append(f'{ctx["prefix_b"]}{text}{ctx["suffix"]}')

        out.write_text("\n".join(output), encoding=encoding)
        return out

    # --------------------------------------------------

    def _raw(self, line: str, ln: int) -> TranslationEntry:
        return TranslationEntry(
            entry_id=f"raw-{ln}",
            original="",
            translation="",
            status=TranslationStatus.UNTRANSLATED,
            context={
                "raw_line": line,
                "is_translatable": False,
                "line_number": ln,
            },
        )
