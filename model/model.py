"""
load our TF saved model
"""
import os
import json
import tensorflow as tf
from PIL import Image
import numpy as np


class ImageClassification(object):
    def __init__(self, model_dir):
        # make sure our exported SavedModel folder exists
        model_path = os.path.realpath(model_dir)
        if not os.path.exists(model_path):
            raise ValueError(f"Exported model folder doesn't exist {model_dir}")
        self.model_path = model_path

        # load our signature json file, this shows us the model inputs and outputs
        # you should open this file and take a look at the inputs/outputs to see their data types, shapes, and names
        with open(os.path.join(model_path, "signature.json"), "r") as f:
            self.signature = json.load(f)
        self.inputs = self.signature.get("inputs")
        self.outputs = self.signature.get("outputs")

        # placeholder for the tensorflow session
        self.session = None

    def load(self):
        self.cleanup()
        # create a new tensorflow session
        self.session = tf.compat.v1.Session(graph=tf.Graph())
        # load our model into the session
        tf.compat.v1.saved_model.loader.load(sess=self.session, tags=self.signature.get("tags"), export_dir=self.model_path)

    def predict(self, image: Image.Image):
        if self.session is None:
            self.load()
        width, height = image.size
        # center crop image
        if width != height:
            size = min(width, height)
            left = (width - size) / 2
            top = (height - size) / 2
            right = (width + size) / 2
            bottom = (height + size) / 2
            # Crop the center of the image
            image = image.crop((left, top, right, bottom))
        # resize image
        input_width = self.inputs["Image"]["shape"][1]
        input_height = self.inputs["Image"]["shape"][2]
        if image.width != input_width or image.height != input_height:
            image = image.resize((input_width, input_height))
        # make 0-1
        image = np.asarray(image) / 255.
        # create the feed dictionary that is the input to the model
        # first, add our image to the dictionary (comes from our signature.json file)
        feed_dict = {self.inputs["Image"]["name"]: [image]}
        # second, add batch size of 1 to the dictionary since we are only passing in an array of 1 image
        feed_dict["batch_size:0"] = 1

        # list the outputs we want from the model -- these come from our signature.json file
        fetches = [self.outputs["Labels_idx_000"]["name"], self.outputs["Labels_idx_001"]["name"]]

        # run the model! there will be as many outputs from session.run as you have in the fetches list
        labels, confidences = self.session.run(fetches=fetches, feed_dict=feed_dict)
        return list(zip([label.decode('utf-8') for label in labels[0].tolist()], confidences[0].tolist()))

    def cleanup(self):
        # close our tensorflow session if one exists
        if self.session is not None:
            self.session.close()
            self.session = None

    def __del__(self):
        self.cleanup()
