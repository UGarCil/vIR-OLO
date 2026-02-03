from huggingface_hub import hf_hub_url
import os, requests, hashlib
from pathlib import Path

class ModelManager():
    def __init__(self):
        self.models_root = ""
        self.model_paths = []
        # Store models as dictionaries with all needed information
        self.models_custom = [
            {
                'url': hf_hub_url(
                    repo_id="UrielGC/spectrai-IR-YOLO-10FG",
                    filename="spectrai_ultralytics_IR_10FG.pt",
                    revision="main"
                ),
                'repo_id': "UrielGC/spectrai-IR-YOLO-10FG",
                'filename': "spectrai_ultralytics_IR_10FG.pt"
            },
            {
                'url': hf_hub_url(
                    repo_id="UrielGC/spectrai-IR-YOLO-12FG",
                    filename="spectrai_ultralytics_IR_12FG.pt",
                    revision="main"
                ),
                'repo_id': "UrielGC/spectrai-IR-YOLO-12FG",
                'filename': "spectrai_ultralytics_IR_12FG.pt"
            },
            
        ]
        


    def download_default_models(self, dest: str | Path, expected_sha256: str | None = None):
        """Downloads both ultralytics and custom models to separate folders"""
        # Convert string to Path if needed
        dest = Path(dest)
        
        # Create models folder
        models_dir = dest / "models"
        models_dir.mkdir(exist_ok=True)
        
        
        # Download each model
        for model in self.models_custom:
            # Create repo-specific folder
            repo_name = model['repo_id'].split('/')[-1]
            model_dir = models_dir / repo_name
            model_dir.mkdir(exist_ok=True)
            
            # Set full path for the model file
            model_path = model_dir / model['filename']
            
            # Check if file already exists
            if model_path.exists():
                print(f"Model {model['filename']} already exists in {model_dir}. Skipping download.")
                continue
            
            # Download the model
            headers = {}
            with requests.get(model['url'], stream=True, headers=headers, timeout=60) as r:
                r.raise_for_status()
                sha = hashlib.sha256()
                with open(model_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            f.write(chunk)
                            sha.update(chunk)
                            
            if expected_sha256 and sha.hexdigest() != expected_sha256:
                raise ValueError(f"Checksum mismatch for {model['filename']}")
            _model_details = {"name": model['filename'], "path": str(model_path)}
            self.model_paths.append(_model_details)

            # Download dataset.yaml
            yaml_url = hf_hub_url(repo_id=model['repo_id'], filename="dataset.yaml", revision="main")
            yaml_path = model_dir / "dataset.yaml"
            if not yaml_path.exists():
                with requests.get(yaml_url, stream=True, timeout=60) as r:
                    r.raise_for_status()
                    with open(yaml_path, "wb") as f:
                        for chunk in r.iter_content(chunk_size=1024 * 1024):
                            if chunk:
                                f.write(chunk)
        
        return 1 #return success