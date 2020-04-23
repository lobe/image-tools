# Image Wrangler: tools for creating image datasets
Image Wrangler helps you form machine learning datasets for image classification.

## Setup
These tools were developed with python 3.7.7

Install the required packages.
```bash
pip install -r requirements.txt
```

## Usage
### Downloading an image dataset from the urls in a csv or txt file:
```bash
python wrangler/download_from_file.py your_file.csv --url_col UrlHeader --label_col LabelHeader
```
This downloader script takes either a csv or txt file and will format an image dataset for you. The resulting images 
will be downloaded to a folder with the same name as your input file. If you supplied labels, the images will be 
grouped into sub-folders with the label name.

* csv file
  * specify the column header for the image urls with the --url_col flag
  * you can optionally give the column header for labels to assign the images if this is a pre-labeled dataset
  
* txt file
  * separate each image url by a newline
