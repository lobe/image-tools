"""
Given a csv or txt file and a Tensorflow 1.15 SavedModel file, run image classification on the urls
and write the predicted label and confidence back to the file
"""
import argparse
import os
import pandas as pd
from csv import writer as csv_writer
from tqdm import tqdm
from lobe import ImageModel
from concurrent.futures import ThreadPoolExecutor


def predict_dataset(filepath, model_dir, url_col=None, progress_hook=None):
	"""
	Given a file with urls to images, predict the given SavedModel on the image and write the label
	and confidene back to the file.

	:param filepath: path to a valid txt or csv file with image urls to download.
	:param model_dir: path to the Lobe Tensorflow SavedModel export.
	:param url_col: if this is a csv, the column header name for the urls to download.
	:param progress_hook: an optional function that will be run with progress_hook(currentProgress, totalProgress) when progress updates.
	"""
	print(f"Predicting {filepath}")
	filepath = os.path.abspath(filepath)
	filename, ext = _name_and_extension(filepath)
	# read the file
	# if this a .txt file, don't treat the first row as a header. Otherwise, use the first row for header column names.
	if ext != '.xlsx':
		csv = pd.read_csv(filepath, header=None if ext == '.txt' else 0)
	else:
		csv = pd.read_excel(filepath, header=0)
	if ext in ['.csv', '.xlsx'] and not url_col:
		raise ValueError(f"Please specify an image url column for the csv.")
	url_col_idx = 0
	if url_col:
		try:
			url_col_idx = list(csv.columns).index(url_col)
		except ValueError:
			raise ValueError(f"Image url column {url_col} not found in csv headers {csv.columns}")

	num_items = len(csv)
	print(f"Predicting {num_items} items...")

	# load the model
	print("Loading model...")
	model = ImageModel.load(model_path=model_dir)
	print("Model loaded!")

	# create our output csv
	fname, ext = os.path.splitext(filepath)
	out_file = f"{fname}_predictions.csv"
	with open(out_file, 'w', encoding="utf-8", newline='') as f:
		# our header names from the pandas columns
		writer = csv_writer(f)
		writer.writerow([*[str(col) if not pd.isna(col) else '' for col in csv.columns], 'label', 'confidence'])

	# iterate over the rows and predict the label
	with tqdm(total=len(csv)) as pbar:
		with ThreadPoolExecutor() as executor:
			model_futures = []
			# make our prediction jobs
			for i, row in enumerate(csv.itertuples(index=False)):
				url = row[url_col_idx]
				model_futures.append(executor.submit(predict_image_url, url=url, model=model, row=row))

			# write the results from the predict (this should go in order of the futures)
			for i, future in enumerate(model_futures):
				label, confidence, row = future.result()
				with open(out_file, 'a', encoding="utf-8", newline='') as f:
					writer = csv_writer(f)
					writer.writerow([*[str(col) if not pd.isna(col) else '' for col in row], label, confidence])
				pbar.update(1)
				if progress_hook:
					progress_hook(i+1, len(csv))


def predict_image_url(url, model: ImageModel, row):
	label, confidence = '', ''
	try:
		result = model.predict_from_url(url=url)
		label, confidence = result.labels[0]
	except Exception as e:
		print(f"Problem predicting image from url: {e}")
	return label, confidence, row


def _name_and_extension(filepath):
	# returns a tuple of the filename and the extension, ignoring any other prefixes in the filepath
	# raises if not a file
	fpath = os.path.abspath(filepath)
	if not os.path.isfile(fpath):
		raise ValueError(f"File {filepath} doesn't exist.")
	filename = os.path.split(fpath)[-1]
	name, ext = os.path.splitext(filename)
	return name, str.lower(ext)


def _valid_file(filepath):
	# file must exist and have a valid extension
	valid_extensions = ['.txt', '.csv', '.xlsx']
	_, extension = _name_and_extension(filepath)
	if extension not in valid_extensions:
		raise ValueError(f"File {filepath} doesn't have one of the valid extensions: {valid_extensions}")
	# good to go
	return filepath


if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Label an image dataset from csv or txt file.')
	parser.add_argument('file', help='Path to your csv or txt file.')
	parser.add_argument('model_dir', help='Path to your SavedModel from Lobe.')
	parser.add_argument('--url', help='If this is a csv with column headers, the column that contains the image urls to download.')
	args = parser.parse_args()
	predict_dataset(filepath=args.file, model_dir=args.model_dir, url_col=args.url)
