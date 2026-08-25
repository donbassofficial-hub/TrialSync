"""
Frame Detector Module
Classifies NBA 2K screens using computer vision
"""

import cv2
import numpy as np
from datetime import datetime
from typing import Optional, Dict, Any
import logging
from pathlib import Path

from .models import Frame, DetectionResult, ScreenType
from ..config.config_loader import load_config

logger = logging.getLogger(__name__)


class FrameDetector:
    """
    Detects and classifies NBA 2K screens from video frames
    """
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """
        Initialize frame detector
        
        Args:
            config_path: Path to configuration file
        """
        self.config = load_config(config_path)
        self.detector_config = self.config.get('frame_detector', {})
        
        self.confidence_threshold = self.detector_config.get('confidence_threshold', 0.75)
        self.model_path = self.detector_config.get('model_path', 'models/screen_detector.pth')
        self.screen_types = self.detector_config.get('screen_types', [])
        
        # Initialize template matching system
        self.templates: Dict[ScreenType, np.ndarray] = {}
        self._load_templates()
        
        logger.info(f"FrameDetector initialized with {len(self.screen_types)} screen types")
    
    def _load_templates(self):
        """
        Load template images for screen detection
        In production, this would use a trained ML model
        """
        templates_dir = Path("models/templates")
        
        if templates_dir.exists():
            for screen_type in self.screen_types:
                template_path = templates_dir / f"{screen_type}.png"
                if template_path.exists():
                    template = cv2.imread(str(template_path), cv2.IMREAD_GRAYSCALE)
                    if template is not None:
                        self.templates[ScreenType(screen_type)] = template
                        logger.info(f"Loaded template for {screen_type}")
        
        if not self.templates:
            logger.warning("No templates loaded, using feature-based detection")
    
    def detect(self, frame: Frame) -> DetectionResult:
        """
        Detect the screen type from a frame
        
        Args:
            frame: Input frame
            
        Returns:
            DetectionResult with screen type and confidence
        """
        try:
            # Decode frame data
            nparr = np.frombuffer(frame.data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                logger.error("Failed to decode frame")
                return self._unknown_result(frame)
            
            # Try template matching first
            if self.templates:
                result = self._template_match(img, frame)
                if result.confidence >= self.confidence_threshold:
                    return result
            
            # Fall back to feature-based detection
            result = self._feature_based_detection(img, frame)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in frame detection: {e}")
            return self._unknown_result(frame)
    
    def _template_match(self, img: np.ndarray, frame: Frame) -> DetectionResult:
        """
        Detect screen using template matching
        
        Args:
            img: OpenCV image
            frame: Original frame object
            
        Returns:
            DetectionResult
        """
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        best_match = ScreenType.UNKNOWN
        best_confidence = 0.0
        
        for screen_type, template in self.templates.items():
            try:
                # Multi-scale template matching
                for scale in [0.8, 0.9, 1.0, 1.1, 1.2]:
                    scaled_template = cv2.resize(template, None, fx=scale, fy=scale)
                    
                    if scaled_template.shape[0] > gray.shape[0] or scaled_template.shape[1] > gray.shape[1]:
                        continue
                    
                    result = cv2.matchTemplate(gray, scaled_template, cv2.TM_CCOEFF_NORMED)
                    _, max_val, _, _ = cv2.minMaxLoc(result)
                    
                    if max_val > best_confidence:
                        best_confidence = max_val
                        best_match = screen_type
                        
            except Exception as e:
                logger.debug(f"Template matching error for {screen_type}: {e}")
                continue
        
        return DetectionResult(
            screen_type=best_match,
            confidence=best_confidence,
            timestamp=datetime.now(),
            frame_number=frame.frame_number,
            metadata={'method': 'template_matching'}
        )
    
    def _feature_based_detection(self, img: np.ndarray, frame: Frame) -> DetectionResult:
        """
        Detect screen using feature-based heuristics
        
        Args:
            img: OpenCV image
            frame: Original frame object
            
        Returns:
            DetectionResult
        """
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Extract features and use heuristics
        features = self._extract_features(gray)
        
        # Classify based on features
        screen_type, confidence = self._classify_features(features)
        
        return DetectionResult(
            screen_type=screen_type,
            confidence=confidence,
            timestamp=datetime.now(),
            frame_number=frame.frame_number,
            metadata={'method': 'feature_based', 'features': features}
        )
    
    def _extract_features(self, gray: np.ndarray) -> Dict[str, Any]:
        """
        Extract features from grayscale image
        
        Args:
            gray: Grayscale image
            
        Returns:
            Dictionary of features
        """
        features = {}
        
        # Edge detection
        edges = cv2.Canny(gray, 50, 150)
        features['edge_density'] = np.sum(edges > 0) / edges.size
        
        # Histogram
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
        features['histogram'] = hist.flatten()
        
        # Texture features
        features['mean_intensity'] = np.mean(gray)
        features['std_intensity'] = np.std(gray)
        
        # Contour analysis
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        features['contour_count'] = len(contours)
        
        # Text regions (potential OCR areas)
        features['text_regions'] = self._detect_text_regions(gray)
        
        return features
    
    def _detect_text_regions(self, gray: np.ndarray) -> int:
        """
        Detect potential text regions in image
        
        Args:
            gray: Grayscale image
            
        Returns:
            Number of text regions detected
        """
        # Use MSER to detect text-like regions
        mser = cv2.MSER_create()
        regions, _ = mser.detectRegions(gray)
        return len(regions)
    
    def _classify_features(self, features: Dict[str, Any]) -> tuple[ScreenType, float]:
        """
        Classify screen based on extracted features
        
        Args:
            features: Feature dictionary
            
        Returns:
            Tuple of (screen_type, confidence)
        """
        # Heuristic classification based on features
        # In production, this would use a trained classifier
        
        edge_density = features.get('edge_density', 0)
        contour_count = features.get('contour_count', 0)
        text_regions = features.get('text_regions', 0)
        mean_intensity = features.get('mean_intensity', 128)
        
        # Simple heuristic rules
        if text_regions > 50 and contour_count > 20:
            # Likely a stats screen with lots of text
            if edge_density > 0.15:
                return ScreenType.BOX_SCORE, 0.6
            else:
                return ScreenType.PLAYER_STATS, 0.55
        elif contour_count > 30 and edge_density > 0.2:
            # Complex UI, likely scoreboard
            return ScreenType.SCOREBOARD, 0.5
        elif text_regions > 100:
            # Lots of text, could be player attributes
            return ScreenType.PLAYER_ATTRIBUTES, 0.45
        else:
            return ScreenType.UNKNOWN, 0.3
    
    def _unknown_result(self, frame: Frame) -> DetectionResult:
        """
        Return unknown detection result
        
        Args:
            frame: Original frame object
            
        Returns:
            DetectionResult with UNKNOWN screen type
        """
        return DetectionResult(
            screen_type=ScreenType.UNKNOWN,
            confidence=0.0,
            timestamp=datetime.now(),
            frame_number=frame.frame_number,
            metadata={'method': 'unknown'}
        )
    
    def train(self, training_data_path: str):
        """
        Train the detector with labeled data
        
        Args:
            training_data_path: Path to training data directory
        """
        logger.info(f"Training detector with data from {training_data_path}")
        # In production, this would train a neural network
        # For now, this is a placeholder
        logger.warning("Training not implemented in current version")


class ScreenClassifier:
    """
    Alternative screen classifier using pre-trained models
    """
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize classifier
        
        Args:
            model_path: Path to pre-trained model
        """
        self.model_path = model_path
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load pre-trained model"""
        if self.model_path and Path(self.model_path).exists():
            try:
                import torch
                self.model = torch.load(self.model_path)
                self.model.eval()
                logger.info(f"Loaded model from {self.model_path}")
            except Exception as e:
                logger.error(f"Failed to load model: {e}")
    
    def classify(self, frame: Frame) -> DetectionResult:
        """
        Classify screen using deep learning model
        
        Args:
            frame: Input frame
            
        Returns:
            DetectionResult
        """
        if self.model is None:
            # Fall back to basic detection
            detector = FrameDetector()
            return detector.detect(frame)
        
        try:
            import torch
            from torchvision import transforms
            
            # Preprocess frame
            nparr = np.frombuffer(frame.data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # Convert to tensor
            transform = transforms.Compose([
                transforms.ToPILImage(),
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                                   std=[0.229, 0.224, 0.225])
            ])
            
            img_tensor = transform(img).unsqueeze(0)
            
            # Run inference
            with torch.no_grad():
                outputs = self.model(img_tensor)
                probabilities = torch.softmax(outputs, dim=1)
                confidence, predicted = torch.max(probabilities, 1)
            
            # Map prediction to screen type
            screen_type = self._map_prediction_to_screen_type(predicted.item())
            
            return DetectionResult(
                screen_type=screen_type,
                confidence=confidence.item(),
                timestamp=datetime.now(),
                frame_number=frame.frame_number,
                metadata={'method': 'deep_learning'}
            )
            
        except Exception as e:
            logger.error(f"Error in model classification: {e}")
            detector = FrameDetector()
            return detector.detect(frame)
    
    def _map_prediction_to_screen_type(self, prediction: int) -> ScreenType:
        """
        Map model prediction to ScreenType enum
        
        Args:
            prediction: Model output class index
            
        Returns:
            ScreenType
        """
        # This mapping should match the model's class indices
        screen_types = [
            ScreenType.SCOREBOARD,
            ScreenType.BOX_SCORE,
            ScreenType.PLAYER_STATS,
            ScreenType.TEAM_STATS,
            ScreenType.MATCHUP_SCREEN,
            ScreenType.PLAYER_CARD,
            ScreenType.PLAYER_ATTRIBUTES,
            ScreenType.SHOT_INFO,
            ScreenType.GAME_SUMMARY,
            ScreenType.FINAL_RESULTS
        ]
        
        if 0 <= prediction < len(screen_types):
            return screen_types[prediction]
        return ScreenType.UNKNOWN
