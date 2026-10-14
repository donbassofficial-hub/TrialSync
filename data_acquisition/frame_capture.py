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
import time
from pathlib import Path
import sys

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
                    logger.warning("Failed to read frame - device may be disconnected")
                    # Don't crash the pipeline, just continue and try again
                    time.sleep(0.1)  # Brief pause before retry
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
                
            except cv2.error as e:
                # Handle OpenCV-specific errors (including device disconnection)
                logger.error(f"OpenCV error in capture loop: {e}")
                logger.warning("Device may have been disconnected. Attempting to recover...")
                
                # Try to reopen the device
                if self._attempt_device_recovery():
                    logger.info("Device recovered successfully")
                else:
                    logger.error("Failed to recover device, stopping capture")
                    self.is_running = False
                    break
                    
            except Exception as e:
                logger.error(f"Unexpected error in capture loop: {e}")
                if not self.is_running:
                    break
        
        logger.info("Capture loop stopped")
    
    def _attempt_device_recovery(self) -> bool:
        """
        Attempt to recover the capture device after disconnection
        
        Returns:
            True if recovery was successful
        """
        try:
            # Release the old capture object
            if self.cap:
                self.cap.release()
            
            # Attempt to reopen the device
            self.cap = cv2.VideoCapture(self.device_index)
            
            if self.cap.isOpened():
                # Re-apply settings
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                self.cap.set(cv2.CAP_PROP_FPS, self.fps)
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                
                logger.info(f"Device recovery successful for index {self.device_index}")
                return True
            else:
                logger.error(f"Failed to reopen device {self.device_index}")
                return False
                
        except Exception as e:
            logger.error(f"Error during device recovery: {e}")
            return False
    
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
        else:
            logger.info("No test images directory provided, will use synthetic frames")
    
    def _load_test_images(self):
        """Load test images from directory"""
        import glob
        image_files = glob.glob(str(Path(self.test_images_dir) / "*.jpg")) + \
                      glob.glob(str(Path(self.test_images_dir) / "*.png"))
        
        for img_file in image_files:
            img = cv2.imread(img_file)
            if img is not None:
                self.test_images.append(img)
        
        if self.test_images:
            logger.info(f"Loaded {len(self.test_images)} test images from {self.test_images_dir}")
        else:
            logger.warning(f"No test images found in {self.test_images_dir}, will use synthetic frames")
    
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
        """Generate a synthetic test frame with realistic NBA 2K content"""
        img = np.zeros((1080, 1920, 3), dtype=np.uint8)
        
        # Create dark background like NBA 2K
        img[:] = (20, 20, 30)
        
        # Cycle through different screen types for variety
        screen_type = self.frame_counter % 4
        
        logger.debug(f"Generating synthetic frame type: {screen_type}")
        
        if screen_type == 0:
            # Generate scoreboard-style frame
            self._generate_scoreboard_frame(img)
        elif screen_type == 1:
            # Generate box score-style frame
            self._generate_box_score_frame(img)
        elif screen_type == 2:
            # Generate player stats-style frame
            self._generate_player_stats_frame(img)
        else:
            # Generate matchup screen frame
            self._generate_matchup_frame(img)
        
        return img
    
    def _generate_scoreboard_frame(self, img: np.ndarray):
        """Generate a realistic scoreboard frame"""
        # Header
        cv2.rectangle(img, (50, 50), (1870, 150), (40, 40, 50), -1)
        cv2.putText(img, "SCOREBOARD", (800, 100), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 200, 0), 3)
        
        # Player info section
        cv2.rectangle(img, (100, 200), (400, 250), (60, 60, 70), -1)
        cv2.putText(img, "LeBron James", (120, 235), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        # Stats boxes
        stats = ["PTS: 28", "REB: 7", "AST: 11"]
        x_positions = [350, 460, 570]
        
        for i, (stat, x) in enumerate(zip(stats, x_positions)):
            cv2.rectangle(img, (x, 200), (x + 100, 250), (80, 80, 90), -1)
            cv2.putText(img, stat, (x + 10, 235), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    def _generate_box_score_frame(self, img: np.ndarray):
        """Generate a realistic box score frame"""
        # Header
        cv2.rectangle(img, (50, 50), (1870, 120), (40, 40, 50), -1)
        cv2.putText(img, "BOX SCORE", (800, 95), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 200, 0), 3)
        
        # Player rows
        players = [
            ("LeBron James", "9/15", "4/8", "6/7", "28", "7", "11", "2", "1", "3"),
            ("Anthony Davis", "8/14", "3/6", "4/5", "23", "12", "3", "1", "4", "2"),
            ("Russell Westbrook", "6/12", "2/5", "3/4", "17", "5", "8", "3", "0", "4")
        ]
        
        start_y = 180
        for i, player in enumerate(players):
            y = start_y + i * 60
            
            # Player name
            cv2.rectangle(img, (50, y), (250, y + 50), (60, 60, 70), -1)
            cv2.putText(img, player[0], (60, y + 35), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            # Stats columns
            x_positions = [260, 350, 440, 530, 600, 670, 740, 810, 880]
            for j, (stat, x) in enumerate(zip(player[1:], x_positions)):
                cv2.rectangle(img, (x, y), (x + 60, y + 50), (70, 70, 80), -1)
                cv2.putText(img, stat, (x + 5, y + 35), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    
    def _generate_player_stats_frame(self, img: np.ndarray):
        """Generate a realistic player stats frame"""
        # Header
        cv2.rectangle(img, (50, 50), (1870, 120), (40, 40, 50), -1)
        cv2.putText(img, "PLAYER ATTRIBUTES", (750, 95), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 200, 0), 3)
        
        # Player name
        cv2.rectangle(img, (100, 180), (500, 230), (60, 60, 70), -1)
        cv2.putText(img, "LeBron James", (120, 215), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
        
        # Attributes grid
        attributes = [
            ("3PT Shot: 92", "Driving Dunk: 85"),
            ("Mid-Range: 88", "Standing Dunk: 70"),
            ("Free Throw: 78", "Post Control: 75"),
            ("Pass Accuracy: 89", "Ball Handle: 82"),
            ("Speed: 78", "Acceleration: 80")
        ]
        
        start_y = 280
        for i, (attr1, attr2) in enumerate(attributes):
            y = start_y + i * 70
            
            # Left attribute
            cv2.rectangle(img, (100, y), (400, y + 60), (70, 70, 80), -1)
            cv2.putText(img, attr1, (120, y + 40), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Right attribute
            cv2.rectangle(img, (500, y), (800, y + 60), (70, 70, 80), -1)
            cv2.putText(img, attr2, (520, y + 40), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    def _generate_matchup_frame(self, img: np.ndarray):
        """Generate a realistic player matchup frame"""
        # Header
        cv2.rectangle(img, (50, 50), (1870, 120), (40, 40, 50), -1)
        cv2.putText(img, "PLAYER MATCHUP", (750, 95), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 200, 0), 3)
        
        # Divider line
        cv2.line(img, (960, 130), (960, 1000), (100, 100, 100), 2)
        
        # Left player data
        left_name = "Solos Turn"
        left_ovr = "85"
        left_position = "SF"
        left_height = "6'8\""
        left_weight = "185"
        
        # Left player header
        cv2.rectangle(img, (100, 180), (400, 230), (60, 60, 70), -1)
        cv2.putText(img, left_name, (120, 215), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        # Left player info row
        info_row_y = 260
        left_info = [
            (f"OVR: {left_ovr}", 100),
            (left_position, 200),
            (left_height, 320),
            (f"{left_weight} lbs", 440)
        ]
        
        for info, x in left_info:
            cv2.rectangle(img, (x, info_row_y), (x + 100, info_row_y + 40), (70, 70, 80), -1)
            cv2.putText(img, info, (x + 5, info_row_y + 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Left player key stats
        left_stats = [
            ("Mid-Range: 94", 100, 320),
            ("Three-Point: 91", 100, 380),
            ("Ball Handle: 86", 100, 440),
            ("Speed: 80", 100, 500),
            ("Agility: 80", 100, 560),
            ("Speed w/ Ball: 80", 100, 620)
        ]
        
        for stat, x, y in left_stats:
            cv2.rectangle(img, (x, y), (x + 250, y + 40), (75, 75, 85), -1)
            cv2.putText(img, stat, (x + 5, y + 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Left player average stats
        avg_header_y = 680
        cv2.putText(img, "LAST 20 GAMES", (100, avg_header_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 2)
        
        left_avg_stats = [
            ("PPG: 0.0", 100, 700),
            ("RPG: 0.0", 220, 700),
            ("APG: 0.0", 340, 700),
            ("FG%: N/A", 460, 700),
            ("3PT%: N/A", 580, 700)
        ]
        
        for stat, x, y in left_avg_stats:
            cv2.rectangle(img, (x, y), (x + 100, y + 40), (80, 60, 60), -1)
            cv2.putText(img, stat, (x + 5, y + 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 200, 200), 2)
        
        # Right player data
        right_name = "leeannston"
        right_ovr = "88"
        right_position = "SG"
        right_height = "6'5\""
        right_weight = "220"
        
        # Right player header
        cv2.rectangle(img, (1000, 180), (1300, 230), (60, 60, 70), -1)
        cv2.putText(img, right_name, (1020, 215), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        # Right player info row
        right_info = [
            (f"OVR: {right_ovr}", 1000),
            (right_position, 1100),
            (right_height, 1220),
            (f"{right_weight} lbs", 1340)
        ]
        
        for info, x in right_info:
            cv2.rectangle(img, (x, info_row_y), (x + 100, info_row_y + 40), (70, 70, 80), -1)
            cv2.putText(img, info, (x + 5, info_row_y + 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Right player key stats
        right_stats = [
            ("Three-Point: 94", 1000, 320),
            ("Speed: 87", 1000, 380),
            ("Perimeter D: 86", 1000, 440),
            ("Strength: 85", 1000, 500),
            ("Agility: 83", 1000, 560),
            ("Ball Handle: 81", 1000, 620)
        ]
        
        for stat, x, y in right_stats:
            cv2.rectangle(img, (x, y), (x + 250, y + 40), (75, 75, 85), -1)
            cv2.putText(img, stat, (x + 5, y + 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Right player average stats
        cv2.putText(img, "LAST 20 GAMES", (1000, avg_header_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 2)
        
        right_avg_stats = [
            ("PPG: 5.7", 1000, 700),
            ("RPG: 0.3", 1120, 700),
            ("APG: 1.3", 1240, 700),
            ("FG%: 31.6", 1360, 700),
            ("3PT%: 33.3", 1480, 700)
        ]
        
        for stat, x, y in right_avg_stats:
            cv2.rectangle(img, (x, y), (x + 100, y + 40), (80, 100, 80), -1)
            cv2.putText(img, stat, (x + 5, y + 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 255, 200), 2)
        
        # Grade for right player
        cv2.rectangle(img, (1600, 700), (1700, 740), (100, 150, 100), -1)
        cv2.putText(img, "B-", (1620, 730), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
    
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
            time.sleep(0.033)  # ~30 FPS to simulate real capture timing
    
    @staticmethod
    def list_devices() -> list:
        """
        List available video capture devices (static method for interface compatibility)
        
        Returns:
            Empty list since simulator doesn't use real devices
        """
        logger.info("Simulator mode - no real devices needed")
        return []
