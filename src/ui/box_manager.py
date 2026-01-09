"""
Box Manager for managing collections of bounding boxes in spectrAI.

This module contains the BoxManager class which handles storing, retrieving,
and manipulating multiple bounding boxes for annotation tasks.
"""

from typing import List, Optional
from .bounding_box import BoundingBox


class BoxManager:
    """
    Manages a collection of bounding boxes for a single image annotation.
    
    Handles adding, removing, updating, and querying bounding boxes,
    all stored in original image coordinate space.
    """
    
    def __init__(self):
        """Initialize an empty box manager."""
        self.boxes: List[BoundingBox] = []
    
    def add_box(self, box: BoundingBox) -> str:
        """
        Add a bounding box to the manager.
        
        Args:
            box (BoundingBox): The bounding box to add
            
        Returns:
            str: The ID of the added box
        """
        self.boxes.append(box)
        return box.box_id
    
    def remove_box(self, box_id: str) -> bool:
        """
        Remove a bounding box by ID.
        
        Args:
            box_id (str): The ID of the box to remove
            
        Returns:
            bool: True if box was removed, False if box_id not found
        """
        for i, box in enumerate(self.boxes):
            if box.box_id == box_id:
                self.boxes.pop(i)
                return True
        return False
    
    def get_box(self, box_id: str) -> Optional[BoundingBox]:
        """
        Retrieve a bounding box by ID.
        
        Args:
            box_id (str): The ID of the box to retrieve
            
        Returns:
            BoundingBox or None: The box if found, None otherwise
        """
        for box in self.boxes:
            if box.box_id == box_id:
                return box
        return None
    
    def get_all_boxes(self) -> List[BoundingBox]:
        """
        Get all bounding boxes.
        
        Returns:
            List[BoundingBox]: List of all boxes
        """
        return self.boxes.copy()
    
    def get_boxes_by_label(self, label_id: int) -> List[BoundingBox]:
        """
        Get all bounding boxes with a specific label.
        
        Args:
            label_id (int): The label ID to filter by
            
        Returns:
            List[BoundingBox]: List of boxes with the specified label
        """
        return [box for box in self.boxes if box.label_id == label_id]
    
    def update_box(self, box_id: str, x: int = None, y: int = None, 
                   width: int = None, height: int = None, label_id: int = None) -> bool:
        """
        Update a bounding box's properties.
        
        Args:
            box_id (str): The ID of the box to update
            x (int): New X coordinate (optional)
            y (int): New Y coordinate (optional)
            width (int): New width (optional)
            height (int): New height (optional)
            label_id (int): New label ID (optional)
            
        Returns:
            bool: True if box was updated, False if box_id not found
        """
        box = self.get_box(box_id)
        if box is None:
            return False
        
        box.update(x, y, width, height)
        if label_id is not None:
            box.label_id = label_id
        
        return True
    
    def clear(self):
        """Remove all bounding boxes."""
        self.boxes.clear()
    
    def count(self) -> int:
        """
        Get the number of bounding boxes.
        
        Returns:
            int: Number of boxes
        """
        return len(self.boxes)
    
    def to_list(self) -> list:
        """
        Convert all boxes to a list of dictionaries (for serialization).
        
        Returns:
            list: List of box dictionaries
        """
        return [box.to_dict() for box in self.boxes]
    
    def from_list(self, data: list) -> None:
        """
        Load boxes from a list of dictionaries (for deserialization).
        
        Args:
            data (list): List of box dictionaries
        """
        self.clear()
        for box_data in data:
            box = BoundingBox.from_dict(box_data)
            self.add_box(box)
    
    def render_all(self, painter, image_manager, labels):
        """
        Render all bounding boxes with color-coded status.
        
        Args:
            painter (QPainter): The painter to draw with
            image_manager: ImageManager instance for coordinate transformations
            labels (list): List of label names from config["LABELS"]
        """
        for box in self.boxes:
            box.render_bounding_box(painter, image_manager, labels)
    
    def __repr__(self) -> str:
        return f"BoxManager(count={self.count()})"
    
    def __len__(self) -> int:
        return self.count()
