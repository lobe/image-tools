"""
Given a csv or txt file, download the image urls to form the dataset.
"""
import argparse
import os
from csv import writer as csv_writer
from multiprocessing import Process, Queue
import requests
import pandas as pd
import numpy as np
from tqdm import tqdm
from pathlib import Path


def create_dataset(filepath, url_col=None, label_col=None, num_processes=10):
	"""
	Given a file with urls to images, downloads those images to a new directory that has the same name
	as the file without the extension. If labels are present, further categorizes the directory to have
	the labels as sub-directories.

	:param filepath: path to a valid txt or csv file with image urls to download.
	:param url_col: if this is a csv, the column header name for the urls to download.
	:param label_col: if this is a csv, the column header name for the labels of the images.
	:param num_processes: the number of processes to use for the multiprocessing pool.
	"""
	print(f"Processing {filepath}")
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
	label_col_idx = None
	if label_col:
		try:
			label_col_idx = list(csv.columns).index(label_col)
		except ValueError:
			raise ValueError(f"Label column {label_col} not found in csv headers {csv.columns}")

	num_items = len(csv)
	print(f"Downloading {num_items} items...")

	# create our processes that will download the images
	# first create the queue for the worker job parameters and the results
	jobs = Queue()
	results = Queue()
	# now make the processes
	processes = [Process(target=_worker, args=(jobs, results, filename)) for _ in range(num_processes)]
	for process in processes:
		process.start()

	# iterate over the rows and add to our download processing job!
	for i, row in enumerate(csv.itertuples(index=False)):
		# job is a dict in the form of {'index': int, 'url': string, 'label': Optional[string]}
		job = {'index': i+1, 'url': row[url_col_idx]}
		if label_col_idx:
			label = row[label_col_idx]
			job['label'] = None if pd.isnull(label) else label
		jobs.put(job)

	# iterate over the results dictionary to update our progress bar and write any errors to the error csv
	num_processed = 0
	errors = []
	with tqdm(total=num_items) as pbar:
		while num_processed < num_items:
			# result is a dict of {'index': int, 'url': string, 'label': Optional[string], 'success': bool}
			result = results.get()
			if not result.get('success'):
				error_row = [result.get('index'), result.get('url')]
				if label_col_idx:
					error_row.append(result.get('label'))
				errors.append(error_row)
			# update progress
			pbar.update(1)
			num_processed += 1

	print('Cleaning up...')
	# write out the error csv
	if len(errors) > 0:
		errors.sort()
		error_file = os.path.splitext(filepath)[0] + "_errors.csv"
		with open(error_file, 'w') as f:
			header = f"index,url{',label' if label_col_idx else ''}\n"
			f.write(header)
			writer = csv_writer(f)
			writer.writerows(errors)

	# terminate the processes
	for process in processes:
		process.terminate()
		process.join()
	jobs.close()
	results.close()
	print('Done!')


def _worker(jobs, results, dest_folder):
	while True:
		# job is a dict in the form of {'index': int, 'url': string, 'label': Optional[string]}
		job = jobs.get()
		url = job.get('url')
		label = job.get('label')
		success = True
		try:
			filename = str(url.split('/')[-1])
			# get our image save location
			save_dir = os.path.abspath(dest_folder)
			if label is not None:
				save_dir = os.path.join(save_dir, label)
			save_fpath = os.path.join(save_dir, filename)
			# skip if the file exists
			if not os.path.exists(save_fpath):
				request = requests.get(url)
				if request.ok:
					# make our destination directory if it doesn't exist
					Path(save_dir).mkdir(parents=True, exist_ok=True)
					# save the image!
					with open(os.path.join(save_dir, filename), 'wb') as f:
						f.write(request.content)
				else:
					success = False
		except Exception:
			success = False
		# result is a dict of {'index': int, 'url': string, 'label': Optional[string], 'success': bool}
		results.put({'index': job.get('index'), 'url': url, 'label': label, 'success': success})


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
	parser = argparse.ArgumentParser(description='Download an image dataset from csv or txt file.')
	parser.add_argument('file', help='Path to your csv or txt file.')
	parser.add_argument('--url_col', help='If this is a csv with column headers, the column that contains the image urls to download.')
	parser.add_argument('--label_col', help='If this is a csv with column headers, the column that contains the labels to assign the images.')
	args = parser.parse_args()
	create_dataset(filepath=args.file, url_col=args.url_col, label_col=args.label_col)
