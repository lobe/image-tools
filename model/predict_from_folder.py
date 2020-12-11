"""
Given a folder of images and a Tensorflow 1.15 SavedModel file, run image classification on the images and move
them into a subdirectory structure where their directory is the predicted label name.
"""
import argparse
import os
import shutil
from tqdm import tqdm
from model.model import ImageClassification, predict_image
from PIL import Image
from concurrent.futures import ThreadPoolExecutor


def predict_folder(img_dir, model_dir, progress_hook=None):
	"""
	Run your model on a directory of images. This will also go through any images in existing subdirectories.
	Move each image into a subdirectory structure based on the prediction -- the predicted label
	becomes the directory name where the image goes.

	:param img_dir: the filepath to your directory of images.
	:param model_dir: path to the Lobe Tensorflow SavedModel export.
	:param progress_hook: an optional function that will be run with progress_hook(currentProgress, totalProgress) when progress updates.
	"""
	print(f"Predicting {img_dir}")
	img_dir = os.path.abspath(img_dir)
	# if this a .txt file, don't treat the first row as a header. Otherwise, use the first row for header column names.
	if not os.path.isdir(img_dir):
		raise ValueError(f"Please specify a directory to images. Found {img_dir}")

	num_items = sum(len(files) for _, _, files in os.walk(img_dir))
	print(f"Predicting {num_items} items...")

	# load the model
	print("Loading model...")
	model = ImageClassification(model_dir=model_dir)
	model.load()
	print("Model loaded!")

	# iterate over the rows and predict the label
	curr_progress = 0
	with tqdm(total=num_items) as pbar:
		with ThreadPoolExecutor() as executor:
			model_futures = []
			# make our prediction jobs
			for root, _, files in os.walk(img_dir):
				for filename in files:
					image_file = os.path.join(root, filename)
					try:
						image = Image.open(image_file)
						model_futures.append((executor.submit(predict_image, image=image, model=model), image_file))
					except Exception:
						pbar.update(1)
						if progress_hook:
							curr_progress += 1
							progress_hook(curr_progress, num_items)

			for future, img_file in model_futures:
				label, _ = future.result()
				# move the file
				dest_dir = os.path.join(img_dir, label)
				os.makedirs(dest_dir, exist_ok=True)
				shutil.move(img_file, dest_dir)
				pbar.update(1)
				if progress_hook:
					curr_progress += 1
					progress_hook(curr_progress, num_items)


if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Predict an image dataset from a folder of images.')
	parser.add_argument('dir', help='Directory path to your images.')
	parser.add_argument('model_dir', help='Path to your SavedModel from Lobe.')
	args = parser.parse_args()
	predict_folder(img_dir=args.dir, model_dir=args.model_dir)
