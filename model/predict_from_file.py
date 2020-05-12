"""
Given a csv or txt file and a Tensorflow 1.14 SavedModel file, run image classification on the urls
and write the predicted label and confidence back to the file
"""
import argparse
import os
from io import BytesIO
import requests
import pandas as pd
from tqdm import tqdm
from model.model import ImageClassification
from PIL import Image


def predict_dataset(filepath, model_dir, url_col=None):
	"""
	Given a file with urls to images, predict the given SavedModel on the image and write the label
	and confidene back to the file.

	:param filepath: path to a valid txt or csv file with image urls to download.
	:param model_dir: path to the Lobe Tensorflow SavedModel export.
	:param url_col: if this is a csv, the column header name for the urls to download.
	"""
	print(f"Predicting {filepath}")
	filepath = os.path.abspath(filepath)
	filename, ext = _name_and_extension(filepath)
	# read the file
	# if this a .txt file, don't treat the first row as a header. Otherwise, use the first row for header column names.
	csv = pd.read_csv(filepath, header=None if ext == '.txt' else 0)
	if ext == '.csv' and not url_col:
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
	model = ImageClassification(model_dir=model_dir)
	model.load()

	# create our output csv
	out_file = os.path.splitext(filepath)[0] + "_predictions.csv"
	with open(out_file, 'w') as f:
		header = f"url,label,confidence\n"
		f.write(header)

	# iterate over the rows and predict the label
	for i, row in tqdm(enumerate(csv.itertuples(index=False)), total=len(csv)):
		url = row[url_col_idx]
		try:
			response = requests.get(url)
			if response.ok:
				image = Image.open(BytesIO(response.content))
				predictions = model.predict(image)
				predictions.sort(key=lambda x: x[1], reverse=True)
				label, confidence = predictions[0]
			else:
				label, confidence = '', ''
		except:
			label, confidence = '', ''
		with open(out_file, 'a') as f:
			f.write(f"{url},{label},{confidence}\n")


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
	valid_extensions = ['.txt', '.csv']
	_, extension = _name_and_extension(filepath)
	if extension not in valid_extensions:
		raise ValueError(f"File {filepath} doesn't have one of the valid extensions: {valid_extensions}")
	# good to go
	return filepath


if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Label an image dataset from csv or txt file.')
	parser.add_argument('file', help='Path to your csv or txt file.')
	parser.add_argument('model_dir', help='Path to your SavedModel from Lobe.')
	parser.add_argument('--url_col', help='If this is a csv with column headers, the column that contains the image urls to download.')
	args = parser.parse_args()
	predict_dataset(filepath=args.file, model_dir=args.model_dir, url_col=args.url_col)
