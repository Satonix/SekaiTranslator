from pathlib import Path
from typing import List
import re

from sekai_translator.parsers.base import BaseParser
from sekai_translator.core import TranslationEntry, TranslationStatus


# ============================================================
# Regex
# ============================================================

# <Natsuki>"Texto"
# <Natsuki>(Texto)
DIALOG_RE = re.compile(
    r'^(?P<prefix><(?P<speaker>[^>]+)>[\"\(])'
    r'(?P<text>.+?)'
    r'(?P<suffix>[\"\)])$'
)


# ============================================================
# Parser
# ============================================================

class KirikiriParser(BaseParser):
    """
    Parser KiriKiri simples (script narrativo + <Nome>"Texto")
    """

    engine_name = "kirikiri"

    # --------------------------------------------------------

    def can_parse(self, file_path: str) -> bool:
        return file_path.lower().endswith((".ks", ".txt"))

    # --------------------------------------------------------
    # PARSE
    # --------------------------------------------------------

    def parse(self, file_path: str, encoding: str) -> List[TranslationEntry]:
        lines = Path(file_path).read_text(
            encoding=encoding, errors="ignore"
        ).splitlines()

        entries: List[TranslationEntry] = []

        for ln, line in enumerate(lines, start=1):
            stripped = line.strip()

            # ----------------------------
            # Linha vazia → estrutural
            # ----------------------------
            if not stripped:
                entries.append(self._raw(line, ln))
                continue

            # ----------------------------
            # Diálogo / Pensamento
            # ----------------------------
            m = DIALOG_RE.match(stripped)
            if m:
                speaker = m.group("speaker")
                text = m.group("text")
                prefix = m.group("prefix")
                suffix = m.group("suffix")

                start = line.find(text)
                end = start + len(text)

                entries.append(
                    TranslationEntry(
                        entry_id=str(ln),
                        original=text,
                        translation="",
                        status=TranslationStatus.UNTRANSLATED,
                        context={
                            "speaker": speaker,
                            "prefix": line[:start],
                            "suffix": line[end:],
                            "is_translatable": True,
                            "line_number": ln,
                        },
                    )
                )
                continue

            # ----------------------------
            # Narrativa (texto puro)
            # ----------------------------
            entries.append(
                TranslationEntry(
                    entry_id=str(ln),
                    original=line,
                    translation="",
                    status=TranslationStatus.UNTRANSLATED,
                    context={
                        "speaker": None,
                        "prefix": "",
                        "suffix": "",
                        "is_translatable": True,
                        "line_number": ln,
                    },
                )
            )

        return entries

    # --------------------------------------------------------
    # REBUILD
    # --------------------------------------------------------

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
            output.append(
                f"{ctx.get('prefix','')}{text}{ctx.get('suffix','')}"
            )

        out.write_text("\n".join(output), encoding=encoding)
        return out

    # --------------------------------------------------------

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
