# vIR-OLO (ScpectrAI)

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/python-3.8+-green)
![PyQt5](https://img.shields.io/badge/PyQt5-GUI-orange)

<div align="center">
    <img src="./logo/cham_anim.gif" alt="vIR-OLO Animation" width="80%">
</div>


**vIR-OLO** is an intelligent annotation and inference tool for IR spectroscopy analysis. This project was born from the necessity of researchers to identify peaks in IR spectra, with the ultimate goal of assisting technicians and accelerating the analysis process.

The application provides a complete PyQt5-based GUI for creating YOLO-format annotations and integrating pre-trained YOLO models for AI-assisted peak detection in infrared spectra images.

---

## 🎯 Key Features

### Annotation Capabilities
- **Interactive bounding box annotation** with intuitive two-click drawing interface
- **YOLO-format compatibility** for seamless integration with YOLO training pipelines
- **Custom label management** - define and edit label sets for your specific peak types
- **Project-based workflow** - organized structure for images and annotations
- **Multiple interaction modes**:
  - **BOX mode**: Draw new bounding boxes
  - **ERASE mode**: Delete existing annotations
  - **UPDATE mode**: Modify box labels

### AI-Assisted Workflow
- **Load pre-trained YOLO models** from Hugging Face or local filesystem
- **One-click prediction** on loaded spectra images
- **Automatic label merging** when integrating models with different label sets
- **Default model downloader** from Hugging Face repository (`UrielGC/spectrai-IR-YOLO`)
- **Hybrid annotation**: Combine AI predictions with manual corrections

### User Interface
- **Image navigation** - browse through multiple spectra with prev/next controls
- **Visual feedback** - color-coded bounding boxes (green=selected, red=unselected)
- **Real-time preview** during box creation
- **Status indicators** for project state and active models

---

## 📦 Installation

### Prerequisites
- Python 3.10 or higher (recommended version 3.12.10)
- Git (for cloning the repository)
- CUDA-compatible GPU (optional, for faster inference)

### Step 1: Clone the Repository

```bash
git clone https://github.com/UGarCil/vIR-OLO.git
cd vIR-OLO
```

### Step 2: Create a Virtual Environment and install dependencies

Choose either **venv** or **conda** based on your preference:

#### Option A: Using venv

```bash
# Create virtual environment
python -m venv .venv

# Activate on Windows
.venv\Scripts\activate

# Activate on Linux/macOS
source .venv/bin/activate
```

>**Important**: Always ensure your virtual environment (venv or conda) is activated before running the application.

```bash
# Create conda environment
conda create -n virolo python=3.12.10
conda activate virolo
```

### Install PyTorch

Install PyTorch with CUDA support for GPU acceleration (recommended for faster inference) or CPU-based:

#### For CUDA 12.6 (Windows/Linux):
```bash
pip3 install torch torchvision --index-url https://download.pytorch.org/whl/cu126
```

#### For CUDA 11.8:
```bash
pip3 install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

#### For CPU only:
```bash
pip3 install torch torchvision
```

> **Note**: Visit [PyTorch's official website](https://pytorch.org/get-started/locally/) to find the installation command for your specific CUDA version.

### Step 3: Install vIR-OLO

With your virtual environment **activated** and inside the repository directory:

```bash
pip install -e .
```

This will install all required dependencies including:
- PyQt5 (GUI framework)
- Pillow (Image processing)
- opencv-python (Computer vision utilities)
- numpy (Numerical operations)
- PyYAML (Configuration files)
- huggingface_hub (Model downloads)
- ultralytics (YOLO inference)
- requests (HTTP requests to connect with Hugging Face API)
---

## 🚀 Quick Start

### 1. Launch the Application

```bash
python main.py
```

### 2. Create a New Project

1. Go to **File → New Project**
2. Select a folder containing your IR spectra images (PNG, JPG, JPEG formats)
3. The application will create the necessary project structure

### 3. Load a Model (Optional)

#### Download Default Model:
- Go to **File → Download Default Models**
- The application will download pre-trained models from Hugging Face

#### Load Custom Model:
- Go to **Models → Load Model**
- Select a folder containing:
  - A `.pt` YOLO model file
  - A `dataset.yaml` file with label definitions

### 4. Start Annotating

- **Manual annotation**: 
  - Ensure **BOX mode** is active (Edit button)
  - Click once to set the first corner
  - Click again to complete the bounding box
  
- **AI-assisted annotation**:
  - Click the **Predict** button to run model inference
  - Review and correct predicted boxes as needed

### 5. Navigate & Save

- Use **Previous/Next** buttons or enter image numbers to navigate
- Annotations are automatically saved when switching images or closing the application

---

## 📁 Project Structure

```
vIR-OLO/
├── main.py                          # Application entry point
├── pyproject.toml                   # Project configuration and dependencies
├── README.md                        # This file
├── INTEGRATION_GUIDE.md            # Integration documentation
├── logo/                           # Application logo assets
└── src/                            # Source code
    ├── __init__.py
    ├── constants.py                # Global configuration dictionary
    ├── dataset.yaml                # Label definitions template
    ├── spectrai.py                 # Main application controller (App class)
    ├── models/
    │   ├── __init__.py
    │   └── predict.py              # PredictorManager for YOLO inference
    ├── tools/
    │   ├── __init__.py
    │   ├── image_loader.py         # ImageManager for image loading & transformations
    │   └── donwload_default_models.py  # ModelManager for Hugging Face downloads
    └── ui/
        ├── __init__.py
        ├── main_ui.py              # Auto-generated UI code from Qt Designer
        ├── main.ui                 # Qt Designer UI definition
        ├── canvas_widget.py        # Interactive annotation canvas (CanvasWidget)
        ├── box_manager.py          # BoxManager for annotation storage
        ├── bounding_box.py         # BoundingBox data class
        ├── label_editor_dialog.py  # Label editing dialog
        ├── label_new_dialog.py     # New label creation dialog
        └── icons/                  # UI icon assets
```

---

## 🔧 How It Works

### Architecture Overview

**vIR-OLO** follows a modular architecture with clear separation of concerns:

1. **Application Layer** ([spectrai.py](src/spectrai.py))
   - Main `App` class coordinates all components
   - Manages project lifecycle and user interactions
   - Connects UI signals to business logic

2. **Image Management** ([image_loader.py](src/tools/image_loader.py))
   - `ImageManager` handles image loading and display
   - Manages coordinate transformations between screen and image space
   - Maintains scaling metadata for accurate annotation positioning

3. **Annotation Management** ([box_manager.py](src/ui/box_manager.py), [bounding_box.py](src/ui/bounding_box.py))
   - `BoxManager` stores collections of bounding boxes per image
   - `BoundingBox` represents individual annotations
   - Converts between YOLO format (normalized) and pixel coordinates

4. **Model Inference** ([predict.py](src/models/predict.py))
   - `PredictorManager` runs YOLO model predictions
   - Maps model labels to workspace labels
   - Converts inference results to annotation format

5. **UI Layer** ([canvas_widget.py](src/ui/canvas_widget.py), [main_ui.py](src/ui/main_ui.py))
   - `CanvasWidget` provides interactive annotation canvas
   - Real-time drawing preview and box selection
   - PyQt5-based modern interface

### Data Flow

```
User Creates/Loads Project
    ↓
ImageManager loads spectra images
    ↓
User Action (Manual or AI-assisted)
    ↓
    ├→ Manual: CanvasWidget captures clicks → BoxManager stores annotation
    └→ AI: PredictorManager runs inference → BoxManager stores predictions
    ↓
Annotations saved in YOLO format (.txt files)
```

---

## 🎓 Usage Tips

### Label Management
- Create custom labels specific to your IR analysis needs
- Labels are stored in `dataset.yaml` format
- When loading models, labels automatically merge with existing ones

### Coordinate Systems
The application handles two coordinate systems:
- **Screen coordinates**: Widget display space (includes padding/offset)
- **Image coordinates**: Original image pixel space (used for storage)

All conversions are handled automatically by `ImageManager`.

### Annotation Workflow Best Practices
1. Start with AI predictions if you have a pre-trained model
2. Review predictions and correct any errors
3. Add missing annotations manually
4. Use consistent labeling across your dataset
5. Regularly save your work (automatic on navigation)

### YOLO Format Output
Annotations are saved as `.txt` files with the format:
```
<class_id> <x_center> <y_center> <width> <height>
```
All values are normalized to [0, 1] relative to image dimensions.

---

## 🤝 Contributing

Contributions are welcome! If you'd like to improve vIR-OLO:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

This project is available for research and educational purposes. Please contact the repository owner for commercial use inquiries.

---

## 🙏 Acknowledgments

- Built with [PyQt5](https://www.riverbankcomputing.com/software/pyqt/) for the GUI framework
- Powered by [Ultralytics YOLO](https://github.com/ultralytics/ultralytics) for object detection
- Default models hosted on [Hugging Face](https://huggingface.co/UrielGC/spectrai-IR-YOLO)

---

## 📞 Support

For questions, issues, or feature requests, please open an issue on the [GitHub repository](https://github.com/UGarCil/vIR-OLO).

---

**Made with ❤️ for the spectroscopy research community**
