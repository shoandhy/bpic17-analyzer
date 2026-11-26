"""Tema Apple Light berdasarkan DESIGN.md untuk seluruh aplikasi PySide6."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication

# Token warna dari DESIGN.md
GALLERY_WHITE = "#ffffff"
STUDIO_MIST = "#f5f5f7"
PAPER_FROST = "#fafafc"
HAIRLINE_SILVER = "#d6d6d6"
CONTROL_GRAY = "#e6e6e8"
INK = "#1d1d1f"
SLATE = "#707070"
STEEL = "#86868b"
APPLE_BLUE = "#0066cc"
PRICING_BLUE = "#0071e3"
LAUNCH_ORANGE = "#b64400"

FONT_FAMILY = '"SF Pro Text", "SF Pro Display", "Segoe UI", Arial, sans-serif'

STYLESHEET = f"""
QWidget {{
    font-family: {FONT_FAMILY};
    font-size: 13px;
    color: {INK};
    background-color: transparent;
}}

QMainWindow, QDialog {{
    background-color: {STUDIO_MIST};
    color: {INK};
}}

/* --- Menu, Toolbar, StatusBar --- */
QMenuBar {{
    background-color: {GALLERY_WHITE};
    color: {INK};
    border-bottom: 1px solid {CONTROL_GRAY};
    padding: 4px 8px;
    font-size: 12px;
}}
QMenuBar::item {{
    padding: 4px 10px;
    border-radius: 8px;
}}
QMenuBar::item:selected {{
    background-color: {STUDIO_MIST};
}}
QMenu {{
    background-color: {PAPER_FROST};
    color: {INK};
    border: 1px solid {CONTROL_GRAY};
    border-radius: 12px;
    padding: 6px;
}}
QMenu::item {{
    padding: 6px 18px;
    border-radius: 8px;
}}
QMenu::item:selected {{
    background-color: {PRICING_BLUE};
    color: {GALLERY_WHITE};
}}

QToolBar {{
    background-color: {GALLERY_WHITE};
    border-bottom: 1px solid {HAIRLINE_SILVER};
    spacing: 8px;
    padding: 6px 12px;
}}
QToolBar QToolButton {{
    background-color: transparent;
    color: {INK};
    border: 1px solid {HAIRLINE_SILVER};
    border-radius: 14px;
    padding: 5px 14px;
    font-size: 12px;
    font-weight: 500;
}}
QToolBar QToolButton:hover {{
    background-color: {STUDIO_MIST};
    border-color: {STEEL};
}}
QToolBar QToolButton:disabled {{
    background-color: {CONTROL_GRAY};
    color: {STEEL};
    border-color: {CONTROL_GRAY};
}}

QStatusBar {{
    background-color: {PAPER_FROST};
    color: {SLATE};
    border-top: 1px solid {CONTROL_GRAY};
    font-size: 12px;
    padding: 2px 10px;
}}

/* --- Sidebar Navigasi --- */
QListWidget#Sidebar {{
    background-color: {PAPER_FROST};
    border: none;
    border-right: 1px solid {CONTROL_GRAY};
    padding: 12px 10px;
    outline: none;
}}
QListWidget#Sidebar::item {{
    color: {INK};
    padding: 9px 12px;
    margin: 2px 0px;
    border-radius: 12px;
    font-size: 13px;
    font-weight: 500;
}}
QListWidget#Sidebar::item:hover {{
    background-color: {CONTROL_GRAY};
}}
QListWidget#Sidebar::item:selected {{
    background-color: {PRICING_BLUE};
    color: {GALLERY_WHITE};
    font-weight: 600;
}}

/* --- Kontainer & Kartu (Gallery White di atas Studio Mist) --- */
QStackedWidget {{
    background-color: {STUDIO_MIST};
}}

QFrame[card="true"] {{
    background-color: {GALLERY_WHITE};
    border: 1px solid {CONTROL_GRAY};
    border-radius: 20px;
}}

QGroupBox {{
    background-color: {GALLERY_WHITE};
    border: 1px solid {CONTROL_GRAY};
    border-radius: 16px;
    margin-top: 12px;
    padding: 18px 14px 12px 14px;
    font-weight: 600;
    color: {INK};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 18px;
    top: 2px;
    padding: 2px 10px;
    background-color: {GALLERY_WHITE};
    border-radius: 8px;
    color: {INK};
    font-size: 13px;
    font-weight: 600;
}}

/* --- Tombol (Outlined Explore Pill & Pricing Blue Pill) --- */
QPushButton {{
    background-color: {GALLERY_WHITE};
    color: {INK};
    border: 1px solid {STEEL};
    border-radius: 16px;
    padding: 6px 16px;
    font-size: 12px;
    font-weight: 500;
    min-height: 20px;
}}
QPushButton:hover {{
    background-color: {STUDIO_MIST};
    border-color: {INK};
}}
QPushButton:pressed {{
    background-color: {CONTROL_GRAY};
}}
QPushButton:disabled {{
    background-color: {CONTROL_GRAY};
    color: {STEEL};
    border-color: {HAIRLINE_SILVER};
}}

QPushButton[variant="primary"] {{
    background-color: {PRICING_BLUE};
    color: {GALLERY_WHITE};
    border: none;
    font-weight: 600;
}}
QPushButton[variant="primary"]:hover {{
    background-color: {APPLE_BLUE};
}}
QPushButton[variant="primary"]:disabled {{
    background-color: {CONTROL_GRAY};
    color: {STEEL};
}}

/* --- Input & Kontrol --- */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    background-color: {GALLERY_WHITE};
    color: {INK};
    border: 1px solid {STEEL};
    border-radius: 16px;
    padding: 5px 14px;
    min-height: 20px;
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 1.5px solid {PRICING_BLUE};
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox QAbstractItemView {{
    background-color: {GALLERY_WHITE};
    color: {INK};
    border: 1px solid {HAIRLINE_SILVER};
    selection-background-color: {PRICING_BLUE};
    selection-color: {GALLERY_WHITE};
}}

QCheckBox {{
    spacing: 8px;
    color: {INK};
    font-size: 13px;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 5px;
    border: 1px solid {STEEL};
    background-color: {GALLERY_WHITE};
}}
QCheckBox::indicator:checked {{
    background-color: {PRICING_BLUE};
    border-color: {PRICING_BLUE};
}}

/* --- Tabel --- */
QTableView, QListWidget {{
    background-color: {GALLERY_WHITE};
    alternate-background-color: {PAPER_FROST};
    color: {INK};
    border: 1px solid {CONTROL_GRAY};
    border-radius: 14px;
    gridline-color: {CONTROL_GRAY};
    selection-background-color: #dcebfa;
    selection-color: {INK};
}}
QHeaderView::section {{
    background-color: {STUDIO_MIST};
    color: {SLATE};
    border: none;
    border-bottom: 1px solid {HAIRLINE_SILVER};
    border-right: 1px solid {CONTROL_GRAY};
    padding: 7px 10px;
    font-size: 12px;
    font-weight: 600;
}}

/* --- Progress Bar --- */
QProgressBar {{
    background-color: {CONTROL_GRAY};
    border: none;
    border-radius: 6px;
    text-align: center;
    color: {INK};
    font-size: 11px;
    min-height: 14px;
}}
QProgressBar::chunk {{
    background-color: {PRICING_BLUE};
    border-radius: 6px;
}}

/* --- Tab Widget --- */
QTabWidget::pane {{
    background-color: {GALLERY_WHITE};
    border: 1px solid {CONTROL_GRAY};
    border-radius: 16px;
}}
QTabBar::tab {{
    background-color: transparent;
    color: {SLATE};
    padding: 8px 16px;
    font-weight: 500;
}}
QTabBar::tab:selected {{
    color: {INK};
    border-bottom: 2px solid {PRICING_BLUE};
    font-weight: 600;
}}

QSplitter::handle {{
    background-color: transparent;
}}

/* --- Scrollbar minimalis Apple Light --- */
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 4px 1px 4px 1px;
}}
QScrollBar::handle:vertical {{
    background: {HAIRLINE_SILVER};
    border-radius: 3px;
    min-height: 28px;
}}
QScrollBar::handle:vertical:hover {{
    background: {STEEL};
}}
QScrollBar::handle:vertical:pressed {{
    background: {SLATE};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
    background: none;
    border: none;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
}}

QScrollBar:horizontal {{
    background: transparent;
    height: 8px;
    margin: 1px 4px 1px 4px;
}}
QScrollBar::handle:horizontal {{
    background: {HAIRLINE_SILVER};
    border-radius: 3px;
    min-width: 28px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {STEEL};
}}
QScrollBar::handle:horizontal:pressed {{
    background: {SLATE};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
    background: none;
    border: none;
}}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: transparent;
}}
QAbstractScrollArea::corner {{
    background: transparent;
}}
"""


def build_light_palette() -> QPalette:
    """Bangun QPalette Light eksplisit agar tema Windows Dark tidak menimpa UI."""
    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window, QColor(STUDIO_MIST))
    pal.setColor(QPalette.ColorRole.WindowText, QColor(INK))
    pal.setColor(QPalette.ColorRole.Base, QColor(GALLERY_WHITE))
    pal.setColor(QPalette.ColorRole.AlternateBase, QColor(PAPER_FROST))
    pal.setColor(QPalette.ColorRole.ToolTipBase, QColor(GALLERY_WHITE))
    pal.setColor(QPalette.ColorRole.ToolTipText, QColor(INK))
    pal.setColor(QPalette.ColorRole.Text, QColor(INK))
    pal.setColor(QPalette.ColorRole.Button, QColor(GALLERY_WHITE))
    pal.setColor(QPalette.ColorRole.ButtonText, QColor(INK))
    pal.setColor(QPalette.ColorRole.Highlight, QColor(PRICING_BLUE))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor(GALLERY_WHITE))
    pal.setColor(QPalette.ColorRole.Mid, QColor(SLATE))
    pal.setColor(QPalette.ColorRole.Link, QColor(APPLE_BLUE))
    return pal


def apply_theme(app: QApplication | None) -> None:
    """Terapkan tema Apple Light (DESIGN.md) ke instance QApplication aktif."""
    if app is None:
        return
    try:
        app.styleHints().setColorScheme(Qt.ColorScheme.Light)
    except AttributeError:
        pass
    app.setStyle("Fusion")
    app.setPalette(build_light_palette())
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(STYLESHEET)
