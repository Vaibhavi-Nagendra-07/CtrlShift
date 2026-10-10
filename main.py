"""
AirOS Entry Point & Application Bootstrapper.
"""

import sys
import os
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from airos.desktop.shell import AirOSShell
from airos.storage.settings import SettingsManager

def main():
    # High DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("AirOS")
    app.setOrganizationName("AirOS Team")

    # Global font setup
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    settings_mgr = SettingsManager()
    shell = AirOSShell(settings_mgr=settings_mgr)
    shell.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
