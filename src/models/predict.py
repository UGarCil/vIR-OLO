"""
predict.py - Model Inference Utilities for spectrAI

This module provides helper functions to load a YOLO model (Ultralytics) from a .pt file and run object detection predictions on images.

Key Features:
- Loads YOLO models from specified weight files (.pt)
- Runs inference on a given image path
- Returns the prediction results for further processing (e.g., extracting bounding boxes)

Notes:
- This module does not import or use OpenCV (cv2) directly, as the Ultralytics YOLO API handles image loading and processing internally.
- If you need to save or manipulate result images (e.g., using results[0].plot()), you may need to import cv2 in your own script.

Example usage:
	from predict import run_yolo_prediction
	result = run_yolo_prediction('path/to/model.pt', 'path/to/image.png')
	boxes = result.boxes
"""
import os
# from ultralytics import YOLO
from constants import config
import yaml



class PredictorManager:
	def __init__(self, yaml_file, pt_file):
		'''
		Manages loading YOLO models and running predictions in coordination with 
		the application state.
		'''
		self.yaml_file = yaml_file
		self.pt_file = pt_file
		self.indexes = self.map_indexes()
  
	def parse_yaml_labels(self):
		"""
		Parses the dataset.yaml file in config["CURRENT_MODEL_PATH"] and returns a list of label names in index order.
		"""
		if not os.path.isfile(self.yaml_file):
			raise FileNotFoundError(f"dataset.yaml not found in {self.yaml_file}")
		with open(self.yaml_file, "r") as f:
			data = yaml.safe_load(f)
		# 'names' can be a dict (index: name) or a list
		names = data.get("names", [])
		if isinstance(names, dict):
			# Convert dict to list in index order
			labels = [names[i] for i in sorted(names.keys(), key=int)]
		elif isinstance(names, list):
			labels = names
		else:
			labels = []
		return labels

	def map_indexes(self):	
		"""
		Returns a list of dictionaries mapping model label indices to user label indices.
		Each dict has keys: 'ORIGINAL_IDX' (int, model label index), 'MAPPED_IDX' (int, user label index).
		If user_labels is not provided, uses config["LABELS"].
		"""
		model_labels = self.parse_yaml_labels()
		user_labels = config.get("LABELS", [])

		mapping = []
		for idx, label in enumerate(model_labels):
			if label in user_labels:
				mapped_idx = user_labels.index(label)
			else:
				user_labels.append(label)
				mapped_idx = len(user_labels) - 1
			mapping.append({"ORIGINAL_IDX": idx, "MAPPED_IDX": mapped_idx, "LABEL": label})
		return mapping
	
	def get_indexes_mapping(self):
		"""
		Returns the list of index mapping dictionaries.
		Each dict has keys: 'ORIGINAL_IDX' (int, model label index), 'MAPPED_IDX' (int, user label index).
		"""
		return self.indexes

	def reformat_results(self, result):
		"""
		Converts a YOLO Results object into a list of dictionaries with pixel coordinates and class index.
		Each dictionary has keys: 'x', 'y', 'w', 'h', 'idx'.
		All values are in pixels, not normalized.
		"""
		boxes = []
		if hasattr(result, 'boxes') and result.boxes is not None:
			xywh = result.boxes.xywh.cpu().numpy()
			cls = result.boxes.cls.cpu().numpy().astype(int)
			for i in range(xywh.shape[0]):
				x_c, y_c, w, h = xywh[i]
				x = float(x_c - w / 2)
				y = float(y_c - h / 2)
				idx = int(cls[i])
				box = {"x": x, "y": y, "w": float(w), "h": float(h), "idx": idx}
				boxes.append(box)
		return boxes

	def __call__(self, image_path: str):
		"""
		Loads a YOLO model from model_path, runs prediction on image_path, and returns results[0].
		"""
		from ultralytics import YOLO
		model = YOLO(self.pt_file)
		results = model(image_path)
		formatted_results = self.reformat_results(results[0])
		return formatted_results

if __name__ == "__main__":
    
    # Example usage
    model_path = "C:\\Users\\Uriel\\Desktop\\spectrAI\\images\\models\\spectrai-IR-YOLO\\spectrai_ultralytics_ir.pt"
    image_path = "C:\\Users\\Uriel\\Desktop\\spectrAI\\images\\images\\train\\image_000000.png"
    config["CURRENT_MODEL_PATH"] = os.path.dirname(model_path)
    predictor = PredictorManager(model_path)
    result = predictor(model_path, image_path)
    print(result)
    # example output
    # [{'x': 285.2972717285156, 'y': 48.377777099609375, 'w': 15.4547119140625, 'h': 46.86598205566406, 'idx': 11}]