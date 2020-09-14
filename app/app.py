from PyQt5 import QtGui, QtCore
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QHBoxLayout,
    QDesktopWidget, QFrame
)
import sys
import os
from multiprocessing import freeze_support
from app.components.navbar import NavBar
from app.components.dataset import Dataset
from app.components.model import Model
from app.components.flickr import Flickr
from app import ASSETS_PATH


try:
    # Include in try/except block if you're also targeting Mac/Linux
    from PyQt5.QtWinExtras import QtWin
    QtWin.setCurrentProcessExplicitAppUserModelID('image-tools.0.1')
except ImportError:
    pass

if hasattr(QtCore.Qt, 'AA_EnableHighDpiScaling'):
    QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)

if hasattr(QtCore.Qt, 'AA_UseHighDpiPixmaps'):
    QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)


# style variables
DARK_0 = "rgb(18,18,18)"
DARK_1 = "rgb(29,29,29)"
DARK_2 = "rgb(33,33,33)"
DARK_3 = "rgb(39,39,39)"
DARK_4 = "rgb(45,45,45)"
DARK_5 = "rgb(55,55,55)"

TEXT = "#e0e0e0"
TEXT_DISABLED = "rgb(54,54,54)"
TEXT_MEDIUM = "rgb(70,70,70)"
TEXT_LIGHT = "rgb(182,182,182)"


class MainWindow(QMainWindow):

    def __init__(self, app, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # initialize our variables
        self.app = app
        self.nav = "Dataset"
        self.init_ui()

    def init_ui(self):
        # make our UI
        self.setMinimumSize(900, 600)
        self.setWindowTitle("Image Tools")
        self.center()

        # our main app consists of two sections -- nav on left and content on right
        app_layout = QHBoxLayout()

        navbar = NavBar(self.nav_click)
        self.dataset = Dataset(self.app)
        self.model = Model(self.app)
        self.flickr = Flickr(self.app)
        # we are on dataset tab by default
        self.model.hide()
        self.flickr.hide()

        app_layout.addWidget(navbar)
        app_layout.addWidget(self.dataset)
        app_layout.addWidget(self.model)
        app_layout.addWidget(self.flickr)
        app_layout.setContentsMargins(0, 0, 0, 0)
        app_layout.setSpacing(0)

        # bind our widget and show
        window = QFrame()
        window.setObjectName("window")
        window.setLayout(app_layout)
        self.setCentralWidget(window)
        self.show()

    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def nav_click(self, button: str):
        if button != self.nav:
            if button == "Dataset":
                self.model.hide()
                self.dataset.show()
                self.flickr.hide()
            elif button == "Model":
                self.dataset.hide()
                self.model.show()
                self.flickr.hide()
            elif button == "Flickr":
                self.flickr.show()
                self.dataset.hide()
                self.model.hide()
            self.nav = button


if __name__ == '__main__':
    freeze_support()
    app = QApplication(sys.argv)
    app.setWindowIcon(QtGui.QIcon(os.path.join(ASSETS_PATH, 'icon.ico')))

    w = MainWindow(app)
    w.setStyleSheet(f"""
        QFrame#window {{
            background: {DARK_0};
        }}
        QLabel {{
            color: {TEXT_LIGHT};
            font-size: 16px;
        }}
        QPushButton {{
            color: {TEXT};
            border: 1px solid {DARK_0};
            background-color: {DARK_5};
            border-radius: 10px;
            font-size: 14px;
            padding: 10px;
            padding-left: 20px;
            padding-right: 20px;
        }}
        QPushButton:pressed {{
            color: {TEXT_LIGHT};
            background-color: {DARK_4};
        }}
        QPushButton:disabled {{
            color: {TEXT_MEDIUM};
            background-color: {DARK_3};
        }}
        QComboBox {{
            padding: 5px;
            padding-left: 10px;
            padding-right: 10px;
        }}
        QProgressBar {{
            color: {TEXT_LIGHT}
        }}

        QFrame#navbar {{
            padding-top: 0px;
        }}
        QLabel#logo {{
            margin: 10px;
        }}
        QPushButton#navbutton {{
            border: none;
            background-color: transparent;
            font-size: 18px;
            color: {TEXT_LIGHT};
            margin-top: 10px;
            margin-left: 15px;
            margin-right: 15px;
            padding-top: 10px;
            padding-bottom: 10px;
            border-radius: 10px;
        }}
        QPushButton#navbutton:checked {{
            background-color: {DARK_2};
            color: {TEXT};
        }}
        QPushButton#navbutton:pressed {{
            background-color: {DARK_1};
        }}

        QFrame#content {{
            background: {DARK_1};
            padding-left: 35px;
            padding-top: 20px;
        }}
        QLabel#h1 {{
            font-size: 26px;
            font-weight: bold;
            color: {TEXT};
        }}
        QLabel#h2 {{
            font-size: 20px;
        }}
        QFrame#separate {{
            margin-top: 30px;
        }}
        QFrame#separateSmall {{
            margin-top: 15px;
        }}
    """)
    app.exec()
