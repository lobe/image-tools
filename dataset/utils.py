"""
Generic download of image files from URLs
"""
import os
from pathlib import Path
import requests


def download_image(url, directory, lock, label=None):
	filepath = None
	try:
		# get our image save location
		save_dir = os.path.abspath(directory)
		if label is not None:
			save_dir = os.path.join(save_dir, label)
		# make our destination directory if it doesn't exist
		Path(save_dir).mkdir(parents=True, exist_ok=True)
		with lock:
			img_file = _get_filepath(url=url, save_dir=save_dir)
		response = requests.get(url, timeout=30)
		if response.ok:
			# save the image!
			with open(img_file, 'wb') as f:
				f.write(response.content)
			filepath = os.path.abspath(img_file)
			success = True
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
	return filepath


def _get_filepath(url, save_dir):
	# given a url and download folder, return the full filepath to image to save
	# get the name from the last url segment
	filename = str(url.split('/')[-1])
	# strip out url params from name
	filename = filename.split('?')[0]
	# if this file already exists in the path, increment its name
	# (since different URLs can have the same end filename)
	filename = _resolve_filename_conflict(directory=save_dir, filename=filename)
	# now that we found the filename, make an empty file with it so that we don't have to wait file to download
	# for subsequent name searches
	filename = os.path.join(save_dir, filename)
	open(filename, 'a').close()
	return filename


def _resolve_filename_conflict(directory, filename, sep="__"):
	# if this file already exists in the path, increment its name
	while os.path.exists(os.path.join(directory, filename)):
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
	return filename
