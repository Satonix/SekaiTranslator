import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPalette, QColor
from PySide6.QtCore import Qt

from sekai_translator.main_window import MainWindow


def apply_dark_theme(app: QApplication):
    """
    Aplica tema escuro global (padrão).
    """
    app.setStyle("Fusion")

    palette = QPalette()

    # Base
    palette.setColor(QPalette.Window, QColor(30, 30, 30))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(24, 24, 24))
    palette.setColor(QPalette.AlternateBase, QColor(36, 36, 36))
    palette.setColor(QPalette.ToolTipBase, Qt.white)
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(45, 45, 45))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.BrightText, Qt.red)

    # Destaques
    palette.setColor(QPalette.Highlight, QColor(60, 120, 200))
    palette.setColor(QPalette.HighlightedText, Qt.white)

    # Estados desativados
    palette.setColor(QPalette.Disabled, QPalette.Text, QColor(130, 130, 130))
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(130, 130, 130))

    app.setPalette(palette)


def main():
    app = QApplication(sys.argv)

    # 🌙 Tema escuro como padrão
    apply_dark_theme(app)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
