"""
OCR/Data Parser Module
Extracts text and numbers from regions using OCR
"""

import cv2
import numpy as np
import pytesseract
from datetime import datetime
from typing import Optional, Dict, Any, List
import re
import logging
from pathlib import Path

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from processing_engine.models import ExtractedRegion, OCRResult, PlayerStats, PlayerAttributes, ScreenType
from config.config_loader import load_config

logger = logging.getLogger(__name__)


class OCRParser:
    """
    Parses text and numbers from extracted regions using OCR
    """
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """
        Initialize OCR parser
        
        Args:
            config_path: Path to configuration file
        """
        self.config = load_config(config_path)
        self.ocr_config = self.config.get('ocr', {})
        
        self.engine = self.ocr_config.get('engine', 'tesseract')
        self.language = self.ocr_config.get('language', 'eng')
        self.confidence_threshold = self.ocr_config.get('confidence_threshold', 0.7)
        self.preprocessing_config = self.ocr_config.get('preprocessing', {})
        
        # Configure Tesseract
        self._configure_tesseract()
        
        logger.info(f"OCRParser initialized with {self.engine} engine")
    
    def _configure_tesseract(self):
        """Configure Tesseract OCR engine"""
        try:
            # Test Tesseract availability
            pytesseract.get_tesseract_version()
            logger.info("Tesseract OCR configured successfully")
        except Exception as e:
            logger.error(f"Tesseract not available: {e}")
            logger.warning("OCR functionality will be limited")
    
    def parse(self, region: ExtractedRegion) -> OCRResult:
        """
        Parse text from an extracted region
        
        Args:
            region: Extracted region to parse
            
        Returns:
            OCRResult with extracted text and confidence
        """
        try:
            # Decode region image
            nparr = np.frombuffer(region.image_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                logger.error("Failed to decode region image")
                return OCRResult(
                    text="",
                    confidence=0.0,
                    region_label=region.roi.label,
                    timestamp=datetime.now()
                )
            
            # Preprocess image
            processed_img = self._preprocess_image(img)
            
            # Perform OCR
            text, confidence = self._perform_ocr(processed_img)
            
            # Post-process text
            cleaned_text = self._clean_text(text)
            
            return OCRResult(
                text=cleaned_text,
                confidence=confidence,
                region_label=region.roi.label,
                timestamp=datetime.now(),
                raw_data=region.image_data
            )
            
        except Exception as e:
            logger.error(f"Error parsing region {region.roi.label}: {e}")
            return OCRResult(
                text="",
                confidence=0.0,
                region_label=region.roi.label,
                timestamp=datetime.now()
            )
    
    def _preprocess_image(self, img: np.ndarray) -> np.ndarray:
        """
        Preprocess image for better OCR results
        
        Args:
            img: Input image
            
        Returns:
            Preprocessed image
        """
        processed = img.copy()
        
        # Convert to grayscale
        if self.preprocessing_config.get('grayscale', True):
            processed = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)
        
        # Apply thresholding
        if self.preprocessing_config.get('threshold', True):
            processed = cv2.threshold(
                processed, 0, 255, 
                cv2.THRESH_BINARY + cv2.THRESH_OTSU
            )[1]
        
        # Denoise
        if self.preprocessing_config.get('denoise', True):
            processed = cv2.fastNlMeansDenoising(processed, None, 10, 7, 21)
        
        # Resize for better OCR (Tesseract works best with ~300 DPI)
        height, width = processed.shape[:2]
        scale_factor = 2.0
        processed = cv2.resize(processed, None, fx=scale_factor, fy=scale_factor, 
                               interpolation=cv2.INTER_CUBIC)
        
        return processed
    
    def _perform_ocr(self, img: np.ndarray) -> tuple[str, float]:
        """
        Perform OCR on preprocessed image
        
        Args:
            img: Preprocessed image
            
        Returns:
            Tuple of (text, confidence)
        """
        try:
            # Configure Tesseract options
            config = f'--psm 6 -l {self.language}'
            
            # Get OCR data with confidence
            data = pytesseract.image_to_data(
                img, 
                config=config,
                output_type=pytesseract.Output.DICT
            )
            
            # Extract text and calculate average confidence
            text_parts = []
            confidences = []
            
            for i, text in enumerate(data['text']):
                conf = int(data['conf'][i])
                if conf > 0:  # Filter out low-confidence detections
                    text_parts.append(text.strip())
                    confidences.append(conf)
            
            text = ' '.join(text_parts)
            avg_confidence = np.mean(confidences) / 100.0 if confidences else 0.0
            
            return text, avg_confidence
            
        except Exception as e:
            logger.error(f"Error performing OCR: {e}")
            return "", 0.0
    
    def _clean_text(self, text: str) -> str:
        """
        Clean and normalize OCR output
        
        Args:
            text: Raw OCR text
            
        Returns:
            Cleaned text
        """
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        # Fix common OCR errors
        text = text.replace('|', 'I')  # Common misrecognition
        text = text.replace('0', 'O')  # Sometimes numbers are letters
        
        return text.strip()
    
    def parse_player_stats(self, regions: List[ExtractedRegion]) -> Optional[PlayerStats]:
        """
        Parse player statistics from multiple regions
        
        Args:
            regions: List of extracted regions containing player stats
            
        Returns:
            PlayerStats object or None if parsing fails
        """
        try:
            stats_dict = {}
            
            # Parse each region
            for region in regions:
                ocr_result = self.parse(region)
                
                if ocr_result.confidence < self.confidence_threshold:
                    logger.debug(f"Low confidence for {region.roi.label}: {ocr_result.confidence}")
                    continue
                
                # Map region label to stat field
                stat_value = self._extract_stat_value(ocr_result.text, region.roi.label)
                if stat_value is not None:
                    stats_dict[region.roi.label] = stat_value
            
            # Create PlayerStats object
            player_stats = PlayerStats(
                player_name=stats_dict.get('player_name', ''),
                points=stats_dict.get('points'),
                rebounds=stats_dict.get('rebounds'),
                assists=stats_dict.get('assists'),
                steals=stats_dict.get('steals'),
                blocks=stats_dict.get('blocks'),
                turnovers=stats_dict.get('turnovers'),
                fg_made=stats_dict.get('fg_made'),
                fg_attempted=stats_dict.get('fg_attempted'),
                three_pt_made=stats_dict.get('three_pt_made'),
                three_pt_attempted=stats_dict.get('three_pt_attempted'),
                ft_made=stats_dict.get('ft_made'),
                ft_attempted=stats_dict.get('ft_attempted')
            )
            
            # Validate that we have meaningful data
            if player_stats.player_name or any([
                player_stats.points, player_stats.rebounds, player_stats.assists
            ]):
                return player_stats
            
            return None
            
        except Exception as e:
            logger.error(f"Error parsing player stats: {e}")
            return None
    
    def _extract_stat_value(self, text: str, label: str) -> Any:
        """
        Extract statistical value from OCR text based on label
        
        Args:
            text: OCR text
            label: Region label indicating stat type
            
        Returns:
            Extracted value (int, str, or None)
        """
        text = text.strip()
        
        # Handle different stat types
        if label in ['player_name', 'gamertag', 'team']:
            return text  # Return as string
        
        if label in ['points', 'rebounds', 'assists', 'steals', 'blocks', 'turnovers']:
            return self._extract_number(text)
        
        if label == 'fg':
            return self._extract_shot_stats(text)
        
        if label == 'three_pt':
            return self._extract_shot_stats(text)
        
        if label == 'ft':
            return self._extract_shot_stats(text)
        
        # Default: try to extract number
        return self._extract_number(text)
    
    def _extract_number(self, text: str) -> Optional[int]:
        """
        Extract integer from text
        
        Args:
            text: Text containing number
            
        Returns:
            Extracted integer or None
        """
        # Find all numbers in text
        numbers = re.findall(r'\d+', text)
        
        if numbers:
            try:
                return int(numbers[0])
            except ValueError:
                pass
        
        return None
    
    def _extract_shot_stats(self, text: str) -> Dict[str, Optional[int]]:
        """
        Extract shooting statistics (made/attempted) from text
        
        Args:
            text: Text like "9/15" or "9-15"
            
        Returns:
            Dictionary with 'made' and 'attempted' keys
        """
        # Try different separators
        for separator in ['/', '-']:
            if separator in text:
                parts = text.split(separator)
                if len(parts) == 2:
                    try:
                        made = int(re.search(r'\d+', parts[0]).group())
                        attempted = int(re.search(r'\d+', parts[1]).group())
                        return {'made': made, 'attempted': attempted}
                    except (ValueError, AttributeError):
                        continue
        
        return {'made': None, 'attempted': None}
    
    def parse_player_attributes(self, regions: List[ExtractedRegion]) -> Optional[PlayerAttributes]:
        """
        Parse player attributes from regions
        
        Args:
            regions: List of extracted regions containing attributes
            
        Returns:
            PlayerAttributes object or None if parsing fails
        """
        try:
            attributes = {}
            player_name = ""
            
            for region in regions:
                ocr_result = self.parse(region)
                
                if ocr_result.confidence < self.confidence_threshold:
                    continue
                
                # Parse attribute line (e.g., "3PT Shot: 92")
                if ':' in ocr_result.text:
                    parts = ocr_result.text.split(':', 1)
                    attr_name = parts[0].strip()
                    attr_value = self._extract_number(parts[1])
                    
                    if attr_value is not None:
                        attributes[attr_name] = attr_value
                elif region.roi.label == 'player_name':
                    player_name = ocr_result.text
            
            if player_name or attributes:
                return PlayerAttributes(
                    player_name=player_name,
                    attributes=attributes
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error parsing player attributes: {e}")
            return None
    
    def batch_parse(self, regions: List[ExtractedRegion]) -> List[OCRResult]:
        """
        Parse multiple regions in batch
        
        Args:
            regions: List of extracted regions
            
        Returns:
            List of OCR results
        """
        results = []
        
        for region in regions:
            result = self.parse(region)
            results.append(result)
        
        return results


class StatParser:
    """
    Specialized parser for basketball statistics
    """
    
    def __init__(self):
        """Initialize stat parser"""
        self.ocr_parser = OCRParser()
    
    def parse_box_score(self, regions: List[ExtractedRegion]) -> List[PlayerStats]:
        """
        Parse complete box score from multiple regions
        
        Args:
            regions: List of extracted regions from box score screen
            
        Returns:
            List of PlayerStats objects
        """
        # Group regions by player (assuming vertical layout)
        player_groups = self._group_regions_by_player(regions)
        
        player_stats_list = []
        
        for player_regions in player_groups:
            stats = self.ocr_parser.parse_player_stats(player_regions)
            if stats:
                player_stats_list.append(stats)
        
        return player_stats_list
    
    def _group_regions_by_player(self, regions: List[ExtractedRegion]) -> List[List[ExtractedRegion]]:
        """
        Group regions by player based on Y coordinates
        
        Args:
            regions: List of extracted regions
            
        Returns:
            List of region groups, each group representing one player
        """
        if not regions:
            return []
        
        # Sort regions by Y coordinate
        sorted_regions = sorted(regions, key=lambda r: r.roi.y)
        
        # Group by Y proximity (assuming same player stats are on same row)
        groups = []
        current_group = [sorted_regions[0]]
        current_y = sorted_regions[0].roi.y
        y_threshold = 30  # Pixels threshold for same row
        
        for region in sorted_regions[1:]:
            if abs(region.roi.y - current_y) < y_threshold:
                current_group.append(region)
            else:
                groups.append(current_group)
                current_group = [region]
                current_y = region.roi.y
        
        if current_group:
            groups.append(current_group)
        
        return groups
    
    def validate_stats(self, stats: PlayerStats) -> bool:
        """
        Validate player statistics for consistency
        
        Args:
            stats: PlayerStats to validate
            
        Returns:
            True if stats are valid
        """
        # Check that made <= attempted for shooting stats
        if stats.fg_made and stats.fg_attempted:
            if stats.fg_made > stats.fg_attempted:
                logger.warning(f"Invalid FG stats: made {stats.fg_made} > attempted {stats.fg_attempted}")
                return False
        
        if stats.three_pt_made and stats.three_pt_attempted:
            if stats.three_pt_made > stats.three_pt_attempted:
                logger.warning(f"Invalid 3PT stats: made {stats.three_pt_made} > attempted {stats.three_pt_attempted}")
                return False
        
        if stats.ft_made and stats.ft_attempted:
            if stats.ft_made > stats.ft_attempted:
                logger.warning(f"Invalid FT stats: made {stats.ft_made} > attempted {stats.ft_attempted}")
                return False
        
        # Check that 3PT made <= FG made
        if stats.three_pt_made and stats.fg_made:
            if stats.three_pt_made > stats.fg_made:
                logger.warning(f"Invalid stats: 3PT made {stats.three_pt_made} > FG made {stats.fg_made}")
                return False
        
        return True
    
    def calculate_advanced_stats(self, stats: PlayerStats) -> Dict[str, Optional[float]]:
        """
        Calculate advanced basketball statistics
        
        Args:
            stats: PlayerStats object
            
        Returns:
            Dictionary of advanced statistics
        """
        return {
            'fg_percentage': stats.fg_percentage,
            'three_pt_percentage': stats.three_pt_percentage,
            'ft_percentage': stats.ft_percentage,
            'efg_percentage': stats.efg_percentage,
            'ts_percentage': stats.ts_percentage
        }
