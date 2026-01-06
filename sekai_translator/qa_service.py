import re
from dataclasses import dataclass
from typing import List

from sekai_translator.core import TranslationEntry, TranslationStatus


# ============================================================
# QA Issue
# ============================================================

@dataclass
class QAIssue:
    level: str      # "warning" | "error"
    code: str       # identificador curto
    message: str    # mensagem amigável


# ============================================================
# QA Service (CORRIGIDO)
# ============================================================

class QAService:

    TAG_PATTERN = re.compile(r"""
        (\{[^}]+\})            |  # {player_name}
        (\[[^\]]+\])           |  # [ruby=...]
        (<[^>]+>)                 # <color=red>
    """, re.VERBOSE)

    LENGTH_RATIO_LIMIT = 1.8

    # --------------------------------------------------------

    @staticmethod
    def run(entry: TranslationEntry) -> List[QAIssue]:
        issues: List[QAIssue] = []

        original = entry.original or ""
        translation = entry.translation or ""

        # Ignora linhas estruturais
        if entry.context.get("is_empty"):
            return issues

        prefix = entry.context.get("prefix", "") or ""
        suffix = entry.context.get("suffix", "") or ""

        rebuilt = f"{prefix}{translation}{suffix}"

        # ----------------------------------------------------
        # 1️⃣ Tradução vazia (SÓ SE NÃO FOR UNTRANSLATED)
        # ----------------------------------------------------
        if (
            entry.status != TranslationStatus.UNTRANSLATED
            and original.strip()
            and not translation.strip()
        ):
            issues.append(
                QAIssue(
                    level="warning",
                    code="EMPTY_TRANSLATION",
                    message="Tradução vazia.",
                )
            )

        # ----------------------------------------------------
        # 2️⃣ Tradução idêntica ao original
        # ----------------------------------------------------
        original_core = original
        if original.startswith(prefix) and original.endswith(suffix):
            original_core = original[len(prefix):len(original) - len(suffix)]

        if (
            entry.status != TranslationStatus.UNTRANSLATED
            and translation.strip()
            and translation.strip() == original_core.strip()
        ):
            issues.append(
                QAIssue(
                    level="warning",
                    code="IDENTICAL_TEXT",
                    message="Tradução idêntica ao original.",
                )
            )

        # ----------------------------------------------------
        # 3️⃣ Tags obrigatórias ausentes
        # ----------------------------------------------------
        original_tags = set(QAService.TAG_PATTERN.findall(original))
        rebuilt_tags = set(QAService.TAG_PATTERN.findall(rebuilt))

        original_tags = {t for group in original_tags for t in group if t}
        rebuilt_tags = {t for group in rebuilt_tags for t in group if t}

        missing_tags = original_tags - rebuilt_tags
        if missing_tags:
            issues.append(
                QAIssue(
                    level="error",
                    code="MISSING_TAG",
                    message=f"Tags ausentes na tradução: {', '.join(missing_tags)}",
                )
            )

        # ----------------------------------------------------
        # 4️⃣ Prefixo / sufixo preservados
        # ----------------------------------------------------
        if prefix and not rebuilt.startswith(prefix):
            issues.append(
                QAIssue(
                    level="error",
                    code="PREFIX_MISMATCH",
                    message="Prefixo original não preservado.",
                )
            )

        if suffix and not rebuilt.endswith(suffix):
            issues.append(
                QAIssue(
                    level="error",
                    code="SUFFIX_MISMATCH",
                    message="Sufixo original não preservado.",
                )
            )

        # ----------------------------------------------------
        # 5️⃣ Texto excessivamente longo
        # ----------------------------------------------------
        if (
            entry.status != TranslationStatus.UNTRANSLATED
            and original.strip()
            and translation.strip()
            and len(translation) > len(original) * QAService.LENGTH_RATIO_LIMIT
        ):
            issues.append(
                QAIssue(
                    level="warning",
                    code="TEXT_TOO_LONG",
                    message="Tradução muito mais longa que o original.",
                )
            )

        return issues
