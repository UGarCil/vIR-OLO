'''
Take a folder containing images of spectrograms and load them into the UI application

The script contains a maing object ImageManager(), which stores information on the current 
image loaded, the state of its annotations and the list of images in the folder.

Important utilities include the saving process to create annotations in YOLO format

The information on the folder and images is stored in a global dictionary, read from a 
json configuration file passed by the user — and created by the program — when a New 
project is created.
'''

import os
from PIL import Image
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
import io # Convert PIL image to bytes
from os.path import join as jn 

class ImageManager():
    def __init__(self, images_path=None, annotations_path = None):
        self.current_image = None
        self.current_index = 0
        self.annotations = sorted([jn(annotations_path, f) for f in os.listdir(annotations_path) if f.lower().endswith(('.txt'))])
        self.image_list = sorted([jn(images_path, f) for f in os.listdir(images_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
        
        # Transformation data for coordinate conversions
        self.original_width = None
        self.original_height = None
        self.scale_x = 1.0
        self.scale_y = 1.0
        self.offset_x = 0
        self.offset_y = 0

    def load_image(self):
        """
        Load the image at current_index and return a QPixmap ready for QLabel display.
        
        Returns:
            QPixmap or None: The loaded image as QPixmap, or None if loading fails
        """
            
        # Get the image path from the list using current_index
        image_path = self.image_list[self.current_index]
             
        # Load image using PIL
        pil_image = Image.open(image_path)
        
        # Convert PIL image to RGB if it's not already to allow it to handle different formats
        if pil_image.mode != 'RGB':
            pil_image = pil_image.convert('RGB')
        
        img_bytes = io.BytesIO()
        pil_image.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        # Create QPixmap from bytes
        pixmap = QPixmap()
        pixmap.loadFromData(img_bytes.getvalue())
        
        # Store reference to current image path
        self.current_image = image_path
        
        return pixmap

    def fit_to_window(self, width: int, height: int, pixmap: QPixmap, stretch: bool = True) -> QPixmap:
        """
        Scale the current image to fit within the specified window dimensions.
        
        Args:
            width (int): The width of the canvas/window
            height (int): The height of the canvas/window
            pixmap (QPixmap): The original QPixmap image to be scaled
            stretch (bool): If True, stretch image to fill window, ignoring aspect ratio
                
        Returns:
            QPixmap: The scaled image as a QPixmap object
        """
            
        # Get the image dimensions
        img_width = pixmap.width()
        img_height = pixmap.height()
        
        if stretch:
            # Simply use the target dimensions
            new_width = width
            new_height = height
            aspect_flag = Qt.IgnoreAspectRatio
        else:
            # Calculate scaling ratios
            width_ratio = width / img_width
            height_ratio = height / img_height
            
            # Use the smaller ratio to ensure the image fits in both dimensions
            scale_ratio = min(width_ratio, height_ratio)
            
            # Calculate new dimensions
            new_width = int(img_width * scale_ratio)
            new_height = int(img_height * scale_ratio)
            aspect_flag = Qt.KeepAspectRatio
        
        # Scale the pixmap
        scaled_pixmap = pixmap.scaled(new_width, new_height, 
                                    aspect_flag, 
                                    Qt.SmoothTransformation)
        
        return scaled_pixmap
    
    def render(self, QtLabel):
        """
        Render the current image onto a given QLabel.
        
        Args:
            QLabel: The QLabel widget where the image will be displayed.
        """
        
        width = QtLabel.width()
        height = QtLabel.height()
        
        # Load the original pixmap
        pixmap = self.load_image()
        
        # Store original dimensions
        self.original_width = pixmap.width()
        self.original_height = pixmap.height()
        
        # Scale it using fit_to_window
        scaled_pixmap = self.fit_to_window(width, height, pixmap)
        
        # Calculate transformation data
        scaled_width = scaled_pixmap.width()
        scaled_height = scaled_pixmap.height()
        
        # Calculate scale ratios
        self.scale_x = scaled_width / self.original_width if self.original_width > 0 else 1.0
        self.scale_y = scaled_height / self.original_height if self.original_height > 0 else 1.0
        
        # Calculate offsets (centered positioning when image is smaller than label)
        self.offset_x = (width - scaled_width) // 2
        self.offset_y = (height - scaled_height) // 2
        
        # Set the scaled pixmap to the label
        QtLabel.setPixmap(scaled_pixmap)
    
    def screen_to_image_coords(self, screen_x: int, screen_y: int) -> tuple:
        """
        Convert screen coordinates to original image coordinates.
        
        Args:
            screen_x (int): X coordinate on screen
            screen_y (int): Y coordinate on screen
            
        Returns:
            tuple: (image_x, image_y) in original image space
        """
        # Subtract offset to get position relative to scaled image
        relative_x = screen_x - self.offset_x
        relative_y = screen_y - self.offset_y
        
        # Check bounds
        if relative_x < 0 or relative_y < 0:
            return None
        
        # Convert to original image coordinates using scale factors
        image_x = int(relative_x / self.scale_x) if self.scale_x > 0 else 0
        image_y = int(relative_y / self.scale_y) if self.scale_y > 0 else 0
        
        # Clamp to image bounds
        image_x = max(0, min(image_x, self.original_width - 1))
        image_y = max(0, min(image_y, self.original_height - 1))
        
        return image_x, image_y
    
    def image_to_screen_coords(self, image_x: int, image_y: int) -> tuple:
        """
        Convert original image coordinates to screen coordinates.
        
        Args:
            image_x (int): X coordinate in original image
            image_y (int): Y coordinate in original image
            
        Returns:
            tuple: (screen_x, screen_y) on the screen
        """
        # Scale from image space to screen space
        scaled_x = int(image_x * self.scale_x)
        scaled_y = int(image_y * self.scale_y)
        
        # Add offset to get absolute screen position
        screen_x = scaled_x + self.offset_x
        screen_y = scaled_y + self.offset_y
        
        return screen_x, screen_y
        
    def next_image(self):
        '''
        Update the index in the Image Manager
        '''
        if self.current_index < len(self.image_list) - 1:
            self.current_index += 1
    
    def previous_image(self):
        '''
        Update the index in the Image Manager
        '''
        if self.current_index > 0:
            self.current_index -= 1