"""
Download images from latitude and longitude bounding boxes in flickr
"""
import argparse
import os
import xml.etree.ElementTree as ET
import requests
from tqdm import tqdm
from dataset.multiprocess_download import MultiprocessDownload, DownloadJob


def download_flickr(
		api_key, directory,
		min_lat=None, min_long=None, max_lat=None, max_long=None,
		search=None, size='z', num_processes=os.cpu_count(), progress_hook=None
):
	url = 'https://www.flickr.com/services/rest/'
	params = {
		'api_key': api_key,
		'method': 'flickr.photos.search',
		'page': 1,
		'per_page': 250,
		'media': 'photos',
	}
	if None not in [min_lat, min_long, max_lat, max_long]:
		params['bbox'] = ','.join([min_long, min_lat, max_long, max_lat])
	if search is not None:
		params['text'] = search
	downloader = None
	# everything in try/catch for keyboard interrupt
	try:
		response = requests.get(url=url, params=params)
		num_jobs = 0
		urls = []
		duplicates = 0
		if response.ok:
			root = ET.fromstring(response.content)
			page = root.find('photos')
			total_images = int(page.get('total'))
			pages = int(page.get('pages'))
			print(f"Downloading {total_images} images for location min: ({min_lat}, {min_long}) max: ({max_lat}, {max_long}) and search term '{search}'")
			downloader = MultiprocessDownload(directory=directory, num_processes=num_processes)
			for i in range(pages):
				params['page'] = i+1
				print(f"Reading page {i+1} / {pages}")
				response = requests.get(url=url, params=params)
				if response.ok:
					root = ET.fromstring(response.content)
					page = root.find('photos')
					for photo in page:
						farm_id = photo.get('farm')
						server_id = photo.get('server')
						photo_id = photo.get('id')
						secret = photo.get('secret')
						img_url = f"https://farm{farm_id}.staticflickr.com/{server_id}/{photo_id}_{secret}_{size}.jpg"
						if img_url not in urls:
							downloader.add_job(index=num_jobs, url=img_url)
							num_jobs += 1
							urls.append(img_url)
						else:
							duplicates += 1

			# iterate over the results dictionary to update our progress bar and write any errors to the error csv
			num_processed = 0
			errors = 0
			with tqdm(total=num_jobs) as pbar:
				while num_processed < num_jobs:
					# result is a DownloadJob with success filled out
					result: DownloadJob = downloader.results.get()
					if not result.success:
						errors += 1
					# update progress
					pbar.update(1)
					num_processed += 1
					if progress_hook:
						progress_hook(num_processed, num_jobs)
			print(f"Done. Had {errors} errors, found {duplicates} duplicates.")
	except Exception:
		raise
	finally:
		if downloader is not None:
			downloader.stop()


if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Download images from flickr by geo location.')
	parser.add_argument('api', type=str, help='Your Flickr API key.')
	parser.add_argument('directory', help='Directory to download the images to.')
	parser.add_argument(
		'--bbox', type=str,
		help='Geographic bounding box to search. Comma separated list of: Min Latitude, Min Longitude, Max Latitude, Max Longitude',
		default=None
	)
	parser.add_argument('--search', type=str, help='Search term to use.', default=None)
	args = parser.parse_args()
	if args.bbox is not None:
		min_lat, min_long, max_lat, max_long = [float(arg.strip()) for arg in args.bbox.split(',')]
	else:
		min_lat, min_long, max_lat, max_long = None, None, None, None
	download_flickr(
		api_key=args.api, directory=args.directory,
		min_lat=min_lat, min_long=min_long, max_lat=max_lat, max_long=max_long,
		search=args.search,
	)
