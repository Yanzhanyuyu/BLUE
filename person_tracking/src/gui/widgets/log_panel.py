"""日志面板组件

显示系统运行日志和事件记录。

功能:
- 实时显示日志信息
- 支持不同日志级别显示 (INFO/WARNING/ERROR)
- 日志条目数量限制
- 清空日志功能
"""

from typing import Optional
from collections import deque
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QPushButton,
    QSizePolicy,
)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QTextCharFormat, QColor, QTextCursor


class LogPanel(QWidget):
    """日志面板组件
    
    显示系统运行日志，支持不同日志级别的颜色区分。
    
    Signals:
        clear_requested: 请求清空日志时发出
    """
    
    clear_requested = Signal()
    
    # 日志级别颜色配置
    LEVEL_COLORS = {
        "DEBUG": QColor("#808080"),
        "INFO": QColor("#D4D4D4"),
        "WARNING": QColor("#DC8C6A"),
        "ERROR": QColor("#CE9178"),
        "CRITICAL": QColor("#FF0000"),
    }
    
    def __init__(self, max_entries: int = 500, parent: Optional[QWidget] = None) -> None:
        """初始化日志面板
        
        Args:
            max_entries: 最大日志条目数
            parent: 父组件
        """
        super().__init__(parent)
        
        self._max_entries = max_entries
        self._entries: deque = deque(maxlen=max_entries)
        
        self._init_ui()
    
    def _init_ui(self) -> None:
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # 标题栏
        header_layout = QHBoxLayout()
        
        self._title_label = QLabel("系统日志")
        self._title_label.setStyleSheet("font-weight: bold; color: #FFFFFF;")
        header_layout.addWidget(self._title_label)
        
        header_layout.addStretch()
        
        # 日志计数
        self._count_label = QLabel("0 条")
        self._count_label.setStyleSheet("color: #808080; font-size: 11px;")
        header_layout.addWidget(self._count_label)
        
        # 清空按钮
        self._clear_btn = QPushButton("清空")
        self._clear_btn.setFixedSize(50, 24)
        self._clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #3E3E42;
                color: #D4D4D4;
                border: none;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #4E4E52;
            }
        """)
        self._clear_btn.clicked.connect(self._on_clear)
        header_layout.addWidget(self._clear_btn)
        
        layout.addLayout(header_layout)
        
        # 日志文本区域
        self._log_text = QTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1E1E1E;
                color: #D4D4D4;
                border: 1px solid #4E4E52;
                border-radius: 4px;
                font-family: 'Consolas', 'Microsoft YaHei Mono', monospace;
                font-size: 11px;
            }
        """)
        self._log_text.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        
        layout.addWidget(self._log_text, 1)
        
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    
    @Slot(str, str)
    def log(self, message: str, level: str = "INFO") -> None:
        """添加日志条目
        
        Args:
            message: 日志消息
            level: 日志级别 (DEBUG/INFO/WARNING/ERROR/CRITICAL)
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] [{level}] {message}"
        
        self._entries.append((entry, level))
        self._append_log(entry, level)
        self._update_count()
    
    def _append_log(self, entry: str, level: str) -> None:
        """追加日志到文本区域
        
        Args:
            entry: 日志条目
            level: 日志级别
        """
        cursor = self._log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        
        # 设置格式
        format = QTextCharFormat()
        color = self.LEVEL_COLORS.get(level, QColor("#D4D4D4"))
        format.setForeground(color)
        
        cursor.insertText(entry + "\n", format)
        
        # 滚动到底部
        scrollbar = self._log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    @Slot()
    def _on_clear(self) -> None:
        """处理清空按钮点击"""
        self._entries.clear()
        self._log_text.clear()
        self._update_count()
        self.clear_requested.emit()
    
    def _update_count(self) -> None:
        """更新日志计数"""
        self._count_label.setText(f"{len(self._entries)} 条")
    
    @Slot()
    def clear(self) -> None:
        """清空日志"""
        self._on_clear()
    
    def log_info(self, message: str) -> None:
        """记录 INFO 级别日志"""
        self.log(message, "INFO")
    
    def log_warning(self, message: str) -> None:
        """记录 WARNING 级别日志"""
        self.log(message, "WARNING")
    
    def log_error(self, message: str) -> None:
        """记录 ERROR 级别日志"""
        self.log(message, "ERROR")
    
    def log_debug(self, message: str) -> None:
        """记录 DEBUG 级别日志"""
        self.log(message, "DEBUG")
