"""
Given a folder of images and a Tensorflow 1.15 SavedModel file, run image classification on the images and move
them into a subdirectory structure where their directory is the predicted label name.
"""
import argparse
import os
import shutil
from tqdm import tqdm
from lobe import ImageModel
from concurrent.futures import ThreadPoolExecutor
from csv import writer as csv_writer


def predict_folder(img_dir, model_dir, progress_hook=None, move=True, csv=False):
	"""
	Run your model on a directory of images. This will also go through any images in existing subdirectories.
	Move each image into a subdirectory structure based on the prediction -- the predicted label
	becomes the directory name where the image goes.

	:param img_dir: the filepath to your directory of images.
	:param model_dir: path to the Lobe Tensorflow SavedModel export.
	:param progress_hook: an optional function that will be run with progress_hook(currentProgress, totalProgress) when progress updates.
	:param move: a flag for whether you want to physically move the image files into a subfolder structure based on the predicted label
	:param csv: a flag for whether you want to create an output csv showing the image filenames and their predictions
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
	model = ImageModel.load(model_path=model_dir)
	print("Model loaded!")

	# create our output csv
	out_csv = os.path.join(img_dir, "predictions.csv")
	if csv:
		with open(out_csv, 'w', encoding="utf-8", newline='') as f:
			writer = csv_writer(f)
			writer.writerow(['File', 'Label', 'Confidence'])

	# iterate over the rows and predict the label
	curr_progress = 0
	no_labels = 0
	with tqdm(total=num_items) as pbar:
		with ThreadPoolExecutor() as executor:
			model_futures = []
			# make our prediction jobs
			for root, _, files in os.walk(img_dir):
				for filename in files:
					image_file = os.path.abspath(os.path.join(root, filename))
					model_futures.append(
						(executor.submit(predict_label_from_image_file, image_file=image_file, model=model), image_file)
					)

			for future, img_file in model_futures:
				label, confidence = future.result()
				if label is None:
					no_labels += 1
				else:
					# move the file
					dest_file = img_file
					if move:
						filename = os.path.split(img_file)[-1]
						name, ext = os.path.splitext(filename)
						dest_dir = os.path.join(img_dir, label)
						os.makedirs(dest_dir, exist_ok=True)
						dest_file = os.path.abspath(os.path.join(dest_dir, filename))
						# only move if the destination is different than the file
						if dest_file != img_file:
							try:
								# rename the file if there is a conflict
								rename_idx = 0
								while os.path.exists(dest_file):
									new_name = f'{name}_{rename_idx}{ext}'
									dest_file = os.path.abspath(os.path.join(dest_dir, new_name))
									rename_idx += 1
								shutil.move(img_file, dest_file)
							except Exception as e:
								print(f"Problem moving file: {e}")
					# write the results to a csv
					if csv:
						with open(out_csv, 'a', encoding="utf-8", newline='') as f:
							writer = csv_writer(f)
							writer.writerow(
								[dest_file, label, confidence])
				pbar.update(1)
				if progress_hook:
					curr_progress += 1
					progress_hook(curr_progress, num_items)
	print(f"Done! Number of images without predicted labels: {no_labels}")


def predict_label_from_image_file(image_file, model: ImageModel):
	try:
		result = model.predict_from_file(path=image_file)
		return result.labels[0]
	except Exception as e:
		print(f"Problem predicting image from file: {e}")
	return None, None


if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Predict an image dataset from a folder of images.')
	parser.add_argument('dir', help='Directory path to your images.')
	parser.add_argument('model_dir', help='Path to your SavedModel from Lobe.')
	args = parser.parse_args()
	predict_folder(img_dir=args.dir, model_dir=args.model_dir, move=True, csv=True)
