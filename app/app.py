from PyQt5 import QtGui
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QFileDialog, QPushButton, QWidget, QGridLayout, QMessageBox, QHBoxLayout, QRadioButton, QProgressBar, QButtonGroup
import pandas as pd
import sys
import os
from model.predict_from_file import predict_dataset
from dataset.download_from_file import create_dataset
from multiprocessing import freeze_support

try:
    # Include in try/except block if you're also targeting Mac/Linux
    from PyQt5.QtWinExtras import QtWin
    QtWin.setCurrentProcessExplicitAppUserModelID('image-tools.0.1')
except ImportError:
    pass


class MainWindow(QMainWindow):

    def __init__(self, app, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # initialize our variables
        self.app = app
        self.setMinimumSize(600, 400)
        self.model_dir = None
        self.csv = None
        self.csv_headers = []
        self.url_col = None
        self.label_col = None
        self.processing = False

        # directory picker for the tensorflow savedmodel if we want to run predictions
        model_button = QPushButton('Select TensorFlow SavedModel')
        model_button.clicked.connect(self.tensorflow_savedmodel_dir)
        self.model_label = QLabel(self.model_dir)

        # file picker for the csv/excel file for running predictions or downloading the dataset
        file_button = QPushButton('Select CSV')
        file_button.clicked.connect(self.csv_file)
        self.file_label = QLabel(self.csv)
        self.radio_boxes = []
        self.radio_buttons = []

        self.download_button = QPushButton('Download Images')

        self.run_button = QPushButton('Run')
        self.run_button_idle()

        self.progress_bar = None

        self.grid = QGridLayout()
        self.grid.addWidget(model_button, 1, 1)
        self.grid.addWidget(self.model_label, 1, 2)
        self.grid.addWidget(file_button, 2, 1)
        self.grid.addWidget(self.file_label, 2, 2)
        self.grid.addWidget(self.run_button, 5, 1)
        self.grid.setColumnStretch(0, 1)
        self.grid.setColumnStretch(3, 1)
        self.grid.setRowStretch(0, 1)
        self.grid.setRowStretch(7, 1)

        window = QWidget()
        window.setLayout(self.grid)

        self.setCentralWidget(window)
        self.setWindowTitle("Image Tools")
        self.show()

    def run_model(self):
        if not self.csv:
            QMessageBox.about(self, "Alert", "Please select a TensorFlow model directory and CSV file.")
        elif not self.url_col:
            QMessageBox.about(self, "Alert", "Please select the image url column in your csv.")
        else:
            try:
                self.processing = True
                self.run_button_running()
                self.init_progress()

                if not self.model_dir:
                    # Download our images from the csv
                    self.run_button.setText("Downloading...")
                    create_dataset(filepath=self.csv, url_col=self.url_col, label_col=self.label_col, progress_hook=self.progress_hook)
                else:
                    # run our saved model on the images from the csv
                    self.run_button.setText("Predicting...")
                    predict_dataset(filepath=self.csv, model_dir=self.model_dir, url_col=self.url_col, progress_hook=self.progress_hook)
            except Exception as e:
                QMessageBox.about(self, "Alert", f"Error, please check your directory and file and try again. {e}")
                self.cancel_run()

    def tensorflow_savedmodel_dir(self):
        if not self.processing:
            self.model_dir = QFileDialog.getExistingDirectory(self, "Select TensorFlow SavedModel Directory")
            self.model_label.setText(str(self.model_dir))
            self.set_run_button_text()
        else:
            QMessageBox.about(self, "Alert", "Please cancel before selecting a new model.")

    def csv_file(self):
        if not self.processing:
            self.csv = QFileDialog.getOpenFileName(self, 'Select CSV or TXT File', filter="CSV (*.csv *.xlsx)")[0]
            self.file_label.setText(str(self.csv))
            if self.csv:
                self.set_csv_headers()
            else:
                self.clear_headers()
                self.url_col = None
            self.set_run_button_text()
        else:
            QMessageBox.about(self, "Alert", "Please cancel before selecting a new csv.")

    def set_run_button_text(self):
        if self.csv and not self.model_dir:
            self.run_button.setText("Download")
        else:
            self.run_button.setText("Run")

    def run_button_idle(self):
        self.set_run_button_text()
        self.run_button.clicked.connect(self.run_model)

    def run_button_running(self):
        self.run_button.setText("Cancel")
        self.run_button.clicked.connect(self.cancel_run)

    def progress_hook(self, current, total):
        self.progress_bar.setValue(float(current) / total * 100)
        if current == total:
            self.cancel_run()
        # make sure to update the UI
        self.app.processEvents()

    def cancel_run(self):
        self.processing = False
        self.run_button_idle()
        self.delete_progress()

    def set_csv_headers(self):
        if not self.csv:
            QMessageBox.about(self, "Alert", "Please select a CSV file.")
        else:
            try:
                if os.path.splitext(self.csv)[1] == ".csv":
                    csv = pd.read_csv(self.csv, header=0)
                else:
                    csv = pd.read_excel(self.csv, header=0)
                self.csv_headers = list(csv.columns)
                self.csv_header_layout()
            except Exception as e:
                QMessageBox.about(self, "Alert", f"Error reading csv: {e}")
                self.csv_headers = []
                self.clear_headers()

    def csv_header_layout(self):
        # todo very ugly, clean later :)
        self.clear_headers()
        url_box = QHBoxLayout()
        url_group = QButtonGroup(self)
        url_label = QLabel("Image URL Header:")
        url_box.addWidget(url_label)
        self.radio_buttons.append(url_label)
        label_box = QHBoxLayout()
        label_group = QButtonGroup(self)
        label_label = QLabel("Labels Header (optional):")
        label_box.addWidget(label_label)
        self.radio_buttons.append(label_label)
        for i, header in enumerate(self.csv_headers):
            url_button = QRadioButton(header)
            url_group.addButton(url_button)
            label_button = QRadioButton(header)
            label_group.addButton(label_button)
            url_button.toggled.connect(self.url_header)
            label_button.toggled.connect(self.label_header)
            url_box.addWidget(url_button)
            label_box.addWidget(label_button)
            self.radio_buttons.extend([url_button, label_button])
        self.grid.addLayout(url_box, 3, 1, 1, 2)
        self.grid.addLayout(label_box, 4, 1, 1, 2)
        self.radio_boxes.extend([url_box, label_box])

    def url_header(self):
        button = self.sender()
        if button.isChecked():
            self.url_col = button.text()

    def label_header(self):
        button = self.sender()
        if button.isChecked():
            self.label_col = button.text()

    def clear_headers(self):
        for old_button in self.radio_buttons:
            old_button.deleteLater()
            del old_button
        for radio_box in self.radio_boxes:
            radio_box.deleteLater()
            del radio_box
        self.radio_boxes = []
        self.radio_buttons = []

    def init_progress(self):
        self.delete_progress()
        self.progress_bar = QProgressBar()
        self.grid.addWidget(self.progress_bar, 6, 1, 1, 2)

    def delete_progress(self):
        if self.progress_bar is not None:
            self.progress_bar.deleteLater()
            del self.progress_bar
            self.progress_bar = None


if __name__ == '__main__':
    freeze_support()
    app = QApplication(sys.argv)
    icon_path = 'assets/icon.ico' if os.path.exists('assets/icon.ico') else 'app/assets/icon.ico'
    app.setWindowIcon(QtGui.QIcon(icon_path))
    app.setStyleSheet("QPushButton { margin-left: 0px; margin-right: 10px; margin-top: 10px; min-width: 160px; max-width: 160px; min-height: 30px; max-height: 30px; }")

    w = MainWindow(app)
    app.exec()
