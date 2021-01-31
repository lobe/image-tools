from PyQt5.QtWidgets import QButtonGroup, QPushButton, QVBoxLayout, QFrame, QLabel
from PyQt5.QtGui import QPixmap
from app import resource_path


class NavBar(QFrame):

	def __init__(self, click_callback, tabs):
		super().__init__()
		# initialize our variables
		self.click_callback = click_callback
		self.init_ui(tabs)

	def init_ui(self, tabs):
		# make our UI
		self.buttons = QButtonGroup(self)
		self.buttons.buttonClicked.connect(lambda button: self.click_callback(button.text()))

		# logo
		label = QLabel(self)
		pixmap = QPixmap(resource_path('icon.ico'))
		label.setPixmap(pixmap)
		label.setScaledContents(True)
		label.setObjectName("logo")

		# our tab buttons
		buttons = [self.nav_button(tab) for tab in tabs]
		# set the first one as checked by default
		buttons[0].setChecked(True)

		layout = QVBoxLayout()
		layout.addWidget(label)
		# add our buttons
		for button in buttons:
			layout.addWidget(button)
		layout.addStretch(1)
		layout.setContentsMargins(0, 0, 0, 0)
		layout.setSpacing(0)
		self.setLayout(layout)
		self.setObjectName("navbar")

	def nav_button(self, name):
		button = QPushButton(name)
		button.setCheckable(True)
		button.setObjectName("navbutton")
		self.buttons.addButton(button)
		return button
