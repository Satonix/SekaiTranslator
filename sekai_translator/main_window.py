from pathlib import Path
from typing import Dict

import sys
import tempfile
import subprocess

from PySide6.QtCore import Qt, QSortFilterProxyModel, QSettings
from PySide6.QtGui import QAction, QFont, QColor
from PySide6.QtWidgets import (
    QMainWindow,
    QSplitter,
    QTreeView,
    QFileSystemModel,
    QMessageBox,
    QTabWidget,
    QWidget,
    QVBoxLayout,
    QHeaderView,
    QLabel,
    QTableView,
    QProgressDialog,
    QApplication,
)

from sekai_translator import __app_name__, __version__
from sekai_translator.update_service import UpdateService

from sekai_translator.core import Project, TranslationStatus
from sekai_translator.project_io import load_project, save_project
from sekai_translator.translation_table import (
    TranslationTableModel,
    TranslationTableView,
)
from sekai_translator.editor_panel import EditorPanel
from sekai_translator.importer import import_file
from sekai_translator.exporter import export_translated_file
from sekai_translator.qa_service import QAService

from sekai_translator.create_project_dialog import CreateProjectDialog
from sekai_translator.open_project_dialog import OpenProjectDialog


# ============================================================
# TreeView Proxy
# ============================================================

class FileFilterProxy(QSortFilterProxyModel):

    ALLOWED_EXTENSIONS = {".ast"}

    def __init__(self):
        super().__init__()
        self.project: Project | None = None
        self.active_path: Path | None = None

    def set_project(self, project: Project | None):
        self.project = project
        self.invalidate()

    def set_active_path(self, path: str | None):
        self.active_path = Path(path).resolve() if path else None
        self.invalidate()

    def filterAcceptsRow(self, row, parent):
        index = self.sourceModel().index(row, 0, parent)
        if not index.isValid():
            return False

        path = Path(self.sourceModel().filePath(index))
        if path.is_dir():
            return True

        return path.suffix.lower() in self.ALLOWED_EXTENSIONS

    def data(self, index, role=Qt.DisplayRole):
        src = self.mapToSource(index)
        path = Path(self.sourceModel().filePath(src)).resolve()

        if role == Qt.FontRole:
            font = QFont()
            if self.active_path and path == self.active_path:
                font.setBold(True)
            return font

        if role == Qt.ForegroundRole and self.project:
            entries = self.project.files.get(str(path))
            if entries and any(e.status == TranslationStatus.TRANSLATED for e in entries):
                return QColor("#a7f3d0")

            if self.active_path and path == self.active_path:
                return QColor("#8ab4f8")

        return super().data(index, role)


# ============================================================
# FileTab
# ============================================================

class FileTab(QWidget):

    def __init__(self, project: Project, file_path: str, parent):
        super().__init__()

        self.project = project
        self.file_path = file_path
        self.parent = parent
        self.dirty = False

        if file_path not in project.files:
            project.files[file_path] = import_file(file_path, project)
            project.index_entries()

        self.all_entries = project.files[file_path]

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Vertical)
        layout.addWidget(splitter)

        # ---------------- TABELA ----------------

        self.table = TranslationTableView()
        self.model = TranslationTableModel(self.all_entries)
        self.table.setModel(self.model)

        self.table.setFocusPolicy(Qt.StrongFocus)
        self.table.setFocus()

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)

        # ---------------- EDITOR ----------------

        self.editor = EditorPanel(self.project)

        splitter.addWidget(self.table)
        splitter.addWidget(self.editor)
        splitter.setSizes([360, 540])

        # ---------------- SIGNALS ----------------

        self.table.selectionModel().selectionChanged.connect(
            self._on_selection_changed
        )
        self.editor.entry_changed.connect(self._on_entry_changed)

        self.editor.request_next.connect(self._go_next)
        self.editor.request_prev.connect(self._go_prev)
        self.model.advance_requested.connect(self._go_next_from_model)

        if self.model.rowCount() > 0:
            self.table.selectRow(0)
            self.table.setFocus()

    # --------------------------------------------------------

    def _on_selection_changed(self, *_):
        rows = sorted(
            i.row() for i in self.table.selectionModel().selectedRows()
        )
        if rows:
            self.editor.set_entries(
                [self.model.entries[r] for r in rows]
            )
            self.table.setFocus()

    def _on_entry_changed(self):
        for entry in self.editor._entries:
            entry.qa_issues = QAService.run(entry)

        self.dirty = True
        self.parent.update_tab_title(self)
        self.model.refresh()
        self.parent.fs_proxy.invalidate()
        self.table.setFocus()

    # --------------------------------------------------------

    def _go_next(self):
        if not self.editor._entries:
            return

        entry = self.editor._entries[-1]

        try:
            row = self.model.entries.index(entry)
        except ValueError:
            return

        next_row = row + 1
        if next_row >= self.model.rowCount():
            return

        self.table.selectRow(next_row)
        self.table.scrollTo(
            self.model.index(next_row, 0),
            QTableView.PositionAtCenter,
        )
        self.table.setFocus()

    def _go_prev(self):
        index = self.table.currentIndex()
        if not index.isValid():
            return

        row = index.row() - 1
        if row < 0:
            return

        self.table.selectRow(row)
        self.table.scrollTo(
            self.model.index(row, 0),
            QTableView.PositionAtCenter,
        )
        self.table.setFocus()

    def _go_next_from_model(self, row: int):
        row += 1
        if row >= self.model.rowCount():
            return

        self.table.selectRow(row)
        self.table.scrollTo(
            self.model.index(row, 0),
            QTableView.PositionAtCenter,
        )
        self.table.setFocus()

    def mark_clean(self):
        self.dirty = False
        self.parent.update_tab_title(self)


# ============================================================
# MainWindow
# ============================================================

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle(f"{__app_name__} v{__version__}")
        self.resize(1500, 900)

        self.settings = QSettings("SekaiVN", "SekaiTranslator")

        self.project: Project | None = None
        self.open_tabs: Dict[str, FileTab] = {}

        self._build_ui()
        self._build_menu()
        self._try_restore_last_project()

        # 🔄 Verificação automática ao iniciar
        self._check_for_updates()

    # --------------------------------------------------------
    # Atualização
    # --------------------------------------------------------

    def _check_for_updates(self):
        info = UpdateService.check(__version__)
        if not info:
            QMessageBox.information(
                self,
                "Atualizações",
                "Você já está usando a versão mais recente.",
            )
            return

        res = QMessageBox.question(
            self,
            "Atualização disponível",
            f"Uma nova versão do {__app_name__} está disponível.\n\n"
            f"Versão atual: {__version__}\n"
            f"Nova versão: {info.version}\n\n"
            f"Deseja atualizar agora?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )

        if res == QMessageBox.Yes:
            self._download_and_update(info)

    def check_for_updates_manual(self):
        self._check_for_updates()

    def _download_and_update(self, info):
        import requests

        tmp_dir = Path(tempfile.gettempdir())
        new_exe = tmp_dir / "SekaiTranslator_new.exe"

        r = requests.get(info.url, stream=True)
        r.raise_for_status()

        total = int(r.headers.get("Content-Length", 0))

        progress = QProgressDialog(
            "Baixando atualização...",
            "Cancelar",
            0,
            total,
            self,
        )
        progress.setWindowTitle("Atualizando")
        progress.setMinimumDuration(0)
        progress.setValue(0)

        downloaded = 0

        with open(new_exe, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if progress.wasCanceled():
                    r.close()
                    if new_exe.exists():
                        new_exe.unlink()
                    return

                if not chunk:
                    continue

                f.write(chunk)
                downloaded += len(chunk)
                progress.setValue(downloaded)
                QApplication.processEvents()

        progress.close()

        updater = Path(sys.executable).with_name("updater.exe")

        subprocess.Popen([
            str(updater),
            str(new_exe),
            sys.executable,
        ])

        sys.exit(0)

    # --------------------------------------------------------

    def closeEvent(self, event):
        dirty_tabs = [
            tab for tab in self.open_tabs.values()
            if tab.dirty
        ]

        if dirty_tabs:
            res = QMessageBox.question(
                self,
                "Projeto não salvo",
                "Existem arquivos não salvos.\n\n"
                "Deseja salvar antes de sair?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                QMessageBox.Yes,
            )

            if res == QMessageBox.Cancel:
                event.ignore()
                return

            if res == QMessageBox.Yes:
                self.save_project()

        event.accept()

    # --------------------------------------------------------

    def _build_ui(self):
        splitter = QSplitter(Qt.Horizontal)
        self.setCentralWidget(splitter)

        tree_container = QWidget()
        tree_layout = QVBoxLayout(tree_container)
        tree_layout.setContentsMargins(6, 6, 6, 6)

        self.tree_header = QLabel("Nenhum projeto aberto")
        tree_layout.addWidget(self.tree_header)

        self.fs_model = QFileSystemModel()
        self.fs_proxy = FileFilterProxy()
        self.fs_proxy.setSourceModel(self.fs_model)

        self.tree = QTreeView()
        self.tree.setModel(self.fs_proxy)
        self.tree.setHeaderHidden(True)
        self.tree.setEnabled(False)

        for i in range(1, 4):
            self.tree.hideColumn(i)

        tree_layout.addWidget(self.tree)
        splitter.addWidget(tree_container)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        splitter.addWidget(self.tabs)

        splitter.setSizes([260, 1240])

        self.tree.doubleClicked.connect(self._on_tree_double_click)
        self.tabs.tabCloseRequested.connect(self._close_tab)

    # --------------------------------------------------------

    def _build_menu(self):
        menu = self.menuBar().addMenu("Arquivo")

        open_action = QAction("Abrir Projeto...", self)
        open_action.triggered.connect(self.open_project)
        menu.addAction(open_action)

        create_action = QAction("Criar Projeto...", self)
        create_action.triggered.connect(self.create_project)
        menu.addAction(create_action)

        save_action = QAction("Salvar Projeto", self)
        save_action.triggered.connect(self.save_project)
        menu.addAction(save_action)

        export_action = QAction("Exportar Arquivo Atual", self)
        export_action.triggered.connect(self.export_current_file)
        menu.addAction(export_action)

        menu.addSeparator()

        update_action = QAction("Verificar atualizações", self)
        update_action.triggered.connect(self.check_for_updates_manual)
        menu.addAction(update_action)

    # --------------------------------------------------------

    def _try_restore_last_project(self):
        last = self.settings.value("last_project_path", "")
        if last and Path(last).exists():
            try:
                self._load_project(last)
            except Exception:
                pass

    # --------------------------------------------------------

    def open_project(self):
        dlg = OpenProjectDialog(self)
        if dlg.exec():
            self._load_project(dlg.project_path)

    def create_project(self):
        dlg = CreateProjectDialog(self)
        if dlg.exec():
            self._load_project(dlg.project_path)

    def _load_project(self, path: str):
        self.project = load_project(path)
        self.project.index_entries()

        root = Path(self.project.root_path)
        src_index = self.fs_model.setRootPath(str(root))
        self.tree.setRootIndex(self.fs_proxy.mapFromSource(src_index))

        self.fs_proxy.set_project(self.project)
        self.tree.setEnabled(True)
        self.tree_header.setText(
            f"{self.project.name}  [lang={self.project.language}]"
        )

        self.tabs.clear()
        self.open_tabs.clear()

    # --------------------------------------------------------

    def _on_tree_double_click(self, proxy_index):
        if not self.project:
            return

        src = self.fs_proxy.mapToSource(proxy_index)
        path = self.fs_model.filePath(src)

        if Path(path).is_dir():
            return

        self._open_file(path)

    def _open_file(self, path: str):
        if path in self.open_tabs:
            self.tabs.setCurrentWidget(self.open_tabs[path])
            return

        tab = FileTab(self.project, path, self)
        self.open_tabs[path] = tab

        rel = str(Path(path).relative_to(self.project.root_path))
        self.tabs.addTab(tab, rel)
        self.tabs.setCurrentWidget(tab)

        self.fs_proxy.set_active_path(path)

    # --------------------------------------------------------

    def update_tab_title(self, tab: FileTab):
        idx = self.tabs.indexOf(tab)
        if idx != -1:
            title = str(Path(tab.file_path).relative_to(self.project.root_path))
            self.tabs.setTabText(idx, f"● {title}" if tab.dirty else title)

    def _close_tab(self, index):
        tab: FileTab = self.tabs.widget(index)
        self.open_tabs.pop(tab.file_path, None)
        self.tabs.removeTab(index)

    # --------------------------------------------------------

    def save_project(self):
        if not self.project:
            return

        save_project(self.project)
        for tab in self.open_tabs.values():
            tab.mark_clean()

    # --------------------------------------------------------

    def export_current_file(self):
        tab = self.tabs.currentWidget()
        if not tab or not self.project:
            return

        critical_errors = [
            issue
            for entry in tab.all_entries
            for issue in entry.qa_issues
            if issue.level == "error"
        ]

        if critical_errors:
            QMessageBox.critical(
                self,
                "Erro crítico de QA",
                "Corrija os erros antes de exportar.",
            )
            return

        out = export_translated_file(
            tab.file_path,
            tab.all_entries,
            self.project,
        )

        QMessageBox.information(
            self,
            "Exportação concluída",
            f"Arquivo exportado:\n{out}",
        )
