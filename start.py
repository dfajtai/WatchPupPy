import os, sys
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication
from src.gui.main_gui import MainGUI

def main():
    """
    Entry point for the WatchPupPy application.
    Initializes the QApplication, creates the MainGUI window,
    and starts the Qt event loop.
    """
    app = QApplication(sys.argv)
    
    if os.path.exists("assets/icon.png"):
        app.setWindowIcon(QIcon("assets/icon.png")) 
        
    main_window = MainGUI()
    main_window.resize(800, 600)
    main_window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()