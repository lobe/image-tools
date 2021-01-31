import os
from PyQt5.QtWidgets import (QPushButton, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QFileDialog, QMessageBox, QComboBox,
                             QProgressBar, QSizePolicy)
from app.components.stretch_wrapper import NoStretch
import pandas as pd
from model.predict_from_file import predict_dataset
from model.predict_from_folder import predict_folder


class Model(QFrame):
	default_model_text = "<i>Please select a TensorFlow model directory.<\i>"
	default_file_text = "<i>Please select a folder of images or a csv of URLs.<\i>"
	predict_text = "Predict"
	predicting_text = "Predicting..."

	def __init__(self, app):
		super().__init__()
		# initialize our variables
		self.app = app
		self.tf_directory = None
		self.file = None
		self.folder = None
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
		title = QLabel("Model")
		title.setObjectName("h1")
		description = QLabel(
			"Run your exported TensorFlow model from Lobe \non a folder of images or a .csv/.xlsx file of image URLs.\nThis will produce a new prediction .csv with the image filepath or URL, \nthe model's prediction, and the model's confidence.")
		description.setObjectName("h2")

		# model select button
		self.model_button = QPushButton("Select model directory")
		self.model_button.clicked.connect(self.select_directory)
		model_container = NoStretch(self.model_button)
		model_container.setObjectName("separate")
		self.model_label = QLabel(self.default_model_text)

		# file or folder selection button
		self.folder_button = QPushButton("Select folder")
		self.folder_button.clicked.connect(self.select_image_folder)
		self.file_button = QPushButton("Select file")
		self.file_button.clicked.connect(self.select_file)
		buttons_container = NoStretch([self.folder_button, self.file_button])
		buttons_container.setObjectName("separate")
		self.path_label = QLabel(self.default_file_text)

		# url column header
		self.url_label = QLabel("Column with image URLs:")
		self.url_label.setObjectName("separateSmall")
		self.url_label.hide()
		self.url_dropdown = QComboBox()
		self.url_dropdown.setSizeAdjustPolicy(QComboBox.AdjustToContents)
		self.url_dropdown.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
		self.url_container = NoStretch(self.url_dropdown)
		self.url_container.hide()

		# predict button
		self.predict_button = QPushButton(self.predict_text)
		self.predict_button.setEnabled(False)
		self.predict_button.clicked.connect(self.predict)
		predict_container = NoStretch(self.predict_button)
		predict_container.setObjectName("separate")

		self.progress_bar = QProgressBar()
		self.progress_bar.hide()

		# make our content layout
		content_layout.addWidget(title)
		content_layout.addWidget(description)
		content_layout.addWidget(model_container)
		content_layout.addWidget(self.model_label)
		content_layout.addWidget(buttons_container)
		content_layout.addWidget(self.path_label)
		content_layout.addWidget(self.url_label)
		content_layout.addWidget(self.url_container)
		content_layout.addWidget(predict_container)
		content_layout.addWidget(self.progress_bar)
		content_layout.addStretch(1)
		content.setLayout(content_layout)

		layout.addWidget(content)
		layout.addStretch(1)
		self.setLayout(layout)

	def select_directory(self):
		self.tf_directory = QFileDialog.getExistingDirectory(self, "Select TensorFlow Model Directory")
		self.model_label.setText(f"<i>{self.tf_directory}</i>" if self.tf_directory else self.default_model_text)
		self.check_predict_button()

	def select_file(self):
		self.file = QFileDialog.getOpenFileName(self, 'Select CSV File', filter="CSV (*.csv *.xlsx)")[0]
		self.path_label.setText(f"<i>{self.file}</i>" if self.file else self.default_file_text)
		self.folder = None
		self.parse_headers()
		self.check_predict_button()

	def select_image_folder(self):
		self.folder = QFileDialog.getExistingDirectory(self, "Select Images Directory")
		self.path_label.setText(f"<i>{self.folder}</i>" if self.folder else self.default_file_text)
		self.file = None
		self.parse_headers()
		self.check_predict_button()

	def check_predict_button(self):
		# enable the button when we have both a model and file
		if self.tf_directory and (self.file or self.folder):
			self.predict_button.setEnabled(True)
		else:
			self.predict_button.setEnabled(False)

	def parse_headers(self):
		if self.file:
			# read the file for its headers and set our dropdown boxes appropriately
			try:
				if os.path.splitext(self.file)[1] == ".csv":
					csv = pd.read_csv(self.file, header=0)
				else:
					csv = pd.read_excel(self.file, header=0)
				self.url_dropdown.clear()
				for header in list(csv.columns):
					self.url_dropdown.addItem(header)
				self.url_dropdown.adjustSize()
				self.url_label.show()
				self.url_container.show()
			except Exception as e:
				QMessageBox.about(self, "Alert", f"Error reading csv: {e}")
				self.clear_headers()
		else:
			self.clear_headers()

	def clear_headers(self):
		self.url_dropdown.clear()
		self.url_label.hide()
		self.url_container.hide()

	def predict(self):
		# disable the buttons so we can't click again
		self.predict_button.setEnabled(False)
		self.predict_button.setText(self.predicting_text)
		self.model_button.setEnabled(False)
		self.file_button.setEnabled(False)
		self.folder_button.setEnabled(False)
		self.progress_bar.setValue(0)
		self.progress_bar.show()
		self.app.processEvents()
		url_col = self.url_dropdown.currentText()
		try:
			if self.file:
				predict_dataset(model_dir=self.tf_directory, filepath=self.file, url_col=url_col,
				                progress_hook=self.progress_hook)
			elif self.folder:
				predict_folder(model_dir=self.tf_directory, img_dir=self.folder, move=True, csv=True,
				               progress_hook=self.progress_hook)
		except Exception as e:
			QMessageBox.about(self, "Alert", f"Error predicting: {e}")
		finally:
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
		self.predict_button.setEnabled(True)
		self.predict_button.setText(self.predict_text)
		self.model_button.setEnabled(True)
		self.file_button.setEnabled(True)
		self.folder_button.setEnabled(True)
		self.app.processEvents()
