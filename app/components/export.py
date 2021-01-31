import os
from PyQt5.QtWidgets import (QPushButton, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QFileDialog, QMessageBox,
                             QProgressBar, QComboBox, QSizePolicy)
from app.components.stretch_wrapper import NoStretch
from dataset.export_from_lobe import get_projects, export_dataset


class Export(QFrame):
	export_text = "Export"
	exporting_text = "Exporting..."

	def __init__(self, app):
		super().__init__()
		# initialize our variables
		self.app = app
		self.export_button = None
		self.progress_bar = None
		self.projects = get_projects()
		self.project_dropdown = None
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
		title = QLabel("Export")
		title.setObjectName("h1")
		description = QLabel("Export your labeled dataset from a Lobe project.")
		description.setObjectName("h2")

		# project dropdown
		project_label = QLabel("Project:")
		project_label.setObjectName("separate")
		self.project_dropdown = QComboBox()
		self.project_dropdown.setSizeAdjustPolicy(QComboBox.AdjustToContents)
		self.project_dropdown.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
		project_container = NoStretch(self.project_dropdown)
		self.populate_projects()

		# button
		self.export_button = QPushButton(self.export_text)
		self.export_button.setEnabled(True)
		self.export_button.clicked.connect(self.export)
		export_container = NoStretch(self.export_button)
		export_container.setObjectName("separate")

		self.progress_bar = QProgressBar()
		self.progress_bar.hide()

		# make our content layout
		content_layout.addWidget(title)
		content_layout.addWidget(description)
		content_layout.addWidget(project_label)
		content_layout.addWidget(project_container)
		content_layout.addWidget(export_container)
		content_layout.addWidget(self.progress_bar)
		content_layout.addStretch(1)
		content.setLayout(content_layout)

		layout.addWidget(content)
		layout.addStretch(1)
		self.setLayout(layout)

	def populate_projects(self):
		self.projects = get_projects()
		self.project_dropdown.clear()
		self.project_dropdown.addItems([name for name, _ in self.projects])
		self.project_dropdown.adjustSize()

	def export(self):
		# disable the buttons so we can't click again
		self.export_button.setEnabled(False)
		self.export_button.setText(self.exporting_text)
		self.progress_bar.setValue(0)
		self.progress_bar.show()
		self.app.processEvents()
		destination_directory = QFileDialog.getExistingDirectory(self, "Select Output Directory")
		# if they hit cancel, don't download
		if not destination_directory:
			self.done()
			return
		# otherwise try exporting to the desired location
		try:
			project_name, project_id = self.projects[self.project_dropdown.currentIndex()]
			export_dir = os.path.join(destination_directory, project_name)
			# rename the directory if there is a conflict
			rename_idx = 1
			while os.path.exists(export_dir):
				export_dir = os.path.abspath(os.path.join(destination_directory, f"{project_name} ({rename_idx})"))
				rename_idx += 1
			export_dataset(project_id=project_id, destination_dir=export_dir, progress_hook=self.progress_hook)
		except Exception as e:
			QMessageBox.about(self, "Alert", f"Error exporting dataset: {e}")
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
		self.export_button.setEnabled(True)
		self.export_button.setText(self.export_text)
		self.app.processEvents()
