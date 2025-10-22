from flask import Flask, request, jsonify
import random
import math
import json
from datetime import datetime, date
import os
import gspread
from google.oauth2.service_account import Credentials
import logging

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Google Sheets configuration
SHEET_NAME = "Football Team Manager"  # Name of your Google Sheet

# Define the scope
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def get_google_credentials():
    """Get Google credentials from environment variables"""
    try:
        # Option 1: Full JSON from environment variable
        if os.environ.get('GOOGLE_CREDENTIALS_JSON'):
            credentials_json = os.environ['GOOGLE_CREDENTIALS_JSON']
            if isinstance(credentials_json, str):
                credentials_dict = json.loads(credentials_json)
            else:
                credentials_dict = credentials_json
            return Credentials.from_service_account_info(credentials_dict, scopes=SCOPES)
        
        # Option 2: Individual environment variables
        elif os.environ.get('GOOGLE_CLIENT_EMAIL') and os.environ.get('GOOGLE_PRIVATE_KEY'):
            credentials_dict = {
                "type": "service_account",
                "project_id": os.environ.get('GOOGLE_PROJECT_ID', ''),
                "private_key_id": os.environ.get('GOOGLE_PRIVATE_KEY_ID', ''),
                "private_key": os.environ.get('GOOGLE_PRIVATE_KEY', '').replace('\\n', '\n'),
                "client_email": os.environ.get('GOOGLE_CLIENT_EMAIL', ''),
                "client_id": os.environ.get('GOOGLE_CLIENT_ID', ''),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs"
            }
            return Credentials.from_service_account_info(credentials_dict, scopes=SCOPES)
        
        # Option 3: Fallback to credentials file (for local development)
        elif os.path.exists("credentials.json"):
            return Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
        
        else:
            logger.error("No Google credentials found in environment variables or credentials.json")
            return None
            
    except Exception as e:
        logger.error(f"Error loading Google credentials: {str(e)}")
        return None

# Initialize Google Sheets client
def init_google_sheets():
    """Initialize Google Sheets client with credentials"""
    try:
        creds = get_google_credentials()
        if not creds:
            logger.error("Failed to get Google credentials")
            return None
            
        client = gspread.authorize(creds)
        logger.info("Successfully authenticated with Google Sheets API")
        return client
        
    except Exception as e:
        logger.error(f"Error initializing Google Sheets: {str(e)}")
        return None

# Initialize the client
sheets_client = init_google_sheets()

class GoogleSheetsManager:
    def __init__(self):
        self.sheet = None
        self.setup_sheets()
    
    def setup_sheets(self):
        """Initialize Google Sheets connection"""
        try:
            if os.path.exists(CREDENTIALS_FILE):
                creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
                client = gspread.authorize(creds)
                
                # Try to open the existing sheet, or create a new one
                try:
                    self.sheet = client.open(SHEET_NAME)
                    logger.info(f"✓ Connected to existing Google Sheet: {SHEET_NAME}")
                except gspread.SpreadsheetNotFound:
                    # Create new sheet if it doesn't exist
                    self.sheet = client.create(SHEET_NAME)
                    # Share with yourself (optional)
                    # self.sheet.share('your-email@gmail.com', perm_type='user', role='writer')
                    logger.info(f"✓ Created new Google Sheet: {SHEET_NAME}")
                
                # Initialize worksheets if they don't exist
                self.initialize_worksheets()
                
            else:
                logger.warning("Google Sheets credentials not found, using local storage fallback")
                self.sheet = None
                
        except Exception as e:
            logger.error(f"Error setting up Google Sheets: {e}")
            self.sheet = None
    
    def initialize_worksheets(self):
        """Initialize the required worksheets with headers"""
        worksheets = {
            'players': ['Player Name', 'Games Played', 'Wins', 'Total Goals', 'Average Rating', 'Last Played', 'Position', 'Skill Level'],
            'games': ['Game ID', 'Date', 'Team A Score', 'Team B Score', 'Location', 'Notes', 'Team A Players', 'Team B Players'],
            'current_players': ['Name', 'Position', 'Skill Level']
        }
        
        for sheet_name, headers in worksheets.items():
            try:
                self.sheet.worksheet(sheet_name)
                logger.info(f"Worksheet '{sheet_name}' already exists")
            except gspread.WorksheetNotFound:
                worksheet = self.sheet.add_worksheet(title=sheet_name, rows="100", cols=str(len(headers)))
                worksheet.append_row(headers)
                logger.info(f"Created worksheet '{sheet_name}' with headers")
    
    def load_data(self):
        """Load data from Google Sheets"""
        if not self.sheet:
            return self.get_default_data()
        
        try:
            data = self.get_default_data()
            
            # Load players
            try:
                players_ws = self.sheet.worksheet('players')
                player_records = players_ws.get_all_records()
                for record in player_records[1:]:  # Skip header row
                    if record['Player Name']:
                        data['players'][record['Player Name']] = {
                            'games_played': int(record.get('Games Played', 0)),
                            'wins': int(record.get('Wins', 0)),
                            'total_goals': int(record.get('Total Goals', 0)),
                            'average_rating': float(record.get('Average Rating', 0)),
                            'last_played': record.get('Last Played'),
                            'position': record.get('Position', ''),
                            'skill_level': int(record.get('Skill Level', 5))
                        }
            except Exception as e:
                logger.error(f"Error loading players: {e}")
            
            # Load games
            try:
                games_ws = self.sheet.worksheet('games')
                game_records = games_ws.get_all_records()
                for record in game_records[1:]:  # Skip header row
                    if record.get('Game ID'):
                        data['games'].append({
                            'id': record['Game ID'],
                            'date': record['Date'],
                            'team_a': {
                                'score': int(record.get('Team A Score', 0)),
                                'players': json.loads(record.get('Team A Players', '[]'))
                            },
                            'team_b': {
                                'score': int(record.get('Team B Score', 0)),
                                'players': json.loads(record.get('Team B Players', '[]'))
                            },
                            'location': record.get('Location', ''),
                            'notes': record.get('Notes', '')
                        })
            except Exception as e:
                logger.error(f"Error loading games: {e}")
            
            # Load current players
            try:
                current_ws = self.sheet.worksheet('current_players')
                current_records = current_ws.get_all_records()
                for record in current_records[1:]:  # Skip header row
                    if record['Name']:
                        data['current_players'].append({
                            'name': record['Name'],
                            'position': record.get('Position', 'midfielder'),
                            'skill_level': int(record.get('Skill Level', 5))
                        })
            except Exception as e:
                logger.error(f"Error loading current players: {e}")
            
            logger.info(f"Loaded data: {len(data['games'])} games, {len(data['players'])} players")
            return data
            
        except Exception as e:
            logger.error(f"Error loading from Google Sheets: {e}")
            return self.get_default_data()
    
    def save_data(self, data):
        """Save data to Google Sheets"""
        if not self.sheet:
            logger.warning("Google Sheets not available, cannot save")
            return False
        
        try:
            # Save players
            players_ws = self.sheet.worksheet('players')
            players_ws.clear()
            players_ws.append_row(['Player Name', 'Games Played', 'Wins', 'Total Goals', 'Average Rating', 'Last Played', 'Position', 'Skill Level'])
            
            player_rows = []
            for name, stats in data['players'].items():
                player_rows.append([
                    name,
                    stats['games_played'],
                    stats['wins'],
                    stats['total_goals'],
                    stats['average_rating'],
                    stats['last_played'] or '',
                    stats.get('position', ''),
                    stats.get('skill_level', 5)
                ])
            
            if player_rows:
                players_ws.append_rows(player_rows)
            
            # Save games
            games_ws = self.sheet.worksheet('games')
            games_ws.clear()
            games_ws.append_row(['Game ID', 'Date', 'Team A Score', 'Team B Score', 'Location', 'Notes', 'Team A Players', 'Team B Players'])
            
            game_rows = []
            for game in data['games']:
                game_rows.append([
                    game['id'],
                    game['date'],
                    game['team_a']['score'],
                    game['team_b']['score'],
                    game.get('location', ''),
                    game.get('notes', ''),
                    json.dumps(game['team_a']['players']),
                    json.dumps(game['team_b']['players'])
                ])
            
            if game_rows:
                games_ws.append_rows(game_rows)
            
            # Save current players
            current_ws = self.sheet.worksheet('current_players')
            current_ws.clear()
            current_ws.append_row(['Name', 'Position', 'Skill Level'])
            
            current_rows = []
            for player in data['current_players']:
                current_rows.append([
                    player['name'],
                    player['position'],
                    player['skill_level']
                ])
            
            if current_rows:
                current_ws.append_rows(current_rows)
            
            logger.info(f"Saved data to Google Sheets: {len(data['games'])} games, {len(data['players'])} players")
            return True
            
        except Exception as e:
            logger.error(f"Error saving to Google Sheets: {e}")
            return False
    
    def get_default_data(self):
        """Return default data structure"""
        return {
            'players': {},
            'games': [],
            'current_players': []
        }

# Initialize Google Sheets manager
sheets_manager = GoogleSheetsManager()

# Fallback to simple file storage
def load_data():
    """Load data with Google Sheets primary, file fallback"""
    # Try Google Sheets first
    sheets_data = sheets_manager.load_data()
    if sheets_manager.sheet:
        logger.info("✓ Using Google Sheets storage")
        return sheets_data
    
    # Fallback to file storage
    try:
        if os.path.exists('football_data.json'):
            with open('football_data.json', 'r') as f:
                data = json.load(f)
                logger.info("✓ Using file storage fallback")
                return data
    except Exception as e:
        logger.error(f"Error loading fallback data: {e}")
    
    logger.info("✓ Using default data structure")
    return sheets_manager.get_default_data()

def save_data(data):
    """Save data with Google Sheets primary, file fallback"""
    # Try Google Sheets first
    if sheets_manager.sheet:
        success = sheets_manager.save_data(data)
        if success:
            logger.info("✓ Data saved to Google Sheets")
            return True
    
    # Fallback to file storage
    logger.warning("Google Sheets save failed, using file storage fallback")
    try:
        with open('football_data.json', 'w') as f:
            json.dump(data, f, indent=2)
        logger.info("✓ Data saved to local file")
        return True
    except Exception as e:
        logger.error(f"Fallback save also failed: {e}")
        return False

class Player:
    def __init__(self, name, position, skill_level=5):
        self.name = name
        self.position = position
        self.skill_level = skill_level
    
    def __repr__(self):
        return f"{self.name} ({self.position}, lvl:{self.skill_level})"

class TeamBalancer:
    POSITION_WEIGHTS = {
        'goalkeeper': 3.0,
        'defender': 1.4,
        'left_wing': 1.3,
        'right_wing': 1.3,
        'midfielder': 1.6,
        'forward': 1.5
    }
    
    @staticmethod
    def calculate_team_strength(players):
        if not players:
            return 0
            
        strength = 0
        position_count = {
            'goalkeeper': 0, 'defender': 0, 'left_wing': 0, 
            'right_wing': 0, 'midfielder': 0, 'forward': 0
        }
        
        for player in players:
            strength += player.skill_level * TeamBalancer.POSITION_WEIGHTS.get(player.position, 1.0)
            position_count[player.position] += 1
        
        if position_count['goalkeeper'] > 0:
            strength += 3
        
        if position_count['defender'] > 0:
            strength += position_count['defender'] * 0.5
        
        if position_count['left_wing'] > 0 or position_count['right_wing'] > 0:
            strength += 1
        
        if position_count['midfielder'] >= 2:
            strength += 2
        elif position_count['midfielder'] > 0:
            strength += 1
        
        if position_count['forward'] > 0:
            strength += position_count['forward'] * 0.3
        
        return strength
    
    @staticmethod
    def balance_teams(players, iterations=1000):
        if len(players) < 2:
            return players, []
        
        best_team_a = []
        best_team_b = []
        best_balance_diff = float('inf')
        
        for _ in range(iterations):
            shuffled = players.copy()
            random.shuffle(shuffled)
            
            split_point = len(shuffled) // 2
            team_a = shuffled[:split_point]
            team_b = shuffled[split_point:]
            
            strength_a = TeamBalancer.calculate_team_strength(team_a)
            strength_b = TeamBalancer.calculate_team_strength(team_b)
            balance_diff = abs(strength_a - strength_b)
            
            if balance_diff < best_balance_diff:
                best_balance_diff = balance_diff
                best_team_a = team_a
                best_team_b = team_b
        
        return best_team_a, best_team_b

@app.route('/')
def home():
    # Your existing HTML code remains exactly the same
    # Only changed the storage status part slightly
    return '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Football Team Manager</title>
    <style>
        /* ALL YOUR EXISTING CSS REMAINS EXACTLY THE SAME */
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        
        body {
            background: linear-gradient(135deg, #1a2a6c, #2a5298);
            color: white;
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1600px;
            margin: 0 auto;
        }
        
        header {
            text-align: center;
            margin-bottom: 30px;
            padding: 30px;
            background: rgba(0, 0, 0, 0.3);
            border-radius: 15px;
            backdrop-filter: blur(10px);
        }
        
        h1 {
            font-size: 2.8rem;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
        }
        
        .storage-status {
            background: rgba(255, 255, 255, 0.1);
            padding: 10px 20px;
            border-radius: 10px;
            margin: 10px 0;
            text-align: center;
            font-size: 0.9rem;
        }
        
        .storage-status.cloud {
            background: rgba(76, 175, 80, 0.2);
            border: 1px solid rgba(76, 175, 80, 0.5);
        }
        
        .storage-status.local {
            background: rgba(255, 193, 7, 0.2);
            border: 1px solid rgba(255, 193, 7, 0.5);
        }
        
        .tab-container {
            margin-bottom: 30px;
        }
        
        .tabs {
            display: flex;
            background: rgba(0, 0, 0, 0.3);
            border-radius: 10px;
            padding: 5px;
            margin-bottom: 20px;
        }
        
        .tab {
            flex: 1;
            padding: 15px;
            text-align: center;
            cursor: pointer;
            border-radius: 8px;
            transition: all 0.3s;
            font-weight: bold;
        }
        
        .tab.active {
            background: rgba(255, 255, 255, 0.2);
        }
        
        .tab-content {
            display: none;
        }
        
        .tab-content.active {
            display: block;
        }
        
        .app-container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin-bottom: 30px;
        }
        
        @media (max-width: 1200px) {
            .app-container {
                grid-template-columns: 1fr;
            }
        }
        
        .input-section, .teams-section, .stats-section {
            background: rgba(255, 255, 255, 0.1);
            padding: 25px;
            border-radius: 15px;
            backdrop-filter: blur(10px);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
        }
        
        .stats-section {
            grid-column: 1 / -1;
        }
        
        h2 {
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid rgba(255, 255, 255, 0.2);
            color: #FFD700;
        }
        
        .player-form {
            display: grid;
            gap: 12px;
            margin-bottom: 20px;
        }
        
        .form-row {
            display: grid;
            grid-template-columns: 2fr 1.5fr 1fr auto;
            gap: 10px;
            align-items: center;
        }
        
        input, select, textarea {
            padding: 12px;
            border: none;
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.9);
            font-size: 1rem;
        }
        
        .skill-input {
            text-align: center;
        }
        
        .remove-btn {
            background: #ff4444;
            color: white;
            border: none;
            padding: 8px 12px;
            border-radius: 5px;
            cursor: pointer;
            transition: background 0.3s;
        }
        
        .remove-btn:hover {
            background: #cc0000;
        }
        
        .buttons {
            display: flex;
            gap: 10px;
            margin: 20px 0;
        }
        
        button {
            flex: 1;
            background: linear-gradient(45deg, #4CAF50, #45a049);
            color: white;
            border: none;
            padding: 15px;
            font-size: 1.1rem;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s;
            font-weight: bold;
        }
        
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
        }
        
        .secondary-btn {
            background: linear-gradient(45deg, #2196F3, #1976D2);
        }
        
        .warning-btn {
            background: linear-gradient(45deg, #ff9800, #f57c00);
        }
        
        .danger-btn {
            background: linear-gradient(45deg, #f44336, #d32f2f);
        }
        
        .teams-display {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }
        
        .team {
            background: rgba(255, 255, 255, 0.05);
            padding: 20px;
            border-radius: 10px;
            border: 2px solid rgba(255, 255, 255, 0.1);
        }
        
        .team-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.2);
        }
        
        .team-strength {
            background: rgba(255, 215, 0, 0.2);
            padding: 5px 10px;
            border-radius: 15px;
            font-size: 0.9rem;
        }
        
        .player-list {
            list-style: none;
        }
        
        .player-item {
            background: rgba(255, 255, 255, 0.1);
            margin: 8px 0;
            padding: 12px;
            border-radius: 8px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: transform 0.2s;
        }
        
        .player-item:hover {
            transform: translateX(5px);
            background: rgba(255, 255, 255, 0.15);
        }
        
        .player-info {
            flex: 1;
        }
        
        .player-name {
            font-weight: bold;
            font-size: 1.1rem;
        }
        
        .player-details {
            font-size: 0.9rem;
            opacity: 0.8;
            margin-top: 4px;
        }
        
        .position-badge {
            background: rgba(76, 175, 80, 0.3);
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 0.8rem;
        }
        
        .position-gk { background: rgba(255, 87, 34, 0.3); }
        .position-def { background: rgba(33, 150, 243, 0.3); }
        .position-lw { background: rgba(156, 39, 176, 0.3); }
        .position-rw { background: rgba(255, 193, 7, 0.3); }
        .position-mid { background: rgba(76, 175, 80, 0.3); }
        .position-fwd { background: rgba(244, 67, 54, 0.3); }
        
        .balance-indicator {
            text-align: center;
            margin: 20px 0;
            padding: 15px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            font-size: 1.1rem;
        }
        
        .balanced { color: #4CAF50; }
        .unbalanced { color: #ff4444; }
        
        .score-input {
            display: grid;
            grid-template-columns: 1fr auto 1fr;
            gap: 15px;
            align-items: center;
            margin: 20px 0;
        }
        
        .score-team {
            text-align: center;
            padding: 15px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
        }
        
        .vs {
            font-size: 1.5rem;
            font-weight: bold;
            color: #FFD700;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        
        .stat-card {
            background: rgba(255, 255, 255, 0.05);
            padding: 20px;
            border-radius: 10px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .player-stats {
            max-height: 500px;
            overflow-y: auto;
        }
        
        .stats-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }
        
        .stats-table th, .stats-table td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .stats-table th {
            background: rgba(255, 255, 255, 0.1);
            font-weight: bold;
            color: #FFD700;
        }
        
        .stats-table tr:hover {
            background: rgba(255, 255, 255, 0.05);
        }
        
        .win-rate {
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 0.8rem;
            font-weight: bold;
        }
        
        .win-rate.high { background: rgba(76, 175, 80, 0.3); }
        .win-rate.medium { background: rgba(255, 193, 7, 0.3); }
        .win-rate.low { background: rgba(244, 67, 54, 0.3); }
        
        .game-history {
            max-height: 400px;
            overflow-y: auto;
        }
        
        .game-item {
            background: rgba(255, 255, 255, 0.05);
            margin: 10px 0;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #4CAF50;
        }
        
        .game-item.lost {
            border-left-color: #f44336;
        }
        
        .game-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
        }
        
        .game-score {
            font-size: 1.2rem;
            font-weight: bold;
            color: #FFD700;
        }
        
        .game-date {
            opacity: 0.8;
            font-size: 0.9rem;
        }
        
        .instructions {
            background: rgba(0, 0, 0, 0.3);
            padding: 25px;
            border-radius: 15px;
            margin-top: 30px;
        }
        
        .instructions h3 {
            color: #FFD700;
            margin-bottom: 15px;
        }
        
        .instructions ul {
            padding-left: 20px;
        }
        
        .instructions li {
            margin-bottom: 10px;
            line-height: 1.5;
        }
        
        .position-weights {
            background: rgba(255, 255, 255, 0.05);
            padding: 15px;
            border-radius: 10px;
            margin-top: 15px;
        }
        
        .weight-item {
            display: flex;
            justify-content: space-between;
            margin: 5px 0;
        }
        
        .hidden {
            display: none;
        }
        
        .data-management {
            background: rgba(255, 255, 255, 0.05);
            padding: 20px;
            border-radius: 10px;
            margin-top: 20px;
        }
        
        .config-section {
            background: rgba(255, 255, 255, 0.05);
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>⚽ Football Team Manager</h1>
            <p>Team splitting, game tracking, and player performance analytics</p>
            <div id="storageStatus" class="storage-status">
                Checking storage status...
            </div>
        </header>
        
        <div class="tab-container">
            <div class="tabs">
                <div class="tab active" onclick="switchTab('team-splitter')">Team Splitter</div>
                <div class="tab" onclick="switchTab('game-tracker')">Game Tracker</div>
                <div class="tab" onclick="switchTab('player-stats')">Player Statistics</div>
                <div class="tab" onclick="switchTab('game-history')">Game History</div>
                <div class="tab" onclick="switchTab('data-management')">Data Management</div>
            </div>
            
            <!-- Team Splitter Tab -->
            <div id="team-splitter" class="tab-content active">
                <div class="app-container">
                    <div class="input-section">
                        <h2>🏃 Add Players</h2>
                        <div class="player-form" id="playerForm">
                            <div class="form-row">
                                <strong>Player Name</strong>
                                <strong>Position</strong>
                                <strong>Skill (1-10)</strong>
                                <span></span>
                            </div>
                        </div>
                        
                        <div class="buttons">
                            <button onclick="addPlayerField()">➕ Add Player</button>
                            <button class="secondary-btn" onclick="addSampleTeam()">🎯 Add Sample Team</button>
                            <button class="warning-btn" onclick="loadSavedPlayers()">📁 Load Saved Players</button>
                        </div>
                        
                        <div class="buttons">
                            <button onclick="balanceTeams()" style="background:linear-gradient(45deg,#FF9800,#F57C00)">
                                ⚖️ Balance Teams
                            </button>
                            <button class="secondary-btn" onclick="randomizeTeams()">
                                🎲 Random Teams
                            </button>
                            <button class="warning-btn" onclick="saveCurrentPlayers()">
                                💾 Save Players
                            </button>
                        </div>
                        
                        <div class="position-weights">
                            <h4>Position Weights:</h4>
                            <div class="weight-item"><span>Goalkeeper:</span> <strong>3.0x</strong></div>
                            <div class="weight-item"><span>Midfielder:</span> <strong>1.6x</strong></div>
                            <div class="weight-item"><span>Forward:</span> <strong>1.5x</strong></div>
                            <div class="weight-item"><span>Defender:</span> <strong>1.4x</strong></div>
                            <div class="weight-item"><span>Left/Right Wing:</span> <strong>1.3x</strong></div>
                        </div>
                    </div>
                    
                    <div class="teams-section">
                        <h2>📊 Teams</h2>
                        <div id="balanceIndicator" class="balance-indicator">
                            Click "Balance Teams" to create balanced teams
                        </div>
                        <div class="teams-display">
                            <div class="team">
                                <div class="team-header">
                                    <h3>🔵 Team A</h3>
                                    <span id="teamAStrength" class="team-strength">Strength: 0</span>
                                </div>
                                <ul id="teamA" class="player-list"></ul>
                            </div>
                            <div class="team">
                                <div class="team-header">
                                    <h3>🔴 Team B</h3>
                                    <span id="teamBStrength" class="team-strength">Strength: 0</span>
                                </div>
                                <ul id="teamB" class="player-list"></ul>
                            </div>
                        </div>
                        
                        <div class="score-input" id="scoreSection" style="display: none;">
                            <div class="score-team">
                                <h4>Team A Score</h4>
                                <input type="number" id="teamAScore" min="0" value="0" style="width: 80px; text-align: center;">
                            </div>
                            <div class="vs">VS</div>
                            <div class="score-team">
                                <h4>Team B Score</h4>
                                <input type="number" id="teamBScore" min="0" value="0" style="width: 80px; text-align: center;">
                            </div>
                        </div>
                        
                        <div class="buttons" id="recordGameSection" style="display: none;">
                            <button onclick="recordGame()">📝 Record Game Result</button>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Game Tracker Tab -->
            <div id="game-tracker" class="tab-content">
                <div class="stats-section">
                    <h2>📝 Record New Game</h2>
                    <div class="app-container">
                        <div class="input-section">
                            <h3>Game Details</h3>
                            <div style="display: grid; gap: 15px;">
                                <div>
                                    <label><strong>Game Date:</strong></label>
                                    <input type="date" id="gameDate" style="width: 100%;">
                                </div>
                                <div>
                                    <label><strong>Location/Venue:</strong></label>
                                    <input type="text" id="gameLocation" placeholder="e.g., Central Park Field" style="width: 100%;">
                                </div>
                                <div>
                                    <label><strong>Notes (optional):</strong></label>
                                    <textarea id="gameNotes" placeholder="Any additional notes about the game..." style="width: 100%; height: 100px;"></textarea>
                                </div>
                            </div>
                        </div>
                        
                        <div class="teams-section">
                            <h3>Select Teams</h3>
                            <p>Use the Team Splitter tab to create balanced teams first, then record the game here.</p>
                            <div id="gameTeamsPreview">
                                <p>Teams will appear here after you create them in the Team Splitter tab.</p>
                            </div>
                            <div class="buttons">
                                <button onclick="loadCurrentTeamsForGame()">🔄 Load Current Teams</button>
                                <button class="secondary-btn" onclick="recordGameFromTracker()">💾 Record Game</button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Player Statistics Tab -->
            <div id="player-stats" class="tab-content">
                <div class="stats-section">
                    <h2>📈 Player Statistics</h2>
                    <div class="player-stats">
                        <table class="stats-table" id="playerStatsTable">
                            <thead>
                                <tr>
                                    <th>Player</th>
                                    <th>Games</th>
                                    <th>Wins</th>
                                    <th>Win Rate</th>
                                    <th>Goals</th>
                                    <th>Avg Rating</th>
                                    <th>Last Played</th>
                                </tr>
                            </thead>
                            <tbody id="playerStatsBody">
                                <!-- Player stats will be populated here -->
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
            
            <!-- Game History Tab -->
            <div id="game-history" class="tab-content">
                <div class="stats-section">
                    <h2>📋 Game History</h2>
                    <div class="game-history" id="gameHistoryList">
                        <!-- Game history will be populated here -->
                    </div>
                </div>
            </div>
            
            <!-- Data Management Tab -->
            <div id="data-management" class="tab-content">
                <div class="stats-section">
                    <h2>🔧 Data Management</h2>
                    
                    <div class="config-section">
                        <h3>Google Sheets Configuration</h3>
                        <p>Current Status: <span id="sheetsStatus">Checking...</span></p>
                        <div class="buttons">
                            <button class="secondary-btn" onclick="testGoogleSheets()">Test Google Sheets Connection</button>
                        </div>
                    </div>
                    
                    <div class="data-management">
                        <h3>Storage Information</h3>
                        <p id="storageInfo">Loading storage information...</p>
                        
                        <div class="buttons">
                            <button class="secondary-btn" onclick="exportData()">📤 Export Data</button>
                            <button class="warning-btn" onclick="importData()">📥 Import Data</button>
                            <button class="danger-btn" onclick="clearAllData()">🗑️ Clear All Data</button>
                        </div>
                        
                        <div id="exportSection" class="hidden">
                            <h4>Export Data</h4>
                            <textarea id="exportData" readonly style="width: 100%; height: 200px; margin: 10px 0;"></textarea>
                            <button onclick="copyExportData()">📋 Copy to Clipboard</button>
                        </div>
                        
                        <div id="importSection" class="hidden">
                            <h4>Import Data</h4>
                            <textarea id="importData" placeholder="Paste your exported data here" style="width: 100%; height: 200px; margin: 10px 0;"></textarea>
                            <div class="buttons">
                                <button onclick="processImport()">✅ Import Data</button>
                                <button class="secondary-btn" onclick="cancelImport()">❌ Cancel</button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let playerCount = 0;
        let currentTeams = { team_a: [], team_b: [] };
        let gameData = { players: {}, games: [], current_players: [] };
        
        // Load saved data on startup
        window.onload = function() {
            loadGameData();
            addPlayerField();
            addPlayerField();
            document.getElementById('gameDate').valueAsDate = new Date();
        };
        
        function switchTab(tabName) {
            document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
            document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
            
            document.getElementById(tabName).classList.add('active');
            event.target.classList.add('active');
            
            if (tabName === 'player-stats' || tabName === 'game-history' || tabName === 'data-management') {
                loadGameData();
                if (tabName === 'player-stats') updatePlayerStats();
                if (tabName === 'game-history') updateGameHistory();
                if (tabName === 'data-management') updateStorageStatus();
            }
        }
        
        function loadGameData() {
            fetch('/load-data')
                .then(response => response.json())
                .then(data => {
                    gameData = data;
                    updateGameTeamsDisplay();
                    updateStorageStatus();
                })
                .catch(error => {
                    console.error('Error loading game data:', error);
                });
        }
        
        function updateStorageStatus() {
            const statusElement = document.getElementById('storageStatus');
            const storageInfoElement = document.getElementById('storageInfo');
            const sheetsStatusElement = document.getElementById('sheetsStatus');
            
            fetch('/storage-status')
                .then(response => response.json())
                .then(data => {
                    if (data.using_google_sheets) {
                        statusElement.innerHTML = `✅ Google Sheets Active | ${data.total_games} Games | ${data.total_players} Players`;
                        statusElement.className = 'storage-status cloud';
                        sheetsStatusElement.innerHTML = '✅ Connected';
                        sheetsStatusElement.style.color = '#4CAF50';
                    } else {
                        statusElement.innerHTML = `⚠️ Using Local Storage | ${data.total_games} Games | ${data.total_players} Players`;
                        statusElement.className = 'storage-status local';
                        sheetsStatusElement.innerHTML = '❌ Not Connected (Using Local Fallback)';
                        sheetsStatusElement.style.color = '#ff9800';
                    }
                    
                    storageInfoElement.innerHTML = `
                        <strong>Current Data Summary:</strong><br>
                        • Games Recorded: ${data.total_games}<br>
                        • Players Tracked: ${data.total_players}<br>
                        • Storage: ${data.using_google_sheets ? 'Google Sheets' : 'Local File'}<br>
                        • Last Updated: Just now
                    `;
                })
                .catch(error => {
                    console.error('Error checking storage status:', error);
                });
        }
        
        function testGoogleSheets() {
            fetch('/test-google-sheets')
                .then(response => response.json())
                .then(data => {
                    if (data.connected) {
                        alert('✅ Google Sheets connection successful!');
                    } else {
                        alert('❌ Google Sheets connection failed: ' + data.error);
                    }
                    updateStorageStatus();
                })
                .catch(error => {
                    alert('Error testing Google Sheets connection');
                });
        }
        
        // ... ALL YOUR EXISTING JAVASCRIPT FUNCTIONS REMAIN EXACTLY THE SAME ...
        // (addPlayerField, balanceTeams, randomizeTeams, saveCurrentPlayers, recordGame, etc.)
        
    </script>
</body>
</html>
    '''

@app.route('/storage-status')
def storage_status():
    data = load_data()
    total_games = len(data.get('games', []))
    total_players = len(data.get('players', {}))
    
    return jsonify({
        'using_google_sheets': sheets_manager.sheet is not None,
        'total_games': total_games,
        'total_players': total_players
    })

@app.route('/test-google-sheets')
def test_google_sheets():
    try:
        if sheets_manager.sheet:
            # Test by trying to access the sheet
            sheets_manager.sheet.worksheets()
            return jsonify({'connected': True})
        else:
            return jsonify({'connected': False, 'error': 'Google Sheets not configured'})
    except Exception as e:
        return jsonify({'connected': False, 'error': str(e)})

# ALL YOUR EXISTING ROUTES REMAIN EXACTLY THE SAME
# (load-data, save-players, record-game, balance-teams, random-teams, import-data, clear-data)

@app.route('/load-data', methods=['GET'])
def load_data_route():
    try:
        data = load_data()
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/save-players', methods=['POST'])
def save_players():
    try:
        data = request.get_json()
        players_data = data['players']
        
        all_data = load_data()
        all_data['current_players'] = players_data
        
        for player_data in players_data:
            name = player_data['name']
            if name not in all_data['players']:
                all_data['players'][name] = {
                    'games_played': 0,
                    'wins': 0,
                    'total_goals': 0,
                    'average_rating': 0,
                    'last_played': None,
                    'position': player_data['position'],
                    'skill_level': player_data['skill_level']
                }
        
        if save_data(all_data):
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Failed to save data'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/record-game', methods=['POST'])
def record_game():
    try:
        game_data = request.get_json()
        all_data = load_data()
        all_data['games'].append(game_data)
        
        team_a_won = game_data['team_a']['score'] > game_data['team_b']['score']
        team_b_won = game_data['team_b']['score'] > game_data['team_a']['score']
        
        for player in game_data['team_a']['players']:
            name = player['name']
            if name not in all_data['players']:
                all_data['players'][name] = {
                    'games_played': 0,
                    'wins': 0,
                    'total_goals': 0,
                    'average_rating': 0,
                    'last_played': None,
                    'position': player.get('position', 'unknown'),
                    'skill_level': player.get('skill_level', 5)
                }
            
            all_data['players'][name]['games_played'] += 1
            if team_a_won:
                all_data['players'][name]['wins'] += 1
            all_data['players'][name]['last_played'] = game_data['date']
        
        for player in game_data['team_b']['players']:
            name = player['name']
            if name not in all_data['players']:
                all_data['players'][name] = {
                    'games_played': 0,
                    'wins': 0,
                    'total_goals': 0,
                    'average_rating': 0,
                    'last_played': None,
                    'position': player.get('position', 'unknown'),
                    'skill_level': player.get('skill_level', 5)
                }
            
            all_data['players'][name]['games_played'] += 1
            if team_b_won:
                all_data['players'][name]['wins'] += 1
            all_data['players'][name]['last_played'] = game_data['date']
        
        if save_data(all_data):
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Failed to save game data'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/balance-teams', methods=['POST'])
def balance_teams():
    try:
        data = request.get_json()
        players_data = data['players']
        
        players = []
        for player_data in players_data:
            player = Player(
                name=player_data['name'],
                position=player_data['position'],
                skill_level=player_data['skill_level']
            )
            players.append(player)
        
        team_a, team_b = TeamBalancer.balance_teams(players)
        
        team_a_dict = [{'name': p.name, 'position': p.position, 'skill_level': p.skill_level} for p in team_a]
        team_b_dict = [{'name': p.name, 'position': p.position, 'skill_level': p.skill_level} for p in team_b]
        
        strength_a = TeamBalancer.calculate_team_strength(team_a)
        strength_b = TeamBalancer.calculate_team_strength(team_b)
        
        response = {
            'team_a': team_a_dict,
            'team_b': team_b_dict,
            'strength_a': strength_a,
            'strength_b': strength_b
        }
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/random-teams', methods=['POST'])
def random_teams():
    try:
        data = request.get_json()
        players_data = data['players']
        
        players = []
        for player_data in players_data:
            player = Player(
                name=player_data['name'],
                position=player_data['position'],
                skill_level=player_data['skill_level']
            )
            players.append(player)
        
        random.shuffle(players)
        split_point = len(players) // 2
        team_a = players[:split_point]
        team_b = players[split_point:]
        
        team_a_dict = [{'name': p.name, 'position': p.position, 'skill_level': p.skill_level} for p in team_a]
        team_b_dict = [{'name': p.name, 'position': p.position, 'skill_level': p.skill_level} for p in team_b]
        
        strength_a = TeamBalancer.calculate_team_strength(team_a)
        strength_b = TeamBalancer.calculate_team_strength(team_b)
        
        response = {
            'team_a': team_a_dict,
            'team_b': team_b_dict,
            'strength_a': strength_a,
            'strength_b': strength_b
        }
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/import-data', methods=['POST'])
def import_data():
    try:
        imported_data = request.get_json()
        if save_data(imported_data):
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Failed to save imported data'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/clear-data', methods=['POST'])
def clear_data():
    try:
        empty_data = {
            'players': {},
            'games': [],
            'current_players': []
        }
        if save_data(empty_data):
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Failed to clear data'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
