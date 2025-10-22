
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
            if method == 'GET':
                response = requests.get(f"{SUPABASE_URL}/rest/v1/{TABLE_NAME}", headers=headers)
            elif method == 'POST':
                response = requests.post(f"{SUPABASE_URL}/rest/v1/{TABLE_NAME}", headers=headers, json=data)
            elif method == 'PATCH' and id:
                response = requests.patch(f"{SUPABASE_URL}/rest/v1/{TABLE_NAME}?id=eq.{id}", headers=headers, json=data)
            elif method == 'DELETE' and id:
                response = requests.delete(f"{SUPABASE_URL}/rest/v1/{TABLE_NAME}?id=eq.{id}", headers=headers)
            
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
            if result and len(result) > 0:
                # Return the first row's data
                return result[0].get('data', {})
        except Exception as e:
            print(f"Error loading from Supabase: {e}")
        
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
            
            payload = {
                'data': data,
                'updated_at': datetime.now().isoformat()
            }
            
            if existing and len(existing) > 0:
                # Update existing record
                payload['id'] = existing[0]['id']
                result = SupabaseManager.make_request('PATCH', payload, existing[0]['id'])
            else:
                # Create new record
                result = SupabaseManager.make_request('POST', payload)
            
            return result is not None
            
        except Exception as e:
            print(f"Error saving to Supabase: {e}")
            return False

# Fallback to file storage if Supabase fails
def load_data():
    """Load data with Supabase primary, file fallback"""
    # Try Supabase first
    supabase_data = SupabaseManager.load_data()
    if supabase_data:
        print("Using Supabase storage")
        return supabase_data
    
    # Fallback to file storage
    try:
        if os.path.exists('football_data.json'):
            with open('football_data.json', 'r') as f:
                data = json.load(f)
                print("Using file storage fallback")
                return data
    except Exception as e:
        print(f"Error loading fallback data: {e}")
    
    print("Using default data structure")
    return {
        'players': {},
        'games': [],
        'current_players': []
    }

def save_data(data):
    """Save data with Supabase primary, file fallback"""
    # Try Supabase first
    success = SupabaseManager.save_data(data)
    if success:
        print("Data saved to Supabase")
        return True
    
    # Fallback to file storage
    print("Supabase save failed, using file storage fallback")
    try:
        with open('football_data.json', 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"Fallback save also failed: {e}")
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
                        <h3>Supabase Configuration</h3>
                        <p>Current Status: <span id="supabaseStatus">Checking...</span></p>
                        <div class="buttons">
                            <button class="secondary-btn" onclick="testSupabase()">Test Supabase Connection</button>
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
            const supabaseStatusElement = document.getElementById('supabaseStatus');
            
            fetch('/storage-status')
                .then(response => response.json())
                .then(data => {
                    if (data.using_supabase) {
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
                        • Storage: ${data.using_supabase ? 'Cloud (Supabase)' : 'Local File'}<br>
                        • Last Updated: Just now
                    `;
                })
                .catch(error => {
                    console.error('Error checking storage status:', error);
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
                    alert('Error testing Supabase connection');
                });
        }
        
        function addPlayerField() {
            playerCount++;
            const form = document.getElementById('playerForm');
            const row = document.createElement('div');
            row.className = 'form-row';
            row.innerHTML = `
                <input type="text" placeholder="Player name" id="playerName${playerCount}">
                <select id="playerPosition${playerCount}">
                    <option value="goalkeeper">Goalkeeper</option>
                    <option value="defender">Defender</option>
                    <option value="midfielder">Midfielder</option>
                    <option value="forward">Forward</option>
                    <option value="left_wing">Left Wing</option>
                    <option value="right_wing">Right Wing</option>
                </select>
                <input type="number" min="1" max="10" value="5" class="skill-input" id="playerSkill${playerCount}">
                <button type="button" class="remove-btn" onclick="this.parentElement.remove()">✕</button>
            `;
            form.appendChild(row);
        }
        
        function addSampleTeam() {
            const samplePlayers = [
                { name: 'John Smith', position: 'goalkeeper', skill: 7 },
                { name: 'Mike Johnson', position: 'defender', skill: 6 },
                { name: 'Chris Davis', position: 'defender', skill: 5 },
                { name: 'David Wilson', position: 'midfielder', skill: 8 },
                { name: 'Paul Brown', position: 'midfielder', skill: 6 },
                { name: 'Mark Miller', position: 'forward', skill: 7 },
                { name: 'James Taylor', position: 'forward', skill: 6 },
                { name: 'Robert Anderson', position: 'left_wing', skill: 5 },
                { name: 'Daniel Thomas', position: 'right_wing', skill: 6 },
                { name: 'Steven Moore', position: 'midfielder', skill: 7 }
            ];
            
            // Clear existing players
            const form = document.getElementById('playerForm');
            while (form.children.length > 1) {
                form.removeChild(form.lastChild);
            }
            playerCount = 0;
            
            // Add sample players
            samplePlayers.forEach(player => {
                playerCount++;
                const row = document.createElement('div');
                row.className = 'form-row';
                row.innerHTML = `
                    <input type="text" placeholder="Player name" id="playerName${playerCount}" value="${player.name}">
                    <select id="playerPosition${playerCount}">
                        <option value="goalkeeper" ${player.position === 'goalkeeper' ? 'selected' : ''}>Goalkeeper</option>
                        <option value="defender" ${player.position === 'defender' ? 'selected' : ''}>Defender</option>
                        <option value="midfielder" ${player.position === 'midfielder' ? 'selected' : ''}>Midfielder</option>
                        <option value="forward" ${player.position === 'forward' ? 'selected' : ''}>Forward</option>
                        <option value="left_wing" ${player.position === 'left_wing' ? 'selected' : ''}>Left Wing</option>
                        <option value="right_wing" ${player.position === 'right_wing' ? 'selected' : ''}>Right Wing</option>
                    </select>
                    <input type="number" min="1" max="10" value="${player.skill}" class="skill-input" id="playerSkill${playerCount}">
                    <button type="button" class="remove-btn" onclick="this.parentElement.remove()">✕</button>
                `;
                form.appendChild(row);
            });
        }
        
        function loadSavedPlayers() {
            const currentPlayers = gameData.current_players || [];
            if (currentPlayers.length === 0) {
                alert('No saved players found!');
                return;
            }
            
            // Clear existing players
            const form = document.getElementById('playerForm');
            while (form.children.length > 1) {
                form.removeChild(form.lastChild);
            }
            playerCount = 0;
            
            // Add saved players
            currentPlayers.forEach(player => {
                playerCount++;
                const row = document.createElement('div');
                row.className = 'form-row';
                row.innerHTML = `
                    <input type="text" placeholder="Player name" id="playerName${playerCount}" value="${player.name}">
                    <select id="playerPosition${playerCount}">
                        <option value="goalkeeper" ${player.position === 'goalkeeper' ? 'selected' : ''}>Goalkeeper</option>
                        <option value="defender" ${player.position === 'defender' ? 'selected' : ''}>Defender</option>
                        <option value="midfielder" ${player.position === 'midfielder' ? 'selected' : ''}>Midfielder</option>
                        <option value="forward" ${player.position === 'forward' ? 'selected' : ''}>Forward</option>
                        <option value="left_wing" ${player.position === 'left_wing' ? 'selected' : ''}>Left Wing</option>
                        <option value="right_wing" ${player.position === 'right_wing' ? 'selected' : ''}>Right Wing</option>
                    </select>
                    <input type="number" min="1" max="10" value="${player.skill_level}" class="skill-input" id="playerSkill${playerCount}">
                    <button type="button" class="remove-btn" onclick="this.parentElement.remove()">✕</button>
                `;
                form.appendChild(row);
            });
            
            alert(`Loaded ${currentPlayers.length} saved players!`);
        }
        
        function getPlayersFromForm() {
            const players = [];
            for (let i = 1; i <= playerCount; i++) {
                const nameElem = document.getElementById('playerName' + i);
                const positionElem = document.getElementById('playerPosition' + i);
                const skillElem = document.getElementById('playerSkill' + i);
                
                if (nameElem && nameElem.value.trim() !== '') {
                    players.push({
                        name: nameElem.value.trim(),
                        position: positionElem.value,
                        skill_level: parseInt(skillElem.value)
                    });
                }
            }
            return players;
        }
        
        function balanceTeams() {
            const players = getPlayersFromForm();
            if (players.length < 2) {
                alert('Need at least 2 players to balance teams!');
                return;
            }
            
            fetch('/balance-teams', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ players: players })
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    alert('Error: ' + data.error);
                    return;
                }
                
                currentTeams = data;
                displayTeams(data.team_a, data.team_b, data.strength_a, data.strength_b);
                
                // Show score input and record game button
                document.getElementById('scoreSection').style.display = 'grid';
                document.getElementById('recordGameSection').style.display = 'flex';
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error balancing teams');
            });
        }
        
        function randomizeTeams() {
            const players = getPlayersFromForm();
            if (players.length < 2) {
                alert('Need at least 2 players to create teams!');
                return;
            }
            
            fetch('/random-teams', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ players: players })
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    alert('Error: ' + data.error);
                    return;
                }
                
                currentTeams = data;
                displayTeams(data.team_a, data.team_b, data.strength_a, data.strength_b);
                
                // Show score input and record game button
                document.getElementById('scoreSection').style.display = 'grid';
                document.getElementById('recordGameSection').style.display = 'flex';
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error creating random teams');
            });
        }
        
        function displayTeams(teamA, teamB, strengthA, strengthB) {
            const teamAElem = document.getElementById('teamA');
            const teamBElem = document.getElementById('teamB');
            const strengthAElem = document.getElementById('teamAStrength');
            const strengthBElem = document.getElementById('teamBStrength');
            const balanceIndicator = document.getElementById('balanceIndicator');
            
            // Clear previous teams
            teamAElem.innerHTML = '';
            teamBElem.innerHTML = '';
            
            // Display Team A
            teamA.forEach(player => {
                const li = document.createElement('li');
                li.className = 'player-item';
                li.innerHTML = `
                    <div class="player-info">
                        <div class="player-name">${player.name}</div>
                        <div class="player-details">
                            <span class="position-badge position-${player.position}">${player.position}</span>
                            • Skill: ${player.skill_level}/10
                        </div>
                    </div>
                `;
                teamAElem.appendChild(li);
            });
            
            // Display Team B
            teamB.forEach(player => {
                const li = document.createElement('li');
                li.className = 'player-item';
                li.innerHTML = `
                    <div class="player-info">
                        <div class="player-name">${player.name}</div>
                        <div class="player-details">
                            <span class="position-badge position-${player.position}">${player.position}</span>
                            • Skill: ${player.skill_level}/10
                        </div>
                    </div>
                `;
                teamBElem.appendChild(li);
            });
            
            // Update strengths
            strengthAElem.textContent = `Strength: ${strengthA.toFixed(1)}`;
            strengthBElem.textContent = `Strength: ${strengthB.toFixed(1)}`;
            
            // Update balance indicator
            const balanceDiff = Math.abs(strengthA - strengthB);
            if (balanceDiff < 2) {
                balanceIndicator.innerHTML = `<span class="balanced">✅ Well Balanced! Difference: ${balanceDiff.toFixed(1)}</span>`;
            } else if (balanceDiff < 5) {
                balanceIndicator.innerHTML = `<span class="balanced">⚖️ Fairly Balanced. Difference: ${balanceDiff.toFixed(1)}</span>`;
            } else {
                balanceIndicator.innerHTML = `<span class="unbalanced">⚠️ Significant Imbalance. Difference: ${balanceDiff.toFixed(1)}</span>`;
            }
        }
        
        function saveCurrentPlayers() {
            const players = getPlayersFromForm();
            if (players.length === 0) {
                alert('No players to save!');
                return;
            }
            
            fetch('/save-players', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ players: players })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('Players saved successfully!');
                    loadGameData();
                } else {
                    alert('Error saving players: ' + (data.error || 'Unknown error'));
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error saving players');
            });
        }
        
        function recordGame() {
            const teamAScore = parseInt(document.getElementById('teamAScore').value);
            const teamBScore = parseInt(document.getElementById('teamBScore').value);
            
            if (isNaN(teamAScore) || isNaN(teamBScore)) {
                alert('Please enter valid scores for both teams!');
                return;
            }
            
            const gameData = {
                date: new Date().toISOString().split('T')[0],
                team_a: {
                    players: currentTeams.team_a,
                    score: teamAScore
                },
                team_b: {
                    players: currentTeams.team_b,
                    score: teamBScore
                },
                location: document.getElementById('gameLocation').value || 'Unknown',
                notes: document.getElementById('gameNotes').value || ''
            };
            
            fetch('/record-game', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(gameData)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('Game recorded successfully!');
                    // Reset scores
                    document.getElementById('teamAScore').value = 0;
                    document.getElementById('teamBScore').value = 0;
                    loadGameData();
                } else {
                    alert('Error recording game: ' + (data.error || 'Unknown error'));
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error recording game');
            });
        }
        
        function loadCurrentTeamsForGame() {
            if (currentTeams.team_a.length === 0) {
                alert('No teams available. Please create teams in the Team Splitter tab first.');
                return;
            }
            
            const preview = document.getElementById('gameTeamsPreview');
            preview.innerHTML = `
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                    <div>
                        <h4>Team A (Strength: ${currentTeams.strength_a?.toFixed(1) || 'N/A'})</h4>
                        <ul>
                            ${currentTeams.team_a.map(player => `<li>${player.name} - ${player.position}</li>`).join('')}
                        </ul>
                    </div>
                    <div>
                        <h4>Team B (Strength: ${currentTeams.strength_b?.toFixed(1) || 'N/A'})</h4>
                        <ul>
                            ${currentTeams.team_b.map(player => `<li>${player.name} - ${player.position}</li>`).join('')}
                        </ul>
                    </div>
                </div>
            `;
        }
        
        function recordGameFromTracker() {
            const teamAScore = parseInt(prompt('Enter Team A score:', '0'));
            const teamBScore = parseInt(prompt('Enter Team B score:', '0'));
            
            if (isNaN(teamAScore) || isNaN(teamBScore)) {
                alert('Please enter valid scores!');
                return;
            }
            
            const gameData = {
                date: document.getElementById('gameDate').value,
                team_a: {
                    players: currentTeams.team_a,
                    score: teamAScore
                },
                team_b: {
                    players: currentTeams.team_b,
                    score: teamBScore
                },
                location: document.getElementById('gameLocation').value || 'Unknown',
                notes: document.getElementById('gameNotes').value || ''
            };
            
            fetch('/record-game', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(gameData)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('Game recorded successfully!');
                    // Clear form
                    document.getElementById('gameLocation').value = '';
                    document.getElementById('gameNotes').value = '';
                    document.getElementById('gameDate').valueAsDate = new Date();
                    loadGameData();
                } else {
                    alert('Error recording game: ' + (data.error || 'Unknown error'));
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error recording game');
            });
        }
        
        function updatePlayerStats() {
            const tbody = document.getElementById('playerStatsBody');
            tbody.innerHTML = '';
            
            const players = gameData.players || {};
            const playerNames = Object.keys(players).sort();
            
            playerNames.forEach(playerName => {
                const stats = players[playerName];
                const winRate = stats.games_played > 0 ? (stats.wins / stats.games_played * 100) : 0;
                const winRateClass = winRate >= 60 ? 'high' : winRate >= 40 ? 'medium' : 'low';
                
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td><strong>${playerName}</strong></td>
                    <td>${stats.games_played}</td>
                    <td>${stats.wins}</td>
                    <td><span class="win-rate ${winRateClass}">${winRate.toFixed(1)}%</span></td>
                    <td>${stats.total_goals || 0}</td>
                    <td>${stats.average_rating ? stats.average_rating.toFixed(1) : 'N/A'}</td>
                    <td>${stats.last_played || 'Never'}</td>
                `;
                tbody.appendChild(row);
            });
            
            if (playerNames.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7" style="text-align: center;">No player statistics available yet.</td></tr>';
            }
        }
        
        function updateGameHistory() {
            const container = document.getElementById('gameHistoryList');
            const games = gameData.games || [];
            
            if (games.length === 0) {
                container.innerHTML = '<p>No games recorded yet.</p>';
                return;
            }
            
            // Sort games by date (newest first)
            games.sort((a, b) => new Date(b.date) - new Date(a.date));
            
            container.innerHTML = '';
            games.forEach(game => {
                const gameElem = document.createElement('div');
                gameElem.className = `game-item ${game.team_a.score === game.team_b.score ? '' : 
                    (game.team_a.score > game.team_b.score ? '' : 'lost')}`;
                
                const winner = game.team_a.score > game.team_b.score ? 'Team A' : 
                              game.team_b.score > game.team_a.score ? 'Team B' : 'Draw';
                
                gameElem.innerHTML = `
                    <div class="game-header">
                        <div class="game-score">${game.team_a.score} - ${game.team_b.score}</div>
                        <div class="game-date">${game.date}</div>
                    </div>
                    <div><strong>Winner:</strong> ${winner}</div>
                    <div><strong>Location:</strong> ${game.location || 'Unknown'}</div>
                    ${game.notes ? `<div><strong>Notes:</strong> ${game.notes}</div>` : ''}
                `;
                container.appendChild(gameElem);
            });
        }
        
        function updateGameTeamsDisplay() {
            // This would update any game-related displays with current data
        }
        
        function exportData() {
            document.getElementById('exportSection').classList.remove('hidden');
            document.getElementById('importSection').classList.add('hidden');
            document.getElementById('exportData').value = JSON.stringify(gameData, null, 2);
        }
        
        function copyExportData() {
            const exportData = document.getElementById('exportData');
            exportData.select();
            document.execCommand('copy');
            alert('Data copied to clipboard!');
        }
        
        function importData() {
            document.getElementById('importSection').classList.remove('hidden');
            document.getElementById('exportSection').classList.add('hidden');
        }
        
        function cancelImport() {
            document.getElementById('importSection').classList.add('hidden');
            document.getElementById('importData').value = '';
        }
        
        function processImport() {
            const importData = document.getElementById('importData').value;
            if (!importData.trim()) {
                alert('Please paste data to import!');
                return;
            }
            
            try {
                const parsedData = JSON.parse(importData);
                
                if (!parsedData.players || !parsedData.games) {
                    alert('Invalid data format!');
                    return;
                }
                
                if (!confirm('This will replace all current data. Are you sure?')) {
                    return;
                }
                
                fetch('/import-data', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(parsedData)
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        alert('Data imported successfully!');
                        cancelImport();
                        loadGameData();
                    } else {
                        alert('Error importing data: ' + (data.error || 'Unknown error'));
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('Error importing data');
                });
                
            } catch (e) {
                alert('Invalid JSON data! Please check your input.');
            }
        }
        
        function clearAllData() {
            if (!confirm('This will permanently delete ALL data (players, games, statistics). Are you sure?')) {
                return;
            }
            
            if (!confirm('This action cannot be undone. Are you absolutely sure?')) {
                return;
            }
            
            fetch('/clear-data', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('All data cleared successfully!');
                    loadGameData();
                    // Reset form
                    const form = document.getElementById('playerForm');
                    while (form.children.length > 1) {
                        form.removeChild(form.lastChild);
                    }
                    playerCount = 0;
                    addPlayerField();
                    addPlayerField();
                } else {
                    alert('Error clearing data: ' + (data.error || 'Unknown error'));
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error clearing data');
            });
        }
    </script>
</body>
</html>
    '''

# Add storage status route
@app.route('/storage-status')
def storage_status():
    data = load_data()
    total_games = len(data.get('games', []))
    total_players = len(data.get('players', {}))
    
    # Check if we're using Supabase by making a test request
    test_data = SupabaseManager.load_data()
    using_supabase = test_data is not None and 'players' in test_data
    
    return jsonify({
        'using_supabase': using_supabase,
        'total_games': total_games,
        'total_players': total_players
    })

@app.route('/test-supabase')
def test_supabase():
    try:
        test_data = SupabaseManager.load_data()
        if test_data is not None:
            return jsonify({'connected': True})
        else:
            return jsonify({'connected': False, 'error': 'No data returned from Supabase'})
    except Exception as e:
        return jsonify({'connected': False, 'error': str(e)})

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
                    'last_played': None
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
                    'last_played': None
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
                    'last_played': None
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
