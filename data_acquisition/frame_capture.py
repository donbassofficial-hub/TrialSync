"""
Frame Capture Module
Captures video frames from Elgato HD60 X capture card
"""

import cv2
import numpy as np
from datetime import datetime
from typing import Optional, Generator
import threading
import queue
import logging
from pathlib import Path

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from processing_engine.models import Frame
from config.config_loader import load_config

logger = logging.getLogger(__name__)


class FrameCapture:
    """
    Captures frames from Elgato HD60 X video feed
    """
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """
        Initialize frame capture
        
        Args:
            config_path: Path to configuration file
        """
        self.config = load_config(config_path)
        self.video_config = self.config.get('video_capture', {})
        
        self.device_index = self.video_config.get('device_index', 0)
        self.width = self.video_config.get('width', 1920)
        self.height = self.video_config.get('height', 1080)
        self.fps = self.video_config.get('fps', 30)
        self.buffer_size = self.video_config.get('buffer_size', 10)
        
        self.cap: Optional[cv2.VideoCapture] = None
        self.frame_queue: queue.Queue = queue.Queue(maxsize=self.buffer_size)
        self.is_running = False
        self.capture_thread: Optional[threading.Thread] = None
        self.frame_counter = 0
        
        logger.info(f"FrameCapture initialized: device={self.device_index}, "
                   f"resolution={self.width}x{self.height}, fps={self.fps}")
    
    def start(self) -> bool:
        """
        Start frame capture
        
        Returns:
            True if capture started successfully
        """
        try:
            self.cap = cv2.VideoCapture(self.device_index)
            
            if not self.cap.isOpened():
                logger.error(f"Failed to open video device {self.device_index}")
                return False
            
            # Set capture properties
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.cap.set(cv2.CAP_PROP_FPS, self.fps)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize buffer for real-time
            
            # Verify settings
            actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = int(self.cap.get(cv2.CAP_PROP_FPS))
            
            logger.info(f"Video capture started: {actual_width}x{actual_height} @ {actual_fps}fps")
            
            self.is_running = True
            self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
            self.capture_thread.start()
            
            return True
            
        except Exception as e:
            logger.error(f"Error starting frame capture: {e}")
            return False
    
    def _capture_loop(self):
        """
        Main capture loop running in separate thread
        """
        logger.info("Capture loop started")
        
        while self.is_running:
            try:
                ret, frame = self.cap.read()
                
                if not ret:
                    logger.warning("Failed to read frame")
                    continue
                
                # Create Frame object
                timestamp = datetime.now()
                self.frame_counter += 1
                
                # Convert frame to bytes
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                frame_bytes = buffer.tobytes()
                
                frame_obj = Frame(
                    data=frame_bytes,
                    timestamp=timestamp,
                    frame_number=self.frame_counter,
                    width=frame.shape[1],
                    height=frame.shape[0],
                    channel_count=frame.shape[2] if len(frame.shape) > 2 else 1
                )
                
                # Add to queue (non-blocking, drop if full)
                try:
                    self.frame_queue.put(frame_obj, block=False)
                except queue.Full:
                    # Drop oldest frame and add new one
                    try:
                        self.frame_queue.get_nowait()
                        self.frame_queue.put(frame_obj, block=False)
                    except queue.Empty:
                        pass
                
            except Exception as e:
                logger.error(f"Error in capture loop: {e}")
                if not self.is_running:
                    break
        
        logger.info("Capture loop stopped")
    
    def get_frame(self, timeout: float = 1.0) -> Optional[Frame]:
        """
        Get the latest frame from the queue
        
        Args:
            timeout: Maximum time to wait for frame in seconds
            
        Returns:
            Frame object or None if timeout
        """
        try:
            return self.frame_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def frames(self) -> Generator[Frame, None, None]:
        """
        Generator that yields frames continuously
        
        Yields:
            Frame objects
        """
        while self.is_running:
            frame = self.get_frame(timeout=0.1)
            if frame:
                yield frame
    
    def stop(self):
        """
        Stop frame capture
        """
        logger.info("Stopping frame capture")
        self.is_running = False
        
        if self.capture_thread:
            self.capture_thread.join(timeout=2.0)
        
        if self.cap:
            self.cap.release()
        
        # Clear queue
        while not self.frame_queue.empty():
            try:
                self.frame_queue.get_nowait()
            except queue.Empty:
                break
        
        logger.info("Frame capture stopped")
    
    def __enter__(self):
        """Context manager entry"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.stop()
    
    @staticmethod
    def list_devices() -> list:
        """
        List available video capture devices
        
        Returns:
            List of device indices that can be opened
        """
        available_devices = []
        
        for i in range(10):  # Check first 10 devices
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                available_devices.append(i)
                cap.release()
        
        logger.info(f"Available video devices: {available_devices}")
        return available_devices


class FrameCaptureSimulator:
    """
    Simulator for testing without actual capture card
    Uses test images or generates synthetic frames
    """
    
    def __init__(self, test_images_dir: Optional[str] = None):
        """
        Initialize simulator
        
        Args:
            test_images_dir: Directory containing test images
        """
        self.test_images_dir = test_images_dir
        self.test_images = []
        self.current_index = 0
        self.frame_counter = 0
        self.is_running = False
        
        if test_images_dir and Path(test_images_dir).exists():
            self._load_test_images()
    
    def _load_test_images(self):
        """Load test images from directory"""
        import glob
        image_files = glob.glob(str(Path(self.test_images_dir) / "*.jpg")) + \
                      glob.glob(str(Path(self.test_images_dir) / "*.png"))
        
        for img_file in image_files:
            img = cv2.imread(img_file)
            if img is not None:
                self.test_images.append(img)
        
        logger.info(f"Loaded {len(self.test_images)} test images")
    
    def start(self):
        """Start simulator"""
        self.is_running = True
        logger.info("Frame capture simulator started")
    
    def get_frame(self) -> Optional[Frame]:
        """Get a frame (synthetic or from test images)"""
        if not self.is_running:
            return None
        
        if self.test_images:
            # Cycle through test images
            img = self.test_images[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.test_images)
        else:
            # Generate synthetic frame
            img = self._generate_synthetic_frame()
        
        # Convert to Frame object
        _, buffer = cv2.imencode('.jpg', img)
        frame_bytes = buffer.tobytes()
        
        self.frame_counter += 1
        
        return Frame(
            data=frame_bytes,
            timestamp=datetime.now(),
            frame_number=self.frame_counter,
            width=img.shape[1],
            height=img.shape[0],
            channel_count=img.shape[2] if len(img.shape) > 2 else 1
        )
    
    def _generate_synthetic_frame(self) -> np.ndarray:
        """Generate a synthetic test frame"""
        img = np.zeros((1080, 1920, 3), dtype=np.uint8)
        
        # Add some visual content
        cv2.rectangle(img, (100, 100), (1820, 980), (50, 50, 50), 2)
        cv2.putText(img, "NBA 2K - Test Frame", (400, 540), 
                   cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
        
        return img
    
    def stop(self):
        """Stop simulator"""
        self.is_running = False
        logger.info("Frame capture simulator stopped")
    
    def frames(self) -> Generator[Frame, None, None]:
        """Generator that yields frames"""
        while self.is_running:
            frame = self.get_frame()
            if frame:
                yield frame
