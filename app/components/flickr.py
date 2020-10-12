import os
from PyQt5.QtWidgets import (QPushButton, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QFileDialog, QMessageBox,
                             QProgressBar, QLineEdit)
from app.components.stretch_wrapper import NoStretch
from dataset.download_from_flickr import download_flickr


class Flickr(QFrame):
	download_text = "Download"
	downloading_text = "Downloading..."

	def __init__(self, app):
		super().__init__()
		# initialize our variables
		self.app = app
		self.api_textbox = None
		self.min_lat_textbox = None
		self.min_long_textbox = None
		self.max_lat_textbox = None
		self.max_long_textbox = None
		self.search_textbox = None
		self.download_button = None
		self.progress_bar = None
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
		title = QLabel("Flickr")
		title.setObjectName("h1")
		description = QLabel("Download images from Flickr from a geographic bounding box location.")
		description.setObjectName("h2")

		# API key
		api_label = QLabel("Flickr API Key:")
		api_label.setObjectName("separateSmall")
		self.api_textbox = QLineEdit()
		api_container = NoStretch(self.api_textbox)

		# geo box
		bbox_label = QLabel("Bounding Box:")
		bbox_label.setObjectName("separateSmall")

		minlat_label = QLabel("Min Latitude:")
		self.min_lat_textbox = QLineEdit()
		min_lat_container = NoStretch(self.min_lat_textbox)
		minlong_label = QLabel("Min Longitude:")
		self.min_long_textbox = QLineEdit()
		min_long_container = NoStretch(self.min_long_textbox)

		maxlat_label = QLabel("Max Latitude:")
		maxlat_label.setObjectName("separateSmall")
		self.max_lat_textbox = QLineEdit()
		max_lat_container = NoStretch(self.max_lat_textbox)
		maxlong_label = QLabel("Max Longitude:")
		self.max_long_textbox = QLineEdit()
		max_long_container = NoStretch(self.max_long_textbox)

		# search term
		search_label = QLabel("Search term:")
		search_label.setObjectName("separateSmall")
		self.search_textbox = QLineEdit()
		search_container = NoStretch(self.search_textbox)


		# download button
		self.download_button = QPushButton(self.download_text)
		self.download_button.setEnabled(True)
		self.download_button.clicked.connect(self.download)
		download_container = NoStretch(self.download_button)
		download_container.setObjectName("separate")

		self.progress_bar = QProgressBar()
		self.progress_bar.hide()

		# make our content layout
		content_layout.addWidget(title)
		content_layout.addWidget(description)
		content_layout.addWidget(api_label)
		content_layout.addWidget(api_container)
		content_layout.addWidget(bbox_label)
		content_layout.addWidget(minlat_label)
		content_layout.addWidget(min_lat_container)
		content_layout.addWidget(minlong_label)
		content_layout.addWidget(min_long_container)
		content_layout.addWidget(maxlat_label)
		content_layout.addWidget(max_lat_container)
		content_layout.addWidget(maxlong_label)
		content_layout.addWidget(max_long_container)
		content_layout.addWidget(search_label)
		content_layout.addWidget(search_container)
		content_layout.addWidget(download_container)
		content_layout.addWidget(self.progress_bar)
		content_layout.addStretch(1)
		content.setLayout(content_layout)

		layout.addWidget(content)
		layout.addStretch(1)
		self.setLayout(layout)

	def download(self):
		# disable the buttons so we can't click again
		self.download_button.setEnabled(False)
		self.download_button.setText(self.downloading_text)
		self.progress_bar.setValue(0)
		self.progress_bar.show()
		self.app.processEvents()
		destination_directory = QFileDialog.getExistingDirectory(self, "Select Output Directory")
		# if they hit cancel, don't download
		if not destination_directory:
			self.done()
			return
		# otherwise try downloading to the desired location
		try:
			download_flickr(
				api_key=self.api_textbox.text(),
				directory=destination_directory,
				min_lat=self.min_lat_textbox.text() or None,
				min_long=self.min_long_textbox.text() or None,
				max_lat=self.max_lat_textbox.text() or None,
				max_long=self.max_long_textbox.text() or None,
				search=self.search_textbox.text() or None,
				progress_hook=self.progress_hook,
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
		self.app.processEvents()
