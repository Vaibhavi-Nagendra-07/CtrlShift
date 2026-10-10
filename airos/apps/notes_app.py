"""
AirOS Built-in Application: Notes.
Supports rich note creation, editing, SQLite persistence, and search.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QLineEdit, QTextEdit, QPushButton, QMessageBox, QSplitter
)
from PySide6.QtCore import Qt, Signal
from airos.storage.settings import SettingsManager

class NotesApp(QWidget):
    def __init__(self, settings_mgr: SettingsManager, parent=None):
        super().__init__(parent)
        self.settings = settings_mgr
        self.current_note_id = None
        self._init_ui()
        self._load_notes()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        splitter = QSplitter(Qt.Horizontal)

        # Left panel: Note list & New button
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.btn_new = QPushButton("＋ New Note")
        self.btn_new.setStyleSheet("background-color: #1f6feb; color: white; font-weight: bold; padding: 6px; border-radius: 4px;")
        self.btn_new.clicked.connect(self._create_new_note)
        left_layout.addWidget(self.btn_new)

        self.note_list = QListWidget()
        self.note_list.setStyleSheet("""
            QListWidget {
                background-color: #0d1117;
                color: #c9d1d9;
                border: 1px solid #30363d;
                border-radius: 4px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #21262d;
            }
            QListWidget::item:selected {
                background-color: #21262d;
                color: #58a6ff;
            }
        """)
        self.note_list.itemClicked.connect(self._select_note)
        left_layout.addWidget(self.note_list)
        splitter.addWidget(left_panel)

        # Right panel: Editor
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Note Title...")
        self.title_input.setStyleSheet("background-color: #0d1117; color: white; border: 1px solid #30363d; border-radius: 4px; padding: 6px; font-weight: bold; font-size: 14px;")
        right_layout.addWidget(self.title_input)

        self.content_input = QTextEdit()
        self.content_input.setPlaceholderText("Write your note here using keyboard or AirType...")
        self.content_input.setStyleSheet("background-color: #0d1117; color: #f0f6fc; border: 1px solid #30363d; border-radius: 4px; padding: 8px; font-size: 13px;")
        right_layout.addWidget(self.content_input)

        btn_bar = QHBoxLayout()
        self.btn_save = QPushButton("Save Note")
        self.btn_save.setStyleSheet("background-color: #238636; color: white; padding: 6px 14px; border-radius: 4px; font-weight: bold;")
        self.btn_save.clicked.connect(self._save_note)
        btn_bar.addWidget(self.btn_save)

        self.btn_delete = QPushButton("Delete")
        self.btn_delete.setStyleSheet("background-color: #da3633; color: white; padding: 6px 14px; border-radius: 4px;")
        self.btn_delete.clicked.connect(self._delete_note)
        btn_bar.addWidget(self.btn_delete)
        btn_bar.addStretch()

        right_layout.addLayout(btn_bar)
        splitter.addWidget(right_panel)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter)

    def _load_notes(self):
        self.note_list.clear()
        notes = self.settings.get_all_notes()
        for nid, title, content, updated in notes:
            item = QListWidgetItem(f"📝 {title}")
            item.setData(Qt.UserRole, (nid, title, content))
            self.note_list.addItem(item)

    def _create_new_note(self):
        self.current_note_id = None
        self.title_input.clear()
        self.content_input.clear()
        self.title_input.setFocus()

    def _select_note(self, item: QListWidgetItem):
        data = item.data(Qt.UserRole)
        if data:
            self.current_note_id, title, content = data
            self.title_input.setText(title)
            self.content_input.setText(content)

    def _save_note(self):
        title = self.title_input.text().strip() or "Untitled Note"
        content = self.content_input.toPlainText()
        self.current_note_id = self.settings.save_note(self.current_note_id, title, content)
        self._load_notes()

    def _delete_note(self):
        if self.current_note_id:
            reply = QMessageBox.question(
                self, "IntentLock Confirmation",
                f"Are you sure you want to delete note '{self.title_input.text()}'?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.settings.delete_note(self.current_note_id)
                self._create_new_note()
                self._load_notes()
