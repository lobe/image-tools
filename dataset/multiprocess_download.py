"""
Generic multiprocess download of image files form URLs
"""
import os
from pathlib import Path
from multiprocessing import Lock, Queue, Process
import requests


class DownloadJob(object):
	"""
	Object with information to pass across processes when downloading images.
	"""
	def __init__(self, index: int, url: str, label: str = None, success: bool = None):
		self.index = index
		self.url = url
		self.label = label
		self.success = success


class MultiprocessDownload(object):
	"""
	An implementation of a multiprocess pool that downlaods images from URLs.
	Exposes both job and results queues so that other functions can add jobs and access results async.
	Will use a lock for finding the filename to download to.
	"""
	def __init__(self, directory: str, num_processes=os.cpu_count()):
		self.num_processes = num_processes
		self.jobs = Queue()
		self.results = Queue()
		self.lock = Lock()
		self.directory = directory
		self.processes = [
			Process(target=self.download_worker, args=(self.jobs, self.results, self.lock, self.directory))
			for _ in range(self.num_processes)
		]
		for process in self.processes:
			process.start()

	def add_job(self, index: int, url: str, label: str = None):
		self.jobs.put(DownloadJob(index=index, url=url, label=label))

	def stop(self):
		for process in self.processes:
			process.terminate()
			process.join()
		self.jobs.close()
		self.results.close()

	@staticmethod
	def download_worker(jobs: Queue, results: Queue, lock: Lock, directory: str):
		while True:
			# job from the queue
			job: DownloadJob = jobs.get()
			success = True
			img_file = None
			try:
				# get our image save location
				save_dir = os.path.abspath(directory)
				if job.label is not None:
					save_dir = os.path.join(save_dir, job.label)
				# make our destination directory if it doesn't exist
				Path(save_dir).mkdir(parents=True, exist_ok=True)
				with lock:
					img_file = _get_filepath(url=job.url, save_dir=save_dir)
				response = requests.get(job.url, timeout=30)
				if response.ok:
					# save the image!
					with open(img_file, 'wb') as f:
						f.write(response.content)
				else:
					success = False
			except Exception:
				success = False
			if not success:
				# with failure, also delete any bit of the temp file we made
				try:
					os.remove(img_file)
				except Exception:
					pass
			# add success to the job and put on the queue
			job.success = success
			results.put(job)


def _get_filepath(url, save_dir):
	sep = "__"
	# given a url and download folder, return the full filepath to image to save
	# get the name from the last url segment
	filename = str(url.split('/')[-1])
	# strip out url params from name
	filename = filename.split('?')[0]
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
	# now that we found the filename, make an empty file with it so that we don't have to wait file to download
	# for subsequent name searches
	filename = os.path.join(save_dir, filename)
	open(filename, 'a').close()
	return filename
