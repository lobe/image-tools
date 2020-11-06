"""
Download images from latitude and longitude bounding boxes in flickr
"""
import argparse
import os
import csv
import xml.etree.ElementTree as ET
from typing import Optional, Tuple
import requests
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from dataset.utils import download_image


def download_flickr(
		api_key, directory,
		min_lat=None, min_long=None, max_lat=None, max_long=None,
		search=None, size='z', progress_hook=None
):
	base_url = 'https://www.flickr.com/services/rest/'
	search_params = {
		'api_key': api_key,
		'method': 'flickr.photos.search',
		'page': 1,
		'per_page': 250,
		'media': 'photos',
	}
	if None not in [min_lat, min_long, max_lat, max_long]:
		search_params['bbox'] = ','.join([min_long, min_lat, max_long, max_lat])
	if search is not None:
		search_params['text'] = search
	# everything in try/catch for keyboard interrupt
	print(f"Searching Flickr with params {search_params}")
	try:
		response = requests.get(url=base_url, params=search_params)
		duplicates = 0
		search_errors = 0
		download_errors = 0
		downloaded_images = 0
		img_urls = []
		csv_lock = Lock()
		filesystem_lock = Lock()
		num_processed = 0
		search_imgs = 0
		if response.ok:
			root = ET.fromstring(response.content)
			page = root.find('photos')
			total_images = int(page.get('total'))
			pages = int(page.get('pages'))
			print(f"Found {total_images} images for location min: ({min_lat}, {min_long}) max: ({max_lat}, {max_long}) and search term '{search}' | {pages} pages")
			total_jobs = pages+total_images
			with tqdm(total=total_jobs) as pbar:
				with ThreadPoolExecutor() as executor:
					# run the search page parser
					search_futures = []
					for i in range(1, pages+1):
						search_futures.append(
							executor.submit(
								images_from_search, page_index=i, base_url=base_url, search_params=search_params)
						)

					# now for all the search results, start downloading
					download_futures = {}
					for future in as_completed(search_futures):
						try:
							for farm_id, server_id, photo_id, secret in future.result():
								search_imgs += 1
								# the image download url from the search result info
								img_url = f"https://farm{farm_id}.staticflickr.com/{server_id}/{photo_id}_{secret}_{size}.jpg"
								# don't download duplicates
								if img_url not in img_urls:
									img_urls.append(img_url)
									# submit job to download the image
									download_futures[
										executor.submit(download_image, url=img_url, directory=directory, lock=filesystem_lock)
									] = (photo_id, secret, img_url)
								else:
									# duplicate found, so don't count this image for jobs
									duplicates += 1
									total_jobs -= 1
									pbar.total = total_jobs
									pbar.refresh()
									if progress_hook:
										progress_hook(num_processed, total_jobs)
							# update progress bar for search page
							pbar.update(1)
							num_processed += 1
							if progress_hook:
								progress_hook(num_processed, total_jobs)
						except Exception:
							# search page error, so don't count this page for jobs
							search_errors += 1
							total_jobs -= 1
							pbar.total = total_jobs
							pbar.refresh()
							if progress_hook:
								progress_hook(num_processed, total_jobs)

					# now for all of our downloaded images, write the csv with info if we can
					info_futures = []
					for future in as_completed(download_futures):
						photo_id, secret, url = download_futures[future]
						filename = future.result()
						if not filename:
							# image download error, so don't count this image for jobs
							download_errors += 1
							total_jobs -= 1
							pbar.total = total_jobs
							pbar.refresh()
							if progress_hook:
								progress_hook(num_processed, total_jobs)
						info_futures.append(
							executor.submit(
								write_photo_csv,
								directory=directory, base_url=base_url, api_key=api_key, img_filename=filename,
								url=url, photo_id=photo_id, secret=secret, lock=csv_lock
							)
						)

					# wait for all our final csv jobs to finish
					for _ in as_completed(info_futures):
						# update our progress bar for the finished image download and csv write
						pbar.update(1)
						downloaded_images += 1
						num_processed += 1
						if progress_hook:
							progress_hook(num_processed, total_jobs)

				# update our progress to be 100%
				# (because original number of images reported from flickr api search can be incorrect)
				pbar.update(total_jobs-num_processed)
			print(f"Downloaded {downloaded_images}\nSearch errors: {search_errors} | Duplicates: {duplicates} | Download errors: {download_errors} | Found {search_imgs} images")
			if progress_hook:
				progress_hook(total_jobs, total_jobs)
	except Exception:
		raise


def parse_search_xml(xml):
	root = ET.fromstring(xml)
	page = root.find('photos')
	for photo in page:
		farm_id = photo.get('farm')
		server_id = photo.get('server')
		photo_id = photo.get('id')
		secret = photo.get('secret')
		yield farm_id, server_id, photo_id, secret


def images_from_search(page_index, base_url, search_params):
	search_params['page'] = page_index
	response = requests.get(url=base_url, params=search_params, timeout=30)
	if response.ok:
		return parse_search_xml(response.content)
	return []


def get_photo_location(url, api_key, photo_id) -> Tuple[Optional[float], Optional[float], Optional[float]]:
	"""
	Given the url and photo details, return the latitude, longitude, and accuracy
	"""
	try:
		exif_params = {
			'api_key': api_key,
			'method': 'flickr.photos.geo.getLocation',
			'photo_id': photo_id,
		}
		response = requests.get(url=url, params=exif_params)
		if response.ok:
			root = ET.fromstring(response.content)
			photo = root.find('photo')
			location = photo.find('location')
			latitude = location.get('latitude')
			longitude = location.get('longitude')
			accuracy = location.get('accuracy')
			return latitude, longitude, accuracy
	except Exception:
		pass
	return None, None, None


def get_photo_info(url, api_key, photo_id, secret) -> Tuple[Optional[str], Optional[str], Optional[str]]:
	"""
	Given the url and photo details, return the user id, title, description, and date taken for the photo
	"""
	try:
		info_params = {
			'api_key': api_key,
			'method': 'flickr.photos.getInfo',
			'photo_id': photo_id,
			'secret': secret,
		}
		response = requests.get(url=url, params=info_params)
		if response.ok:
			root = ET.fromstring(response.content)
			photo = root.find('photo')
			owner = photo.find('owner')
			user_id = owner.get('nsid')
			title = photo.find('title').text
			dates = photo.find('dates')
			date_taken = dates.get('taken')
			return user_id, title, date_taken
	except Exception:
		pass
	return None, None, None


def write_photo_csv(directory, base_url, api_key, img_filename, url, photo_id, secret, lock):
	out_file = os.path.join(directory, 'images.csv')
	latitude, longitude, accuracy = get_photo_location(url=base_url, api_key=api_key, photo_id=photo_id)
	user_id, title, date_taken = get_photo_info(url=base_url, api_key=api_key, photo_id=photo_id, secret=secret)
	with lock:
		make_header = not os.path.isfile(out_file)
		with open(out_file, 'a', newline='', encoding='utf-8') as f:
			writer = csv.writer(f)
			# make this header if not a file already
			if make_header:
				writer.writerow(['File', 'URL', 'User ID', 'Title', 'Date Taken', 'Latitude', 'Longitude', 'Geo Accuracy'])
			# write to csv the filename, url, gps data
			try:
				writer.writerow([img_filename, url, user_id, title, date_taken, latitude, longitude, accuracy])
			except Exception as e:
				# probably has exception on title -- make that None (from non-encodable character)
				writer.writerow([img_filename, url, user_id, None, date_taken, latitude, longitude, accuracy])


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
