from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFileDialog,
    QMessageBox,
    QComboBox,
)

from sekai_translator.project_io import create_project


class CreateProjectDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Criar Projeto")
        self.resize(420, 260)

        self.project_path: str | None = None

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Nome do projeto"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Ex: Stella of the End (PT-BR)")
        layout.addWidget(self.name_edit)

        layout.addWidget(QLabel("Pasta do jogo"))
        root_layout = QHBoxLayout()
        self.root_edit = QLineEdit()
        browse_btn = QPushButton("Selecionar...")
        browse_btn.clicked.connect(self._browse_root)

        root_layout.addWidget(self.root_edit)
        root_layout.addWidget(browse_btn)
        layout.addLayout(root_layout)

        layout.addWidget(QLabel("Idioma a traduzir"))
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["en", "jp", "cn"])
        layout.addWidget(self.lang_combo)

        layout.addWidget(QLabel("Engine do jogo"))
        self.engine_combo = QComboBox()
        self.engine_combo.addItems([
            "artemis",
            # "kirikiri",
            # "renpy",
        ])
        layout.addWidget(self.engine_combo)

        create_btn = QPushButton("Criar Projeto")
        create_btn.clicked.connect(self._create_project)
        layout.addWidget(create_btn)

    # --------------------------------------------------

    def _browse_root(self):
        path = QFileDialog.getExistingDirectory(
            self, "Selecione a pasta do jogo"
        )
        if path:
            self.root_edit.setText(path)

    def _create_project(self):
        name = self.name_edit.text().strip()
        root = self.root_edit.text().strip()
        language = self.lang_combo.currentText()
        engine = self.engine_combo.currentText()

        if not name or not root:
            QMessageBox.warning(
                self,
                "Dados incompletos",
                "Informe o nome do projeto e a pasta do jogo.",
            )
            return

        project = create_project(
            name=name,
            root_path=root,
            language=language,
            engine=engine,
        )

        self.project_path = project.project_path
        self.accept()
