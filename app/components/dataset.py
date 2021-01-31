import os
from PyQt5.QtWidgets import (QPushButton, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QFileDialog, QMessageBox, QComboBox,
                             QProgressBar, QSizePolicy)
from app.components.stretch_wrapper import NoStretch
import pandas as pd
from dataset.download_from_file import create_dataset


class Dataset(QFrame):
	default_text = "<i>Please select a file.<\i>"
	download_text = "Download"
	downloading_text = "Downloading..."

	def __init__(self, app):
		super().__init__()
		# initialize our variables
		self.app = app
		self.file = None
		self.init_ui()

	def init_ui(self):
		# make our UI
		self.setObjectName("content")
		layout = QHBoxLayout()
		layout.setContentsMargins(0, 0, 0, 0)

		# our main content area
		content = QFrame()
		content_layout = QVBoxLayout()

		# some info
		title = QLabel("Dataset")
		title.setObjectName("h1")
		description = QLabel(
			"Download images from URLs in a .csv or .xlsx file.\nOptionally, supply labels to organize your images into folders by label.")
		description.setObjectName("h2")

		# file selection button
		self.file_button = QPushButton("Select file")
		self.file_button.clicked.connect(self.select_file)
		button_container = NoStretch(self.file_button)
		button_container.setObjectName("separate")

		# display filepath
		self.path_label = QLabel(self.default_text)

		# url column header and optional label column header
		self.header_container = QFrame()
		self.header_container.setObjectName("separateSmall")
		header_layout = QVBoxLayout()
		header_layout.setContentsMargins(0, 0, 0, 0)
		url_label = QLabel("Column with image URLs:")
		self.url_dropdown = QComboBox()
		self.url_dropdown.setSizeAdjustPolicy(QComboBox.AdjustToContents)
		self.url_dropdown.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
		url_container = NoStretch(self.url_dropdown)
		label_label = QLabel("(Optional) column with labels:")
		label_label.setObjectName("separateSmall")
		self.label_dropdown = QComboBox()
		self.label_dropdown.setSizeAdjustPolicy(QComboBox.AdjustToContents)
		self.label_dropdown.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
		label_container = NoStretch(self.label_dropdown)
		header_layout.addWidget(url_label)
		header_layout.addWidget(url_container)
		header_layout.addWidget(label_label)
		header_layout.addWidget(label_container)
		self.header_container.setLayout(header_layout)
		self.header_container.hide()

		# download button
		self.download_button = QPushButton(self.download_text)
		self.download_button.setEnabled(False)
		self.download_button.clicked.connect(self.download)
		download_container = NoStretch(self.download_button)
		download_container.setObjectName("separate")

		self.progress_bar = QProgressBar()
		self.progress_bar.hide()

		# make our content layout
		content_layout.addWidget(title)
		content_layout.addWidget(description)
		content_layout.addWidget(button_container)
		content_layout.addWidget(self.path_label)
		content_layout.addWidget(self.header_container)
		content_layout.addWidget(download_container)
		content_layout.addWidget(self.progress_bar)
		content_layout.addStretch(1)
		content.setLayout(content_layout)

		layout.addWidget(content)
		layout.addStretch(1)
		self.setLayout(layout)

	def select_file(self):
		self.file = QFileDialog.getOpenFileName(self, 'Select CSV File', filter="CSV (*.csv *.xlsx)")[0]
		self.path_label.setText(f"<i>{self.file}</i>" if self.file else self.default_text)
		self.parse_headers()

	def parse_headers(self):
		if self.file:
			# read the file for its headers and set our dropdown boxes appropriately
			try:
				if os.path.splitext(self.file)[1] == ".csv":
					csv = pd.read_csv(self.file, header=0)
				else:
					csv = pd.read_excel(self.file, header=0)
				self.label_dropdown.clear()
				self.url_dropdown.clear()
				self.label_dropdown.addItem(None)
				for header in list(csv.columns):
					self.url_dropdown.addItem(header)
					self.label_dropdown.addItem(header)
				self.url_dropdown.adjustSize()
				self.header_container.show()
				self.download_button.setEnabled(True)
			except Exception as e:
				QMessageBox.about(self, "Alert", f"Error reading csv: {e}")
				self.clear_headers()
		else:
			self.clear_headers()

	def clear_headers(self):
		self.header_container.hide()
		self.url_dropdown.clear()
		self.label_dropdown.clear()
		self.download_button.setEnabled(False)

	def download(self):
		# disable the buttons so we can't click again
		self.download_button.setEnabled(False)
		self.download_button.setText(self.downloading_text)
		self.file_button.setEnabled(False)
		self.progress_bar.setValue(0)
		self.progress_bar.show()
		self.app.processEvents()
		url_col = self.url_dropdown.currentText()
		label_col = self.label_dropdown.currentText()
		destination_directory = QFileDialog.getExistingDirectory(self, "Select Output Directory")
		# if they hit cancel, don't download
		if not destination_directory:
			self.done()
			return
		# otherwise try downloading to the desired location
		try:
			create_dataset(
				filepath=self.file, url_col=url_col, label_col=label_col if label_col else None,
				progress_hook=self.progress_hook, destination_directory=destination_directory,
			)
		except Exception as e:
			QMessageBox.about(self, "Alert", f"Error creating dataset: {e}")
			self.done()

	def progress_hook(self, current, total):
		self.progress_bar.setValue(float(current) / total * 100)
		if current == total:
			self.done()
		# make sure to update the UI
		self.app.processEvents()

	def done(self):
		self.progress_bar.setValue(0)
		self.progress_bar.hide()
		self.download_button.setEnabled(True)
		self.download_button.setText(self.download_text)
		self.file_button.setEnabled(True)
		self.app.processEvents()
