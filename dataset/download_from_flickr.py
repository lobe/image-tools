"""
Download images from latitude and longitude bounding boxes in flickr
"""
import argparse
import os
import xml.etree.ElementTree as ET
import requests
from tqdm import tqdm
from dataset.multiprocess_download import MultiprocessDownload, DownloadJob


def download_by_geo(api_key, min_lat, min_long, max_lat, max_long, directory, size='z', num_processes=os.cpu_count(), progress_hook=None):
	url = 'https://www.flickr.com/services/rest/'
	params = {
		'api_key': api_key,
		'method': 'flickr.photos.search',
		'bbox': ','.join([min_long, min_lat, max_long, max_lat]),
		'page': 1,
	}
	response = requests.get(url=url, params=params)
	num_jobs = 0
	if response.ok:
		root = ET.fromstring(response.content)
		page = root.find('photos')
		total_images = int(page.get('total'))
		pages = int(page.get('pages'))
		print(f"Downloading {total_images} images for location min: ({min_lat}, {min_long}) max: ({max_lat}, {max_long})")
		downloader = MultiprocessDownload(directory=directory, num_processes=num_processes)
		for i in range(pages):
			params['page'] = i+1
			print(f"Page {i+1} / {pages}")
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
					downloader.add_job(index=num_jobs, url=img_url)
					num_jobs += 1

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
		print(f"Done. Had {errors} errors.")


if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Download images from flickr by geo location.')
	parser.add_argument('api', help='Your Flickr API key.')
	parser.add_argument('min_lat', help='Minimum latitude to search.')
	parser.add_argument('min_long', help='Minimum longitude to search.')
	parser.add_argument('max_lat', help='Maximum latitude to search.')
	parser.add_argument('max_long', help='Maximum longitude to search.')
	parser.add_argument('directory', help='Directory to download the images to.')
	args = parser.parse_args()
	download_by_geo(
		api_key=args.api, min_lat=args.min_lat, min_long=args.min_long, max_lat=args.max_lat, max_long=args.max_long,
		directory=args.directory
	)
