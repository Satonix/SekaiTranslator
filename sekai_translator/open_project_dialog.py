from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QMessageBox,
    QInputDialog,
)

from sekai_translator.project_io import (
    list_projects,
    rename_project,
    delete_project,
)


class OpenProjectDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Abrir Projeto")
        self.resize(460, 380)

        self.project_path: str | None = None
        self._projects = []

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("<b>Projetos existentes</b>"))

        self.list = QListWidget()
        layout.addWidget(self.list)

        # ---------------- Botões ----------------

        btn_layout = QHBoxLayout()

        self.open_btn = QPushButton("Abrir")
        self.rename_btn = QPushButton("Renomear")
        self.delete_btn = QPushButton("Deletar")

        self.open_btn.clicked.connect(self._open_selected)
        self.rename_btn.clicked.connect(self._rename_selected)
        self.delete_btn.clicked.connect(self._delete_selected)

        btn_layout.addWidget(self.open_btn)
        btn_layout.addWidget(self.rename_btn)
        btn_layout.addWidget(self.delete_btn)

        layout.addLayout(btn_layout)

        self.list.itemDoubleClicked.connect(self._open_item)

        self._load_projects()

    # --------------------------------------------------------

    def _load_projects(self):
        self.list.clear()
        self._projects = list_projects()

        if not self._projects:
            self.list.addItem("(Nenhum projeto encontrado)")
            self.list.setEnabled(False)
            self.open_btn.setEnabled(False)
            self.rename_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)
            return

        self.list.setEnabled(True)
        self.open_btn.setEnabled(True)
        self.rename_btn.setEnabled(True)
        self.delete_btn.setEnabled(True)

        for project in self._projects:
            item = QListWidgetItem(project.name)
            item.setData(Qt.UserRole, project)
            self.list.addItem(item)

    # --------------------------------------------------------

    def _current_project(self):
        item = self.list.currentItem()
        if not item:
            return None
        return item.data(Qt.UserRole)

    # --------------------------------------------------------

    def _open_item(self, item: QListWidgetItem):
        project = item.data(Qt.UserRole)
        self.project_path = project.project_path
        self.accept()

    def _open_selected(self):
        project = self._current_project()
        if not project:
            QMessageBox.warning(
                self,
                "Nenhum projeto selecionado",
                "Selecione um projeto para abrir.",
            )
            return

        self.project_path = project.project_path
        self.accept()

    # --------------------------------------------------------
    # Renomear
    # --------------------------------------------------------

    def _rename_selected(self):
        project = self._current_project()
        if not project:
            return

        new_name, ok = QInputDialog.getText(
            self,
            "Renomear Projeto",
            "Novo nome do projeto:",
            text=project.name,
        )

        if not ok or not new_name.strip():
            return

        rename_project(project, new_name.strip())
        self._load_projects()

    # --------------------------------------------------------
    # Deletar
    # --------------------------------------------------------

    def _delete_selected(self):
        project = self._current_project()
        if not project:
            return

        res = QMessageBox.question(
            self,
            "Deletar Projeto",
            f"Tem certeza que deseja deletar o projeto:\n\n"
            f"\"{project.name}\"?\n\n"
            "⚠️ Apenas os dados do projeto serão apagados.\n"
            "Os arquivos do jogo NÃO serão removidos.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if res != QMessageBox.Yes:
            return

        delete_project(project)
        self._load_projects()
