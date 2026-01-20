"""
Bounding box classes for annotation in spectrAI.

This module contains the BoundingBox class which represents individual bounding boxes
in image-relative coordinates, and BoxManager which manages collections of bounding boxes.
"""

from PyQt5.QtGui import QPen, QColor, QFont
from PyQt5.QtCore import QRect
import uuid
from constants import *

class BoundingBox:
    """
    Represents a single bounding box in original image coordinate space.
    
    All coordinates and dimensions are stored relative to the original image,
    independent of scaling or display transformations.
    """
    
    def __init__(self, x: int, y: int, width: int, height: int, label_id: int, box_id: str = None, is_prediction=False):
        """
        Initialize a bounding box.
        
        Args:
            x (int): X coordinate of the top-left corner in original image space
            y (int): Y coordinate of the top-left corner in original image space
            width (int): Width of the bounding box in original image space
            height (int): Height of the bounding box in original image space
            label_id (int): Index/ID of the label from dataset.yaml
            box_id (str): Unique identifier for this box. If None, will be generated.
        """
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.label_id = label_id
        self.box_id = box_id if box_id is not None else str(uuid.uuid4())
        self.status = False  # True if selected, False otherwise
        self.default_color =  QColor(255, 140, 0) if is_prediction else QColor(200, 0, 0)
    def get_bounds(self) -> tuple:
        """
        Get the bounding box bounds.
        
        Returns:
            tuple: (x, y, x2, y2) where x2 = x + width, y2 = y + height
        """
        return (self.x, self.y, self.x + self.width, self.y + self.height)
    
    def update(self, x: int = None, y: int = None, width: int = None, height: int = None):
        """
        Update the bounding box dimensions.
        
        Args:
            x (int): New X coordinate (optional)
            y (int): New Y coordinate (optional)
            width (int): New width (optional)
            height (int): New height (optional)
        """
        if x is not None:
            self.x = x
        if y is not None:
            self.y = y
        if width is not None:
            self.width = width
        if height is not None:
            self.height = height
    
    def to_dict(self) -> dict:
        """
        Convert the bounding box to a dictionary (useful for serialization).
        
        Returns:
            dict: Dictionary representation of the bounding box
        """
        return {
            'box_id': self.box_id,
            'x': self.x,
            'y': self.y,
            'width': self.width,
            'height': self.height,
            'label_id': self.label_id
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'BoundingBox':
        """
        Create a BoundingBox from a dictionary.
        
        Args:
            data (dict): Dictionary with keys x, y, width, height, label_id, box_id
            
        Returns:
            BoundingBox: New instance created from dictionary data
        """
        return cls(
            x=data['x'],
            y=data['y'],
            width=data['width'],
            height=data['height'],
            label_id=data['label_id'],
            box_id=data.get('box_id')
        )
    
    def render_bounding_box(self, painter, image_manager, labels):
        """
        Render the bounding box on a QPainter.
        
        Args:
            painter (QPainter): The painter to draw with
            image_manager: ImageManager instance for coordinate transformations
            labels (list): List of label names from config["LABELS"]
        """
        # Convert image coordinates to screen coordinates
        screen_x, screen_y = image_manager.image_to_screen_coords(self.x, self.y)
        screen_x2, screen_y2 = image_manager.image_to_screen_coords(
            self.x + self.width,
            self.y + self.height
        )
        
        # Choose color based on status: green if selected, red otherwise
        color = QColor(0, 200, 0) if self.status else self.default_color
        pen = QPen(color)
        pen.setWidth(2)
        painter.setPen(pen)
        
        # Draw the rectangle
        rect = QRect(screen_x, screen_y, screen_x2 - screen_x, screen_y2 - screen_y)
        painter.drawRect(rect)
        
        # Draw label text
        font = QFont()
        font.setPointSize(9)
        painter.setFont(font)
        
        # Get label name from config["LABELS"] or use label_id as fallback
        if labels and 0 <= self.label_id < len(labels):
            label_text = labels[self.label_id]
        else:
            label_text = str(self.label_id)
        
        painter.drawText(screen_x + 4, screen_y + 14, label_text)
    
    def __repr__(self) -> str:
        return f"BoundingBox(id={self.box_id}, x={self.x}, y={self.y}, w={self.width}, h={self.height}, label_id={self.label_id})"
