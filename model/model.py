"""
load our TF saved model
"""
import os
import json
import tensorflow as tf
from PIL import Image
import numpy as np
from threading import Lock


class ImageClassification(object):
    def __init__(self, model_dir):
        # make this thread-safe
        self.lock = Lock()
        # make sure our exported SavedModel folder exists
        model_path = os.path.realpath(model_dir)
        if not os.path.exists(model_path):
            raise ValueError(f"Exported model folder doesn't exist: `{model_dir}`")
        self.model_path = model_path

        # load our signature json file, this shows us the model inputs and outputs
        # you should open this file and take a look at the inputs/outputs to see their data types, shapes, and names
        with open(os.path.join(model_path, "signature.json"), "r") as f:
            self.signature = json.load(f)
        self.inputs = self.signature.get("inputs")
        self.outputs = self.signature.get("outputs")
        self.labels = self.signature.get("classes", {}).get("Label", [])

        # placeholder for the tensorflow session
        self.session = None

    def load(self):
        self.cleanup()
        with self.lock:
            # create a new tensorflow session
            self.session = tf.compat.v1.Session(graph=tf.Graph())
            # load our model into the session
            tf.compat.v1.saved_model.loader.load(sess=self.session, tags=self.signature.get("tags"), export_dir=self.model_path)

    def predict(self, image: Image.Image):
        # load the model if we don't have a session
        if self.session is None:
            self.load()
        # get the image width and height
        width, height = image.size
        # center crop image (you can substitute any other method to make a square image, such as just resizing or padding edges with 0)
        if width != height:
            square_size = min(width, height)
            left = (width - square_size) / 2
            top = (height - square_size) / 2
            right = (width + square_size) / 2
            bottom = (height + square_size) / 2
            # Crop the center of the image
            image = image.crop((left, top, right, bottom))
        # now the image is square, resize it to be the right shape for the model input
        if "Image" not in self.inputs:
            raise ValueError("Couldn't find Image in model inputs - please report issue to Lobe!")
        input_width, input_height = self.inputs["Image"]["shape"][1:3]
        if image.width != input_width or image.height != input_height:
            image = image.resize((input_width, input_height))
        # make 0-1 float instead of 0-255 int (that PIL Image loads by default)
        image = np.asarray(image) / 255.0
        # create the feed dictionary that is the input to the model
        # first, add our image to the dictionary (comes from our signature.json file)
        feed_dict = {self.inputs["Image"]["name"]: [image]}

        # list the outputs we want from the model -- these come from our signature.json file
        # since we are using dictionaries that could have different orders, make tuples of (key, name) to keep track for putting
        # the results back together in a dictionary
        fetches = [(key, output["name"]) for key, output in self.outputs.items()]

        # run the model! there will be as many outputs from session.run as you have in the fetches list
        outputs = self.session.run(fetches=[name for _, name in fetches], feed_dict=feed_dict)
        # do a bit of postprocessing
        results = {}
        # since we actually ran on a batch of size 1, index out the items from the returned numpy arrays
        for i, (key, _) in enumerate(fetches):
            val = outputs[i].tolist()[0]
            if isinstance(val, bytes):
                val = val.decode()
            results[key] = val

        # return our (label, confidence) pairs
        confidences = results.get('Confidences')
        return list(zip(self.labels, confidences))

    def cleanup(self):
        with self.lock:
            # close our tensorflow session if one exists
            if self.session is not None:
                self.session.close()
                self.session = None

    def __del__(self):
        self.cleanup()


def predict_image(image, model):
    label, confidence = '', ''
    try:
        # convert to rgb image if this isn't one
        if image.mode != "RGB":
            image = image.convert("RGB")
        predictions = model.predict(image)
        predictions.sort(key=lambda x: x[1], reverse=True)
        label, confidence = predictions[0]
    except Exception as e:
        print(f"Problem predicting image: {e}")
    return label, confidence
