''' The main integration of GUI with the utilities and auxiliary files needed to run spectrAI'''

import sys
from ui.main_ui import Ui_MainWindow
from ui.canvas_widget import CanvasWidget
from ui.label_editor_dialog import LabelEditorDialog
from ui.label_new_dialog import LabelNewDialog
from tools.image_loader import ImageManager
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QLabel, QMainWindow, QPushButton, QColorDialog, QMessageBox, QShortcut, QHBoxLayout
from PyQt5 import QtGui, QtCore
from constants import *
from tools.donwload_default_models import ModelManager
import os
import json
import yaml
import shutil
import time
# from ultralytics import YOLO
from models.predict import PredictorManager

QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.setWindowTitle("vIR-OLO v.1.0.0")
        # Set default value for CurrentModelLabel
        self.ui.CurrentModelLabel.setText("")

        # swap the static QLabel for the interactive CanvasWidget
        self.canvas = CanvasWidget(self.ui.widget_5)
        self.canvas.setObjectName("spectroPanel")
        self.canvas.setMinimumSize(self.ui.spectroPanel.minimumSize())
        self.canvas.setMaximumSize(self.ui.spectroPanel.maximumSize())
        self.canvas.setStyleSheet(self.ui.spectroPanel.styleSheet())
        self.ui.horizontalLayout_12.replaceWidget(self.ui.spectroPanel, self.canvas)
        self.ui.spectroPanel.deleteLater()
        self.ui.spectroPanel = self.canvas
        # Add a resize timer to prevent too frequent updates
        self.resize_timer = QtCore.QTimer()
        self.resize_timer.setSingleShot(True)
        self.resize_timer.timeout.connect(self.handle_delayed_resize)
        # setup the File Menu actions and buttons
        self.ui.actionNew.triggered.connect(self.create_new_project)
        self.ui.actionLoad.triggered.connect(self.load_existing_project)
        self.shortcut_new = QShortcut(QtGui.QKeySequence("Ctrl+N"), self)
        self.shortcut_new.activated.connect(self.create_new_project)
        self.shortcut_load = QShortcut(QtGui.QKeySequence("Ctrl+L"), self)
        self.shortcut_load.activated.connect(self.load_existing_project)
        self.ui.actionDownloadDefaultModels.triggered.connect(self.wrapper_default_downloader)
        # connect buttons to specific functions
        self.ui.openBtn.clicked.connect(self.open_images_folder)
        self.ui.prevBtn.clicked.connect(lambda: self.navigate_image('-'))
        self.ui.nextBtn.clicked.connect(lambda: self.navigate_image('+'))
        self.ui.editBtn.setCheckable(True)
        self.ui.editBtn.setChecked(False)
        self.ui.editBtn.toggled.connect(self.on_edit_mode_toggled)
        
        # Setup trash button (ERASE mode) - checkable toggle
        self.ui.trashBtn.setCheckable(True)
        self.ui.trashBtn.setChecked(False)
        self.ui.trashBtn.toggled.connect(self.on_erase_mode_toggled)
        
        # Setup update button (UPDATE mode) - checkable toggle
        self.ui.updateBoxLabelBtn.setCheckable(True)
        self.ui.updateBoxLabelBtn.setChecked(False)
        self.ui.updateBoxLabelBtn.toggled.connect(self.on_update_mode_toggled)
        
        # Mode buttons dictionary for centralized mode switching
        self.mode_buttons = {
            "BOX": self.ui.editBtn,
            "ERASE": self.ui.trashBtn,
            "UPDATE": self.ui.updateBoxLabelBtn
        }
        # preload the predictor manager
        self.predictor_manager = None
        
        # preload the image manager
        self.image_manager = None
        self.model_manager = ModelManager()
        
        # Store edit icon for later use
        self.icon_editLabel = QtGui.QIcon()
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui", "icons", "editLabel_icon.png")
        self.icon_editLabel.addPixmap(QtGui.QPixmap(icon_path), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        
        # initialize mode to BOX and cursor to crosshair for drawing
        self.on_edit_mode_toggled(True)

        self.ui.addBtn.clicked.connect(self.on_add_label_clicked)
        self.ui.GoBtn.clicked.connect(self.on_go_btn_clicked)
        self.ui.ImageGoLineEd.returnPressed.connect(self.on_go_btn_clicked)
        self.ui.actionLoadModel.triggered.connect(self.on_load_model_clicked)

        # Connect predictBtn to prediction handler
        self.ui.predictBtn.clicked.connect(self.on_click_predict)
    
    def update_statusLabel(self, message: str):
        """
        Update the status label in the UI and the config dictionary.
        
        Args:
            message (str): The new status message to set.
        """
        self.ui.StatusLabel.setText(message)
        # update_status(message)
        
    def closeEvent(self, event):
        """
        Called when the window is closing.
        Save current annotations before exiting.
        """
        self.save_current_annotations()
        event.accept()  # Accept the close event to proceed with closing

    def on_load_model_clicked(self):
        from PyQt5.QtWidgets import QFileDialog, QMessageBox
        folder = QFileDialog.getExistingDirectory(self, "Select Model Folder")
        if not folder:
            return  # User cancelled

        if config.get("PROJECT_LOADED", False) is False:
            QMessageBox.warning(self, "No Project Loaded", "Please load or create a project before loading a model.")
            return
        
        pt_files = [f for f in os.listdir(folder) if f.endswith('.pt')]
        yaml_file = os.path.join(folder, "dataset.yaml")

        if pt_files and os.path.isfile(yaml_file):
            # Show warning dialog before merging labels
            reply = QMessageBox.warning(
                self,
                "Warning: You're about to merge two workspaces",
                "The action you're about to take will bring a new set of labels to your workspace, and the labels from the loaded model will be appended to your dataset.yaml file.\n\nThis action cannot be undone. Do you wish to proceed?\n\nIf your project already contains annotations you may want to consider creating a new project if you don't want your labels to be combined.",
                QMessageBox.Ok | QMessageBox.Cancel
            )
            if reply != QMessageBox.Ok:
                return
            
            print("Model successfully loaded")
            config["CURRENT_MODEL_PATH"] = folder
            # initialize a predictormanager to parse labels
            pt_file = os.path.join(folder, pt_files[0])
            self.predictor_manager = PredictorManager(yaml_file, pt_file)
            
            self.set_current_model_label() # update the label in the UI to know which model we're using
            # Update the merged labels into UI and saved them into project's yaml
            self.update_label_buttons()
            self.save_labels_to_yaml()
            
            
        else:
            QMessageBox.warning(self, "Missing Files", "Both a .pt model file and dataset.yaml must be present in the selected folder.")


    def on_click_predict(self):
        """
        Handler for predictBtn. Checks if CURRENT_MODEL_PATH exists and contains a .pt file.
        """
        from PyQt5.QtWidgets import QMessageBox
        model_dir = config.get("CURRENT_MODEL_PATH", "")
        if not model_dir or not os.path.isdir(model_dir):
            QMessageBox.warning(self, "Prediction Error", "No model directory set. Please load a model first.")
            return
        pt_files = [f for f in os.listdir(model_dir) if f.endswith('.pt')]
        if not pt_files:
            QMessageBox.warning(self, "Prediction Error", "No .pt model file found in the selected model directory.")
            return
        
        self.statusBar().showMessage("Making a prediction...")
        # pass the model (.pt) path and the current image path to the predictor manager
        results = self.predictor_manager(self.image_manager.get_current_image_path())
        if len(results) == 0:
            self.statusBar().showMessage("No predictions were made for the current image.", 3000)
            return
        else:
            self.statusBar().showMessage(f"Prediction completed with {len(results)} results.", 3000)
        # iterate over the results and create instances of bounding boxes
        self.ui.spectroPanel.box_manager.instantiate_from_predictions(results) 
        self.ui.spectroPanel.update()
    
    def set_current_model_label(self):
        """
        Helper to set the CurrentModelLabel text to the folder name of CURRENT_MODEL_PATH.
        If not set, defaults to "".
        """
        model_path = config.get("CURRENT_MODEL_PATH", "")
        if model_path:
            folder_name = os.path.basename(os.path.normpath(model_path))
            self.ui.CurrentModelLabel.setText(folder_name)
        else:
            self.ui.CurrentModelLabel.setText("")
    
    def wrapper_default_downloader(self):
        """Wrapper method to handle the download of default models"""
        if config.get("PROJECT_LOADED", False):
            root_path = config.get("ROOT")
            if root_path:
                # show a message in the statusbar
                self.statusBar().showMessage("Downloading model, please wait...")
                # force the status bar to update
                QApplication.processEvents()

                success = self.model_manager.download_default_models(root_path)
                if success:
                    QMessageBox.information(self, "Download Model", "Default model downloaded successfully!")
                    self.statusBar().clearMessage()
                    
                    # Read existing config
                    json_file_path = os.path.join(config["ROOT"], "config.json")
                    with open(json_file_path, "r") as json_file:
                        config_data = json.load(json_file)
                    
                    # Update with model paths
                    config_data["MODEL_PATHS"] = self.model_manager.model_paths
                    
                    # Write back the complete config if models were downloaded
                    if len(self.model_manager.model_paths) > 0:
                        with open(json_file_path, "w") as json_file:
                            json.dump(config_data, json_file, indent=2)
                    
            else:
                QMessageBox.warning(self, "Download Models", "Project root path not set!")
        else:
            QMessageBox.warning(self, "Download Models", "Please load or create a project first!")
            
    def resizeEvent(self, event):
        """Override the resize event to handle window resizing"""
        super().resizeEvent(event)
        # Start or restart the timer
        self.resize_timer.start(150)  # 150ms delay

    def handle_delayed_resize(self):
        """Handle the resize event after a short delay to prevent excessive updates"""
        if self.image_manager and self.image_manager.current_image:
            self.image_manager.render(self.ui.spectroPanel)
        
    def initialize_image_manager(self):
        '''
        Initialize the ImageManager and pass the paths from the config dictionary: 
        IMAGES_PATH and ANNOTATIONS_PATH
        '''
        self.image_manager = ImageManager(images_path=config.get("IMAGES_PATH", ""),
                                          annotations_path=config.get("ANNOTATIONS_PATH", ""))
        self.image_manager.render(self.ui.spectroPanel)
        if hasattr(self.ui.spectroPanel, "set_image_manager"):
            self.ui.spectroPanel.set_image_manager(self.image_manager)
        print("attempted render of image")
        
    def open_images_folder(self):
        '''
        When button pressed, open the folder specified in the config["IMAGES_PATH"]
        '''
        images_path = config.get("IMAGES_PATH", "")
        if images_path:
            os.startfile(images_path)
        else:
            QMessageBox.warning(self, "Open Images Folder", "Images folder path is not set. Create or load a new project first!")
    
    def update_canvas_labels(self):
        '''
        Update the canvas widget with current labels from config["LABELS"].
        Should be called after loading labels from dataset.yaml.
        '''
        if hasattr(self.ui, 'spectroPanel') and hasattr(self.ui.spectroPanel, 'set_labels'):
            labels = config.get("LABELS", [])
            self.ui.spectroPanel.set_labels(labels)
            print(f"Canvas labels updated with {len(labels)} labels")
    
    def get_labels_from_yaml(self, project_folder):
        '''
        Read the dataset.yaml file and extract labels, storing them in config["LABELS"]
        '''
        dataset_yaml_path = os.path.join(project_folder, "dataset.yaml")
        
        if os.path.exists(dataset_yaml_path):
            try:
                with open(dataset_yaml_path, 'r') as file:
                    dataset_config = yaml.safe_load(file)
                
                # Extract names and convert to ordered list
                names_dict = dataset_config.get('names', {})
                
                # Sort by index and extract labels
                sorted_labels = []
                for i in sorted(names_dict.keys()):
                    sorted_labels.append(names_dict[i])
                
                config["LABELS"] = sorted_labels
                return True
                
            except Exception as e:
                QMessageBox.warning(self, "Load Labels", f"Error reading dataset.yaml: {str(e)}")
                return False
        else:
            QMessageBox.warning(self, "Load Labels", "dataset.yaml file not found in project folder.")
            return False
    
    def update_label_buttons(self):
        '''
        Update the label buttons in the UI based on config["LABELS"]
        '''
        if "LABELS" not in config or not config["LABELS"]:
            return
        
        # Clear existing layouts in the scroll area
        scroll_widget = self.ui.scrollAreaWidgetContents
        layout = scroll_widget.layout()
        
        # Remove all existing widgets from the layout
        if layout:
            while layout.count():
                child = layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
                elif child.layout():
                    self.clear_layout(child.layout())
        
        # Create new button groups for each label
        for i, label_name in enumerate(config["LABELS"]):
            # Create horizontal layout for this label
            label_layout = QHBoxLayout()
            label_layout.setObjectName(f"label{i+1}_Layout")
            
            # Create main label button
            label_button = QPushButton(scroll_widget)
            label_button.setMinimumSize(QtCore.QSize(0, 30))
            font = QtGui.QFont()
            font.setFamily("Oswald")
            label_button.setFont(font)
            label_button.setText(label_name)
            label_button.setObjectName(f"labelButton_{i}")
            label_button.setCheckable(True)
            label_button.clicked.connect(lambda checked, idx=i: self.on_label_button_clicked(idx))
            label_layout.addWidget(label_button)
            
            # Create edit button
            edit_button = QPushButton(scroll_widget)
            edit_button.setMinimumSize(QtCore.QSize(0, 30))
            edit_button.setStyleSheet("background-color: rgb(178, 188, 178);")
            edit_button.setText("")
            edit_button.setIcon(self.icon_editLabel)
            edit_button.setObjectName(f"editButton_{i}")
            # Connect edit button - pass the label_button reference directly
            edit_button.clicked.connect(lambda checked, btn=label_button, idx=i: self.on_edit_label_clicked(btn,idx))
            label_layout.addWidget(edit_button)
            
            # Set stretch to make label button take more space
            label_layout.setStretch(0, 1)
            
            # Add layout to the main vertical layout
            layout.addLayout(label_layout)
        
        # Select first label by default
        if config["LABELS"]:
            self.on_label_button_clicked(0)
    
    def on_label_button_clicked(self, index: int):
        '''
        Handle label button click to set the current active label.
        
        Updates config["CURRENT_LABEL"] and provides visual feedback
        by checking only the selected button.
        
        Args:
            index (int): The index of the clicked label in config["LABELS"]
        '''
        config["CURRENT_LABEL"] = index
        
        # Update visual feedback - uncheck all, check only selected
        scroll_widget = self.ui.scrollAreaWidgetContents
        layout = scroll_widget.layout()
        
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item.layout():  # It's a horizontal layout containing the buttons
                h_layout = item.layout()
                for j in range(h_layout.count()):
                    widget = h_layout.itemAt(j).widget()
                    if widget and widget.objectName().startswith("labelButton_"):
                        btn_index = int(widget.objectName().split("_")[1])
                        widget.setChecked(btn_index == index)
        
        print(f"Current label set to: {index} ({config['LABELS'][index]})")
    
    def on_edit_label_clicked(self, label_button: QPushButton, idx: int):
        '''
        Open the label editor dialog for editing or deleting a label.
        
        Args:
            label_button (QPushButton): The label button to edit
            idx (int): The index of the label in config["LABELS"]
        '''
        dialog = LabelEditorDialog(label_button, idx, self)
        dialog.exec_()
        
        result = dialog.get_result()
        
        if result == "accept":
            # Button text was already updated by the dialog
            # Sync config["LABELS"] with the new name
            new_name = label_button.text()
            config["LABELS"][idx] = new_name
            self.save_labels_to_yaml()
            print(f"Label updated: config['LABELS'][{idx}] = '{new_name}'")
            
        elif result == "delete":
            self.delete_label(idx)

    def delete_label(self, idx: int):
        '''
        Delete a label at the given index.
        Prevents deletion if only one label remains.
        '''
        if len(config["LABELS"]) <= 1:
            QMessageBox.warning(
                self,
                "Cannot Delete Label",
                "At least one label must remain in the project.\nAdd another label before deleting this one."
            )
            return
        
        if idx < 0 or idx >= len(config["LABELS"]):
            return
        
        deleted_name = config["LABELS"][idx]
        
        # Update all annotation files BEFORE removing from config
        removed_count, shifted_count = self.update_annotations_after_label_delete(idx)
        
        # Remove from config
        config["LABELS"].pop(idx)
        
        # Update CURRENT_LABEL if needed
        if len(config["LABELS"]) == 0:
            config["CURRENT_LABEL"] = 0
        elif config["CURRENT_LABEL"] >= len(config["LABELS"]):
            config["CURRENT_LABEL"] = len(config["LABELS"]) - 1
        
        # Rebuild UI (indices changed after deletion)
        self.update_label_buttons()
        
        # Save to yaml
        self.save_labels_to_yaml()
        
        # Reload annotations for current image to reflect changes
        self.ui.spectroPanel.box_manager.clear()
        self.load_annotations_for_current_image()
        self.ui.spectroPanel.update()
        
        # Inform user
        QMessageBox.information(
            self,
            "Label Deleted",
            f"Label '{deleted_name}' (index {idx}) deleted.\n\n"
            f"Annotations updated:\n"
            f"  - {removed_count} boxes removed\n"
            f"  - {shifted_count} boxes had their label index shifted"
        )
        
        print(f"Label '{deleted_name}' (index {idx}) deleted")

    def update_annotations_after_label_delete(self, deleted_idx: int) -> tuple:
        '''
        Update all annotation files after a label is deleted.
        
        For each .txt file in config["ANNOTATIONS_PATH"]:
        - Remove lines where label_id == deleted_idx
        - Decrement label_id for lines where label_id > deleted_idx
        
        Args:
            deleted_idx (int): The index of the label being deleted
        
        Returns:
            tuple: (removed_count, shifted_count) - number of boxes removed and shifted
        '''
        annotations_path = config.get("ANNOTATIONS_PATH", "")
        if not annotations_path or not os.path.exists(annotations_path):
            print("Warning: Annotations path not set or doesn't exist")
            return (0, 0)
        
        total_removed = 0
        total_shifted = 0
        
        # Iterate through all .txt files in the annotations folder
        for filename in os.listdir(annotations_path):
            if not filename.endswith(".txt"):
                continue
            
            filepath = os.path.join(annotations_path, filename)
            removed, shifted = self.update_single_annotation_file(filepath, deleted_idx)
            total_removed += removed
            total_shifted += shifted
        
        print(f"Annotation update complete: {total_removed} removed, {total_shifted} shifted")
        return (total_removed, total_shifted)

    def update_single_annotation_file(self, filepath: str, deleted_idx: int) -> tuple:
        '''
        Update a single annotation file after a label is deleted.
        
        - Removes lines where label_id == deleted_idx
        - Decrements label_id for lines where label_id > deleted_idx
        
        Args:
            filepath (str): Path to the annotation .txt file
            deleted_idx (int): The index of the label being deleted
        
        Returns:
            tuple: (removed_count, shifted_count) for this file
        '''
        removed_count = 0
        shifted_count = 0
        updated_lines = []
        
        try:
            with open(filepath, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    parts = line.split()
                    if len(parts) >= 5:
                        try:
                            label_id = int(parts[0])
                            
                            if label_id == deleted_idx:
                                # Remove this annotation
                                removed_count += 1
                                continue
                            elif label_id > deleted_idx:
                                # Shift index down by 1
                                parts[0] = str(label_id - 1)
                                shifted_count += 1
                            
                            # Keep this line (possibly modified)
                            updated_lines.append("\t".join(parts))
                        except ValueError:
                            # Keep malformed lines as-is
                            updated_lines.append(line)
                    else:
                        # Keep malformed lines as-is
                        updated_lines.append(line)
            
            # Write back the updated content
            with open(filepath, 'w') as f:
                for line in updated_lines:
                    f.write(line + "\n")
                    
        except Exception as e:
            print(f"Error updating annotation file {filepath}: {e}")
        
        return (removed_count, shifted_count)

    def save_labels_to_yaml(self):
        '''
        Save the current labels in config["LABELS"] to the dataset.yaml file.
        
        Returns:
            bool: True if saved successfully, False otherwise
        '''
        if not config.get("ROOT"):
            print("Warning: No project root set, cannot save labels")
            return False
        
        dataset_yaml_path = os.path.join(config["ROOT"], "dataset.yaml")
        
        try:
            # Read existing config
            with open(dataset_yaml_path, 'r') as file:
                dataset_config = yaml.safe_load(file)
            
            # Update names with current labels
            names_dict = {i: name for i, name in enumerate(config["LABELS"])}
            dataset_config['names'] = names_dict
            dataset_config['nc'] = len(config["LABELS"])
            
            # Write back
            with open(dataset_yaml_path, 'w') as file:
                yaml.dump(dataset_config, file, default_flow_style=False, sort_keys=False)
            
            # print(f"Labels saved to: {dataset_yaml_path}")
            return True
            
        except Exception as e:
            print(f"Error saving labels to YAML: {e}")
            QMessageBox.warning(self, "Save Labels", f"Error saving labels: {str(e)}")
            return False
    
    def clear_layout(self, layout):
        '''
        Helper method to recursively clear a layout
        '''
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                self.clear_layout(child.layout())
                
    def load_existing_project(self):
        '''
        Open the File Manager to select a folder that already contains a configuration file.
        If the configuration file is found, load it and store the path to the images in the constants.config dictionary
        Otherwise show a warning message to the user, suggesting to create a new project because config file wasn't found
        '''
        folder_path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Project Folder")
        if folder_path:
            # check if config file exists in the selected folder
            json_file_path = os.path.join(folder_path, "config.json")
            
            if os.path.exists(json_file_path):
                with open(json_file_path, "r") as json_file:
                    config_data = json.load(json_file)
                    config["IMAGES_PATH"] = config_data.get("IMAGES_PATH", "")
                    config["ANNOTATIONS_PATH"] = config_data.get("ANNOTATIONS_PATH", "")
                    config["ROOT"] = config_data.get("ROOT", "")
                    self.model_manager.model_paths = config_data.get("MODEL_PATHS", [])
                    # if both images path and annotation path are found, show success message
                    if config["IMAGES_PATH"] and config["ANNOTATIONS_PATH"]:
                        # Load labels from dataset.yaml and update buttons
                        if self.get_labels_from_yaml(folder_path):
                            self.update_label_buttons()
                            self.update_canvas_labels()
                        
                        QMessageBox.information(self, "Load Project", f"Project loaded successfully!\nImages Path: {config['IMAGES_PATH']}\nAnnotations Path: {config['ANNOTATIONS_PATH']}")
                    else:
                        QMessageBox.warning(self, "Load Project", "Configuration file is missing required paths. Please create a new project.")
                        return
                    config["PROJECT_LOADED"] = True
                    # # if models paths are found, call the list_models_in_dropdown function
                    # if self.model_manager.model_paths:
                    #     self.list_models_in_dropdown()
                    # Initialize the image manager with the loaded paths
                    self.initialize_image_manager()
                    # Load annotations for the first image
                    self.load_annotations_for_current_image()
            else:
                QMessageBox.warning(self, "Load Project", "No configuration file found. Please create a new project.")

    def create_new_project(self):
        '''
        Open the File manager to select a folder.
        The location of the folder will be stored by the constants.config dictionary
        All the images found in the folder will be moved into a new subfolder called "images"
        A new subfolder next to the "images" folder will be created called "annotations"
        A new .json file will be created that will be found and loaded when the sibling to this
        function load_new_project() is called
        '''
        folder_path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Project Folder")
        success = False
        if folder_path:
            # Create YOLO dataset structure
            # Create main directories
            images_folder = os.path.join(folder_path, "images")
            labels_folder = os.path.join(folder_path, "labels")
            
            # Check if directories already exist
            if os.path.exists(images_folder) or os.path.exists(labels_folder):
                QMessageBox.warning(self, "New Project", f"The project structure already exists in this folder. Please choose another location or delete the existing folders.")
                return
            
            # Create images subdirectories
            images_train_folder = os.path.join(images_folder, "train")
            images_val_folder = os.path.join(images_folder, "val")
            os.makedirs(images_train_folder, exist_ok=True)
            os.makedirs(images_val_folder, exist_ok=True)
            
            # Create labels subdirectories
            labels_train_folder = os.path.join(labels_folder, "train")
            labels_val_folder = os.path.join(labels_folder, "val")
            os.makedirs(labels_train_folder, exist_ok=True)
            os.makedirs(labels_val_folder, exist_ok=True)
            
            # Move all images from the selected folder to the train subfolder
            for file_name in os.listdir(folder_path):
                if file_name.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif')):
                    source = os.path.join(folder_path, file_name)
                    destination = os.path.join(images_train_folder, file_name)
                    os.rename(source, destination)
            
            # Set config paths to the train folders
            config["IMAGES_PATH"] = images_train_folder
            config["ANNOTATIONS_PATH"] = labels_train_folder
            config["ROOT"] = folder_path
            # Create a new .json file
            json_file_path = os.path.join(folder_path, "config.json")
            with open(json_file_path, "w") as json_file:
                # save the location of the images and labels train folders
                json.dump({
                    "IMAGES_PATH": images_train_folder, 
                    "ANNOTATIONS_PATH": labels_train_folder,
                    "ROOT": folder_path,
                }, json_file, indent=2)
            
            # Create a copy of dataset.yaml, found next to this script in the src folder
            import shutil
            import yaml
            
            # Get the path to the source dataset.yaml file
            src_dir = os.path.dirname(os.path.abspath(__file__))
            source_dataset_yaml = os.path.join(src_dir, "dataset.yaml")
            
            if os.path.exists(source_dataset_yaml):
                # Read the original dataset.yaml
                with open(source_dataset_yaml, 'r') as file:
                    dataset_config = yaml.safe_load(file)
                
                # Update the path to point to the new project folder
                dataset_config['path'] = folder_path
                
                # Create the destination dataset.yaml file
                dest_dataset_yaml = os.path.join(folder_path, "dataset.yaml")
                with open(dest_dataset_yaml, 'w') as file:
                    yaml.dump(dataset_config, file, default_flow_style=False, sort_keys=False)
                
                # Load labels from the created dataset.yaml and update buttons
                if self.get_labels_from_yaml(folder_path):
                    self.update_label_buttons()
                    self.update_canvas_labels()
                
            success = True
        # Let the user know the process is done with success
        if success:
            QMessageBox.information(self, "New Project", f"New project created at: {folder_path}")
            config["PROJECT_LOADED"] = True
            self.initialize_image_manager()
        else:
            QMessageBox.warning(self, "New Project", "No folder selected. Project creation cancelled.")
    
    def navigate_image(self, direction: str):
        '''
        Navigate to previous or next image with proper canvas reset.
        
        Saves current annotations, resets any in-progress drawing and clears 
        existing boxes before changing to the new image. Used by both buttons 
        and keyboard shortcuts.
        
        Args:
            direction (str): '+' for next image, '-' for previous image
        '''
        if config.get("PROJECT_LOADED", False):
            self.save_current_annotations()
            self.ui.spectroPanel.reset_for_new_image()
            self.change_image(direction)

    def save_current_annotations(self):
        '''
        Save current bounding box annotations to a YOLO format .txt file.
        
        Converts all boxes to YOLO format:
            label_id  x_center  y_center  width  height
        
        Where x_center, y_center, width, height are normalized (0.0-1.0)
        relative to the original image dimensions.
        
        The file is saved to config["ANNOTATIONS_PATH"] with the same
        base name as the current image.
        
        Note: If no boxes exist, the file is not created/overwritten to
        preserve any existing annotations.
        
        Returns:
            bool: True if saved successfully, False otherwise
        '''
        # Check if we have an image loaded
        if not self.image_manager or not self.image_manager.current_image:
            return False
        
        # Get all boxes - skip saving if empty to avoid overwriting existing annotations
        boxes = self.ui.spectroPanel.box_manager.get_all_boxes()
        # if not boxes:
        #     print("No annotations to save, skipping to preserve existing file")
        #     return False
        
        # Get image dimensions for normalization
        img_width = self.image_manager.original_width
        img_height = self.image_manager.original_height
        
        if img_width <= 0 or img_height <= 0:
            print("Warning: Invalid image dimensions, cannot save annotations")
            return False
        
        # Get the current image filename and create annotation filename
        current_image_path = self.image_manager.current_image
        image_basename = os.path.basename(current_image_path)
        annotation_basename = os.path.splitext(image_basename)[0] + ".txt"
        annotation_path = os.path.join(config["ANNOTATIONS_PATH"], annotation_basename)
        
        # Convert boxes to YOLO format and write to file
        with open(annotation_path, 'w') as f:
            for box in boxes:
                # Calculate normalized center coordinates
                x_center = (box.x + box.width / 2) / img_width
                y_center = (box.y + box.height / 2) / img_height
                
                # Calculate normalized width and height
                norm_width = box.width / img_width
                norm_height = box.height / img_height
                
                # Write in YOLO format: label_id x_center y_center width height
                f.write(f"{box.label_id}\t{x_center:.6f}\t{y_center:.6f}\t{norm_width:.6f}\t{norm_height:.6f}\n")
        
        # print(f"Saved {len(boxes)} annotations to: {annotation_path}")
        return True

    def load_annotations_for_current_image(self):
        '''
        Load existing annotations from a YOLO format .txt file for the current image.
        
        Reads the annotation file matching the current image name from
        config["ANNOTATIONS_PATH"], parses each line, and adds boxes
        to the box_manager.
        
        Returns:
            bool: True if annotations were loaded, False otherwise
        '''
        # Check if we have an image loaded
        if not self.image_manager or not self.image_manager.current_image:
            return False
        
        # Get image dimensions for denormalization
        img_width = self.image_manager.original_width
        img_height = self.image_manager.original_height
        
        if img_width <= 0 or img_height <= 0:
            print("Warning: Invalid image dimensions, cannot load annotations")
            return False
        
        # Get the current image filename and find matching annotation file
        current_image_path = self.image_manager.current_image
        image_basename = os.path.basename(current_image_path)
        annotation_basename = os.path.splitext(image_basename)[0] + ".txt"
        annotation_path = os.path.join(config["ANNOTATIONS_PATH"], annotation_basename)
        
        # Check if annotation file exists
        if not os.path.exists(annotation_path):
            print(f"No annotation file found: {annotation_path}")
            return False
        
        # Read and parse the annotation file
        boxes_loaded = 0
        with open(annotation_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                # Parse YOLO format: label_id x_center y_center width height
                parts = line.split()
                if len(parts) >= 5:
                    try:
                        label_id = int(parts[0])
                        x_center = float(parts[1])
                        y_center = float(parts[2])
                        norm_width = float(parts[3])
                        norm_height = float(parts[4])
                        
                        # Add box using box_manager helper
                        self.ui.spectroPanel.box_manager.add_box_from_yolo(
                            label_id=label_id,
                            x_center=x_center,
                            y_center=y_center,
                            norm_width=norm_width,
                            norm_height=norm_height,
                            img_width=img_width,
                            img_height=img_height
                        )
                        boxes_loaded += 1
                    except ValueError as e:
                        print(f"Warning: Could not parse annotation line: {line} - {e}")
                        continue
        
        if boxes_loaded > 0:
            # print(f"Loaded {boxes_loaded} annotations from: {annotation_path}")
            self.ui.spectroPanel.update()
        
        return boxes_loaded > 0

    def change_image(self, sign: str = '+'):
        '''
        Load the previous or next image in the list.
        
        Note: For user-facing navigation, use navigate_image() instead
        which handles canvas reset.
        
        Args:
            sign (str): '+' for next image, '-' for previous image
        '''
        if config["PROJECT_LOADED"]:
            # update the index and call render again
            if sign == '+':
                self.image_manager.next_image()
            else:
                self.image_manager.previous_image()
            self.image_manager.render(self.ui.spectroPanel)
            # Load annotations for the new image
            self.load_annotations_for_current_image()
            self.update_image_index_display()
            # Show current image name in status bar
            current_image_path = self.image_manager.get_current_image_path()
            image_name = os.path.basename(current_image_path)
            self.statusBar().showMessage(f"Current image: {image_name}", 15000)
    
    def update_image_index_display(self):
        """Show the current image index in the ImageGoLineEd field."""
        if self.image_manager:
            self.ui.ImageGoLineEd.setText(str(self.image_manager.current_index))

    def go_to_image(self, idx: int):
        """Navigate to a specific image index, saving and clearing as needed."""
        if not config.get("PROJECT_LOADED", False):
            return
        self.save_current_annotations()
        self.ui.spectroPanel.reset_for_new_image()
        self.image_manager.current_index = idx
        self.image_manager.render(self.ui.spectroPanel)
        self.load_annotations_for_current_image()
        config["CURRENT_IMAGE"] = idx
        self.update_image_index_display()


    def _set_button_checked_silent(self, button, checked: bool):
        '''
        Set a button's checked state without triggering its toggled signal.
        
        This is useful for maintaining mutual exclusivity between toggle buttons
        without causing recursive signal emissions.
        
        Args:
            button: The QPushButton (or similar checkable widget) to modify
            checked (bool): The desired checked state
        '''
        button.blockSignals(True)
        button.setChecked(checked)
        button.blockSignals(False)

    def _set_mode(self, mode: str):
        '''
        Centralized mode switching method.
        
        Sets the application mode and ensures mutual exclusivity between mode buttons.
        Handles cleanup of in-progress states and resets box statuses.
        
        Args:
            mode (str): The mode to switch to ("BOX", "ERASE", "UPDATE")
        '''
        config["MODE"] = mode
        
        # Uncheck all other mode buttons (mutual exclusivity)
        for btn_mode, button in self.mode_buttons.items():
            if btn_mode != mode:
                self._set_button_checked_silent(button, False)
        
        # Cancel any in-progress box drawing
        if self.ui.spectroPanel.is_box_started:
            self.ui.spectroPanel.is_box_started = False
        
        # Reset all box statuses (clear hover highlighting)
        for box in self.ui.spectroPanel.box_manager.get_all_boxes():
            box.status = False
        
        # Set appropriate cursor
        if mode == "BOX":
            self.ui.spectroPanel.setCursor(Qt.CrossCursor)
        else:
            self.ui.spectroPanel.setCursor(Qt.ArrowCursor)
        
        self.ui.spectroPanel.update()

    def on_edit_mode_toggled(self, checked: bool):
        '''
        Toggle interaction mode to BOX (drawing) mode.
        When checked, sets mode to "BOX" enabling drawing on the canvas.
        '''
        if checked:
            self._set_mode("BOX")
        
        # update status label
        self.update_statusLabel("Mode: BOX (Draw)")

    def on_erase_mode_toggled(self, checked: bool):
        '''
        Toggle interaction mode to ERASE mode.
        When checked, sets mode to "ERASE" enabling deletion of boxes by clicking.
        '''
        if checked:
            self._set_mode("ERASE")
            self.update_statusLabel("Mode: ERASE (Delete)")
            
    def on_update_mode_toggled(self, checked: bool):
        '''
        Toggle interaction mode to UPDATE mode.
        When checked, sets mode to "UPDATE" enabling label changes on boxes by clicking.
        Clicking a box will update its label_id to config["CURRENT_LABEL"].
        '''
        if checked:
            self._set_mode("UPDATE")
            self.update_statusLabel("Mode: UPDATE (Change Label)")

    def keyPressEvent(self, event):
        '''
        Handle keyboard input for application-level shortcuts.
        
        Supports:
            - Escape: Cancel in-progress box drawing (in BOX mode)
            - A or Left Arrow: Navigate to previous image
            - D or Right Arrow: Navigate to next image
        
        Args:
            event (QKeyEvent): PyQt5 key event containing key info.
        '''
        
        # Cancel box drawing with Escape
        if event.key() == Qt.Key_Escape:
            if config.get("MODE") == "BOX":
                self.ui.spectroPanel.reset_current_drawing()
                return
        
        # Image navigation requires a loaded project
        if not config.get("PROJECT_LOADED", False):
            super().keyPressEvent(event)
            return
        
        # Navigate to previous image
        if event.key() in (Qt.Key_A, Qt.Key_Left):
            self.navigate_image('-')
            return
        
        # Navigate to next image
        if event.key() in (Qt.Key_D, Qt.Key_Right):
            self.navigate_image('+')
            return
        
        super().keyPressEvent(event)

    def on_add_label_clicked(self):
        dialog = LabelNewDialog(self)
        dialog.exec_()
        result, new_name = dialog.get_result()
        if result == "accept":
            config["LABELS"].append(new_name)
            self.update_label_buttons()
            self.save_labels_to_yaml()

    def on_go_btn_clicked(self):
        # Defensive: check if project is loaded and image_manager is initialized
        if not config.get("PROJECT_LOADED", False) or self.image_manager is None:
            QMessageBox.warning(self, "No Project", "Please load or create a project first.")
            return
        
        total_images = len(self.image_manager.image_list)
        if total_images == 0:
            QMessageBox.warning(self, "No Images", "No images are loaded in the project.")
            return

        user_input = self.ui.ImageGoLineEd.text().strip()
        try:
            idx = int(user_input)
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please enter a valid integer image index.")
            return

        idx = max(0, min(idx, total_images - 1))
        self.go_to_image(idx)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = App()
    MainWindow.show()
    sys.exit(app.exec_())
#     import sys
#     QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
#     QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
#     app = QtWidgets.QApplication(sys.argv)
#     MainWindow = App()
#     MainWindow.show()
#     sys.exit(app.exec_())