from sekai_translator.core import TranslationEntry, TranslationStatus


class StatusService:
    """
    Fonte ÚNICA da verdade sobre status de tradução.
    """

    @staticmethod
    def on_text_edited(entry: TranslationEntry, text: str):
        """
        Chamado quando o usuário digita algo,
        mas ainda não confirmou a tradução.
        """
        entry.translation = text

        if not text.strip():
            entry.status = TranslationStatus.UNTRANSLATED
        else:
            entry.status = TranslationStatus.IN_PROGRESS

    @staticmethod
    def on_translation_committed(entry: TranslationEntry, text: str):
        """
        Chamado quando o usuário CONFIRMA a tradução (Enter).
        """
        entry.translation = text

        if text.strip():
            entry.status = TranslationStatus.TRANSLATED
        else:
            entry.status = TranslationStatus.UNTRANSLATED
