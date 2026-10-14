"""
Data models for HoopSync pipeline
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
import uuid


class ScreenType(Enum):
    """Types of NBA 2K screens that can be detected"""
    SCOREBOARD = "scoreboard"
    BOX_SCORE = "box_score"
    PLAYER_STATS = "player_stats"
    TEAM_STATS = "team_stats"
    MATCHUP_SCREEN = "matchup_screen"
    PLAYER_CARD = "player_card"
    PLAYER_ATTRIBUTES = "player_attributes"
    SHOT_INFO = "shot_info"
    GAME_SUMMARY = "game_summary"
    FINAL_RESULTS = "final_results"
    UNKNOWN = "unknown"


@dataclass
class Frame:
    """Represents a single video frame"""
    data: bytes
    timestamp: datetime
    frame_number: int
    width: int
    height: int
    channel_count: int = 3


@dataclass
class DetectionResult:
    """Result of frame detection"""
    screen_type: ScreenType
    confidence: float
    timestamp: datetime
    frame_number: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ROI:
    """Region of Interest"""
    x: int
    y: int
    width: int
    height: int
    label: str


@dataclass
class ExtractedRegion:
    """Extracted region from a frame"""
    roi: ROI
    image_data: bytes
    timestamp: datetime


@dataclass
class OCRResult:
    """Result of OCR processing"""
    text: str
    confidence: float
    region_label: str
    timestamp: datetime
    raw_data: Optional[bytes] = None


@dataclass
class PlayerStats:
    """Player statistics from a game"""
    player_name: str
    gamertag: Optional[str] = None
    team: Optional[str] = None
    points: Optional[int] = None
    rebounds: Optional[int] = None
    assists: Optional[int] = None
    steals: Optional[int] = None
    blocks: Optional[int] = None
    turnovers: Optional[int] = None
    fg_made: Optional[int] = None
    fg_attempted: Optional[int] = None
    three_pt_made: Optional[int] = None
    three_pt_attempted: Optional[int] = None
    ft_made: Optional[int] = None
    ft_attempted: Optional[int] = None
    
    @property
    def fg_percentage(self) -> Optional[float]:
        if self.fg_attempted and self.fg_attempted > 0:
            return (self.fg_made / self.fg_attempted) * 100
        return None
    
    @property
    def three_pt_percentage(self) -> Optional[float]:
        if self.three_pt_attempted and self.three_pt_attempted > 0:
            return (self.three_pt_made / self.three_pt_attempted) * 100
        return None
    
    @property
    def ft_percentage(self) -> Optional[float]:
        if self.ft_attempted and self.ft_attempted > 0:
            return (self.ft_made / self.ft_attempted) * 100
        return None
    
    @property
    def efg_percentage(self) -> Optional[float]:
        """Effective Field Goal Percentage"""
        if self.fg_attempted and self.fg_attempted > 0:
            points = (self.fg_made or 0) + 0.5 * (self.three_pt_made or 0)
            return (points / self.fg_attempted) * 100
        return None
    
    @property
    def ts_percentage(self) -> Optional[float]:
        """True Shooting Percentage"""
        if self.fg_attempted and self.ft_attempted:
            pts = self.points or 0
            fga = self.fg_attempted or 0
            fta = self.ft_attempted or 0
            if (fga + 0.44 * fta) > 0:
                return (pts / (2 * (fga + 0.44 * fta))) * 100
        return None


@dataclass
class PlayerAttributes:
    """Player build attributes"""
    player_name: str
    gamertag: Optional[str] = None
    attributes: Dict[str, int] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class PlayerMatchupStats:
    """Individual player stats from matchup screen"""
    player_name: str
    gamertag: Optional[str] = None
    ovr: Optional[int] = None  # Overall rating
    position: Optional[str] = None  # SF, SG, PG, etc.
    height: Optional[str] = None  # 6'8"
    weight: Optional[int] = None  # 185 lbs
    key_stats: Dict[str, int] = field(default_factory=dict)  # Mid-Range Shot: 94, etc.
    average_stats: Dict[str, float] = field(default_factory=dict)  # PPG: 5.7, RPG: 0.3, etc.
    grade: Optional[str] = None  # B-, A, etc.
    
    def get_display_name(self) -> str:
        """Get formatted display name"""
        if self.gamertag:
            return f"{self.player_name} ({self.gamertag})"
        return self.player_name


@dataclass
class PlayerMatchup:
    """Complete player matchup comparison"""
    left_player: PlayerMatchupStats
    right_player: PlayerMatchupStats
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def ovr_difference(self) -> int:
        """Get OVR difference (right - left)"""
        if self.left_player.ovr and self.right_player.ovr:
            return self.right_player.ovr - self.left_player.ovr
        return 0
    
    @property
    def favored_player(self) -> str:
        """Get which player is favored by OVR"""
        if self.ovr_difference > 0:
            return self.right_player.get_display_name()
        elif self.ovr_difference < 0:
            return self.left_player.get_display_name()
        return "Even matchup"


@dataclass
class GameEvent:
    """Deduplicated game event"""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    game_session_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    event_type: str = ""
    player_name: str = ""
    gamertag: Optional[str] = None
    team: Optional[str] = None
    opponent: Optional[str] = None
    screen_source: ScreenType = ScreenType.UNKNOWN
    stats: Optional[PlayerStats] = None
    attributes: Optional[PlayerAttributes] = None
    matchup: Optional[PlayerMatchup] = None
    detection_confidence: float = 0.0
    ocr_confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GameSession:
    """Represents a complete game session"""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    user_gamertag: str = ""
    events: List[GameEvent] = field(default_factory=list)
    
    @property
    def duration(self) -> Optional[float]:
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    @property
    def total_events(self) -> int:
        return len(self.events)
