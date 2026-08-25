"""
HoopSync Main Pipeline Orchestrator
Coordinates the entire NBA 2K statistics pipeline
"""

import logging
import signal
import sys
from datetime import datetime
from typing import Optional
from pathlib import Path

from data_acquisition import FrameCapture, FrameCaptureSimulator
from processing_engine import (
    FrameDetector, ROIExtractor, OCRParser, StatParser,
    GameEvent, GameSession, ScreenType
)
from local_storage_display import LocalEventDatabase, Dashboard
from cloud_services import CloudSync, CloudAPI
from config.config_loader import load_config

# Configure logging
def setup_logging(config):
    """Setup logging configuration"""
    log_config = config.get('logging', {})
    log_level = getattr(logging, log_config.get('level', 'INFO'))
    log_file = log_config.get('file', 'logs/hoopsync.log')
    log_format = log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Create logs directory
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )


class HoopSyncPipeline:
    """
    Main orchestrator for the HoopSync pipeline
    """
    
    def __init__(self, config_path: str = "config/config.yaml", use_simulator: bool = False):
        """
        Initialize HoopSync pipeline
        
        Args:
            config_path: Path to configuration file
            use_simulator: Use frame capture simulator instead of real device
        """
        self.config = load_config(config_path)
        setup_logging(self.config)
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing HoopSync Pipeline")
        
        # Initialize components
        self.use_simulator = use_simulator
        self._initialize_components()
        
        # Pipeline state
        self.is_running = False
        self.current_session: Optional[GameSession] = None
        self.processed_frames = 0
        self.detected_screens = 0
        self.extracted_events = 0
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _initialize_components(self):
        """Initialize all pipeline components"""
        try:
            # Frame Capture
            if self.use_simulator:
                self.logger.info("Using frame capture simulator")
                self.frame_capture = FrameCaptureSimulator()
            else:
                self.frame_capture = FrameCapture()
            
            # Frame Detector
            self.frame_detector = FrameDetector()
            
            # ROI Extractor
            self.roi_extractor = ROIExtractor()
            
            # OCR Parser
            self.ocr_parser = OCRParser()
            self.stat_parser = StatParser()
            
            # Database
            self.database = LocalEventDatabase()
            
            # Cloud Sync
            self.cloud_sync = CloudSync()
            self.cloud_api = CloudAPI(self.cloud_sync)
            
            # Dashboard
            self.dashboard = Dashboard()
            
            self.logger.info("All components initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing components: {e}")
            raise
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
    
    def start(self, user_gamertag: str = "Player"):
        """
        Start the HoopSync pipeline
        
        Args:
            user_gamertag: User's gamertag for the session
        """
        if self.is_running:
            self.logger.warning("Pipeline is already running")
            return
        
        self.logger.info("Starting HoopSync Pipeline")
        self.is_running = True
        
        # Create new game session
        self.current_session = self.database.create_session(user_gamertag)
        self.logger.info(f"Created session: {self.current_session.session_id}")
        
        # Start frame capture
        if not self.use_simulator:
            if not self.frame_capture.start():
                self.logger.error("Failed to start frame capture")
                self.stop()
                return
        else:
            self.frame_capture.start()
        
        # Start processing loop
        self._processing_loop()
    
    def _processing_loop(self):
        """Main processing loop"""
        self.logger.info("Starting processing loop")
        
        try:
            for frame in self.frame_capture.frames():
                if not self.is_running:
                    break
                
                self.processed_frames += 1
                
                # Process frame
                self._process_frame(frame)
                
                # Log progress periodically
                if self.processed_frames % 100 == 0:
                    self.logger.info(
                        f"Processed {self.processed_frames} frames, "
                        f"detected {self.detected_screens} screens, "
                        f"extracted {self.extracted_events} events"
                    )
        
        except Exception as e:
            self.logger.error(f"Error in processing loop: {e}")
        
        finally:
            self._cleanup()
    
    def _process_frame(self, frame):
        """
        Process a single frame through the pipeline
        
        Args:
            frame: Frame to process
        """
        try:
            # Step 1: Detect screen type
            detection = self.frame_detector.detect(frame)
            
            if detection.screen_type == ScreenType.UNKNOWN:
                return  # Skip unknown screens
            
            self.detected_screens += 1
            
            # Step 2: Extract regions of interest
            regions = self.roi_extractor.extract(frame, detection)
            
            if not regions:
                return  # No regions extracted
            
            # Step 3: Parse regions with OCR
            ocr_results = []
            for region in regions:
                ocr_result = self.ocr_parser.parse(region)
                ocr_results.append(ocr_result)
            
            # Step 4: Create game event based on screen type
            event = self._create_game_event(frame, detection, regions, ocr_results)
            
            if event:
                # Step 5: Store event in database with deduplication
                if self.database.add_event(event):
                    self.extracted_events += 1
                    self.logger.debug(f"Added event: {event.event_type} for {event.player_name}")
                    
                    # Step 6: Sync to cloud if enabled
                    if self.cloud_sync.is_enabled():
                        self._sync_event(event)
        
        except Exception as e:
            self.logger.error(f"Error processing frame: {e}")
    
    def _create_game_event(self, frame, detection, regions, ocr_results) -> Optional[GameEvent]:
        """
        Create a game event from processing results
        
        Args:
            frame: Original frame
            detection: Detection result
            regions: Extracted regions
            ocr_results: OCR results
            
        Returns:
            GameEvent or None
        """
        try:
            event_type = detection.screen_type.value
            player_name = ""
            gamertag = None
            team = None
            opponent = None
            stats = None
            attributes = None
            
            # Parse based on screen type
            if detection.screen_type in [ScreenType.BOX_SCORE, ScreenType.PLAYER_STATS]:
                # Parse player statistics
                stats = self.stat_parser.parse_player_stats(regions)
                if stats:
                    player_name = stats.player_name
                    gamertag = stats.gamertag
                    team = stats.team
            elif detection.screen_type == ScreenType.PLAYER_ATTRIBUTES:
                # Parse player attributes
                attributes = self.ocr_parser.parse_player_attributes(regions)
                if attributes:
                    player_name = attributes.player_name
                    gamertag = attributes.gamertag
            
            # Validate that we have meaningful data
            if not player_name and not stats and not attributes:
                return None
            
            # Create event
            event = GameEvent(
                game_session_id=self.current_session.session_id,
                timestamp=datetime.now(),
                event_type=event_type,
                player_name=player_name or "Unknown",
                gamertag=gamertag,
                team=team,
                opponent=opponent,
                screen_source=detection.screen_type,
                stats=stats,
                attributes=attributes,
                detection_confidence=detection.confidence,
                ocr_confidence=sum(r.confidence for r in ocr_results) / len(ocr_results) if ocr_results else 0.0,
                metadata={
                    'frame_number': frame.frame_number,
                    'roi_count': len(regions),
                    'ocr_results_count': len(ocr_results)
                }
            )
            
            return event
            
        except Exception as e:
            self.logger.error(f"Error creating game event: {e}")
            return None
    
    def _sync_event(self, event: GameEvent):
        """
        Sync event to cloud
        
        Args:
            event: GameEvent to sync
        """
        try:
            # For now, we'll batch sync at session end
            # Individual event sync can be enabled for real-time requirements
            pass
        except Exception as e:
            self.logger.error(f"Error syncing event: {e}")
    
    def _cleanup(self):
        """Cleanup when pipeline stops"""
        self.logger.info("Cleaning up pipeline")
        
        # Stop frame capture
        self.frame_capture.stop()
        
        # End session
        if self.current_session:
            self.database.end_session(self.current_session.session_id)
            
            # Sync complete session to cloud
            if self.cloud_sync.is_enabled():
                events = self.database.get_session_events(self.current_session.session_id)
                self.cloud_api.upload_session_complete(self.current_session, events)
        
        # Log final statistics
        self.logger.info(
            f"Pipeline stopped. Processed {self.processed_frames} frames, "
            f"detected {self.detected_screens} screens, "
            f"extracted {self.extracted_events} events"
        )
        
        # Log database statistics
        db_stats = self.database.get_statistics()
        self.logger.info(f"Database statistics: {db_stats}")
        
        # Log cloud sync statistics
        if self.cloud_sync.is_enabled():
            sync_stats = self.cloud_sync.get_sync_stats()
            self.logger.info(f"Cloud sync statistics: {sync_stats}")
    
    def stop(self):
        """Stop the pipeline"""
        if not self.is_running:
            return
        
        self.logger.info("Stopping HoopSync Pipeline")
        self.is_running = False
    
    def run_dashboard(self):
        """Run the dashboard server"""
        self.logger.info("Starting dashboard server")
        self.dashboard.create_templates()
        self.dashboard.run(debug=False)
    
    def get_pipeline_status(self) -> dict:
        """
        Get current pipeline status
        
        Returns:
            Dictionary with pipeline status
        """
        return {
            'is_running': self.is_running,
            'current_session_id': self.current_session.session_id if self.current_session else None,
            'processed_frames': self.processed_frames,
            'detected_screens': self.detected_screens,
            'extracted_events': self.extracted_events,
            'cloud_sync_enabled': self.cloud_sync.is_enabled(),
            'use_simulator': self.use_simulator
        }


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='HoopSync NBA 2K Statistics Pipeline')
    parser.add_argument('--config', default='config/config.yaml', help='Path to configuration file')
    parser.add_argument('--simulator', action='store_true', help='Use frame capture simulator')
    parser.add_argument('--gamertag', default='Player', help='User gamertag')
    parser.add_argument('--dashboard-only', action='store_true', help='Run dashboard only')
    parser.add_argument('--test-capture', action='store_true', help='Test video capture devices')
    
    args = parser.parse_args()
    
    # Test capture devices if requested
    if args.test_capture:
        print("Testing video capture devices...")
        devices = FrameCapture.list_devices()
        print(f"Available devices: {devices}")
        return
    
    # Create pipeline
    pipeline = HoopSyncPipeline(
        config_path=args.config,
        use_simulator=args.simulator
    )
    
    # Run dashboard only if requested
    if args.dashboard_only:
        pipeline.run_dashboard()
        return
    
    # Run full pipeline
    try:
        pipeline.start(user_gamertag=args.gamertag)
    except KeyboardInterrupt:
        pipeline.logger.info("Keyboard interrupt received")
    finally:
        pipeline.stop()


if __name__ == "__main__":
    main()
