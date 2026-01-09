"""
Canvas Widget for Interactive Bounding Box Annotation in spectrAI.

This module provides the CanvasWidget class, a custom PyQt5 QLabel widget that enables
interactive annotation of spectrograms through bounding box creation. The widget implements
a two-click interface for intuitive box drawing and manages the rendering of all annotations
with real-time visual feedback.

The widget integrates with the ImageManager for coordinate transformations and the BoxManager
for annotation data management, maintaining a clear separation between presentation (UI events)
and business logic (box creation and storage).

Module Contents:
    - CanvasWidget: Main widget class for annotation canvas
    
Author: spectrAI Project
Version: 1.0.0
"""

from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import Qt, pyqtSignal, QRect, QPoint
from PyQt5.QtGui import QMouseEvent, QPainter, QPen, QColor, QFont, QCursor
from typing import Optional, Tuple
from .bounding_box import BoundingBox
from .box_manager import BoxManager
from constants import config


class CanvasWidget(QLabel):
    """
    Interactive annotation canvas for creating and managing bounding boxes.
    
    This widget provides a specialized QLabel subclass that handles user interaction for
    creating and editing bounding boxes on spectrogram images. It implements a two-click
    interface where:
    
    1. **First Click**: Establishes an anchor point at the user's click location, initiating
       a dynamic preview that follows the mouse cursor.
    
    2. **Second Click**: Finalizes the bounding box with dynamically adjusted corners based
       on the drag direction. The final box is added to the BoxManager and rendered with
       the selected label class name.
    
    **Key Features**:
        - Two-click bounding box creation with dynamic corner adjustment
        - Real-time preview rendering with dashed outline and label name
        - Support for click-to-select existing boxes with visual feedback
        - Color-coded rendering (green=selected, red=unselected)
        - Automatic coordinate transformation between screen and image spaces
        - Project-aware: respects config["PROJECT_LOADED"] state
        - Signal-based integration for external event handling
        - Smart bounds checking to prevent boxes outside image boundaries
    
    **Coordinate Systems**:
        - **Screen Coordinates**: Pixel positions on the widget display (offset by padding)
        - **Image Coordinates**: Pixel positions in the original image space (no offset)
        - Automatic bidirectional conversion via ImageManager
    
    **State Management**:
        - Box drawing state (is_box_started, anchor points, current mouse position)
        - Box selection state (selected_box_id, status flags)
        - Current label selection for new boxes
        - References to ImageManager and BoxManager
        - Cached label names from config["LABELS"]
    
    **Signals**:
        - box_created(str): Emitted when a new box is finalized with its ID
        - box_deleted(str): Emitted when a box is deleted with its ID
        - box_updated(str): Emitted when a box is modified with its ID
    
    Attributes:
        image_manager: Reference to ImageManager for coordinate transformations
        box_manager (BoxManager): Manages all bounding boxes for the current image
        labels (list): Cached list of label names from config["LABELS"]
        is_box_started (bool): True when first click done, awaiting second click
        anchor_x, anchor_y (int): Image coordinates of the initial click point
        current_mouse_x, current_mouse_y (int): Current mouse position in image coords
        current_label_id (int): Label index for the next box to be created
        selected_box_id (str): ID of currently selected box, None if nothing selected
        box_color (QColor): Color for unselected boxes (red)
        selected_box_color (QColor): Color for selected boxes (green)
        preview_box_color (QColor): Color for preview boxes while drawing (light blue)
        box_line_width (int): Thickness of box outlines in pixels
    """
    
    # PyQt5 Signals for external event handling
    box_created = pyqtSignal(str)
    """Signal emitted when a bounding box is created. Carries the box_id."""
    
    box_deleted = pyqtSignal(str)
    """Signal emitted when a bounding box is deleted. Carries the box_id."""
    
    box_updated = pyqtSignal(str)
    """Signal emitted when a bounding box is modified. Carries the box_id."""
    
    def __init__(self, parent=None):
        """
        Initialize the canvas widget with default settings.
        
        Sets up the widget as a QLabel with mouse tracking enabled, initializes all
        state variables for box drawing, and configures visual settings for rendering.
        
        Args:
            parent (QWidget, optional): Parent widget in the Qt widget hierarchy.
                                       Defaults to None.
        
        Returns:
            None
        
        Side Effects:
            - Enables mouse tracking for continuous cursor position updates
            - Creates a new BoxManager instance
            - Initializes color and styling constants
        """
        super().__init__(parent)
        
        # Enable mouse tracking to receive mouseMoveEvent even without button press
        self.setMouseTracking(True)
        
        # ==================== External References ====================
        # These are set by the parent application and provide access to required systems
        self.image_manager = None  # Will be set by parent app via set_image_manager()
        self.box_manager = BoxManager()  # Local box manager for this canvas
        self.labels = []  # Will be populated by parent app via set_labels()
        
        # ==================== Drawing State Variables ====================
        # These track the current state of box creation (two-click system)
        self.is_box_started = False  # True after first click, False at rest or after finalization
        self.anchor_x = 0  # X coordinate of first click in image space
        self.anchor_y = 0  # Y coordinate of first click in image space
        self.current_mouse_x = 0  # Current mouse X in image space (updated on mouseMoveEvent)
        self.current_mouse_y = 0  # Current mouse Y in image space (updated on mouseMoveEvent)
        
        # ==================== Label Selection ====================
        # Tracks which label class is assigned to new boxes
        self.current_label_id = 0  # Index into config["LABELS"], defaults to first label
        
        # ==================== Box Selection ====================
        # Tracks which (if any) box is currently selected by the user
        self.selected_box_id = None  # UUID of selected box, None if no selection
        
        # ==================== Visual Settings ====================
        # Configure colors and styling for box rendering
        self.box_color = QColor(200, 0, 0)  # Red for unselected boxes
        self.selected_box_color = QColor(0, 200, 0)  # Green for selected boxes
        self.preview_box_color = QColor(100, 150, 255)  # Light blue for preview during drawing
        self.box_line_width = 2  # Pixel width of box outlines
    
    # =====================================================================
    # Configuration Methods
    # =====================================================================
    
    def set_image_manager(self, image_manager):
        """
        Register the ImageManager for coordinate transformations.
        
        The ImageManager provides bidirectional coordinate conversion between screen
        space (with offset due to scaling/padding) and image space (original pixel coords).
        This must be called before any drawing operations.
        
        Args:
            image_manager (ImageManager): Instance providing coordinate transformation
                                         methods and image dimension information.
        
        Returns:
            None
        
        Raises:
            AttributeError: If image_manager doesn't have expected methods
                           (screen_to_image_coords, image_to_screen_coords)
        
        Example:
            >>> canvas = CanvasWidget()
            >>> image_manager = ImageManager(...)
            >>> canvas.set_image_manager(image_manager)
        """
        self.image_manager = image_manager
    
    def set_labels(self, labels: list):
        """
        Register the label names for rendering on boxes.
        
        Updates the cached list of label names from the project's dataset.yaml,
        which are displayed next to each bounding box. Should be called whenever
        the project's labels change.
        
        Args:
            labels (list): List of label name strings, indexed by label_id.
                          Should match config["LABELS"].
        
        Returns:
            None
        
        Side Effects:
            - Updates self.labels with provided list (or empty list if None)
            - Triggers a repaint to update all box labels
        
        Example:
            >>> canvas.set_labels(config["LABELS"])
            # Boxes now display their proper label names instead of IDs
        """
        self.labels = config.get("LABELS", [])
        self.update()  # Trigger paint event to refresh rendering
    
    def set_current_label(self, label_id: int):
        """
        Set the label class for the next box to be created.
        
        When the user creates a new bounding box, it will be assigned this label ID.
        This is typically called when the user clicks a label button in the UI.
        
        Args:
            label_id (int): Index into config["LABELS"] for the label to assign.
                           Must be in range [0, len(config["LABELS"])).
        
        Returns:
            None
        
        Raises:
            ValueError: If label_id is out of valid range (check not performed, 
                       caller's responsibility).
        
        Example:
            >>> canvas.set_current_label(2)  # Next box will have label_id=2
            >>> # User clicks twice to create box
            # New box will be assigned to label at config["LABELS"][2]
        """
        self.current_label_id = label_id
    
    # =====================================================================
    # Coordinate Transformation Methods
    # =====================================================================
    
    def is_mouse_in_image(self, screen_pos) -> bool:
        """
        Determine if a screen position is within the displayed image bounds.
        
        Checks if the given screen coordinate (which may be padded due to scaling)
        falls within the actual image display area. Used to prevent box creation
        outside the image boundaries.
        
        The image may be smaller than the widget if aspect ratio is preserved,
        creating padding around it. This method accounts for that padding.
        
        Args:
            screen_pos (QPoint): Screen coordinate to test, typically from a mouse event.
        
        Returns:
            bool: True if position is within image bounds, False otherwise.
            Returns False if ImageManager is not set.
        
        Algorithm:
            1. Extract X, Y from screen_pos
            2. Get image boundaries using offset and scale from ImageManager
            3. Perform bounds check: img_left <= x <= img_right and img_top <= y <= img_bottom
        
        Example:
            >>> canvas.is_mouse_in_image(event.pos())
            True  # Click was over the image
            
        Note:
            Does not validate that ImageManager is properly initialized.
            Returns False if ImageManager is None (safe default).
        """
        if self.image_manager is None:
            return False
        
        x = screen_pos.x()
        y = screen_pos.y()
        
        # Calculate image boundaries in screen coordinate space
        # offset_x/y account for padding from aspect ratio preservation
        img_left = self.image_manager.offset_x
        img_top = self.image_manager.offset_y
        
        # Calculate right and bottom edges using scale factors
        img_right = img_left + int(self.image_manager.original_width * self.image_manager.scale_x)
        img_bottom = img_top + int(self.image_manager.original_height * self.image_manager.scale_y)
        
        # Perform bounds check
        return img_left <= x <= img_right and img_top <= y <= img_bottom
    
    def screen_to_image_coords(self, screen_x: int, screen_y: int) -> Optional[Tuple[int, int]]:
        """
        Convert screen coordinates to original image coordinates.
        
        Transforms pixel coordinates in the widget's display space (which may include
        padding from aspect ratio scaling) to coordinates in the original image space
        (0 to original_width/original_height).
        
        This is the primary method for translating user clicks into image-relative
        positions for bounding box creation.
        
        Args:
            screen_x (int): X coordinate in screen/widget space.
            screen_y (int): Y coordinate in screen/widget space.
        
        Returns:
            tuple(int, int) or None: (image_x, image_y) if valid, None if:
                - ImageManager not set
                - Coordinates out of image bounds
                - Result is negative or beyond image dimensions
        
        Algorithm:
            1. Delegate to ImageManager.screen_to_image_coords()
            2. Validate result is not None
            3. Clamp to image bounds [0, original_width-1] x [0, original_height-1]
            4. Return clamped coords or None if out of bounds
        
        Coordinate Transformation Formula:
            image_x = (screen_x - offset_x) / scale_x
            image_y = (screen_y - offset_y) / scale_y
        
        Example:
            >>> result = canvas.screen_to_image_coords(640, 480)
            >>> if result:
            ...     img_x, img_y = result
            ...     print(f"Clicked at image position ({img_x}, {img_y})")
        
        Note:
            Returns None silently for out-of-bounds coordinates rather than raising
            exceptions, allowing caller to check for valid clicks.
        """
        if self.image_manager is None:
            return None
        
        # Delegate transformation to ImageManager
        result = self.image_manager.screen_to_image_coords(screen_x, screen_y)
        
        if result is None:
            return None
        
        img_x, img_y = result
        
        # Validate bounds and clamp to valid range
        if (img_x < 0 or img_y < 0 or 
            img_x >= self.image_manager.original_width or 
            img_y >= self.image_manager.original_height):
            return None
        
        return img_x, img_y
    
    def image_to_screen_coords(self, image_x: int, image_y: int) -> Tuple[int, int]:
        """
        Convert original image coordinates to screen coordinates.
        
        Transforms coordinates from the original image space (before any scaling)
        to the widget's display space. Used primarily for rendering bounding boxes
        that are stored in image-relative coordinates.
        
        This is the inverse operation of screen_to_image_coords().
        
        Args:
            image_x (int): X coordinate in original image space [0, original_width-1].
            image_y (int): Y coordinate in original image space [0, original_height-1].
        
        Returns:
            tuple(int, int): (screen_x, screen_y) in widget display space.
            Returns (image_x, image_y) unchanged if ImageManager not set (fallback).
        
        Coordinate Transformation Formula:
            screen_x = offset_x + image_x * scale_x
            screen_y = offset_y + image_y * scale_y
        
        Algorithm:
            1. Check if ImageManager is available
            2. If yes, delegate to ImageManager.image_to_screen_coords()
            3. If no, return coordinates unchanged (fallback, should not occur in practice)
        
        Example:
            >>> # Render a box that spans (100,50) to (300,200) in image space
            >>> top_left = canvas.image_to_screen_coords(100, 50)
            >>> bottom_right = canvas.image_to_screen_coords(300, 200)
            >>> draw_rect(top_left, bottom_right)
        
        Note:
            This is a lightweight wrapper around ImageManager's method.
            Does not validate that coordinates are within image bounds.
        """
        if self.image_manager is None:
            return (image_x, image_y)
        
        return self.image_manager.image_to_screen_coords(image_x, image_y)
    
    # =====================================================================
    # Mouse Event Handlers
    # =====================================================================
    
    def mousePressEvent(self, event: QMouseEvent):
        """
        Handle left mouse button press for two-click box creation.
        
        Implements the two-click interface:
        - **First Click**: If not currently drawing, sets anchor point and begins preview.
                         If click is on existing box, selects it instead.
        - **Second Click**: Finalizes the box with dynamically adjusted corners,
                          adds to BoxManager, and resets state for next box.
        
        The anchor point and current position dynamically adjust corners:
        - Mouse drag to LEFT/ABOVE anchor: anchors stay at top-left
        - Mouse drag to RIGHT/BELOW anchor: anchors stay at top-left
        - Width/height calculated as absolute difference
        
        Args:
            event (QMouseEvent): PyQt5 mouse event containing position and button info.
        
        Returns:
            None
        
        Side Effects:
            - Sets is_box_started = True on first click (outside existing box)
            - Updates anchor_x, anchor_y to first click position
            - Sets is_box_started = False on second click and finalizes box
            - Deselects all boxes when starting new box
            - Updates all box status flags when selecting existing box
            - Emits box_created signal when finalizing
            - Triggers widget repaint via self.update()
        
        Algorithm:
            1. Check if left mouse button pressed
            2. Check if click is within image bounds
            3. If not drawing:
               a. Check if click is on existing box
               b. If yes: select it (update status flags, update display)
               c. If no: start new box (set anchor, set is_box_started=True)
            4. If already drawing (second click):
               a. Set is_box_started=False
               b. Get end coordinates in image space
               c. Normalize to top-left and bottom-right
               d. Create BoundingBox if dimensions > 5x5 pixels
               e. Add to box_manager and emit signal
            5. Update display
        
        Example:
            User sequence:
            >>> # User clicks at (100, 150) in image
            # canvas.anchor_x=100, canvas.anchor_y=150, is_box_started=True
            # Preview box appears with dashed outline
            
            >>> # User moves mouse to (300, 300)
            # Preview updates in real-time
            
            >>> # User clicks again at (300, 300)
            # Box finalized: x=100, y=150, width=200, height=150
            # Box added to manager, signal emitted
        
        Notes:
            - Only responds to left mouse button (Qt.LeftButton)
            - Returns immediately unless config["MODE"] == "BOX"
            - Returns silently if click outside image bounds
            - Minimum box size is 5x5 pixels to prevent accidental tiny boxes
            - No error checking for ImageManager being set (relies on caller)
        """
        # Respect global interaction mode; cancel in-progress preview if mode changed
        if config.get("MODE") != "BOX":
            if self.is_box_started:
                self.is_box_started = False
                self.update()
            return

        if event.button() != Qt.LeftButton:
            return
        
        if not self.is_mouse_in_image(event.pos()):
            return
        
        if not self.is_box_started:
            # ==================== FIRST CLICK ====================
            # Attempt to select existing box at click position
            clicked_box = self._get_box_at_position(event.pos())
            
            if clicked_box:
                # User clicked on existing box - select it
                for box in self.box_manager.get_all_boxes():
                    box.status = (box is clicked_box)
                self.selected_box_id = clicked_box.box_id
                self.update()
            else:
                # User clicked on empty space - start new box
                self.is_box_started = True
                self.anchor_x = event.pos().x()
                self.anchor_y = event.pos().y()
                self.current_mouse_x = event.pos().x()
                self.current_mouse_y = event.pos().y()
                
                # Deselect any previously selected box
                for box in self.box_manager.get_all_boxes():
                    box.status = False
                self.selected_box_id = None
                
                self.update()
        else:
            # ==================== SECOND CLICK ====================
            # Finalize the box with anchor and current position as corners
            self.is_box_started = False
            
            # Convert both click positions to image coordinates
            start_coords = self.screen_to_image_coords(self.anchor_x, self.anchor_y)
            end_coords = self.screen_to_image_coords(event.pos().x(), event.pos().y())
            
            if start_coords and end_coords:
                x1, y1 = start_coords
                x2, y2 = end_coords
                
                # Normalize coordinates to ensure top-left is (x, y)
                # and bottom-right is (x + width, y + height)
                x = min(x1, x2)
                y = min(y1, y2)
                width = abs(x2 - x1)
                height = abs(y2 - y1)
                
                # Only create box if it has reasonable minimum size
                # Prevents accidental creation of tiny boxes
                if width > 5 and height > 5:
                    # Create new bounding box in image coordinates
                    box = BoundingBox(x, y, width, height, self.current_label_id)
                    box.status = False  # New boxes are unselected by default
                    
                    # Add to manager and emit signal
                    box_id = self.box_manager.add_box(box)
                    self.box_created.emit(box_id)
                    
                    # Debug output
                    print(f"Box created: id={box_id}, x={x}, y={y}, w={width}, h={height}, label={self.current_label_id}")
                
                self.update()
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """
        Handle mouse movement for real-time preview feedback.
        
        Updates the current mouse position (in image coordinates) while drawing,
        causing the preview box outline to update in real-time as the user drags.
        The preview bounds adjust dynamically based on anchor and current position.
        
        This method only performs work if a box is currently being drawn (is_box_started=True).
        When not drawing, it's a no-op.
        
        Args:
            event (QMouseEvent): PyQt5 mouse event containing current position.
        
        Returns:
            None
        
        Side Effects:
            - Converts screen position to image coordinates
            - Updates current_mouse_x and current_mouse_y
            - Clamps to valid image bounds
            - Triggers widget repaint via self.update()
        
        Algorithm:
            1. Check if is_box_started is True
            2. If yes:
               a. Convert screen position to image coordinates
               b. Clamp to image bounds
               c. Store in current_mouse_x, current_mouse_y
               d. Trigger repaint
            3. If no: return (no-op)
        
        Performance Note:
            This method is called frequently (many times per second) during mouse
            movement. The implementation is optimized to be fast:
            - Only performs work if is_box_started is True
            - Coordinate conversion is just arithmetic, no heavy computation
            - Clamping prevents out-of-bounds renders
        
        Example:
            User sequence:
            >>> # User has clicked once, now moving mouse
            # Each mouseMoveEvent updates preview box to follow cursor
            # Preview box corner adjusts dynamically based on drag direction
        
        Notes:
            - Does nothing if ImageManager not set or no box in progress
            - Mouse tracking must be enabled for this to work (set in __init__)
        """
        if config.get("MODE") != "BOX":
            return
        if not self.is_box_started:
            return
        
        # Convert screen coordinates to image coordinates
        img_coords = self.screen_to_image_coords(event.pos().x(), event.pos().y())
        
        if img_coords:
            self.current_mouse_x, self.current_mouse_y = img_coords
            
            # Clamp to image bounds to prevent preview from extending outside image
            if self.image_manager:
                self.current_mouse_x = max(0, min(self.current_mouse_x, 
                                                   self.image_manager.original_width - 1))
                self.current_mouse_y = max(0, min(self.current_mouse_y, 
                                                   self.image_manager.original_height - 1))
        
        # Trigger repaint to update preview box in paintEvent
        self.update()
    
    # =====================================================================
    # Painting and Rendering
    # =====================================================================
    
    def paintEvent(self, event):
        """
        Render the image and all annotations (boxes and preview).
        
        This is the main painting method called by the Qt event loop whenever
        the widget needs to be redrawn. It handles:
        1. Base image (from parent QLabel)
        2. All finalized bounding boxes (via BoxManager)
        3. Preview box (while drawing)
        
        Args:
            event (QPaintEvent): PyQt5 paint event (unused, required by Qt).
        
        Returns:
            None
        
        Side Effects:
            - Calls parent's paintEvent to render the image
            - Creates QPainter for custom drawing
            - Renders all boxes with color coding based on selection status
            - Renders preview box if drawing in progress
        
        Algorithm:
            1. Call parent QLabel's paintEvent to render base image
            2. Create QPainter with antialiasing enabled
            3. Call box_manager.render_all() to render all finalized boxes
            4. If is_box_started: call _draw_preview_box() to show preview
            5. End painter
        
        Rendering Order:
            1. Base image (bottom layer)
            2. Finalized boxes (middle layer)
            3. Preview box (top layer, only while drawing)
        
        Performance Notes:
            - Antialiasing is enabled for smooth box rendering
            - Only renders if ImageManager is available
            - Preview rendering is minimal (dashed rectangle + text)
        
        Example:
            After user clicks twice to create a box:
            >>> # paintEvent automatically called when widget updates
            # Base image rendered
            # Green box rendered for selected box, red for unselected
            # Each box shows its label name
        
        Notes:
            - This method is called frequently by Qt event loop
            - Should not be called manually; use update() to trigger repaint
            - All drawing must happen within this method's painter context
        """
        # Paint base image (handled by parent QLabel)
        super().paintEvent(event)
        
        # Create painter for custom annotation rendering
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)  # Smooth lines and text
        
        # Render all finalized boxes using BoxManager's render method
        # This automatically color-codes based on selection status:
        # - Green (self.selected_box_color) if box.status == True
        # - Red (self.box_color) if box.status == False
        if self.image_manager:
            self.box_manager.render_all(painter, self.image_manager, self.labels)
        
        # Render preview box (dashed outline) if user is currently drawing
        if self.is_box_started:
            self._draw_preview_box(painter)
        
        painter.end()
    
    def _draw_preview_box(self, painter: QPainter):
        """
        Render the dynamic preview box while user is drawing.
        
        Displays a dashed rectangle from anchor point to current mouse position,
        showing what the final box will look like. Updates in real-time as the
        user moves the mouse. Includes the label name as preview text.
        
        The preview box dynamically adjusts corners based on drag direction:
        - Dragging left/up from anchor: moves the top-left corner
        - Dragging right/down from anchor: moves the bottom-right corner
        - Width and height calculated as absolute difference
        
        Args:
            painter (QPainter): Active painter for drawing. Should have been created
                              in paintEvent and have antialiasing enabled.
        
        Returns:
            None
        
        Side Effects:
            - Modifies painter's pen settings (color, width, style)
            - Modifies painter's font settings
            - Draws on the painter (does not call painter.begin/end)
        
        Algorithm:
            1. Convert anchor point to screen coordinates
            2. Convert current mouse position to screen coordinates
            3. Normalize to ensure x <= x2 and y <= y2
            4. Create dashed pen (light blue color)
            5. Draw rectangle outline
            6. Draw label text near top-left corner
            7. Restore painter state (implicit via end of method)
        
        Visual Style:
            - Color: preview_box_color (light blue: RGB 100,150,255)
            - Line Style: Dashed (Qt.DashLine)
            - Line Width: box_line_width (usually 2 pixels)
            - Text: Label name from config["LABELS"][current_label_id]
            - Text Size: 9pt, bold
        
        Example:
            User has clicked once and moved mouse:
            >>> # User drags from (100,50) to (300,200) in image space
            >>> # Preview shows dashed rectangle with label name
            >>> # As mouse moves, rectangle updates in real-time
        
        Notes:
            - Only called if is_box_started is True
            - Works in screen coordinates (calls image_to_screen_coords)
            - Does not modify box_manager, purely visual feedback
        """
        # Convert anchor and current positions to screen coordinates
        # This accounts for image scaling and padding
        screen_x1, screen_y1 = self.image_to_screen_coords(self.anchor_x, self.anchor_y)
        screen_x2, screen_y2 = self.image_to_screen_coords(self.current_mouse_x, self.current_mouse_y)
        
        # Normalize to ensure top-left and bottom-right ordering
        x = min(screen_x1, screen_x2)
        y = min(screen_y1, screen_y2)
        width = abs(screen_x2 - screen_x1)
        height = abs(screen_y2 - screen_y1)
        
        # Configure pen for dashed outline
        pen = QPen(self.preview_box_color)
        pen.setWidth(self.box_line_width)
        pen.setStyle(Qt.DashLine)
        painter.setPen(pen)
        
        # Draw preview rectangle
        rect = QRect(x, y, width, height)
        painter.drawRect(rect)
        
        # Configure font and draw label text
        font = QFont()
        font.setPointSize(9)
        font.setBold(True)
        painter.setFont(font)
        
        # Get label name from config or fallback to label_id
        if self.labels and 0 <= self.current_label_id < len(self.labels):
            label_text = f"[{self.labels[self.current_label_id]}]"
        else:
            label_text = f"[Label {self.current_label_id}]"
        
        # Draw text near top-left corner of preview box
        painter.drawText(x + 4, y + 14, label_text)
    
    # =====================================================================
    # Utility Methods
    # =====================================================================
    
    def _get_box_at_position(self, screen_pos) -> Optional[BoundingBox]:
        """
        Find the bounding box at a given screen position, if any exists.
        
        Performs a point-in-rectangle test for all boxes, checking from last
        (top visual layer) to first (bottom layer). Returns the topmost box
        at the given position for proper click handling in overlapping scenarios.
        
        Args:
            screen_pos (QPoint): Screen coordinate to test (typically from mouse event).
        
        Returns:
            BoundingBox or None: The box at the position, or None if no box found
                                or ImageManager not set.
        
        Algorithm:
            1. Extract x, y from screen_pos
            2. Iterate boxes in reverse order (last added = top layer)
            3. For each box:
               a. Convert box corners to screen coordinates
               b. Check if point is within rectangle
               c. Return box if point is inside (first match = topmost)
            4. Return None if no box contains point
        
        Point-in-Rectangle Test:
            Checks: screen_x <= x <= screen_x2 and screen_y <= y <= screen_y2
        
        Example:
            >>> box = canvas._get_box_at_position(event.pos())
            >>> if box:
            ...     print(f"Clicked on box: {box.box_id}")
            ... else:
            ...     print("Clicked on empty space")
        
        Notes:
            - Returns first (topmost) box found, not all boxes at position
            - Requires ImageManager to be set
            - Does not validate coordinate bounds (relies on image_to_screen_coords)
            - Returns None silently if no box found (caller responsibility to handle)
        """
        x = screen_pos.x()
        y = screen_pos.y()
        
        # Check boxes in reverse order for proper visual layering
        # (last-added box is on top)
        for box in reversed(self.box_manager.get_all_boxes()):
            # Convert box corners from image coordinates to screen coordinates
            screen_x, screen_y = self.image_to_screen_coords(box.x, box.y)
            screen_x2, screen_y2 = self.image_to_screen_coords(
                box.x + box.width,
                box.y + box.height
            )
            
            # Check if point is within box bounds
            if screen_x <= x <= screen_x2 and screen_y <= y <= screen_y2:
                return box
        
        return None
    
    # =====================================================================
    # Public Interface Methods
    # =====================================================================
    
    def delete_selected_box(self) -> bool:
        """
        Remove the currently selected bounding box.
        
        Deletes the box identified by selected_box_id from the BoxManager
        and updates the display. Does nothing if no box is currently selected.
        
        Args:
            None
        
        Returns:
            bool: True if box was deleted, False if no selection or removal failed.
        
        Side Effects:
            - Removes box from box_manager
            - Clears selected_box_id
            - Emits box_deleted signal with box_id
            - Triggers widget repaint
        
        Example:
            >>> canvas.select_box(some_box_id)  # Select a box
            >>> canvas.delete_selected_box()  # Delete it
            # Box is removed from annotation, display updates
        
        Notes:
            - Only affects the selected box, not all boxes
            - Can be called when no selection exists (safe no-op)
            - Typically bound to Delete key in parent application
        """
        if self.selected_box_id:
            self.box_manager.remove_box(self.selected_box_id)
            self.box_deleted.emit(self.selected_box_id)
            self.selected_box_id = None
            self.update()
            return True
        return False
    
    def clear_all_boxes(self) -> None:
        """
        Remove all bounding boxes from the canvas.
        
        Clears the entire box_manager and resets the canvas to a clean state.
        This is typically called when loading a new image or clearing annotations.
        
        Args:
            None
        
        Returns:
            None
        
        Side Effects:
            - Removes all boxes from box_manager
            - Clears selected_box_id
            - Resets drawing state (is_box_started = False)
            - Triggers widget repaint
        
        Example:
            >>> canvas.clear_all_boxes()
            # All annotations removed, canvas shows image only
        
        Notes:
            - This is destructive and cannot be undone in this implementation
            - Does not save boxes to file (caller's responsibility)
            - Safe to call even if no boxes exist
        """
        self.box_manager.clear()
        self.selected_box_id = None
        self.is_box_started = False
        self.update()
