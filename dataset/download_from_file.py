"""
Given a csv or txt file, download the image urls to form the dataset.
"""
import argparse
import os
from csv import writer as csv_writer
from multiprocessing import Process, Queue
import requests
import pandas as pd
from tqdm import tqdm
from pathlib import Path


class DownloadJob(object):
	"""
	Object with information to pass across processes when downloading images.
	"""
	def __init__(self, index: int, url: str, label: str = None, success: bool = None):
		self.index = index
		self.url = url
		self.label = label
		self.success = success


def create_dataset(filepath, url_col=None, label_col=None, num_processes=10, progress_hook=None):
	"""
	Given a file with urls to images, downloads those images to a new directory that has the same name
	as the file without the extension. If labels are present, further categorizes the directory to have
	the labels as sub-directories.

	:param filepath: path to a valid txt or csv file with image urls to download.
	:param url_col: if this is a csv, the column header name for the urls to download.
	:param label_col: if this is a csv, the column header name for the labels of the images.
	:param num_processes: the number of processes to use for the multiprocessing pool.
	:param progress_hook: an optional function that will be run with progress_hook(currentProgress, totalProgress) when progress updates.
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

	print(f"Downloading {len(csv)} items...")

	# create our processes that will download the images
	# first create the queue for the worker job parameters and the results
	jobs = Queue()
	results = Queue()
	errors = []
	# now make the processes
	processes = [Process(target=_worker, args=(jobs, results, filename)) for _ in range(num_processes)]
	for process in processes:
		process.start()

	# iterate over the rows and add to our download processing job!
	num_jobs = 0
	for i, row in enumerate(csv.itertuples(index=False)):
		# job is passed to our worker processes
		job = DownloadJob(index=i+1, url=row[url_col_idx])
		if label_col_idx:
			label = row[label_col_idx]
			job.label = None if pd.isnull(label) else label
		jobs.put(job)
		num_jobs += 1

	# iterate over the results dictionary to update our progress bar and write any errors to the error csv
	num_processed = 0
	with tqdm(total=num_jobs) as pbar:
		while num_processed < num_jobs:
			# result is a DownloadJob with success filled out
			result: DownloadJob = results.get()
			if not result.success:
				error_row = [result.index, result.url]
				if label_col_idx:
					error_row.append(result.label)
				errors.append(error_row)
			# update progress
			pbar.update(1)
			num_processed += 1
			if progress_hook:
				progress_hook(num_processed, num_jobs)

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

	# terminate the processes
	for process in processes:
		process.terminate()
		process.join()
	jobs.close()
	results.close()
	print('Done!')


def _worker(jobs, results, dest_folder):
	while True:
		# job from the queue
		job: DownloadJob = jobs.get()
		success = True
		try:
			# get our image save location
			save_dir = os.path.abspath(dest_folder)
			if job.label is not None:
				save_dir = os.path.join(save_dir, job.label)
			img_file = _get_filepath(url=job.url, save_dir=save_dir)
			request = requests.get(job.url, timeout=30)
			if request.ok:
				# make our destination directory if it doesn't exist
				Path(save_dir).mkdir(parents=True, exist_ok=True)
				# save the image!
				with open(img_file, 'wb') as f:
					f.write(request.content)
			else:
				success = False
		except Exception:
			success = False
		# add success to the job and put on the queue
		job.success = success
		results.put(job)


def _name_and_extension(filepath):
	# returns a tuple of the filename and the extension, ignoring any other prefixes in the filepath
	# raises if not a file
	fpath = os.path.abspath(filepath)
	if not os.path.isfile(fpath):
		raise ValueError(f"File {filepath} doesn't exist.")
	filename = os.path.split(fpath)[-1]
	name, ext = os.path.splitext(filename)
	return name, str.lower(ext)


def _get_filepath(url, save_dir):
	sep = "__"
	# given a url and download folder, return the full filepath to image to save
	# get the name from the last url segment
	filename = str(url.split('/')[-1])
	# if this file already exists in the path, increment its name
	# (since different URLs can have the same end filename)
	while os.path.exists(os.path.join(save_dir, filename)):
		name, extension = os.path.splitext(filename)
		name_parts = name.rsplit(sep, 1)
		base_name = name_parts[0]
		# get the counter value after the sep
		counter = 1
		if len(name_parts) > 1:
			try:
				counter = int(name_parts[-1]) + 1
			except ValueError:
				base_name = sep.join(name_parts)
		filename = f"{base_name}{sep}{counter}{extension}"
	return os.path.join(save_dir, filename)


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
