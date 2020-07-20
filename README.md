# Image Tools: creating image datasets
Image Wrangler helps you form machine learning datasets for image classification.

## Setup
These tools were developed with python 3.7.7

Install the required packages.
```bash
pip install -r requirements.txt
```

## Usage
### CSV or TXT files
####Downloading an image dataset from the urls in a csv or txt file:
```bash
python dataset/download_from_file.py your_file.csv --url UrlHeader --label LabelHeader
```
This downloader script takes either a csv or txt file and will format an image dataset for you. The resulting images 
will be downloaded to a folder with the same name as your input file. If you supplied labels, the images will be 
grouped into sub-folders with the label name.

* csv file
  * specify the column header for the image urls with the --url flag
  * you can optionally give the column header for labels to assign the images if this is a pre-labeled dataset
  
* txt file
  * separate each image url by a newline

####Predicting labels and confidences for images in a csv or txt file:
```bash
python -m model.predict_from_file your_file.csv path/to/lobe/savedmodel --url UrlHeader
```
This prediction script will take a csv or txt file with urls to images and a Lobe TensorFlow SavedModel export directory, 
and create and output csv with the url, label, and confidence

* csv file
  * specify the column header for the image urls with the --url flag
  
* txt file
  * separate each image url by a newline
  
  
##Desktop Application
You can create a desktop GUI application using PyInstaller:

```bash
python -m PyInstaller app/app.spec
```

This will create a `dist/` folder that will contain the application executable `Image Tools.exe`
