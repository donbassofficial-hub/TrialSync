"""
Local Event Database Module
Handles storage and retrieval of game events with deduplication
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from pathlib import Path
import logging
from contextlib import contextmanager

from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.dialects.sqlite import JSON

from ..processing_engine.models import GameEvent, GameSession, PlayerStats, PlayerAttributes, ScreenType
from ..config.config_loader import load_config

logger = logging.getLogger(__name__)

Base = declarative_base()


class DBGameSession(Base):
    """Database model for game sessions"""
    __tablename__ = 'game_sessions'
    
    session_id = Column(String, primary_key=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    user_gamertag = Column(String, nullable=False)
    
    # Relationships
    events = relationship("DBGameEvent", back_populates="session", cascade="all, delete-orphan")


class DBGameEvent(Base):
    """Database model for game events"""
    __tablename__ = 'game_events'
    
    event_id = Column(String, primary_key=True)
    game_session_id = Column(String, ForeignKey('game_sessions.session_id'), nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    event_type = Column(String, nullable=False, index=True)
    player_name = Column(String, nullable=False, index=True)
    gamertag = Column(String, nullable=True, index=True)
    team = Column(String, nullable=True)
    opponent = Column(String, nullable=True)
    screen_source = Column(String, nullable=False)
    detection_confidence = Column(Float, nullable=False)
    ocr_confidence = Column(Float, nullable=False)
    
    # Store stats as JSON
    stats_data = Column(JSON, nullable=True)
    attributes_data = Column(JSON, nullable=True)
    metadata = Column(JSON, nullable=True)
    
    # Deduplication fields
    is_duplicate = Column(Boolean, default=False, index=True)
    duplicate_of = Column(String, nullable=True)
    
    # Relationships
    session = relationship("DBGameSession", back_populates="events")


class LocalEventDatabase:
    """
    Local database for storing game events with deduplication
    """
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """
        Initialize local event database
        
        Args:
            config_path: Path to configuration file
        """
        self.config = load_config(config_path)
        self.db_config = self.config.get('database', {})
        
        self.db_type = self.db_config.get('type', 'sqlite')
        self.db_path = self.db_config.get('path', 'data/hoopsync.db')
        self.pool_size = self.db_config.get('pool_size', 5)
        
        # Deduplication settings
        self.dedup_config = self.config.get('deduplication', {})
        self.time_window = timedelta(seconds=self.dedup_config.get('time_window_seconds', 5))
        self.similarity_threshold = self.dedup_config.get('similarity_threshold', 0.95)
        
        # Initialize database
        self.engine = None
        self.SessionLocal = None
        self._initialize_database()
        
        logger.info(f"LocalEventDatabase initialized: {self.db_path}")
    
    def _initialize_database(self):
        """Initialize database connection and create tables"""
        try:
            # Create data directory if it doesn't exist
            db_file = Path(self.db_path)
            db_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Create engine
            db_url = f"sqlite:///{self.db_path}"
            self.engine = create_engine(
                db_url,
                pool_size=self.pool_size,
                echo=False
            )
            
            # Create session factory
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            
            # Create tables
            Base.metadata.create_all(bind=self.engine)
            
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
    @contextmanager
    def get_session(self) -> Session:
        """
        Context manager for database sessions
        
        Yields:
            SQLAlchemy session
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def create_session(self, user_gamertag: str) -> GameSession:
        """
        Create a new game session
        
        Args:
            user_gamertag: User's gamertag
            
        Returns:
            GameSession object
        """
        with self.get_session() as session:
            db_session = DBGameSession(
                session_id=str(GameSession().session_id),
                start_time=datetime.now(),
                user_gamertag=user_gamertag
            )
            session.add(db_session)
            
            return GameSession(
                session_id=db_session.session_id,
                start_time=db_session.start_time,
                user_gamertag=db_session.user_gamertag
            )
    
    def end_session(self, session_id: str):
        """
        End a game session
        
        Args:
            session_id: Session ID to end
        """
        with self.get_session() as session:
            db_session = session.query(DBGameSession).filter(
                DBGameSession.session_id == session_id
            ).first()
            
            if db_session:
                db_session.end_time = datetime.now()
                logger.info(f"Session {session_id} ended")
    
    def add_event(self, event: GameEvent) -> bool:
        """
        Add a game event with deduplication
        
        Args:
            event: GameEvent to add
            
        Returns:
            True if event was added (not duplicate), False if duplicate
        """
        # Check for duplicates
        if self._is_duplicate(event):
            logger.debug(f"Duplicate event detected: {event.event_id}")
            return False
        
        with self.get_session() as session:
            # Convert stats and attributes to dict
            stats_dict = None
            if event.stats:
                stats_dict = {
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
            
            attributes_dict = None
            if event.attributes:
                attributes_dict = {
                    'player_name': event.attributes.player_name,
                    'gamertag': event.attributes.gamertag,
                    'attributes': event.attributes.attributes
                }
            
            db_event = DBGameEvent(
                event_id=event.event_id,
                game_session_id=event.game_session_id,
                timestamp=event.timestamp,
                event_type=event.event_type,
                player_name=event.player_name,
                gamertag=event.gamertag,
                team=event.team,
                opponent=event.opponent,
                screen_source=event.screen_source.value,
                detection_confidence=event.detection_confidence,
                ocr_confidence=event.ocr_confidence,
                stats_data=stats_dict,
                attributes_data=attributes_dict,
                metadata=event.metadata,
                is_duplicate=False
            )
            
            session.add(db_event)
            logger.debug(f"Added event: {event.event_id}")
            return True
    
    def _is_duplicate(self, event: GameEvent) -> bool:
        """
        Check if event is a duplicate based on time window and similarity
        
        Args:
            event: Event to check
            
        Returns:
            True if duplicate, False otherwise
        """
        with self.get_session() as session:
            # Query for similar events within time window
            time_start = event.timestamp - self.time_window
            time_end = event.timestamp + self.time_window
            
            similar_events = session.query(DBGameEvent).filter(
                DBGameEvent.game_session_id == event.game_session_id,
                DBGameEvent.player_name == event.player_name,
                DBGameEvent.event_type == event.event_type,
                DBGameEvent.timestamp >= time_start,
                DBGameEvent.timestamp <= time_end,
                DBGameEvent.is_duplicate == False
            ).all()
            
            for similar_event in similar_events:
                # Calculate similarity
                similarity = self._calculate_similarity(event, similar_event)
                
                if similarity >= self.similarity_threshold:
                    # Mark new event as duplicate
                    return True
            
            return False
    
    def _calculate_similarity(self, event: GameEvent, db_event: DBGameEvent) -> float:
        """
        Calculate similarity between two events
        
        Args:
            event: New event
            db_event: Database event
            
        Returns:
            Similarity score (0.0 to 1.0)
        """
        similarity_score = 0.0
        factors = 0
        
        # Compare stats if available
        if event.stats and db_event.stats_data:
            factors += 1
            stats_similarity = self._compare_stats(event.stats, db_event.stats_data)
            similarity_score += stats_similarity
        
        # Compare attributes if available
        if event.attributes and db_event.attributes_data:
            factors += 1
            attr_similarity = self._compare_attributes(event.attributes, db_event.attributes_data)
            similarity_score += attr_similarity
        
        # Compare screen source
        if event.screen_source.value == db_event.screen_source:
            factors += 1
            similarity_score += 1.0
        
        # Compare detection confidence
        conf_diff = abs(event.detection_confidence - db_event.detection_confidence)
        conf_similarity = max(0.0, 1.0 - conf_diff)
        factors += 1
        similarity_score += conf_similarity
        
        # Calculate average similarity
        if factors > 0:
            return similarity_score / factors
        
        return 0.0
    
    def _compare_stats(self, stats: PlayerStats, db_stats: Dict[str, Any]) -> float:
        """
        Compare two player stats for similarity
        
        Args:
            stats: PlayerStats object
            db_stats: Dictionary of stats from database
            
        Returns:
            Similarity score (0.0 to 1.0)
        """
        fields_to_compare = [
            'points', 'rebounds', 'assists', 'steals', 'blocks', 'turnovers',
            'fg_made', 'fg_attempted', 'three_pt_made', 'three_pt_attempted'
        ]
        
        matches = 0
        total = 0
        
        for field in fields_to_compare:
            stat_value = getattr(stats, field, None)
            db_value = db_stats.get(field)
            
            if stat_value is not None and db_value is not None:
                total += 1
                if stat_value == db_value:
                    matches += 1
        
        return matches / total if total > 0 else 0.0
    
    def _compare_attributes(self, attributes: PlayerAttributes, db_attributes: Dict[str, Any]) -> float:
        """
        Compare two player attributes for similarity
        
        Args:
            attributes: PlayerAttributes object
            db_attributes: Dictionary of attributes from database
            
        Returns:
            Similarity score (0.0 to 1.0)
        """
        attr_dict = attributes.attributes
        db_attr_dict = db_attributes.get('attributes', {})
        
        if not attr_dict or not db_attr_dict:
            return 0.0
        
        # Compare top 5 attributes
        matches = 0
        total = min(len(attr_dict), len(db_attr_dict), 5)
        
        for attr_name, attr_value in list(attr_dict.items())[:5]:
            if attr_name in db_attr_dict:
                if db_attr_dict[attr_name] == attr_value:
                    matches += 1
        
        return matches / total if total > 0 else 0.0
    
    def get_session_events(self, session_id: str) -> List[GameEvent]:
        """
        Get all events for a session
        
        Args:
            session_id: Session ID
            
        Returns:
            List of GameEvent objects
        """
        with self.get_session() as session:
            db_events = session.query(DBGameEvent).filter(
                DBGameEvent.game_session_id == session_id,
                DBGameEvent.is_duplicate == False
            ).order_by(DBGameEvent.timestamp).all()
            
            events = []
            for db_event in db_events:
                event = self._db_event_to_game_event(db_event)
                events.append(event)
            
            return events
    
    def _db_event_to_game_event(self, db_event: DBGameEvent) -> GameEvent:
        """
        Convert database event to GameEvent object
        
        Args:
            db_event: Database event
            
        Returns:
            GameEvent object
        """
        # Reconstruct stats if available
        stats = None
        if db_event.stats_data:
            stats = PlayerStats(
                player_name=db_event.stats_data.get('player_name', ''),
                gamertag=db_event.stats_data.get('gamertag'),
                team=db_event.stats_data.get('team'),
                points=db_event.stats_data.get('points'),
                rebounds=db_event.stats_data.get('rebounds'),
                assists=db_event.stats_data.get('assists'),
                steals=db_event.stats_data.get('steals'),
                blocks=db_event.stats_data.get('blocks'),
                turnovers=db_event.stats_data.get('turnovers'),
                fg_made=db_event.stats_data.get('fg_made'),
                fg_attempted=db_event.stats_data.get('fg_attempted'),
                three_pt_made=db_event.stats_data.get('three_pt_made'),
                three_pt_attempted=db_event.stats_data.get('three_pt_attempted'),
                ft_made=db_event.stats_data.get('ft_made'),
                ft_attempted=db_event.stats_data.get('ft_attempted')
            )
        
        # Reconstruct attributes if available
        attributes = None
        if db_event.attributes_data:
            attributes = PlayerAttributes(
                player_name=db_event.attributes_data.get('player_name', ''),
                gamertag=db_event.attributes_data.get('gamertag'),
                attributes=db_event.attributes_data.get('attributes', {})
            )
        
        return GameEvent(
            event_id=db_event.event_id,
            game_session_id=db_event.game_session_id,
            timestamp=db_event.timestamp,
            event_type=db_event.event_type,
            player_name=db_event.player_name,
            gamertag=db_event.gamertag,
            team=db_event.team,
            opponent=db_event.opponent,
            screen_source=ScreenType(db_event.screen_source),
            stats=stats,
            attributes=attributes,
            detection_confidence=db_event.detection_confidence,
            ocr_confidence=db_event.ocr_confidence,
            metadata=db_event.metadata or {}
        )
    
    def get_player_stats(self, session_id: str, player_name: str) -> Optional[PlayerStats]:
        """
        Get aggregated stats for a player across a session
        
        Args:
            session_id: Session ID
            player_name: Player name
            
        Returns:
            Aggregated PlayerStats or None
        """
        with self.get_session() as session:
            db_events = session.query(DBGameEvent).filter(
                DBGameEvent.game_session_id == session_id,
                DBGameEvent.player_name == player_name,
                DBGameEvent.is_duplicate == False,
                DBGameEvent.stats_data.isnot(None)
            ).all()
            
            if not db_events:
                return None
            
            # Aggregate stats
            total_stats = {
                'points': 0, 'rebounds': 0, 'assists': 0,
                'steals': 0, 'blocks': 0, 'turnovers': 0,
                'fg_made': 0, 'fg_attempted': 0,
                'three_pt_made': 0, 'three_pt_attempted': 0,
                'ft_made': 0, 'ft_attempted': 0
            }
            
            for db_event in db_events:
                stats_data = db_event.stats_data
                for key in total_stats:
                    if stats_data.get(key) is not None:
                        total_stats[key] += stats_data[key]
            
            # Get player info from first event
            first_event = db_events[0]
            
            return PlayerStats(
                player_name=player_name,
                gamertag=first_event.gamertag,
                team=first_event.team,
                points=total_stats['points'],
                rebounds=total_stats['rebounds'],
                assists=total_stats['assists'],
                steals=total_stats['steals'],
                blocks=total_stats['blocks'],
                turnovers=total_stats['turnovers'],
                fg_made=total_stats['fg_made'],
                fg_attempted=total_stats['fg_attempted'],
                three_pt_made=total_stats['three_pt_made'],
                three_pt_attempted=total_stats['three_pt_attempted'],
                ft_made=total_stats['ft_made'],
                ft_attempted=total_stats['ft_attempted']
            )
    
    def get_all_sessions(self) -> List[GameSession]:
        """
        Get all game sessions
        
        Returns:
            List of GameSession objects
        """
        with self.get_session() as session:
            db_sessions = session.query(DBGameSession).order_by(
                DBGameSession.start_time.desc()
            ).all()
            
            sessions = []
            for db_session in db_sessions:
                session_obj = GameSession(
                    session_id=db_session.session_id,
                    start_time=db_session.start_time,
                    end_time=db_session.end_time,
                    user_gamertag=db_session.user_gamertag
                )
                sessions.append(session_obj)
            
            return sessions
    
    def cleanup_old_events(self, days: int = 30):
        """
        Clean up events older than specified days
        
        Args:
            days: Number of days to keep events
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        
        with self.get_session() as session:
            old_events = session.query(DBGameEvent).filter(
                DBGameEvent.timestamp < cutoff_date
            ).all()
            
            count = len(old_events)
            for event in old_events:
                session.delete(event)
            
            logger.info(f"Cleaned up {count} old events")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get database statistics
        
        Returns:
            Dictionary with database statistics
        """
        with self.get_session() as session:
            total_sessions = session.query(DBGameSession).count()
            total_events = session.query(DBGameEvent).filter(
                DBGameEvent.is_duplicate == False
            ).count()
            duplicate_events = session.query(DBGameEvent).filter(
                DBGameEvent.is_duplicate == True
            ).count()
            
            return {
                'total_sessions': total_sessions,
                'total_events': total_events,
                'duplicate_events': duplicate_events,
                'deduplication_rate': duplicate_events / (total_events + duplicate_events) if (total_events + duplicate_events) > 0 else 0.0
            }
