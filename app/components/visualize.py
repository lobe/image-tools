from PyQt5.QtWidgets import QPushButton, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QFileDialog, QMessageBox
from PyQt5.QtGui import QPixmap
from PIL.ImageQt import ImageQt
from PIL import Image
from app.components.stretch_wrapper import NoStretch
from lobe import ImageModel


class Visualize(QFrame):
	default_model_text = "<i>Please select a TensorFlow model directory.<\i>"
	default_file_text = "<i>Please select an image file.<\i>"
	loading_text = "Loading..."

	def __init__(self, app):
		super().__init__()
		# initialize our variables
		self.app = app
		self.tf_directory = None
		self.file = None
		self.image = None
		self.model = None
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
		title = QLabel("Visualize")
		title.setObjectName("h1")
		description = QLabel(
			"Visualize the model's prediction as a heatmap on the image.\nThis shows which parts of the image determined the predicted label.")
		description.setObjectName("h2")

		# model select button
		self.model_button = QPushButton("Select model directory")
		self.model_button.clicked.connect(self.select_directory)
		model_container = NoStretch(self.model_button)
		model_container.setObjectName("separate")
		self.model_label = QLabel(self.default_model_text)

		# file selection button
		self.file_button = QPushButton("Select image")
		self.file_button.clicked.connect(self.select_file)
		buttons_container = NoStretch(self.file_button)
		buttons_container.setObjectName("separate")
		self.path_label = QLabel(self.default_file_text)

		# image display
		self.image_label = QLabel()
		image_container = NoStretch(self.image_label)
		image_container.setObjectName("separate")
		self.prediction_label = QLabel()

		# make our content layout
		content_layout.addWidget(title)
		content_layout.addWidget(description)
		content_layout.addWidget(model_container)
		content_layout.addWidget(self.model_label)
		content_layout.addWidget(buttons_container)
		content_layout.addWidget(self.path_label)
		content_layout.addWidget(image_container)
		content_layout.addWidget(self.prediction_label)
		content_layout.addStretch(1)
		content.setLayout(content_layout)

		layout.addWidget(content)
		layout.addStretch(1)
		self.setLayout(layout)

	def select_directory(self):
		self.tf_directory = QFileDialog.getExistingDirectory(self, "Select TensorFlow Model Directory")
		self.model_label.setText(f"<i>{self.tf_directory}</i>" if self.tf_directory else self.default_model_text)
		self.model = None
		self.visualize()

	def select_file(self):
		self.file = QFileDialog.getOpenFileName(self, 'Select Image File')[0]
		self.path_label.setText(f"<i>{self.file}</i>" if self.file else self.default_file_text)
		self.visualize()

	def visualize(self):
		self.app.processEvents()
		if self.tf_directory is not None and self.file is not None:
			# disable the buttons so we can't click again
			self.model_button.setEnabled(False)
			self.file_button.setEnabled(False)
			self.image_label.setText(self.loading_text)
			self.prediction_label.setText("")
			self.app.processEvents()
			try:
				if self.model is None:
					self.model = ImageModel.load(self.tf_directory)
				self.image = Image.open(self.file)
				prediction = self.model.predict(self.image).prediction
				self.prediction_label.setText(f"Predicted label: {prediction}")
				viz = self.model.visualize(self.image, prediction)
				self.image_label.setPixmap(QPixmap.fromImage(ImageQt(viz)))
			except Exception as e:
				self.image = None
				self.model = None
				QMessageBox.about(self, "Alert", f"Error visualizing: {e}")
			finally:
				self.done()

	def done(self):
		self.model_button.setEnabled(True)
		self.file_button.setEnabled(True)
		if not self.image:
			self.image_label.setText("")
			self.prediction_label.setText("")
		self.app.processEvents()
