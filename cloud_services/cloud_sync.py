"""
Cloud Sync Module
Synchronizes structured data to cloud backend
"""

import requests
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
import logging
import time
from pathlib import Path

from ..processing_engine.models import GameEvent, GameSession, PlayerStats, PlayerAttributes
from ..config.config_loader import load_config

logger = logging.getLogger(__name__)


class CloudSync:
    """
    Handles synchronization of local data to cloud backend
    """
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """
        Initialize cloud sync
        
        Args:
            config_path: Path to configuration file
        """
        self.config = load_config(config_path)
        self.cloud_config = self.config.get('cloud', {})
        
        self.enabled = self.cloud_config.get('enabled', False)
        self.api_endpoint = self.cloud_config.get('api_endpoint', 'https://api.hoopsync.com')
        self.api_key = self.cloud_config.get('api_key', '')
        self.sync_interval = self.cloud_config.get('sync_interval_seconds', 60)
        self.retry_attempts = self.cloud_config.get('retry_attempts', 3)
        self.timeout = self.cloud_config.get('timeout_seconds', 30)
        
        # Session for HTTP requests
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'HoopSync/1.0'
        })
        
        if self.api_key:
            self.session.headers.update({
                'Authorization': f'Bearer {self.api_key}'
            })
        
        # Sync state
        self.last_sync_time = None
        self.sync_stats = {
            'successful_syncs': 0,
            'failed_syncs': 0,
            'total_events_synced': 0
        }
        
        logger.info(f"CloudSync initialized (enabled: {self.enabled})")
    
    def is_enabled(self) -> bool:
        """Check if cloud sync is enabled"""
        return self.enabled and bool(self.api_key)
    
    def sync_session(self, session: GameSession) -> bool:
        """
        Sync a complete game session to cloud
        
        Args:
            session: GameSession to sync
            
        Returns:
            True if sync successful
        """
        if not self.is_enabled():
            logger.debug("Cloud sync is disabled")
            return False
        
        try:
            # Prepare session data
            session_data = {
                'session_id': session.session_id,
                'start_time': session.start_time.isoformat(),
                'end_time': session.end_time.isoformat() if session.end_time else None,
                'user_gamertag': session.user_gamertag,
                'duration': session.duration,
                'total_events': session.total_events
            }
            
            # Send to cloud
            response = self._make_request(
                'POST',
                f'{self.api_endpoint}/sessions',
                json=session_data
            )
            
            if response and response.status_code in [200, 201]:
                logger.info(f"Successfully synced session {session.session_id}")
                self.sync_stats['successful_syncs'] += 1
                return True
            else:
                logger.error(f"Failed to sync session {session.session_id}")
                self.sync_stats['failed_syncs'] += 1
                return False
                
        except Exception as e:
            logger.error(f"Error syncing session: {e}")
            self.sync_stats['failed_syncs'] += 1
            return False
    
    def sync_events(self, events: List[GameEvent]) -> bool:
        """
        Sync multiple events to cloud
        
        Args:
            events: List of GameEvent objects to sync
            
        Returns:
            True if all events synced successfully
        """
        if not self.is_enabled() or not events:
            return False
        
        try:
            # Prepare events data
            events_data = []
            
            for event in events:
                event_data = {
                    'event_id': event.event_id,
                    'game_session_id': event.game_session_id,
                    'timestamp': event.timestamp.isoformat(),
                    'event_type': event.event_type,
                    'player_name': event.player_name,
                    'gamertag': event.gamertag,
                    'team': event.team,
                    'opponent': event.opponent,
                    'screen_source': event.screen_source.value,
                    'detection_confidence': event.detection_confidence,
                    'ocr_confidence': event.ocr_confidence,
                    'metadata': event.metadata
                }
                
                # Add stats if available
                if event.stats:
                    event_data['stats'] = {
                        'player_name': event.stats.player_name,
                        'gamertag': event.stats.gamertag,
                        'team': event.stats.team,
                        'points': event.stats.points,
                        'rebounds': event.stats.rebounds,
                        'assists': event.stats.assists,
                        'steals': event.stats.steals,
                        'blocks': event.stats.blocks,
                        'turnovers': event.stats.turnovers,
                        'fg_made': event.stats.fg_made,
                        'fg_attempted': event.stats.fg_attempted,
                        'three_pt_made': event.stats.three_pt_made,
                        'three_pt_attempted': event.stats.three_pt_attempted,
                        'ft_made': event.stats.ft_made,
                        'ft_attempted': event.stats.ft_attempted
                    }
                
                # Add attributes if available
                if event.attributes:
                    event_data['attributes'] = {
                        'player_name': event.attributes.player_name,
                        'gamertag': event.attributes.gamertag,
                        'attributes': event.attributes.attributes
                    }
                
                events_data.append(event_data)
            
            # Send to cloud
            response = self._make_request(
                'POST',
                f'{self.api_endpoint}/events/batch',
                json={'events': events_data}
            )
            
            if response and response.status_code in [200, 201]:
                logger.info(f"Successfully synced {len(events)} events")
                self.sync_stats['successful_syncs'] += 1
                self.sync_stats['total_events_synced'] += len(events)
                return True
            else:
                logger.error(f"Failed to sync events")
                self.sync_stats['failed_syncs'] += 1
                return False
                
        except Exception as e:
            logger.error(f"Error syncing events: {e}")
            self.sync_stats['failed_syncs'] += 1
            return False
    
    def sync_player_stats(self, session_id: str, player_stats: PlayerStats) -> bool:
        """
        Sync aggregated player statistics to cloud
        
        Args:
            session_id: Session ID
            player_stats: PlayerStats to sync
            
        Returns:
            True if sync successful
        """
        if not self.is_enabled():
            return False
        
        try:
            stats_data = {
                'session_id': session_id,
                'player_name': player_stats.player_name,
                'gamertag': player_stats.gamertag,
                'team': player_stats.team,
                'points': player_stats.points,
                'rebounds': player_stats.rebounds,
                'assists': player_stats.assists,
                'steals': player_stats.steals,
                'blocks': player_stats.blocks,
                'turnovers': player_stats.turnovers,
                'fg_made': player_stats.fg_made,
                'fg_attempted': player_stats.fg_attempted,
                'three_pt_made': player_stats.three_pt_made,
                'three_pt_attempted': player_stats.three_pt_attempted,
                'ft_made': player_stats.ft_made,
                'ft_attempted': player_stats.ft_attempted,
                'fg_percentage': player_stats.fg_percentage,
                'three_pt_percentage': player_stats.three_pt_percentage,
                'ft_percentage': player_stats.ft_percentage,
                'efg_percentage': player_stats.efg_percentage,
                'ts_percentage': player_stats.ts_percentage
            }
            
            response = self._make_request(
                'POST',
                f'{self.api_endpoint}/player-stats',
                json=stats_data
            )
            
            if response and response.status_code in [200, 201]:
                logger.info(f"Successfully synced stats for {player_stats.player_name}")
                return True
            else:
                logger.error(f"Failed to sync stats for {player_stats.player_name}")
                return False
                
        except Exception as e:
            logger.error(f"Error syncing player stats: {e}")
            return False
    
    def sync_player_attributes(self, session_id: str, attributes: PlayerAttributes) -> bool:
        """
        Sync player attributes to cloud
        
        Args:
            session_id: Session ID
            attributes: PlayerAttributes to sync
            
        Returns:
            True if sync successful
        """
        if not self.is_enabled():
            return False
        
        try:
            attributes_data = {
                'session_id': session_id,
                'player_name': attributes.player_name,
                'gamertag': attributes.gamertag,
                'attributes': attributes.attributes,
                'timestamp': attributes.timestamp.isoformat()
            }
            
            response = self._make_request(
                'POST',
                f'{self.api_endpoint}/player-attributes',
                json=attributes_data
            )
            
            if response and response.status_code in [200, 201]:
                logger.info(f"Successfully synced attributes for {attributes.player_name}")
                return True
            else:
                logger.error(f"Failed to sync attributes for {attributes.player_name}")
                return False
                
        except Exception as e:
            logger.error(f"Error syncing player attributes: {e}")
            return False
    
    def fetch_leaderboards(self) -> Optional[Dict[str, Any]]:
        """
        Fetch leaderboards from cloud
        
        Returns:
            Dictionary of leaderboards or None if failed
        """
        if not self.is_enabled():
            return None
        
        try:
            response = self._make_request(
                'GET',
                f'{self.api_endpoint}/leaderboards'
            )
            
            if response and response.status_code == 200:
                return response.json()
            else:
                logger.error("Failed to fetch leaderboards")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching leaderboards: {e}")
            return None
    
    def fetch_friends_stats(self) -> Optional[List[Dict[str, Any]]]:
        """
        Fetch friends' statistics from cloud
        
        Returns:
            List of friend statistics or None if failed
        """
        if not self.is_enabled():
            return None
        
        try:
            response = self._make_request(
                'GET',
                f'{self.api_endpoint}/friends/stats'
            )
            
            if response and response.status_code == 200:
                return response.json()
            else:
                logger.error("Failed to fetch friends stats")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching friends stats: {e}")
            return None
    
    def _make_request(self, method: str, url: str, **kwargs) -> Optional[requests.Response]:
        """
        Make HTTP request with retry logic
        
        Args:
            method: HTTP method
            url: Request URL
            **kwargs: Additional arguments for requests
            
        Returns:
            Response object or None if failed
        """
        for attempt in range(self.retry_attempts):
            try:
                response = self.session.request(
                    method,
                    url,
                    timeout=self.timeout,
                    **kwargs
                )
                
                if response.status_code in [200, 201, 202]:
                    return response
                elif response.status_code == 401:
                    logger.error("Authentication failed")
                    return None
                elif response.status_code == 429:
                    # Rate limited - wait and retry
                    wait_time = 2 ** attempt
                    logger.warning(f"Rate limited, waiting {wait_time}s")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.warning(f"Request failed with status {response.status_code}")
                    if attempt < self.retry_attempts - 1:
                        time.sleep(1)
                    continue
                    
            except requests.exceptions.Timeout:
                logger.warning(f"Request timeout (attempt {attempt + 1}/{self.retry_attempts})")
                if attempt < self.retry_attempts - 1:
                    time.sleep(1)
                continue
            except requests.exceptions.RequestException as e:
                logger.error(f"Request error: {e}")
                if attempt < self.retry_attempts - 1:
                    time.sleep(1)
                continue
        
        return None
    
    def get_sync_stats(self) -> Dict[str, Any]:
        """
        Get synchronization statistics
        
        Returns:
            Dictionary of sync statistics
        """
        return {
            'enabled': self.enabled,
            'last_sync_time': self.last_sync_time.isoformat() if self.last_sync_time else None,
            'successful_syncs': self.sync_stats['successful_syncs'],
            'failed_syncs': self.sync_stats['failed_syncs'],
            'total_events_synced': self.sync_stats['total_events_synced'],
            'success_rate': self.sync_stats['successful_syncs'] / max(1, self.sync_stats['successful_syncs'] + self.sync_stats['failed_syncs'])
        }
    
    def reset_sync_stats(self):
        """Reset synchronization statistics"""
        self.sync_stats = {
            'successful_syncs': 0,
            'failed_syncs': 0,
            'total_events_synced': 0
        }
        logger.info("Sync statistics reset")


class CloudAPI:
    """
    Interface for cloud API operations
    """
    
    def __init__(self, cloud_sync: CloudSync):
        """
        Initialize cloud API
        
        Args:
            cloud_sync: CloudSync instance
        """
        self.cloud_sync = cloud_sync
    
    def upload_session_complete(self, session: GameSession, events: List[GameEvent]) -> bool:
        """
        Upload complete session data to cloud
        
        Args:
            session: GameSession object
            events: List of events in the session
            
        Returns:
            True if upload successful
        """
        if not self.cloud_sync.is_enabled():
            return False
        
        # Sync session
        session_success = self.cloud_sync.sync_session(session)
        
        # Sync events
        events_success = self.cloud_sync.sync_events(events)
        
        return session_success and events_success
    
    def upload_player_data(self, session_id: str, player_stats: PlayerStats, 
                          player_attributes: Optional[PlayerAttributes] = None) -> bool:
        """
        Upload player data to cloud
        
        Args:
            session_id: Session ID
            player_stats: PlayerStats object
            player_attributes: Optional PlayerAttributes object
            
        Returns:
            True if upload successful
        """
        if not self.cloud_sync.is_enabled():
            return False
        
        stats_success = self.cloud_sync.sync_player_stats(session_id, player_stats)
        
        attributes_success = True
        if player_attributes:
            attributes_success = self.cloud_sync.sync_player_attributes(session_id, player_attributes)
        
        return stats_success and attributes_success
    
    def download_leaderboards(self) -> Optional[Dict[str, Any]]:
        """
        Download leaderboards from cloud
        
        Returns:
            Dictionary of leaderboards or None if failed
        """
        return self.cloud_sync.fetch_leaderboards()
    
    def download_friends_data(self) -> Optional[List[Dict[str, Any]]]:
        """
        Download friends data from cloud
        
        Returns:
            List of friend data or None if failed
        """
        return self.cloud_sync.fetch_friends_stats()
    
    def test_connection(self) -> bool:
        """
        Test connection to cloud API
        
        Returns:
            True if connection successful
        """
        if not self.cloud_sync.is_enabled():
            return False
        
        try:
            response = self.cloud_sync._make_request(
                'GET',
                f'{self.cloud_sync.api_endpoint}/health'
            )
            
            return response is not None and response.status_code == 200
            
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False


class SyncScheduler:
    """
    Schedules periodic synchronization tasks
    """
    
    def __init__(self, cloud_sync: CloudSync):
        """
        Initialize sync scheduler
        
        Args:
            cloud_sync: CloudSync instance
        """
        self.cloud_sync = cloud_sync
        self.sync_interval = cloud_sync.sync_interval
        self.is_running = False
        self.sync_thread = None
    
    def start_auto_sync(self, callback):
        """
        Start automatic synchronization
        
        Args:
            callback: Function to call for each sync
        """
        import threading
        
        self.is_running = True
        self.sync_thread = threading.Thread(target=self._sync_loop, args=(callback,))
        self.sync_thread.daemon = True
        self.sync_thread.start()
        
        logger.info(f"Auto-sync started (interval: {self.sync_interval}s)")
    
    def _sync_loop(self, callback):
        """
        Main sync loop
        """
        import time
        
        while self.is_running:
            try:
                callback()
                time.sleep(self.sync_interval)
            except Exception as e:
                logger.error(f"Error in sync loop: {e}")
                time.sleep(self.sync_interval)
    
    def stop_auto_sync(self):
        """Stop automatic synchronization"""
        self.is_running = False
        if self.sync_thread:
            self.sync_thread.join(timeout=5)
        
        logger.info("Auto-sync stopped")
