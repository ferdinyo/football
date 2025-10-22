
from flask import Flask, request, jsonify
import random
import math
import json
from datetime import datetime, date
import os
import requests

app = Flask(__name__)

# Supabase configuration - YOU NEED TO UPDATE THESE!
SUPABASE_URL = "https://eglrpoztowhvgwoudiwc.supabase.co"  # Replace with your Supabase URL
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVnbHJwb3p0b3dodmd3b3VkaXdjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjA4NzU0MjEsImV4cCI6MjA3NjQ1MTQyMX0.dqf8hintMcgKWSSsmy9TVW6ov7gzF5EdrSjbiVEhADM"  # Replace with your Supabase anon/public key
TABLE_NAME = "football_data"

class SupabaseManager:
    @staticmethod
    def make_request(method, data=None, id=None):
        """Make authenticated request to Supabase"""
        headers = {
            'apikey': SUPABASE_KEY,
            'Authorization': f'Bearer {SUPABASE_KEY}',
            'Content-Type': 'application/json',
            'Prefer': 'return=representation'
        }
        
        try:
            url = f"{SUPABASE_URL}/rest/v1/{TABLE_NAME}"
            if method == 'GET':
                if id:
                    response = requests.get(f"{url}?id=eq.{id}", headers=headers)
                else:
                    response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, headers=headers, json=data)
            elif method == 'PATCH' and id:
                response = requests.patch(f"{url}?id=eq.{id}", headers=headers, json=data)
            elif method == 'DELETE' and id:
                response = requests.delete(f"{url}?id=eq.{id}", headers=headers)
            else:
                return None
            
            print(f"Supabase {method} response status: {response.status_code}")
            
            if response.status_code in [200, 201, 204]:
                return response.json() if response.content else True
            else:
                print(f"Supabase error {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            print(f"Supabase request error: {e}")
            return None
    
    @staticmethod
    def load_data():
        """Load data from Supabase"""
        try:
            result = SupabaseManager.make_request('GET')
            print(f"Supabase load result: {result}")
            
            if result and len(result) > 0:
                # Return the first row's data
                data = result[0].get('data', {})
                print(f"Loaded data from Supabase: {len(data.get('games', []))} games, {len(data.get('players', {}))} players")
                return data
        except Exception as e:
            print(f"Error loading from Supabase: {e}")
        
        print("No data found in Supabase, returning default structure")
        # Return default structure if no data exists
        return {
            'players': {},
            'games': [],
            'current_players': []
        }
    
    @staticmethod
    def save_data(data):
        """Save data to Supabase"""
        try:
            # First, try to get existing records
            existing = SupabaseManager.make_request('GET')
            print(f"Existing records: {existing}")
            
            payload = {
                'data': data,
                'updated_at': datetime.now().isoformat()
            }
            
            if existing and len(existing) > 0:
                # Update existing record - use the first record's ID
                record_id = existing[0]['id']
                print(f"Updating existing record with ID: {record_id}")
                result = SupabaseManager.make_request('PATCH', payload, record_id)
            else:
                # Create new record
                print("Creating new record in Supabase")
                result = SupabaseManager.make_request('POST', payload)
            
            print(f"Save result: {result}")
            return result is not None
            
        except Exception as e:
            print(f"Error saving to Supabase: {e}")
            return False

# Enhanced file storage with better error handling
def load_data():
    """Load data with Supabase primary, file fallback"""
    # Try Supabase first
    print("Attempting to load from Supabase...")
    supabase_data = SupabaseManager.load_data()
    if supabase_data and (supabase_data.get('players') or supabase_data.get('games')):
        print("✓ Using Supabase storage")
        return supabase_data
    
    # Fallback to file storage
    print("Falling back to file storage...")
    try:
        if os.path.exists('football_data.json'):
            with open('football_data.json', 'r') as f:
                data = json.load(f)
                print("✓ Using file storage fallback")
                return data
    except Exception as e:
        print(f"✗ Error loading fallback data: {e}")
    
    print("✗ Using default data structure")
    return {
        'players': {},
        'games': [],
        'current_players': []
    }

def save_data(data):
    """Save data with Supabase primary, file fallback"""
    print(f"Saving data: {len(data.get('games', []))} games, {len(data.get('players', {}))} players")
    
    # Try Supabase first
    print("Attempting to save to Supabase...")
    success = SupabaseManager.save_data(data)
    if success:
        print("✓ Data saved to Supabase")
        return True
    
    # Fallback to file storage
    print("✗ Supabase save failed, using file storage fallback")
    try:
        with open('football_data.json', 'w') as f:
            json.dump(data, f, indent=2)
        print("✓ Data saved to local file")
        return True
    except Exception as e:
        print(f"✗ Fallback save also failed: {e}")
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
    return '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Football Team Manager</title>
    <style>
        /* Your existing CSS remains the same */
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
        
        .storage-status.error {
            background: rgba(244, 67, 54, 0.2);
            border: 1px solid rgba(244, 67, 54, 0.5);
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
        
        .debug-info {
            background: rgba(255, 0, 0, 0.1);
            padding: 10px;
            border-radius: 5px;
            margin: 10px 0;
            font-family: monospace;
            font-size: 0.8rem;
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
                        <h3>Supabase Configuration</h3>
                        <p>Current Status: <span id="supabaseStatus">Checking...</span></p>
                        <div class="buttons">
                            <button class="secondary-btn" onclick="testSupabase()">Test Supabase Connection</button>
                            <button class="warning-btn" onclick="forceLocalStorage()">🔄 Force Local Storage</button>
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
                        
                        <div id="debugSection" class="hidden">
                            <h4>Debug Information</h4>
                            <div id="debugInfo" class="debug-info"></div>
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
        let useLocalStorage = false;
        
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
                    console.log('Loaded game data:', data);
                    updateGameTeamsDisplay();
                    updateStorageStatus();
                })
                .catch(error => {
                    console.error('Error loading game data:', error);
                    showError('Failed to load data: ' + error.message);
                });
        }
        
        function updateStorageStatus() {
            const statusElement = document.getElementById('storageStatus');
            const storageInfoElement = document.getElementById('storageInfo');
            const supabaseStatusElement = document.getElementById('supabaseStatus');
            
            fetch('/storage-status')
                .then(response => response.json())
                .then(data => {
                    if (useLocalStorage) {
                        statusElement.innerHTML = `🔧 Forced Local Storage | ${data.total_games} Games | ${data.total_players} Players`;
                        statusElement.className = 'storage-status local';
                        supabaseStatusElement.innerHTML = '🔧 Local Storage Forced';
                        supabaseStatusElement.style.color = '#ff9800';
                    } else if (data.using_supabase) {
                        statusElement.innerHTML = `✅ Cloud Storage Active | ${data.total_games} Games | ${data.total_players} Players`;
                        statusElement.className = 'storage-status cloud';
                        supabaseStatusElement.innerHTML = '✅ Connected';
                        supabaseStatusElement.style.color = '#4CAF50';
                    } else {
                        statusElement.innerHTML = `⚠️ Using Local Storage | ${data.total_games} Games | ${data.total_players} Players`;
                        statusElement.className = 'storage-status local';
                        supabaseStatusElement.innerHTML = '❌ Not Connected (Using Local Fallback)';
                        supabaseStatusElement.style.color = '#ff9800';
                    }
                    
                    storageInfoElement.innerHTML = `
                        <strong>Current Data Summary:</strong><br>
                        • Games Recorded: ${data.total_games}<br>
                        • Players Tracked: ${data.total_players}<br>
                        • Storage: ${useLocalStorage ? 'Forced Local' : (data.using_supabase ? 'Cloud (Supabase)' : 'Local File')}<br>
                        • Last Updated: ${new Date().toLocaleTimeString()}
                    `;
                })
                .catch(error => {
                    console.error('Error checking storage status:', error);
                    statusElement.innerHTML = `❌ Storage Error | Check Console`;
                    statusElement.className = 'storage-status error';
                });
        }
        
        function testSupabase() {
            fetch('/test-supabase')
                .then(response => response.json())
                .then(data => {
                    if (data.connected) {
                        alert('✅ Supabase connection successful!');
                    } else {
                        alert('❌ Supabase connection failed: ' + data.error);
                    }
                    updateStorageStatus();
                })
                .catch(error => {
                    alert('Error testing Supabase connection: ' + error.message);
                });
        }
        
        function forceLocalStorage() {
            useLocalStorage = true;
            alert('🔄 Now using local storage. Data will be saved to file instead of Supabase.');
            updateStorageStatus();
        }
        
        // ... (all your existing JavaScript functions remain the same)
        // Only showing the key changes above for brevity
        
    </script>
</body>
</html>
    '''

# Enhanced routes with better error handling
@app.route('/storage-status')
def storage_status():
    try:
        data = load_data()
        total_games = len(data.get('games', []))
        total_players = len(data.get('players', {}))
        
        # Check if we're using Supabase by making a test request
        using_supabase = False
        try:
            test_data = SupabaseManager.load_data()
            using_supabase = test_data is not None and isinstance(test_data, dict)
        except:
            using_supabase = False
        
        return jsonify({
            'using_supabase': using_supabase,
            'total_games': total_games,
            'total_players': total_players
        })
    except Exception as e:
        return jsonify({
            'using_supabase': False,
            'total_games': 0,
            'total_players': 0,
            'error': str(e)
        })

@app.route('/test-supabase')
def test_supabase():
    try:
        # Test both connection and data retrieval
        test_data = SupabaseManager.load_data()
        if test_data is not None and isinstance(test_data, dict):
            return jsonify({'connected': True})
        else:
            return jsonify({'connected': False, 'error': 'No valid data returned from Supabase'})
    except Exception as e:
        return jsonify({'connected': False, 'error': str(e)})

# Enhanced save-players route
@app.route('/save-players', methods=['POST'])
def save_players():
    try:
        data = request.get_json()
        print(f"Received players data: {data}")
        
        players_data = data['players']
        
        all_data = load_data()
        all_data['current_players'] = players_data
        
        # Update player statistics
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
        
        print(f"Saving data with {len(all_data['players'])} players")
        success = save_data(all_data)
        
        if success:
            return jsonify({'success': True, 'message': f'Saved {len(players_data)} players'})
        else:
            return jsonify({'error': 'Failed to save data to storage'}), 500
            
    except Exception as e:
        print(f"Error in save_players: {e}")
        return jsonify({'error': str(e)}), 500

# Enhanced record-game route
@app.route('/record-game', methods=['POST'])
def record_game():
    try:
        game_data = request.get_json()
        print(f"Recording game: {game_data}")
        
        all_data = load_data()
        
        # Add game to history
        game_data['id'] = len(all_data['games']) + 1
        game_data['recorded_at'] = datetime.now().isoformat()
        all_data['games'].append(game_data)
        
        # Update player statistics
        team_a_won = game_data['team_a']['score'] > game_data['team_b']['score']
        team_b_won = game_data['team_b']['score'] > game_data['team_a']['score']
        
        # Process Team A players
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
        
        # Process Team B players
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
        
        print(f"Saving game data with {len(all_data['games'])} games and {len(all_data['players'])} players")
        success = save_data(all_data)
        
        if success:
            return jsonify({
                'success': True, 
                'message': f'Game recorded! {game_data["team_a"]["score"]}-{game_data["team_b"]["score"]}',
                'total_games': len(all_data['games']),
                'total_players': len(all_data['players'])
            })
        else:
            return jsonify({'error': 'Failed to save game data to storage'}), 500
            
    except Exception as e:
        print(f"Error in record_game: {e}")
        return jsonify({'error': str(e)}), 500

# Keep all other routes the same as before...

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
