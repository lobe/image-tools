"""
Given a csv or txt file, download the image urls to form the dataset.
"""
import argparse
import os
from csv import writer as csv_writer
import pandas as pd
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from dataset.utils import download_image


def create_dataset(filepath, url_col=None, label_col=None, progress_hook=None, destination_directory=None):
	"""
	Given a file with urls to images, downloads those images to a new directory that has the same name
	as the file without the extension. If labels are present, further categorizes the directory to have
	the labels as sub-directories.

	:param filepath: path to a valid txt or csv file with image urls to download.
	:param url_col: if this is a csv, the column header name for the urls to download.
	:param label_col: if this is a csv, the column header name for the labels of the images.
	:param progress_hook: an optional function that will be run with progress_hook(currentProgress, totalProgress) when progress updates.
	:param destination_directory: an optional directory path to download the dataset to.
	"""
	print(f"Processing {filepath}")
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
	label_col_idx = None
	if label_col:
		try:
			label_col_idx = list(csv.columns).index(label_col)
		except ValueError:
			raise ValueError(f"Label column {label_col} not found in csv headers {csv.columns}")

	total_jobs = len(csv)
	print(f"Downloading {total_jobs} items...")

	errors = []
	dest = os.path.join(destination_directory, filename) if destination_directory else filename

	# try/catch for keyboard interrupt
	try:
		# iterate over the rows and add to our download processing job!
		with tqdm(total=total_jobs) as pbar:
			with ThreadPoolExecutor() as executor:
				# for every image in the row, download it!
				download_futures = {}
				lock = Lock()
				for i, row in enumerate(csv.itertuples(index=False)):
					# job is passed to our worker processes
					index = i + 1
					url = row[url_col_idx]
					label = None
					if label_col_idx:
						label = row[label_col_idx]
						label = None if pd.isnull(label) else label
					download_futures[
						executor.submit(download_image, url=url, directory=dest, lock=lock, label=label)
					] = (index, url, label)


				# iterate over the results to update our progress bar and write any errors to the error csv
				num_processed = 0
				for future in as_completed(download_futures):
					index, url, label = download_futures[future]
					filename = future.result()
					if not filename:
						error_row = [index, url]
						if label_col_idx:
							error_row.append(label)
						errors.append(error_row)
					# update progress
					pbar.update(1)
					num_processed += 1
					if progress_hook:
						progress_hook(num_processed, total_jobs)

		print('Cleaning up...')
		# write out the error csv
		if len(errors) > 0:
			errors.sort()
			fname, ext = os.path.splitext(filepath)
			error_file = f"{fname}_errors.csv"
			with open(error_file, 'w', newline='') as f:
				header = f"index,url{',label' if label_col_idx else ''}\n"
				f.write(header)
				writer = csv_writer(f)
				writer.writerows(errors)

	except Exception:
		raise


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
	parser = argparse.ArgumentParser(description='Download an image dataset from csv or txt file.')
	parser.add_argument('file', help='Path to your csv or txt file.')
	parser.add_argument('--url', help='If this is a csv with column headers, the column that contains the image urls to download.')
	parser.add_argument('--label', help='If this is a csv with column headers, the column that contains the labels to assign the images.')
	args = parser.parse_args()
	create_dataset(filepath=args.file, url_col=args.url, label_col=args.label)
