"""
ROI Extractor Module
Crops regions of interest from detected screens
"""

import cv2
import numpy as np
from datetime import datetime
from typing import List, Optional, Dict, Any
import logging
from pathlib import Path

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from processing_engine.models import Frame, DetectionResult, ROI, ExtractedRegion, ScreenType
from config.config_loader import load_config

logger = logging.getLogger(__name__)


class ROIExtractor:
    """
    Extracts regions of interest from detected screens
    """
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """
        Initialize ROI extractor
        
        Args:
            config_path: Path to configuration file
        """
        self.config = load_config(config_path)
        self.roi_config = self.config.get('roi_extractor', {})
        
        # Define ROI configurations for each screen type
        self.screen_rois: Dict[ScreenType, List[ROI]] = {}
        self._load_roi_definitions()
        
        logger.info(f"ROIExtractor initialized with {len(self.screen_rois)} screen types")
    
    def _load_roi_definitions(self):
        """Load ROI definitions from configuration"""
        for screen_name, rois in self.roi_config.items():
            try:
                screen_type = ScreenType(screen_name)
                roi_list = []
                
                for label, coords in rois.items():
                    if len(coords) == 4:
                        x, y, width, height = coords
                        roi = ROI(x=x, y=y, width=width, height=height, label=label)
                        roi_list.append(roi)
                
                self.screen_rois[screen_type] = roi_list
                logger.info(f"Loaded {len(roi_list)} ROIs for {screen_name}")
                
            except ValueError:
                logger.warning(f"Unknown screen type: {screen_name}")
            except Exception as e:
                logger.error(f"Error loading ROI for {screen_name}: {e}")
    
    def extract(self, frame: Frame, detection: DetectionResult) -> List[ExtractedRegion]:
        """
        Extract regions of interest from a frame based on detection
        
        Args:
            frame: Input frame
            detection: Detection result from frame detector
            
        Returns:
            List of extracted regions
        """
        screen_type = detection.screen_type
        
        if screen_type == ScreenType.UNKNOWN:
            logger.debug("Unknown screen type, skipping ROI extraction")
            return []
        
        if screen_type not in self.screen_rois:
            logger.warning(f"No ROIs defined for screen type: {screen_type}")
            return []
        
        try:
            # Decode frame
            nparr = np.frombuffer(frame.data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                logger.error("Failed to decode frame for ROI extraction")
                return []
            
            # Extract regions
            rois = self.screen_rois[screen_type]
            extracted_regions = []
            
            for roi in rois:
                try:
                    # Validate ROI bounds
                    roi = self._validate_roi(roi, img.shape)
                    
                    if roi is None:
                        logger.warning(f"Invalid ROI bounds: {roi.label}")
                        continue
                    
                    # Crop region
                    cropped = img[roi.y:roi.y + roi.height, roi.x:roi.x + roi.width]
                    
                    # Encode cropped region
                    _, buffer = cv2.imencode('.png', cropped)
                    region_bytes = buffer.tobytes()
                    
                    extracted_region = ExtractedRegion(
                        roi=roi,
                        image_data=region_bytes,
                        timestamp=datetime.now()
                    )
                    
                    extracted_regions.append(extracted_region)
                    
                except Exception as e:
                    logger.error(f"Error extracting ROI {roi.label}: {e}")
                    continue
            
            logger.debug(f"Extracted {len(extracted_regions)} regions from {screen_type}")
            return extracted_regions
            
        except Exception as e:
            logger.error(f"Error in ROI extraction: {e}")
            return []
    
    def _validate_roi(self, roi: ROI, image_shape: tuple) -> Optional[ROI]:
        """
        Validate and adjust ROI bounds to fit within image
        
        Args:
            roi: ROI to validate
            image_shape: Image shape (height, width, channels)
            
        Returns:
            Validated ROI or None if invalid
        """
        img_height, img_width = image_shape[:2]
        
        # Check if ROI is within image bounds
        if roi.x < 0 or roi.y < 0:
            return None
        if roi.x + roi.width > img_width or roi.y + roi.height > img_height:
            return None
        if roi.width <= 0 or roi.height <= 0:
            return None
        
        return roi
    
    def add_roi(self, screen_type: ScreenType, roi: ROI):
        """
        Add a new ROI definition for a screen type
        
        Args:
            screen_type: Screen type to add ROI for
            roi: ROI to add
        """
        if screen_type not in self.screen_rois:
            self.screen_rois[screen_type] = []
        
        self.screen_rois[screen_type].append(roi)
        logger.info(f"Added ROI '{roi.label}' to {screen_type}")
    
    def remove_roi(self, screen_type: ScreenType, label: str):
        """
        Remove an ROI definition from a screen type
        
        Args:
            screen_type: Screen type to remove ROI from
            label: Label of ROI to remove
        """
        if screen_type in self.screen_rois:
            self.screen_rois[screen_type] = [
                roi for roi in self.screen_rois[screen_type] 
                if roi.label != label
            ]
            logger.info(f"Removed ROI '{label}' from {screen_type}")
    
    def get_rois(self, screen_type: ScreenType) -> List[ROI]:
        """
        Get all ROIs for a screen type
        
        Args:
            screen_type: Screen type to get ROIs for
            
        Returns:
            List of ROIs
        """
        return self.screen_rois.get(screen_type, [])
    
    def auto_detect_rois(self, frame: Frame, detection: DetectionResult) -> List[ROI]:
        """
        Automatically detect ROIs using image analysis
        
        Args:
            frame: Input frame
            detection: Detection result
            
        Returns:
            List of detected ROIs
        """
        try:
            # Decode frame
            nparr = np.frombuffer(frame.data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                return []
            
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Detect text regions using MSER
            mser = cv2.MSER_create()
            regions, _ = mser.detectRegions(gray)
            
            # Convert regions to bounding boxes
            rois = []
            for i, region in enumerate(regions):
                if len(region) < 5:
                    continue
                
                # Get bounding box
                x, y, w, h = cv2.boundingRect(region)
                
                # Filter small regions
                if w < 20 or h < 10:
                    continue
                
                roi = ROI(x=x, y=y, width=w, height=h, label=f"auto_{i}")
                rois.append(roi)
            
            # Merge overlapping ROIs
            rois = self._merge_overlapping_rois(rois)
            
            logger.info(f"Auto-detected {len(rois)} ROIs")
            return rois
            
        except Exception as e:
            logger.error(f"Error in auto ROI detection: {e}")
            return []
    
    def _merge_overlapping_rois(self, rois: List[ROI], iou_threshold: float = 0.5) -> List[ROI]:
        """
        Merge overlapping ROIs based on IoU threshold
        
        Args:
            rois: List of ROIs to merge
            iou_threshold: IoU threshold for merging
            
        Returns:
            List of merged ROIs
        """
        if not rois:
            return []
        
        merged = [rois[0]]
        
        for roi in rois[1:]:
            merged_with_existing = False
            
            for i, existing_roi in enumerate(merged):
                iou = self._calculate_iou(roi, existing_roi)
                
                if iou > iou_threshold:
                    # Merge ROIs
                    x1 = min(roi.x, existing_roi.x)
                    y1 = min(roi.y, existing_roi.y)
                    x2 = max(roi.x + roi.width, existing_roi.x + existing_roi.width)
                    y2 = max(roi.y + roi.height, existing_roi.y + existing_roi.height)
                    
                    merged_roi = ROI(
                        x=x1,
                        y=y1,
                        width=x2 - x1,
                        height=y2 - y1,
                        label=f"merged_{existing_roi.label}_{roi.label}"
                    )
                    
                    merged[i] = merged_roi
                    merged_with_existing = True
                    break
            
            if not merged_with_existing:
                merged.append(roi)
        
        return merged
    
    def _calculate_iou(self, roi1: ROI, roi2: ROI) -> float:
        """
        Calculate Intersection over Union (IoU) between two ROIs
        
        Args:
            roi1: First ROI
            roi2: Second ROI
            
        Returns:
            IoU value
        """
        # Calculate intersection
        x1 = max(roi1.x, roi2.x)
        y1 = max(roi1.y, roi2.y)
        x2 = min(roi1.x + roi1.width, roi2.x + roi2.width)
        y2 = min(roi1.y + roi1.height, roi2.y + roi2.height)
        
        if x2 <= x1 or y2 <= y1:
            return 0.0
        
        intersection = (x2 - x1) * (2 - y1)
        
        # Calculate union
        area1 = roi1.width * roi1.height
        area2 = roi2.width * roi2.height
        union = area1 + area2 - intersection
        
        if union == 0:
            return 0.0
        
        return intersection / union
    
    def visualize_rois(self, frame: Frame, detection: DetectionResult, output_path: Optional[str] = None):
        """
        Visualize ROIs on a frame for debugging
        
        Args:
            frame: Input frame
            detection: Detection result
            output_path: Optional path to save visualization
        """
        try:
            # Decode frame
            nparr = np.frombuffer(frame.data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                return
            
            # Get ROIs for this screen type
            rois = self.get_rois(detection.screen_type)
            
            # Draw ROIs on image
            for roi in rois:
                cv2.rectangle(img, (roi.x, roi.y), 
                            (roi.x + roi.width, roi.y + roi.height), 
                            (0, 255, 0), 2)
                cv2.putText(img, roi.label, (roi.x, roi.y - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            # Save or display
            if output_path:
                cv2.imwrite(output_path, img)
                logger.info(f"Saved ROI visualization to {output_path}")
            else:
                cv2.imshow("ROI Visualization", img)
                cv2.waitKey(0)
                cv2.destroyAllWindows()
                
        except Exception as e:
            logger.error(f"Error visualizing ROIs: {e}")


class DynamicROIExtractor:
    """
    Dynamic ROI extractor that adapts to different screen layouts
    """
    
    def __init__(self):
        """Initialize dynamic ROI extractor"""
        self.base_extractor = ROIExtractor()
        self.adaptive_rois: Dict[str, List[ROI]] = {}
    
    def extract_with_adaptation(self, frame: Frame, detection: DetectionResult) -> List[ExtractedRegion]:
        """
        Extract ROIs with adaptive layout detection
        
        Args:
            frame: Input frame
            detection: Detection result
            
        Returns:
            List of extracted regions
        """
        # First try standard extraction
        regions = self.base_extractor.extract(frame, detection)
        
        if not regions:
            # Fall back to auto-detection
            auto_rois = self.base_extractor.auto_detect_rois(frame, detection)
            
            # Use auto-detected ROIs
            for roi in auto_rois:
                try:
                    nparr = np.frombuffer(frame.data, np.uint8)
                    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    
                    if img is None:
                        continue
                    
                    cropped = img[roi.y:roi.y + roi.height, roi.x:roi.x + roi.width]
                    _, buffer = cv2.imencode('.png', cropped)
                    region_bytes = buffer.tobytes()
                    
                    region = ExtractedRegion(
                        roi=roi,
                        image_data=region_bytes,
                        timestamp=datetime.now()
                    )
                    regions.append(region)
                    
                except Exception as e:
                    logger.error(f"Error extracting adaptive ROI: {e}")
                    continue
        
        return regions
    
    def learn_layout(self, frames: List[Frame], detections: List[DetectionResult]):
        """
        Learn common ROI layouts from sample frames
        
        Args:
            frames: Sample frames
            detections: Corresponding detections
        """
        logger.info("Learning ROI layouts from sample frames")
        
        # Analyze frames to find common patterns
        layout_data = {}
        
        for frame, detection in zip(frames, detections):
            screen_type = detection.screen_type
            
            if screen_type == ScreenType.UNKNOWN:
                continue
            
            auto_rois = self.base_extractor.auto_detect_rois(frame, detection)
            
            if screen_type not in layout_data:
                layout_data[screen_type] = []
            
            layout_data[screen_type].append(auto_rois)
        
        # Find common ROIs across frames
        for screen_type, roi_lists in layout_data.items():
            common_rois = self._find_common_rois(roi_lists)
            self.adaptive_rois[screen_type.value] = common_rois
            logger.info(f"Learned {len(common_rois)} common ROIs for {screen_type}")
    
    def _find_common_rois(self, roi_lists: List[List[ROI]], min_occurrence: int = 2) -> List[ROI]:
        """
        Find ROIs that appear in multiple frames
        
        Args:
            roi_lists: Lists of ROIs from different frames
            min_occurrence: Minimum number of frames for ROI to be considered common
            
        Returns:
            List of common ROIs
        """
        # Count ROI occurrences
        roi_counts = {}
        
        for roi_list in roi_lists:
            for roi in roi_list:
                key = (roi.x, roi.y, roi.width, roi.height)
                roi_counts[key] = roi_counts.get(key, 0) + 1
        
        # Filter common ROIs
        common_rois = []
        for (x, y, w, h), count in roi_counts.items():
            if count >= min_occurrence:
                roi = ROI(x=x, y=y, width=w, height=h, label=f"common_{count}")
                common_rois.append(roi)
        
        return common_rois
