from flask import Flask, request, jsonify
import random
import math
import traceback
import json
from datetime import datetime, date
import os

app = Flask(__name__)

# Simple file-based storage
DATA_FILE = 'football_data.json'

def load_data():
    """Load existing data from file"""
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
                print(f"Loaded data: {len(data.get('games', []))} games, {len(data.get('players', {}))} players")
                return data
    except Exception as e:
        print(f"Error loading data: {e}")
    
    # Return default structure if no file exists
    default_data = {
        'players': {},
        'games': [],
        'current_players': []
    }
    print("Returning default data structure")
    return default_data

def save_data(data):
    """Save data to file"""
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Saved data: {len(data.get('games', []))} games, {len(data.get('players', {}))} players")
        return True
    except Exception as e:
        print(f"Error saving data: {e}")
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
        
        .storage-status.active {
            background: rgba(76, 175, 80, 0.2);
            border: 1px solid rgba(76, 175, 80, 0.5);
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
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>⚽ Football Team Manager</h1>
            <p>Team splitting, game tracking, and player performance analytics</p>
            <div id="storageStatus" class="storage-status">
                Loading storage status...
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
                    </div>
                </div>
            </div>
            
            <!-- Data Management Tab -->
            <div id="data-management" class="tab-content">
                <div class="stats-section">
                    <h2>🔧 Data Management</h2>
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
            
            <!-- Include other tabs (Game Tracker, Player Stats, Game History) from your working version -->
            
        </div>
        
        <div class="instructions">
            <h3>How to Use the System</h3>
            <ul>
                <li><strong>Team Splitter:</strong> Create balanced teams and save player lists</li>
                <li><strong>Game Tracker:</strong> Record game scores and details</li>
                <li><strong>Player Statistics:</strong> View performance metrics and win rates</li>
                <li><strong>Game History:</strong> Review past games and results</li>
                <li><strong>Data Management:</strong> Export/import your data for backup</li>
                <li>Data is automatically saved between sessions</li>
            </ul>
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
            // Hide all tabs
            document.querySelectorAll('.tab-content').forEach(tab => {
                tab.classList.remove('active');
            });
            document.querySelectorAll('.tab').forEach(tab => {
                tab.classList.remove('active');
            });
            
            // Show selected tab
            document.getElementById(tabName).classList.add('active');
            event.target.classList.add('active');
            
            // Refresh data when switching to stats or history tabs
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
            
            if (gameData && gameData.games) {
                const totalGames = gameData.games.length;
                const totalPlayers = Object.keys(gameData.players || {}).length;
                
                statusElement.innerHTML = `✅ Data Loaded | ${totalGames} Games | ${totalPlayers} Players`;
                statusElement.className = 'storage-status active';
                
                storageInfoElement.innerHTML = `
                    <strong>Current Data Summary:</strong><br>
                    • Games Recorded: ${totalGames}<br>
                    • Players Tracked: ${totalPlayers}<br>
                    • Last Updated: Just now<br>
                    • Storage: File System
                `;
            } else {
                statusElement.innerHTML = 'No data loaded yet';
                statusElement.className = 'storage-status';
                storageInfoElement.innerHTML = 'No data available yet. Start by creating teams and recording games!';
            }
        }
        
        function addPlayerField(name = '', position = 'midfielder', skill = '5') {
            playerCount++;
            const form = document.getElementById('playerForm');
            const div = document.createElement('div');
            div.className = 'form-row';
            div.innerHTML = `
                <input type="text" class="player-name" placeholder="Player name" value="${name}">
                <select class="player-position">
                    <option value="goalkeeper" ${position === 'goalkeeper' ? 'selected' : ''}>Goalkeeper</option>
                    <option value="defender" ${position === 'defender' ? 'selected' : ''}>Defender</option>
                    <option value="left_wing" ${position === 'left_wing' ? 'selected' : ''}>Left Wing</option>
                    <option value="right_wing" ${position === 'right_wing' ? 'selected' : ''}>Right Wing</option>
                    <option value="midfielder" ${position === 'midfielder' ? 'selected' : ''}>Midfielder</option>
                    <option value="forward" ${position === 'forward' ? 'selected' : ''}>Forward</option>
                </select>
                <input type="number" class="player-skill skill-input" min="1" max="10" value="${skill}">
                <button type="button" class="remove-btn" onclick="this.parentElement.remove()">✕</button>
            `;
            form.appendChild(div);
        }
        
        function addSampleTeam() {
            document.getElementById('playerForm').querySelectorAll('.form-row:not(:first-child)').forEach(row => row.remove());
            playerCount = 0;
            
            const samplePlayers = [
                ['Alex', 'goalkeeper', 8],
                ['Ben', 'defender', 7],
                ['Chris', 'defender', 6],
                ['David', 'left_wing', 7],
                ['Eric', 'right_wing', 6],
                ['Frank', 'midfielder', 8],
                ['George', 'midfielder', 7],
                ['Henry', 'midfielder', 6],
                ['Ian', 'forward', 8],
                ['John', 'forward', 6],
                ['Kevin', 'forward', 5],
                ['Liam', 'goalkeeper', 6]
            ];
            
            samplePlayers.forEach(player => addPlayerField(player[0], player[1], player[2]));
        }
        
        function getPlayersData() {
            const players = [];
            const rows = document.getElementById('playerForm').querySelectorAll('.form-row:not(:first-child)');
            
            rows.forEach(row => {
                const name = row.querySelector('.player-name').value.trim();
                const position = row.querySelector('.player-position').value;
                const skill = parseInt(row.querySelector('.player-skill').value) || 5;
                
                if (name) {
                    players.push({
                        name: name,
                        position: position,
                        skill_level: skill
                    });
                }
            });
            
            return players;
        }
        
        function balanceTeams() {
            const players = getPlayersData();
            
            if (players.length < 2) {
                alert('Please add at least 2 players');
                return;
            }
            
            fetch('/balance-teams', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ players: players })
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`Server returned ${response.status}: ${response.statusText}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.error) {
                    alert('Error: ' + data.error);
                } else {
                    currentTeams = data;
                    displayTeams(data.team_a, data.team_b, data.strength_a, data.strength_b);
                    updateGameTeamsDisplay();
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error balancing teams: ' + error.message);
            });
        }
        
        function randomizeTeams() {
            const players = getPlayersData();
            
            if (players.length < 2) {
                alert('Please add at least 2 players');
                return;
            }
            
            fetch('/random-teams', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ players: players })
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`Server returned ${response.status}: ${response.statusText}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.error) {
                    alert('Error: ' + data.error);
                } else {
                    currentTeams = data;
                    displayTeams(data.team_a, data.team_b, data.strength_a, data.strength_b);
                    updateGameTeamsDisplay();
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error creating random teams: ' + error.message);
            });
        }
        
        function displayTeams(teamA, teamB, strengthA, strengthB) {
            const teamAElement = document.getElementById('teamA');
            const teamBElement = document.getElementById('teamB');
            const balanceIndicator = document.getElementById('balanceIndicator');
            const teamAStrengthElement = document.getElementById('teamAStrength');
            const teamBStrengthElement = document.getElementById('teamBStrength');
            
            if (teamAStrengthElement) {
                teamAStrengthElement.textContent = `Strength: ${strengthA.toFixed(1)}`;
            }
            if (teamBStrengthElement) {
                teamBStrengthElement.textContent = `Strength: ${strengthB.toFixed(1)}`;
            }
            
            const balanceDiff = Math.abs(strengthA - strengthB);
            const isBalanced = balanceDiff < 3;
            
            if (balanceIndicator) {
                balanceIndicator.innerHTML = isBalanced ? 
                    `✅ Teams are well balanced! (Difference: ${balanceDiff.toFixed(1)})` :
                    `⚠️ Teams are somewhat unbalanced (Difference: ${balanceDiff.toFixed(1)})`;
                balanceIndicator.className = `balance-indicator ${isBalanced ? 'balanced' : 'unbalanced'}`;
            }
            
            if (teamAElement) {
                teamAElement.innerHTML = teamA.map(player => `
                    <li class="player-item">
                        <div class="player-info">
                            <div class="player-name">${player.name}</div>
                            <div class="player-details">
                                <span class="position-badge position-${player.position.substring(0, 3)}">${player.position.replace('_', ' ')}</span>
                                • Skill: ${player.skill_level}/10
                            </div>
                        </div>
                    </li>
                `).join('');
            }
            
            if (teamBElement) {
                teamBElement.innerHTML = teamB.map(player => `
                    <li class="player-item">
                        <div class="player-info">
                            <div class="player-name">${player.name}</div>
                            <div class="player-details">
                                <span class="position-badge position-${player.position.substring(0, 3)}">${player.position.replace('_', ' ')}</span>
                                • Skill: ${player.skill_level}/10
                            </div>
                        </div>
                    </li>
                `).join('');
            }
        }
        
        function saveCurrentPlayers() {
            const players = getPlayersData();
            if (players.length === 0) {
                alert('No players to save');
                return;
            }
            
            fetch('/save-players', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ players: players })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('Players saved successfully!');
                    loadGameData();
                } else {
                    alert('Error saving players: ' + data.error);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error saving players');
            });
        }
        
        function loadSavedPlayers() {
            document.getElementById('playerForm').querySelectorAll('.form-row:not(:first-child)').forEach(row => row.remove());
            playerCount = 0;
            
            if (gameData.current_players && gameData.current_players.length > 0) {
                gameData.current_players.forEach(player => {
                    addPlayerField(player.name, player.position, player.skill_level);
                });
                alert('Loaded ' + gameData.current_players.length + ' saved players');
            } else {
                alert('No saved players found');
            }
        }
        
        function updateGameTeamsDisplay() {
            const gameTeamsDiv = document.getElementById('gameTeams');
            if (!gameTeamsDiv) return;
            
            if (currentTeams.team_a && currentTeams.team_a.length > 0) {
                gameTeamsDiv.innerHTML = `
                    <div class="teams-display">
                        <div class="team">
                            <h3>🔵 Team A</h3>
                            <ul class="player-list">
                                ${currentTeams.team_a.map(player => `
                                    <li class="player-item">
                                        <div class="player-info">
                                            <div class="player-name">${player.name}</div>
                                            <div class="player-details">
                                                <span class="position-badge position-${player.position.substring(0, 3)}">${player.position.replace('_', ' ')}</span>
                                            </div>
                                        </div>
                                    </li>
                                `).join('')}
                            </ul>
                        </div>
                        <div class="team">
                            <h3>🔴 Team B</h3>
                            <ul class="player-list">
                                ${currentTeams.team_b.map(player => `
                                    <li class="player-item">
                                        <div class="player-info">
                                            <div class="player-name">${player.name}</div>
                                            <div class="player-details">
                                                <span class="position-badge position-${player.position.substring(0, 3)}">${player.position.replace('_', ' ')}</span>
                                            </div>
                                        </div>
                                    </li>
                                `).join('')}
                            </ul>
                        </div>
                    </div>
                `;
            } else {
                gameTeamsDiv.innerHTML = '<p>First create balanced teams in the Team Splitter tab</p>';
            }
        }
        
        function recordGameResult() {
            const teamAScore = parseInt(document.getElementById('teamAScore').value) || 0;
            const teamBScore = parseInt(document.getElementById('teamBScore').value) || 0;
            const gameDate = document.getElementById('gameDate').value;
            const location = document.getElementById('gameLocation').value;
            const notes = document.getElementById('gameNotes').value;
            
            if (!currentTeams.team_a || currentTeams.team_a.length === 0) {
                alert('Please create teams first in the Team Splitter tab');
                return;
            }
            
            const gameDataToSave = {
                date: gameDate,
                location: location,
                notes: notes,
                team_a: {
                    players: currentTeams.team_a,
                    score: teamAScore
                },
                team_b: {
                    players: currentTeams.team_b,
                    score: teamBScore
                }
            };
            
            fetch('/record-game', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(gameDataToSave)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('Game recorded successfully!');
                    // Reset scores
                    document.getElementById('teamAScore').value = 0;
                    document.getElementById('teamBScore').value = 0;
                    document.getElementById('gameNotes').value = '';
                    loadGameData();
                } else {
                    alert('Error recording game: ' + data.error);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error recording game');
            });
        }
        
        function loadLastGame() {
            if (gameData.games && gameData.games.length > 0) {
                const lastGame = gameData.games[gameData.games.length - 1];
                document.getElementById('teamAScore').value = lastGame.team_a.score;
                document.getElementById('teamBScore').value = lastGame.team_b.score;
                document.getElementById('gameDate').value = lastGame.date;
                document.getElementById('gameLocation').value = lastGame.location || '';
                document.getElementById('gameNotes').value = lastGame.notes || '';
                
                // Load teams
                currentTeams = {
                    team_a: lastGame.team_a.players,
                    team_b: lastGame.team_b.players
                };
                updateGameTeamsDisplay();
                
                alert('Last game loaded successfully');
            } else {
                alert('No previous games found');
            }
        }
        
        function updatePlayerStats() {
            const statsBody = document.getElementById('playerStatsBody');
            if (!statsBody) return;
            
            if (!gameData.players || Object.keys(gameData.players).length === 0) {
                statsBody.innerHTML = '<tr><td colspan="8" style="text-align: center;">No player data available</td></tr>';
                return;
            }
            
            let statsHTML = '';
            Object.entries(gameData.players).forEach(([playerName, playerData]) => {
                const totalGames = playerData.games_played || 0;
                const wins = playerData.wins || 0;
                const losses = totalGames - wins;
                const winRate = totalGames > 0 ? ((wins / totalGames) * 100).toFixed(1) : 0;
                const avgRating = playerData.average_rating ? playerData.average_rating.toFixed(1) : 'N/A';
                const goals = playerData.total_goals || 0;
                const lastPlayed = playerData.last_played || 'Never';
                
                let winRateClass = 'medium';
                if (winRate >= 60) winRateClass = 'high';
                else if (winRate < 40) winRateClass = 'low';
                
                statsHTML += `
                    <tr>
                        <td><strong>${playerName}</strong></td>
                        <td>${totalGames}</td>
                        <td>${wins}</td>
                        <td>${losses}</td>
                        <td><span class="win-rate ${winRateClass}">${winRate}%</span></td>
                        <td>${avgRating}</td>
                        <td>${goals}</td>
                        <td>${lastPlayed}</td>
                    </tr>
                `;
            });
            
            statsBody.innerHTML = statsHTML || '<tr><td colspan="8" style="text-align: center;">No game data recorded yet</td></tr>';
        }
        
        function updateGameHistory() {
            const historyList = document.getElementById('gameHistoryList');
            if (!historyList) return;
            
            if (!gameData.games || gameData.games.length === 0) {
                historyList.innerHTML = '<p style="text-align: center; opacity: 0.8;">No games recorded yet</p>';
                return;
            }
            
            let historyHTML = '';
            gameData.games.slice().reverse().forEach((game, index) => {
                const gameNumber = gameData.games.length - index;
                const winner = game.team_a.score > game.team_b.score ? 'Team A' : 
                              game.team_b.score > game.team_a.score ? 'Team B' : 'Draw';
                const isWin = winner !== 'Draw';
                
                historyHTML += `
                    <div class="game-item ${isWin ? '' : 'lost'}">
                        <div class="game-header">
                            <strong>Game #${gameNumber}</strong>
                            <span class="game-date">${game.date}</span>
                        </div>
                        <div class="game-score">
                            Team A: ${game.team_a.score} - ${game.team_b.score} :Team B
                            ${winner !== 'Draw' ? `<span style="margin-left: 10px;">🏆 ${winner} Wins!</span>` : '🤝 Draw'}
                        </div>
                        ${game.location ? `<div><strong>Location:</strong> ${game.location}</div>` : ''}
                        ${game.notes ? `<div><strong>Notes:</strong> ${game.notes}</div>` : ''}
                    </div>
                `;
            });
            
            historyList.innerHTML = historyHTML;
        }
        
        function exportData() {
            const exportData = JSON.stringify(gameData, null, 2);
            document.getElementById('exportData').value = exportData;
            document.getElementById('exportSection').classList.remove('hidden');
        }
        
        function importData() {
            document.getElementById('importSection').classList.remove('hidden');
        }
        
        function copyExportData() {
            const exportText = document.getElementById('exportData');
            exportText.select();
            document.execCommand('copy');
            alert('Data copied to clipboard!');
        }
        
        function processImport() {
            const importText = document.getElementById('importData').value;
            try {
                const importedData = JSON.parse(importText);
                
                if (confirm('This will replace ALL current data. Are you sure?')) {
                    fetch('/import-data', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify(importedData)
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            alert('Data imported successfully!');
                            loadGameData();
                            cancelImport();
                        } else {
                            alert('Error importing data: ' + data.error);
                        }
                    })
                    .catch(error => {
                        alert('Error importing data: ' + error.message);
                    });
                }
            } catch (e) {
                alert('Invalid data format. Please check your exported data.');
            }
        }
        
        function cancelImport() {
            document.getElementById('importSection').classList.add('hidden');
            document.getElementById('importData').value = '';
        }
        
        function clearAllData() {
            if (confirm('🚨 DANGER! This will permanently delete ALL data including games, players, and statistics. This cannot be undone!')) {
                if (confirm('Are you absolutely sure? This will delete everything!')) {
                    fetch('/clear-data', {
                        method: 'POST'
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            alert('All data cleared successfully!');
                            loadGameData();
                        } else {
                            alert('Error clearing data: ' + data.error);
                        }
                    })
                    .catch(error => {
                        alert('Error clearing data: ' + error.message);
                    });
                }
            }
        }
    </script>
</body>
</html>
    '''

# Add the data management routes
@app.route('/import-data', methods=['POST'])
def import_data():
    """Import data from JSON"""
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
    """Clear all data"""
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

# Keep all your existing routes
@app.route('/load-data', methods=['GET'])
def load_data_route():
    try:
        data = load_data()
        return jsonify(data)
    except Exception as e:
        print(f"Error in load-data: {e}")
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
        error_msg = f"Error in balance_teams: {str(e)}"
        print(error_msg)
        return jsonify({'error': error_msg}), 500

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
        error_msg = f"Error in random_teams: {str(e)}"
        print(error_msg)
        return jsonify({'error': error_msg}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
