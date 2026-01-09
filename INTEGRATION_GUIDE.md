"""
INTEGRATION GUIDE: Bounding Box Annotation System
==================================================

This guide shows how to integrate the new bounding box annotation system
into the main spectrAI application.

FILE STRUCTURE:
===============
src/ui/
├── bounding_box.py       (NEW - BoundingBox class)
├── box_manager.py        (NEW - BoxManager class)
├── canvas_widget.py      (NEW - CanvasWidget class)
├── main_ui.py            (unchanged - auto-generated)
└── __init__.py           (should import new classes)

INTEGRATION STEPS:
==================

1. Update src/ui/__init__.py to export new classes:
   -----------------------------------------------
   from .canvas_widget import CanvasWidget
   from .box_manager import BoxManager
   from .bounding_box import BoundingBox
   
   __all__ = ['CanvasWidget', 'BoxManager', 'BoundingBox']


2. In src/spectrai.py, replace QLabel with CanvasWidget:
   -------------------------------------------------------
   
   BEFORE (current approach):
   ```python
   self.ui.spectroPanel = QtWidgets.QLabel(...)
   ```
   
   AFTER (new approach):
   ```python
   from ui.canvas_widget import CanvasWidget
   
   # Replace the spectroPanel creation in initialize_image_manager
   self.ui.spectroPanel = CanvasWidget()
   self.ui.spectroPanel.set_image_manager(self.image_manager)
   ```


3. Connect label buttons to canvas widget:
   ----------------------------------------
   
   When a user clicks a label button, update the current label:
   ```python
   self.ui.labelButton.clicked.connect(
       lambda label_id=index: self.ui.spectroPanel.set_current_label(label_id)
   )
   ```


4. Handle box signals (optional):
   -------------------------------
   
   ```python
   # Connect signals to handle box events
   self.ui.spectroPanel.box_created.connect(self.on_box_created)
   self.ui.spectroPanel.box_updated.connect(self.on_box_updated)
   self.ui.spectroPanel.box_deleted.connect(self.on_box_deleted)
   
   def on_box_created(self, box_id):
       print(f"Box created: {box_id}")
       # Update UI, save to file, etc.
   ```


5. Save/Load annotations:
   ----------------------
   
   When saving annotations:
   ```python
   boxes_data = self.ui.spectroPanel.box_manager.to_list()
   # Save boxes_data to YOLO format file
   ```
   
   When loading annotations:
   ```python
   boxes_data = load_from_file()  # Your load function
   self.ui.spectroPanel.box_manager.from_list(boxes_data)
   ```


KEY FEATURES:
=============

✓ All bounding boxes stored in ORIGINAL IMAGE coordinates
✓ Automatic coordinate transformation (screen ↔ image)
✓ Handles padding/offset from aspect ratio preservation
✓ Separate scale_x and scale_y for flexibility
✓ Mouse bounds checking (prevents boxes outside image)
✓ Click to select boxes
✓ Delete selected box
✓ Visual feedback (different colors for selected boxes)
✓ Signal-based architecture for clean integration


COORDINATE SYSTEM:
==================

ImageManager tracks:
  - original_width, original_height     (original image dimensions)
  - scale_x, scale_y                    (scaling factors)
  - offset_x, offset_y                  (padding offsets)

CanvasWidget provides:
  - screen_to_image_coords()            (mouse clicks → image coords)
  - image_to_screen_coords()            (boxes → screen display)
  - is_mouse_in_image()                 (bounds checking)

BoundingBox stores:
  - x, y, width, height                 (in original image space)
  - label_id                            (from dataset.yaml)
  - box_id                              (unique identifier)


EXAMPLE USAGE:
==============

# Create a box programmatically
box = BoundingBox(x=100, y=50, width=200, height=150, label_id=0)
box_id = canvas_widget.box_manager.add_box(box)

# Get all boxes
all_boxes = canvas_widget.box_manager.get_all_boxes()

# Get boxes with specific label
label_boxes = canvas_widget.box_manager.get_boxes_by_label(label_id=2)

# Update a box
canvas_widget.box_manager.update_box(box_id, x=120, y=60, label_id=1)

# Remove a box
canvas_widget.box_manager.remove_box(box_id)

# Serialize boxes
boxes_list = canvas_widget.box_manager.to_list()

# Deserialize boxes
canvas_widget.box_manager.from_list(boxes_list)


MOUSE INTERACTIONS:
===================

• Left Click + Drag:    Draw a new bounding box
• Left Click on box:    Select the box (highlighted in orange)
• Delete key:           Delete selected box (needs implementation)
• Click empty area:     Deselect box


CUSTOMIZATION:
==============

Modify CanvasWidget attributes to customize appearance:

  - box_color:             Color of unselected boxes (default: green)
  - selected_box_color:    Color of selected boxes (default: orange)
  - box_line_width:        Width of box outline (default: 2)


TROUBLESHOOTING:
================

1. Boxes not appearing?
   - Ensure image_manager is set: canvas.set_image_manager(image_manager)
   - Check that render() is called after loading image
   
2. Coordinate misalignment?
   - Verify offset_x, offset_y are calculated in ImageManager.render()
   - Check scale_x, scale_y match the actual scaled pixmap dimensions
   
3. Boxes outside image bounds?
   - This is prevented by bounds checking in mousePressEvent()
   - Verify is_mouse_in_image() logic in CanvasWidget
"""

# This is a documentation file - no code to execute
