import os
from PyQt5.QtWidgets import QButtonGroup, QPushButton, QVBoxLayout, QFrame, QLabel
from PyQt5.QtGui import QPixmap
from app import resource_path


class NavBar(QFrame):

	def __init__(self, click_callback):
		super().__init__()
		# initialize our variables
		self.click_callback = click_callback
		self.init_ui()

	def init_ui(self):
		# make our UI
		self.buttons = QButtonGroup(self)
		self.buttons.buttonClicked.connect(lambda button: self.click_callback(button.text()))

		# logo
		label = QLabel(self)
		pixmap = QPixmap(resource_path('icon.ico'))
		label.setPixmap(pixmap)
		label.setScaledContents(True)
		label.setObjectName("logo")

		# dataset button
		dataset_button = self.nav_button("Dataset")
		dataset_button.setChecked(True)

		# model button
		model_button = self.nav_button("Model")

		# flickr button
		flickr_button = self.nav_button("Flickr")

		layout = QVBoxLayout()
		layout.addWidget(label)
		layout.addWidget(dataset_button)
		layout.addWidget(model_button)
		layout.addWidget(flickr_button)
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
