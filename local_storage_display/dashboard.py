"""
Live User Dashboard Module
Web-based dashboard for displaying game statistics
"""

from flask import Flask, render_template, jsonify, request
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging
from pathlib import Path

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from local_storage_display.database import LocalEventDatabase
from processing_engine.models import GameSession, PlayerStats
from config.config_loader import load_config

logger = logging.getLogger(__name__)


class Dashboard:
    """
    Live dashboard for displaying HoopSync statistics
    """
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """
        Initialize dashboard
        
        Args:
            config_path: Path to configuration file
        """
        self.config = load_config(config_path)
        self.dashboard_config = self.config.get('dashboard', {})
        
        self.host = self.dashboard_config.get('host', '127.0.0.1')
        self.port = self.dashboard_config.get('port', 8080)
        self.refresh_rate = self.dashboard_config.get('refresh_rate_ms', 1000)
        
        # Initialize database
        self.database = LocalEventDatabase(config_path)
        
        # Create Flask app
        self.app = Flask(__name__, 
                        template_folder='templates',
                        static_folder='static')
        
        # Setup routes
        self._setup_routes()
        
        logger.info(f"Dashboard initialized on {self.host}:{self.port}")
    
    def _setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/')
        def index():
            """Main dashboard page"""
            return render_template('dashboard.html',
                                 refresh_rate=self.refresh_rate)
        
        @self.app.route('/api/sessions')
        def get_sessions():
            """Get all game sessions"""
            try:
                sessions = self.database.get_all_sessions()
                sessions_data = []
                
                for session in sessions:
                    session_data = {
                        'session_id': session.session_id,
                        'start_time': session.start_time.isoformat(),
                        'end_time': session.end_time.isoformat() if session.end_time else None,
                        'user_gamertag': session.user_gamertag,
                        'duration': session.duration,
                        'total_events': session.total_events
                    }
                    sessions_data.append(session_data)
                
                return jsonify({'sessions': sessions_data})
                
            except Exception as e:
                logger.error(f"Error getting sessions: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/session/<session_id>')
        def get_session(session_id: str):
            """Get specific session details"""
            try:
                events = self.database.get_session_events(session_id)
                
                events_data = []
                for event in events:
                    event_data = {
                        'event_id': event.event_id,
                        'timestamp': event.timestamp.isoformat(),
                        'event_type': event.event_type,
                        'player_name': event.player_name,
                        'gamertag': event.gamertag,
                        'team': event.team,
                        'opponent': event.opponent,
                        'screen_source': event.screen_source.value,
                        'detection_confidence': event.detection_confidence,
                        'ocr_confidence': event.ocr_confidence
                    }
                    
                    if event.stats:
                        event_data['stats'] = {
                            'player_name': event.stats.player_name,
                            'points': event.stats.points,
                            'rebounds': event.stats.rebounds,
                            'assists': event.stats.assists,
                            'steals': event.stats.steals,
                            'blocks': event.stats.blocks,
                            'turnovers': event.stats.turnovers,
                            'fg_percentage': event.stats.fg_percentage,
                            'three_pt_percentage': event.stats.three_pt_percentage,
                            'ft_percentage': event.stats.ft_percentage,
                            'efg_percentage': event.stats.efg_percentage,
                            'ts_percentage': event.stats.ts_percentage
                        }
                    
                    if event.attributes:
                        event_data['attributes'] = {
                            'player_name': event.attributes.player_name,
                            'attributes': event.attributes.attributes
                        }
                    
                    events_data.append(event_data)
                
                return jsonify({'events': events_data})
                
            except Exception as e:
                logger.error(f"Error getting session: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/session/<session_id>/stats')
        def get_session_stats(session_id: str):
            """Get aggregated statistics for a session"""
            try:
                events = self.database.get_session_events(session_id)
                
                # Group by player
                player_stats = {}
                
                for event in events:
                    if event.stats:
                        player_name = event.stats.player_name
                        if player_name not in player_stats:
                            player_stats[player_name] = {
                                'player_name': player_name,
                                'gamertag': event.stats.gamertag,
                                'team': event.stats.team,
                                'points': 0, 'rebounds': 0, 'assists': 0,
                                'steals': 0, 'blocks': 0, 'turnovers': 0,
                                'fg_made': 0, 'fg_attempted': 0,
                                'three_pt_made': 0, 'three_pt_attempted': 0,
                                'ft_made': 0, 'ft_attempted': 0,
                                'games': 0
                            }
                        
                        # Aggregate stats
                        stats = player_stats[player_name]
                        stats['points'] += event.stats.points or 0
                        stats['rebounds'] += event.stats.rebounds or 0
                        stats['assists'] += event.stats.assists or 0
                        stats['steals'] += event.stats.steals or 0
                        stats['blocks'] += event.stats.blocks or 0
                        stats['turnovers'] += event.stats.turnovers or 0
                        stats['fg_made'] += event.stats.fg_made or 0
                        stats['fg_attempted'] += event.stats.fg_attempted or 0
                        stats['three_pt_made'] += event.stats.three_pt_made or 0
                        stats['three_pt_attempted'] += event.stats.three_pt_attempted or 0
                        stats['ft_made'] += event.stats.ft_made or 0
                        stats['ft_attempted'] += event.stats.ft_attempted or 0
                        stats['games'] += 1
                
                # Calculate percentages
                for player_name, stats in player_stats.items():
                    if stats['fg_attempted'] > 0:
                        stats['fg_percentage'] = (stats['fg_made'] / stats['fg_attempted']) * 100
                    else:
                        stats['fg_percentage'] = None
                    
                    if stats['three_pt_attempted'] > 0:
                        stats['three_pt_percentage'] = (stats['three_pt_made'] / stats['three_pt_attempted']) * 100
                    else:
                        stats['three_pt_percentage'] = None
                    
                    if stats['ft_attempted'] > 0:
                        stats['ft_percentage'] = (stats['ft_made'] / stats['ft_attempted']) * 100
                    else:
                        stats['ft_percentage'] = None
                    
                    # Calculate advanced metrics
                    if stats['fg_attempted'] > 0:
                        points = stats['fg_made'] + 0.5 * stats['three_pt_made']
                        stats['efg_percentage'] = (points / stats['fg_attempted']) * 100
                    else:
                        stats['efg_percentage'] = None
                    
                    if stats['fg_attempted'] > 0 and stats['ft_attempted'] > 0:
                        pts = stats['points']
                        fga = stats['fg_attempted']
                        fta = stats['ft_attempted']
                        if (fga + 0.44 * fta) > 0:
                            stats['ts_percentage'] = (pts / (2 * (fga + 0.44 * fta))) * 100
                    else:
                        stats['ts_percentage'] = None
                
                return jsonify({'player_stats': list(player_stats.values())})
                
            except Exception as e:
                logger.error(f"Error getting session stats: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/player/<session_id>/<player_name>')
        def get_player_stats(session_id: str, player_name: str):
            """Get stats for a specific player"""
            try:
                stats = self.database.get_player_stats(session_id, player_name)
                
                if stats:
                    stats_data = {
                        'player_name': stats.player_name,
                        'gamertag': stats.gamertag,
                        'team': stats.team,
                        'points': stats.points,
                        'rebounds': stats.rebounds,
                        'assists': stats.assists,
                        'steals': stats.steals,
                        'blocks': stats.blocks,
                        'turnovers': stats.turnovers,
                        'fg_made': stats.fg_made,
                        'fg_attempted': stats.fg_attempted,
                        'three_pt_made': stats.three_pt_made,
                        'three_pt_attempted': stats.three_pt_attempted,
                        'ft_made': stats.ft_made,
                        'ft_attempted': stats.ft_attempted,
                        'fg_percentage': stats.fg_percentage,
                        'three_pt_percentage': stats.three_pt_percentage,
                        'ft_percentage': stats.ft_percentage,
                        'efg_percentage': stats.efg_percentage,
                        'ts_percentage': stats.ts_percentage
                    }
                    return jsonify(stats_data)
                else:
                    return jsonify({'error': 'Player not found'}), 404
                    
            except Exception as e:
                logger.error(f"Error getting player stats: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/stats')
        def get_database_stats():
            """Get database statistics"""
            try:
                stats = self.database.get_statistics()
                return jsonify(stats)
            except Exception as e:
                logger.error(f"Error getting database stats: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/leaderboard')
        def get_leaderboard():
            """Get leaderboard data"""
            try:
                # Get all sessions and aggregate player stats
                sessions = self.database.get_all_sessions()
                all_player_stats = {}
                
                for session in sessions:
                    events = self.database.get_session_events(session.session_id)
                    
                    for event in events:
                        if event.stats:
                            player_name = event.stats.player_name
                            if player_name not in all_player_stats:
                                all_player_stats[player_name] = {
                                    'player_name': player_name,
                                    'gamertag': event.stats.gamertag,
                                    'points': 0, 'rebounds': 0, 'assists': 0,
                                    'fg_made': 0, 'fg_attempted': 0,
                                    'three_pt_made': 0, 'three_pt_attempted': 0,
                                    'games': 0
                                }
                            
                            stats = all_player_stats[player_name]
                            stats['points'] += event.stats.points or 0
                            stats['rebounds'] += event.stats.rebounds or 0
                            stats['assists'] += event.stats.assists or 0
                            stats['fg_made'] += event.stats.fg_made or 0
                            stats['fg_attempted'] += event.stats.fg_attempted or 0
                            stats['three_pt_made'] += event.stats.three_pt_made or 0
                            stats['three_pt_attempted'] += event.stats.three_pt_attempted or 0
                            stats['games'] += 1
                
                # Calculate percentages and create leaderboards
                leaderboards = {
                    'highest_fg_percentage': [],
                    'highest_3pt_percentage': [],
                    'highest_ppg': [],
                    'highest_apg': [],
                    'highest_rpg': []
                }
                
                for player_name, stats in all_player_stats.items():
                    # Calculate per-game averages
                    games = max(stats['games'], 1)
                    ppg = stats['points'] / games
                    apg = stats['assists'] / games
                    rpg = stats['rebounds'] / games
                    
                    # Calculate percentages
                    fg_pct = (stats['fg_made'] / stats['fg_attempted'] * 100) if stats['fg_attempted'] > 0 else 0
                    three_pt_pct = (stats['three_pt_made'] / stats['three_pt_attempted'] * 100) if stats['three_pt_attempted'] > 0 else 0
                    
                    player_entry = {
                        'player_name': player_name,
                        'gamertag': stats['gamertag'],
                        'value': 0,
                        'games': stats['games']
                    }
                    
                    # Add to leaderboards
                    if fg_pct > 0:
                        player_entry['value'] = fg_pct
                        leaderboards['highest_fg_percentage'].append(player_entry.copy())
                    
                    if three_pt_pct > 0:
                        player_entry['value'] = three_pt_pct
                        leaderboards['highest_3pt_percentage'].append(player_entry.copy())
                    
                    player_entry['value'] = ppg
                    leaderboards['highest_ppg'].append(player_entry.copy())
                    
                    player_entry['value'] = apg
                    leaderboards['highest_apg'].append(player_entry.copy())
                    
                    player_entry['value'] = rpg
                    leaderboards['highest_rpg'].append(player_entry.copy())
                
                # Sort leaderboards
                for key in leaderboards:
                    leaderboards[key].sort(key=lambda x: x['value'], reverse=True)
                    leaderboards[key] = leaderboards[key][:10]  # Top 10
                
                return jsonify(leaderboards)
                
            except Exception as e:
                logger.error(f"Error getting leaderboard: {e}")
                return jsonify({'error': str(e)}), 500
    
    def run(self, debug: bool = False):
        """
        Run the dashboard server
        
        Args:
            debug: Enable debug mode
        """
        logger.info(f"Starting dashboard server on {self.host}:{self.port}")
        self.app.run(host=self.host, port=self.port, debug=debug)
    
    def create_templates(self):
        """Create HTML templates for the dashboard"""
        templates_dir = Path(__file__).parent / 'templates'
        templates_dir.mkdir(parents=True, exist_ok=True)
        
        # Create main dashboard template
        dashboard_html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HoopSync Dashboard</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #1a1a2e;
            color: #eee;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .header h1 {
            color: #e94560;
            margin: 0;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .card {
            background-color: #16213e;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        }
        .card h2 {
            color: #e94560;
            margin-top: 0;
            border-bottom: 2px solid #0f3460;
            padding-bottom: 10px;
        }
        .stat-row {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #0f3460;
        }
        .stat-label {
            color: #a0a0a0;
        }
        .stat-value {
            font-weight: bold;
            color: #4ecca3;
        }
        .player-table {
            width: 100%;
            border-collapse: collapse;
        }
        .player-table th,
        .player-table td {
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #0f3460;
        }
        .player-table th {
            background-color: #0f3460;
            color: #e94560;
        }
        .player-table tr:hover {
            background-color: #1a1a2e;
        }
        .loading {
            text-align: center;
            padding: 20px;
            color: #a0a0a0;
        }
        .refresh-info {
            text-align: center;
            color: #a0a0a0;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏀 HoopSync Dashboard</h1>
            <p>NBA 2K Statistics Tracker</p>
        </div>
        
        <div class="stats-grid">
            <div class="card">
                <h2>Database Statistics</h2>
                <div id="db-stats">
                    <div class="loading">Loading...</div>
                </div>
            </div>
            
            <div class="card">
                <h2>Recent Sessions</h2>
                <div id="sessions">
                    <div class="loading">Loading...</div>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h2>Player Statistics</h2>
            <div id="player-stats">
                <div class="loading">Select a session to view statistics</div>
            </div>
        </div>
        
        <div class="card">
            <h2>Leaderboards</h2>
            <div id="leaderboards">
                <div class="loading">Loading...</div>
            </div>
        </div>
        
        <div class="refresh-info">
            Auto-refresh every {{ refresh_rate // 1000 }} seconds
        </div>
    </div>
    
    <script>
        const REFRESH_RATE = {{ refresh_rate }};
        
        async function loadDatabaseStats() {
            try {
                const response = await fetch('/api/stats');
                const stats = await response.json();
                
                document.getElementById('db-stats').innerHTML = `
                    <div class="stat-row">
                        <span class="stat-label">Total Sessions:</span>
                        <span class="stat-value">${stats.total_sessions}</span>
                    </div>
                    <div class="stat-row">
                        <span class="stat-label">Total Events:</span>
                        <span class="stat-value">${stats.total_events}</span>
                    </div>
                    <div class="stat-row">
                        <span class="stat-label">Duplicate Events:</span>
                        <span class="stat-value">${stats.duplicate_events}</span>
                    </div>
                    <div class="stat-row">
                        <span class="stat-label">Deduplication Rate:</span>
                        <span class="stat-value">${(stats.deduplication_rate * 100).toFixed(1)}%</span>
                    </div>
                `;
            } catch (error) {
                console.error('Error loading database stats:', error);
            }
        }
        
        async function loadSessions() {
            try {
                const response = await fetch('/api/sessions');
                const data = await response.json();
                
                let html = '<table class="player-table"><thead><tr><th>Session ID</th><th>Start Time</th><th>Duration</th><th>Events</th></tr></thead><tbody>';
                
                data.sessions.forEach(session => {
                    const duration = session.duration ? Math.floor(session.duration / 60) + 'm' : 'Active';
                    const startTime = new Date(session.start_time).toLocaleString();
                    
                    html += `
                        <tr>
                            <td><a href="#" onclick="loadSessionStats('${session.session_id}')">${session.session_id.substring(0, 8)}...</a></td>
                            <td>${startTime}</td>
                            <td>${duration}</td>
                            <td>${session.total_events}</td>
                        </tr>
                    `;
                });
                
                html += '</tbody></table>';
                document.getElementById('sessions').innerHTML = html;
            } catch (error) {
                console.error('Error loading sessions:', error);
            }
        }
        
        async function loadSessionStats(sessionId) {
            try {
                const response = await fetch(`/api/session/${sessionId}/stats`);
                const data = await response.json();
                
                let html = '<table class="player-table"><thead><tr><th>Player</th><th>PTS</th><th>REB</th><th>AST</th><th>FG%</th><th>3PT%</th><th>TS%</th></tr></thead><tbody>';
                
                data.player_stats.forEach(player => {
                    html += `
                        <tr>
                            <td>${player.player_name}</td>
                            <td>${player.points}</td>
                            <td>${player.rebounds}</td>
                            <td>${player.assists}</td>
                            <td>${player.fg_percentage ? player.fg_percentage.toFixed(1) : '-'}</td>
                            <td>${player.three_pt_percentage ? player.three_pt_percentage.toFixed(1) : '-'}</td>
                            <td>${player.ts_percentage ? player.ts_percentage.toFixed(1) : '-'}</td>
                        </tr>
                    `;
                });
                
                html += '</tbody></table>';
                document.getElementById('player-stats').innerHTML = html;
            } catch (error) {
                console.error('Error loading session stats:', error);
            }
        }
        
        async function loadLeaderboards() {
            try {
                const response = await fetch('/api/leaderboard');
                const leaderboards = await response.json();
                
                let html = '';
                
                for (const [key, entries] of Object.entries(leaderboards)) {
                    const title = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                    
                    html += `<h3>${title}</h3>`;
                    html += '<table class="player-table"><thead><tr><th>Rank</th><th>Player</th><th>Value</th><th>Games</th></tr></thead><tbody>';
                    
                    entries.forEach((entry, index) => {
                        const value = key.includes('percentage') ? entry.value.toFixed(1) + '%' : entry.value.toFixed(1);
                        html += `
                            <tr>
                                <td>${index + 1}</td>
                                <td>${entry.player_name}</td>
                                <td>${value}</td>
                                <td>${entry.games}</td>
                            </tr>
                        `;
                    });
                    
                    html += '</tbody></table><br>';
                }
                
                document.getElementById('leaderboards').innerHTML = html;
            } catch (error) {
                console.error('Error loading leaderboards:', error);
            }
        }
        
        // Initial load
        loadDatabaseStats();
        loadSessions();
        loadLeaderboards();
        
        // Auto-refresh
        setInterval(() => {
            loadDatabaseStats();
            loadSessions();
            loadLeaderboards();
        }, REFRESH_RATE);
    </script>
</body>
</html>'''
        
        dashboard_template = templates_dir / 'dashboard.html'
        dashboard_template.write_text(dashboard_html)
        
        logger.info(f"Created dashboard template at {dashboard_template}")


class StatisticsCalculator:
    """
    Calculates advanced basketball statistics
    """
    
    @staticmethod
    def calculate_team_stats(events: List) -> Dict[str, Any]:
        """
        Calculate team statistics from events
        
        Args:
            events: List of game events
            
        Returns:
            Dictionary of team statistics
        """
        team_stats = {}
        
        for event in events:
            if event.stats:
                team = event.stats.team or 'Unknown'
                if team not in team_stats:
                    team_stats[team] = {
                        'points': 0, 'rebounds': 0, 'assists': 0,
                        'fg_made': 0, 'fg_attempted': 0,
                        'three_pt_made': 0, 'three_pt_attempted': 0
                    }
                
                stats = team_stats[team]
                stats['points'] += event.stats.points or 0
                stats['rebounds'] += event.stats.rebounds or 0
                stats['assists'] += event.stats.assists or 0
                stats['fg_made'] += event.stats.fg_made or 0
                stats['fg_attempted'] += event.stats.fg_attempted or 0
                stats['three_pt_made'] += event.stats.three_pt_made or 0
                stats['three_pt_attempted'] += event.stats.three_pt_attempted or 0
        
        # Calculate percentages
        for team, stats in team_stats.items():
            if stats['fg_attempted'] > 0:
                stats['fg_percentage'] = (stats['fg_made'] / stats['fg_attempted']) * 100
            else:
                stats['fg_percentage'] = 0
            
            if stats['three_pt_attempted'] > 0:
                stats['three_pt_percentage'] = (stats['three_pt_made'] / stats['three_pt_attempted']) * 100
            else:
                stats['three_pt_percentage'] = 0
        
        return team_stats
    
    @staticmethod
    def calculate_head_to_head(events: List) -> Dict[str, Any]:
        """
        Calculate head-to-head statistics
        
        Args:
            events: List of game events
            
        Returns:
            Dictionary of head-to-head statistics
        """
        # Group by matchup
        matchups = {}
        
        for event in events:
            if event.stats and event.team and event.opponent:
                matchup_key = tuple(sorted([event.team, event.opponent]))
                
                if matchup_key not in matchups:
                    matchups[matchup_key] = {
                        'team1': matchup_key[0],
                        'team2': matchup_key[1],
                        'team1_wins': 0,
                        'team2_wins': 0,
                        'games': 0
                    }
                
                matchups[matchup_key]['games'] += 1
                
                # Determine winner (simplified - would need more context)
                if event.stats.points:
                    # This is a simplified calculation
                    pass
        
        return matchups
