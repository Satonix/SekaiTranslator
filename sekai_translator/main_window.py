from pathlib import Path
from typing import Dict
import os
import sys
import subprocess

from PySide6.QtCore import Qt, QSortFilterProxyModel, QSettings
from PySide6.QtGui import QFont, QColor, QShortcut
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
from sekai_translator.project_status import build_project_status, export_project_status

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
        self.active_path: str | None = None

    def set_project(self, project: Project | None):
        self.project = project
        self.invalidateFilter()

    def set_active_path(self, path: str | None):
        self.active_path = os.path.normpath(path) if path else None
        self.invalidateFilter()

    def filterAcceptsRow(self, row, parent):
        index = self.sourceModel().index(row, 0, parent)
        if not index.isValid():
            return False

        path = self.sourceModel().filePath(index)
        if os.path.isdir(path):
            return True

        return Path(path).suffix.lower() in self.ALLOWED_EXTENSIONS

    def data(self, index, role=Qt.DisplayRole):
        src = self.mapToSource(index)
        path = self.sourceModel().filePath(src)

        if role == Qt.DisplayRole:
            name = os.path.basename(path)
            if self.project and path in self.project.files:
                progress = self.project.file_progress(path)
                return f"{name} [{progress}%]"
            return name

        if role == Qt.FontRole:
            font = QFont()
            if self.active_path and os.path.normpath(path) == self.active_path:
                font.setBold(True)
            return font

        if role == Qt.ForegroundRole and self.project:
            if self.project.file_status_cache.get(path):
                return QColor("#a7f3d0")

            if self.active_path and os.path.normpath(path) == self.active_path:
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
            project.update_file_status(file_path)

        self.all_entries = project.files[file_path]

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Vertical)
        layout.addWidget(splitter)

        self.table = TranslationTableView()
        self.model = TranslationTableModel(self.all_entries)
        self.table.setModel(self.model)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)

        self.editor = EditorPanel(self.project)

        splitter.addWidget(self.table)
        splitter.addWidget(self.editor)
        splitter.setSizes([360, 540])

        self.table.selectionModel().selectionChanged.connect(
            self._on_selection_changed
        )
        self.editor.entry_changed.connect(self._on_entry_changed)

        self.editor.request_next.connect(self._go_next)
        self.editor.request_prev.connect(self._go_prev)
        self.model.advance_requested.connect(self._go_next_from_model)

        if self.model.rowCount() > 0:
            self.table.selectRow(0)

    def _on_selection_changed(self, *_):
        rows = sorted(
            i.row() for i in self.table.selectionModel().selectedRows()
        )
        if rows:
            self.editor.set_entries([self.model.entries[r] for r in rows])

    def _on_entry_changed(self):
        for entry in self.editor._entries:
            entry.qa_issues = QAService.run(entry)

        self.project.update_file_status(self.file_path)

        self.dirty = True
        self.parent.update_tab_title(self)
        self.parent._update_status_bar()

        self.model.refresh()

    def _go_next(self):
        if not self.editor._entries:
            return
        entry = self.editor._entries[-1]
        try:
            row = self.model.entries.index(entry)
        except ValueError:
            return

        if row + 1 < self.model.rowCount():
            self.table.selectRow(row + 1)

    def _go_prev(self):
        index = self.table.currentIndex()
        if index.isValid() and index.row() > 0:
            self.table.selectRow(index.row() - 1)

    def _go_next_from_model(self, row: int):
        if row + 1 < self.model.rowCount():
            self.table.selectRow(row + 1)

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
        self._build_status_bar()
        self._build_menu()
        self._install_global_shortcuts()
        self._try_restore_last_project()

        self.check_for_updates(auto=True)

    # --------------------------------------------------------
    # Status bar
    # --------------------------------------------------------

    def _build_status_bar(self):
        bar = self.statusBar()

        self.status_file = QLabel("Arquivo: -")
        self.status_file_progress = QLabel("Arquivo: 0%")
        self.status_project_progress = QLabel("Projeto: 0%")

        bar.addWidget(self.status_file)
        bar.addWidget(self.status_file_progress)
        bar.addPermanentWidget(self.status_project_progress)

    def _update_status_bar(self):
        if not self.project:
            self.status_file.setText("Arquivo: -")
            self.status_file_progress.setText("Arquivo: 0%")
            self.status_project_progress.setText("Projeto: 0%")
            return

        tab = self.tabs.currentWidget()

        if tab:
            name = Path(tab.file_path).name
            progress = self.project.file_progress(tab.file_path)
            self.status_file.setText(f"Arquivo: {name}")
            self.status_file_progress.setText(f"Arquivo: {progress}%")
        else:
            self.status_file.setText("Arquivo: -")
            self.status_file_progress.setText("Arquivo: 0%")

        stats = build_project_status(self.project)
        self.status_project_progress.setText(
            f"Projeto: {stats['stats']['progress']}%"
        )

    # --------------------------------------------------------
    # Global shortcuts
    # --------------------------------------------------------

    def _install_global_shortcuts(self):
        self.undo_shortcut = QShortcut("Ctrl+Z", self)
        self.undo_shortcut.setContext(Qt.ApplicationShortcut)
        self.undo_shortcut.activated.connect(self.undo)

        self.redo_shortcut = QShortcut("Ctrl+Y", self)
        self.redo_shortcut.setContext(Qt.ApplicationShortcut)
        self.redo_shortcut.activated.connect(self.redo)

    # --------------------------------------------------------
    # UI
    # --------------------------------------------------------

    def _build_ui(self):
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.setCentralWidget(self.main_splitter)

        tree_container = QWidget()
        tree_layout = QVBoxLayout(tree_container)
        tree_layout.setContentsMargins(6, 6, 6, 6)

        self.tree_header = QLabel("Nenhum projeto aberto")
        tree_layout.addWidget(self.tree_header)

        self.fs_model = QFileSystemModel()
        self.fs_model.setNameFilters(["*.ast"])
        self.fs_model.setNameFilterDisables(False)

        self.fs_proxy = FileFilterProxy()
        self.fs_proxy.setSourceModel(self.fs_model)

        self.tree = QTreeView()
        self.tree.setModel(self.fs_proxy)
        self.tree.setHeaderHidden(True)
        self.tree.setEnabled(False)
        self.tree.setUniformRowHeights(True)
        self.tree.setMinimumWidth(220)
        self.tree.setMaximumWidth(400)

        for i in range(1, 4):
            self.tree.hideColumn(i)

        tree_layout.addWidget(self.tree)
        self.main_splitter.addWidget(tree_container)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.main_splitter.addWidget(self.tabs)
        self.main_splitter.setSizes([300, 1200])

        self.tree.doubleClicked.connect(self._on_tree_double_click)
        self.tabs.tabCloseRequested.connect(self._close_tab)

    # --------------------------------------------------------
    # MENUS
    # --------------------------------------------------------

    def _build_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("Arquivo")
        file_menu.addAction("Abrir Projeto...", self.open_project)
        file_menu.addAction("Criar Projeto...", self.create_project)
        file_menu.addAction("Salvar Projeto", self.save_project)
        file_menu.addSeparator()
        file_menu.addAction("Exportar Arquivo Atual", self.export_current_file)
        file_menu.addAction("Exportar Status do Projeto", self._export_project_status)
        file_menu.addSeparator()
        file_menu.addAction("Sair", self.close)

        help_menu = menubar.addMenu("Ajuda")
        help_menu.addAction("Verificar atualizações", self.check_for_updates)
        help_menu.addAction("Sobre", self._show_about)

    # --------------------------------------------------------
    # Undo / Redo
    # --------------------------------------------------------

    def undo(self):
        if self.project and self.project.undo_stack.can_undo():
            self.project.undo_stack.undo(self.project)
            self._refresh_after_undo_redo()

    def redo(self):
        if self.project and self.project.undo_stack.can_redo():
            self.project.undo_stack.redo(self.project)
            self._refresh_after_undo_redo()

    def _refresh_after_undo_redo(self):
        for tab in self.open_tabs.values():
            tab.model.refresh()

        if self.project:
            self.project.rebuild_all_file_status()
            self.fs_proxy.invalidateFilter()

        self._update_status_bar()

    # --------------------------------------------------------
    # Project lifecycle
    # --------------------------------------------------------

    def _try_restore_last_project(self):
        last = self.settings.value("last_project_path", "")
        if last and Path(last).exists():
            try:
                self._load_project(last)
            except Exception:
                pass

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

        self.settings.setValue("last_project_path", path)
        self.main_splitter.setSizes([300, 1200])
        self._update_status_bar()

    # --------------------------------------------------------
    # File handling
    # --------------------------------------------------------

    def _on_tree_double_click(self, proxy_index):
        if not self.project:
            return

        src = self.fs_proxy.mapToSource(proxy_index)
        path = self.fs_model.filePath(src)

        if not Path(path).is_dir():
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
        self._update_status_bar()

    def update_tab_title(self, tab: FileTab):
        idx = self.tabs.indexOf(tab)
        if idx != -1:
            title = str(Path(tab.file_path).relative_to(self.project.root_path))
            self.tabs.setTabText(idx, f"● {title}" if tab.dirty else title)

    def _close_tab(self, index):
        tab: FileTab = self.tabs.widget(index)
        self.open_tabs.pop(tab.file_path, None)
        self.tabs.removeTab(index)
        self._update_status_bar()

    # --------------------------------------------------------
    # Actions
    # --------------------------------------------------------

    def save_project(self):
        if not self.project:
            return

        save_project(self.project)
        export_project_status(self.project)

        for tab in self.open_tabs.values():
            tab.mark_clean()

        self._update_status_bar()

    def export_current_file(self):
        tab = self.tabs.currentWidget()
        if not tab or not self.project:
            return

        critical = [
            issue
            for entry in tab.all_entries
            for issue in entry.qa_issues
            if issue.level == "error"
        ]

        if critical:
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

    # --------------------------------------------------------
    # Helpers
    # --------------------------------------------------------

    def _export_project_status(self):
        if self.project:
            export_project_status(self.project)

    def _show_about(self):
        QMessageBox.information(
            self,
            "Sobre",
            f"{__app_name__}\nVersão {__version__}\n\n"
            "Ferramenta de tradução de Visual Novels.",
        )

    # --------------------------------------------------------
    # Update
    # --------------------------------------------------------

    def check_for_updates(self, auto: bool = False):
        info = UpdateService.check(__version__)
        if not info:
            if not auto:
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
            self._run_updater(info.url)

    def _run_updater(self, installer_url: str):
        updater = Path(sys.executable).with_name("updater.exe")
        subprocess.Popen([str(updater), installer_url], shell=True)
        sys.exit(0)

    # --------------------------------------------------------
    # Close event
    # --------------------------------------------------------

    def closeEvent(self, event):
        if not self.project:
            event.accept()
            return

        has_dirty = any(tab.dirty for tab in self.open_tabs.values())
        if not has_dirty:
            event.accept()
            return

        res = QMessageBox.question(
            self,
            "Projeto não salvo",
            "Existem alterações não salvas no projeto.\n\n"
            "Deseja salvar antes de sair?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
            QMessageBox.Save,
        )

        if res == QMessageBox.Save:
            self.save_project()
            event.accept()
        elif res == QMessageBox.Discard:
            event.accept()
        else:
            event.ignore()
