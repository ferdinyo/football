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
        :root {
            --primary-color: #2c3e50;
            --secondary-color: #3498db;
            --accent-color: #e74c3c;
            --light-color: #ecf0f1;
            --dark-color: #34495e;
            --success-color: #2ecc71;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        
        body {
            background-color: #f5f7fa;
            color: #333;
            line-height: 1.6;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        header {
            background-color: var(--primary-color);
            color: white;
            padding: 20px 0;
            border-radius: 8px 8px 0 0;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }
        
        .header-content {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0 20px;
        }
        
        h1 {
            font-size: 28px;
            font-weight: 600;
        }
        
        .status-bar {
            display: flex;
            gap: 20px;
            font-size: 14px;
        }
        
        .status-item {
            background-color: var(--dark-color);
            padding: 5px 10px;
            border-radius: 4px;
        }
        
        .active {
            color: var(--success-color);
        }
        
        nav {
            background-color: var(--secondary-color);
            padding: 15px 0;
            border-radius: 0 0 8px 8px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }
        
        .nav-tabs {
            display: flex;
            justify-content: center;
            gap: 10px;
            padding: 0 20px;
        }
        
        .tab {
            background-color: rgba(255, 255, 255, 0.2);
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 4px;
            cursor: pointer;
            transition: background-color 0.3s;
            font-weight: 500;
        }
        
        .tab:hover, .tab.active {
            background-color: white;
            color: var(--secondary-color);
        }
        
        .main-content {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-top: 20px;
        }
        
        .panel {
            background-color: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }
        
        .panel-title {
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 15px;
            color: var(--primary-color);
            border-bottom: 1px solid #eee;
            padding-bottom: 10px;
        }
        
        .form-group {
            margin-bottom: 15px;
        }
        
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: 500;
        }
        
        input, select {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }
        
        .btn {
            background-color: var(--secondary-color);
            color: white;
            border: none;
            padding: 10px 15px;
            border-radius: 4px;
            cursor: pointer;
            font-weight: 500;
            transition: background-color 0.3s;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 5px;
        }
        
        .btn:hover {
            background-color: var(--primary-color);
        }
        
        .btn-danger {
            background-color: var(--accent-color);
        }
        
        .btn-success {
            background-color: var(--success-color);
        }
        
        .button-group {
            display: flex;
            gap: 10px;
            margin-top: 15px;
        }
        
        .players-list {
            max-height: 300px;
            overflow-y: auto;
            border: 1px solid #eee;
            border-radius: 4px;
            padding: 10px;
            margin-top: 15px;
        }
        
        .player-item {
            display: flex;
            justify-content: space-between;
            padding: 8px 5px;
            border-bottom: 1px solid #f0f0f0;
        }
        
        .player-item:last-child {
            border-bottom: none;
        }
        
        .player-info {
            display: flex;
            gap: 10px;
        }
        
        .player-name {
            font-weight: 500;
        }
        
        .player-position {
            color: var(--secondary-color);
            font-size: 12px;
            background-color: #e1f0fa;
            padding: 2px 6px;
            border-radius: 10px;
        }
        
        .player-skill {
            color: var(--dark-color);
            font-weight: 600;
        }
        
        .teams-container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-top: 20px;
        }
        
        .team {
            background-color: #f8f9fa;
            border-radius: 8px;
            padding: 15px;
            border: 1px solid #e9ecef;
        }
        
        .team-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        
        .team-name {
            font-weight: 600;
            font-size: 18px;
            color: var(--primary-color);
        }
        
        .team-strength {
            background-color: var(--dark-color);
            color: white;
            padding: 5px 10px;
            border-radius: 4px;
            font-size: 14px;
        }
        
        .team-players {
            min-height: 150px;
        }
        
        .hidden {
            display: none;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
            margin-top: 15px;
        }
        
        .stat-card {
            background-color: #f8f9fa;
            border-radius: 8px;
            padding: 15px;
            text-align: center;
        }
        
        .stat-value {
            font-size: 24px;
            font-weight: 700;
            color: var(--secondary-color);
            margin: 10px 0;
        }
        
        .stat-label {
            font-size: 14px;
            color: var(--dark-color);
        }
        
        .game-history {
            margin-top: 15px;
        }
        
        .game-item {
            display: flex;
            justify-content: space-between;
            padding: 10px;
            border-bottom: 1px solid #eee;
        }
        
        .game-result {
            font-weight: 600;
        }
        
        .game-date {
            color: #777;
            font-size: 14px;
        }
        
        footer {
            text-align: center;
            margin-top: 30px;
            padding: 20px;
            color: #777;
            font-size: 14px;
        }
        
        @media (max-width: 768px) {
            .main-content {
                grid-template-columns: 1fr;
            }
            
            .nav-tabs {
                flex-wrap: wrap;
            }
            
            .teams-container {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="header-content">
                <h1>Football Team Manager</h1>
                <div class="status-bar">
                    <div class="status-item active">Cloud Storage Active</div>
                    <div class="status-item">0 Games</div>
                    <div class="status-item">0 Players</div>
                </div>
            </div>
        </header>
        
        <nav>
            <div class="nav-tabs">
                <button class="tab active" data-tab="team-splitter">Team Splitter</button>
                <button class="tab" data-tab="game-tracker">Game Tracker</button>
                <button class="tab" data-tab="player-statistics">Player Statistics</button>
                <button class="tab" data-tab="game-history">Game History</button>
                <button class="tab" data-tab="data-management">Data Management</button>
            </div>
        </nav>
        
        <main class="main-content">
            <div class="panel">
                <h2 class="panel-title">Add Players</h2>
                <div class="form-group">
                    <label for="player-name">Player Name</label>
                    <input type="text" id="player-name" placeholder="Enter player name">
                </div>
                <div class="form-group">
                    <label for="player-position">Position</label>
                    <select id="player-position">
                        <option value="">Select position</option>
                        <option value="Goalkeeper">Goalkeeper</option>
                        <option value="Defender">Defender</option>
                        <option value="Midfielder">Midfielder</option>
                        <option value="Forward">Forward</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="player-skill">Skill (1-10)</label>
                    <input type="number" id="player-skill" min="1" max="10" placeholder="Enter skill level">
                </div>
                <button class="btn" id="add-player-btn">+ Add Player</button>
                
                <div class="button-group">
                    <button class="btn btn-success" id="add-sample-btn">Add Sample</button>
                    <button class="btn" id="load-saved-btn">Load Saved</button>
                </div>
                
                <div class="players-list" id="players-list">
                    <!-- Player list will be populated here -->
                </div>
            </div>
            
            <div class="panel">
                <h2 class="panel-title">Teams</h2>
                <p>Click "Balance Teams" to create balanced teams</p>
                
                <div class="button-group">
                    <button class="btn" id="balance-teams-btn">Balance Teams</button>
                    <button class="btn" id="random-teams-btn">Random Teams</button>
                    <button class="btn btn-success" id="save-players-btn">Save Players</button>
                </div>
                
                <div class="teams-container">
                    <div class="team">
                        <div class="team-header">
                            <div class="team-name">Team A</div>
                            <div class="team-strength">Strength: <span id="team-a-strength">0</span></div>
                        </div>
                        <div class="team-players" id="team-a-players">
                            <!-- Team A players will be listed here -->
                        </div>
                    </div>
                    
                    <div class="team">
                        <div class="team-header">
                            <div class="team-name">Team B</div>
                            <div class="team-strength">Strength: <span id="team-b-strength">0</span></div>
                        </div>
                        <div class="team-players" id="team-b-players">
                            <!-- Team B players will be listed here -->
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Additional panels for other tabs -->
            <div id="game-tracker-panel" class="panel hidden">
                <h2 class="panel-title">Game Tracker</h2>
                <p>Track and record game results here.</p>
                <!-- Game tracker content would go here -->
            </div>
            
            <div id="player-statistics-panel" class="panel hidden">
                <h2 class="panel-title">Player Statistics</h2>
                <p>View detailed player performance analytics.</p>
                <!-- Player statistics content would go here -->
            </div>
            
            <div id="game-history-panel" class="panel hidden">
                <h2 class="panel-title">Game History</h2>
                <p>Review past games and results.</p>
                <!-- Game history content would go here -->
            </div>
            
            <div id="data-management-panel" class="panel hidden">
                <h2 class="panel-title">Data Management</h2>
                <p>Manage your data storage and backups.</p>
                <!-- Data management content would go here -->
            </div>
        </main>
        
        <footer>
            <p>Football Team Manager &copy; 2025 | All rights reserved</p>
        </footer>
    </div>

    <script>
        // Sample data for demonstration
        const samplePlayers = [
            { id: 1, name: "John Smith", position: "Forward", skill: 8 },
            { id: 2, name: "Michael Johnson", position: "Midfielder", skill: 7 },
            { id: 3, name: "David Williams", position: "Defender", skill: 6 },
            { id: 4, name: "Robert Brown", position: "Goalkeeper", skill: 9 },
            { id: 5, name: "James Davis", position: "Forward", skill: 7 },
            { id: 6, name: "Daniel Miller", position: "Midfielder", skill: 8 },
            { id: 7, name: "Thomas Wilson", position: "Defender", skill: 6 },
            { id: 8, name: "Paul Moore", position: "Midfielder", skill: 7 }
        ];

        let players = [];
        let teams = { teamA: [], teamB: [] };

        // DOM Elements
        const playerNameInput = document.getElementById('player-name');
        const playerPositionSelect = document.getElementById('player-position');
        const playerSkillInput = document.getElementById('player-skill');
        const addPlayerBtn = document.getElementById('add-player-btn');
        const addSampleBtn = document.getElementById('add-sample-btn');
        const loadSavedBtn = document.getElementById('load-saved-btn');
        const playersList = document.getElementById('players-list');
        const balanceTeamsBtn = document.getElementById('balance-teams-btn');
        const randomTeamsBtn = document.getElementById('random-teams-btn');
        const savePlayersBtn = document.getElementById('save-players-btn');
        const teamAStrength = document.getElementById('team-a-strength');
        const teamBStrength = document.getElementById('team-b-strength');
        const teamAPlayers = document.getElementById('team-a-players');
        const teamBPlayers = document.getElementById('team-b-players');
        const tabs = document.querySelectorAll('.tab');
        const panels = document.querySelectorAll('.panel');

        // Initialize the application
        function init() {
            updatePlayersList();
            updateStatusBar();
            setupEventListeners();
        }

        // Set up event listeners
        function setupEventListeners() {
            addPlayerBtn.addEventListener('click', addPlayer);
            addSampleBtn.addEventListener('click', addSamplePlayers);
            loadSavedBtn.addEventListener('click', loadSavedPlayers);
            balanceTeamsBtn.addEventListener('click', balanceTeams);
            randomTeamsBtn.addEventListener('click', createRandomTeams);
            savePlayersBtn.addEventListener('click', savePlayers);
            
            // Tab navigation
            tabs.forEach(tab => {
                tab.addEventListener('click', () => {
                    const tabId = tab.getAttribute('data-tab');
                    switchTab(tabId);
                });
            });
        }

        // Add a new player
        function addPlayer() {
            const name = playerNameInput.value.trim();
            const position = playerPositionSelect.value;
            const skill = parseInt(playerSkillInput.value);
            
            if (!name || !position || isNaN(skill) || skill < 1 || skill > 10) {
                alert('Please fill in all fields with valid values');
                return;
            }
            
            const newPlayer = {
                id: Date.now(), // Simple ID generation
                name,
                position,
                skill
            };
            
            players.push(newPlayer);
            updatePlayersList();
            updateStatusBar();
            clearPlayerForm();
        }

        // Add sample players
        function addSamplePlayers() {
            players = [...players, ...samplePlayers];
            updatePlayersList();
            updateStatusBar();
        }

        // Load saved players (simulated)
        function loadSavedPlayers() {
            // In a real app, this would load from localStorage or a server
            const savedPlayers = JSON.parse(localStorage.getItem('footballPlayers') || '[]');
            if (savedPlayers.length > 0) {
                players = savedPlayers;
                updatePlayersList();
                updateStatusBar();
                alert('Saved players loaded successfully!');
            } else {
                alert('No saved players found. Try adding some players first and saving them.');
            }
        }

        // Save players to localStorage
        function savePlayers() {
            if (players.length === 0) {
                alert('No players to save. Please add some players first.');
                return;
            }
            
            localStorage.setItem('footballPlayers', JSON.stringify(players));
            alert('Players saved successfully!');
        }

        // Balance teams based on player skill
        function balanceTeams() {
            if (players.length < 2) {
                alert('Need at least 2 players to create teams');
                return;
            }
            
            // Sort players by skill (descending)
            const sortedPlayers = [...players].sort((a, b) => b.skill - a.skill);
            
            // Reset teams
            teams.teamA = [];
            teams.teamB = [];
            
            // Distribute players to balance teams
            sortedPlayers.forEach((player, index) => {
                if (index % 2 === 0) {
                    teams.teamA.push(player);
                } else {
                    teams.teamB.push(player);
                }
            });
            
            updateTeamsDisplay();
        }

        // Create random teams
        function createRandomTeams() {
            if (players.length < 2) {
                alert('Need at least 2 players to create teams');
                return;
            }
            
            // Reset teams
            teams.teamA = [];
            teams.teamB = [];
            
            // Shuffle players array
            const shuffledPlayers = [...players].sort(() => Math.random() - 0.5);
            
            // Distribute players randomly
            shuffledPlayers.forEach((player, index) => {
                if (index % 2 === 0) {
                    teams.teamA.push(player);
                } else {
                    teams.teamB.push(player);
                }
            });
            
            updateTeamsDisplay();
        }

        // Update the players list display
        function updatePlayersList() {
            playersList.innerHTML = '';
            
            if (players.length === 0) {
                playersList.innerHTML = '<p>No players added yet</p>';
                return;
            }
            
            players.forEach(player => {
                const playerElement = document.createElement('div');
                playerElement.className = 'player-item';
                playerElement.innerHTML = `
                    <div class="player-info">
                        <span class="player-name">${player.name}</span>
                        <span class="player-position">${player.position}</span>
                    </div>
                    <div class="player-skill">${player.skill}/10</div>
                `;
                playersList.appendChild(playerElement);
            });
        }

        // Update teams display
        function updateTeamsDisplay() {
            // Clear team displays
            teamAPlayers.innerHTML = '';
            teamBPlayers.innerHTML = '';
            
            // Calculate team strengths
            const teamAStrengthValue = teams.teamA.reduce((sum, player) => sum + player.skill, 0);
            const teamBStrengthValue = teams.teamB.reduce((sum, player) => sum + player.skill, 0);
            
            // Update strength displays
            teamAStrength.textContent = teamAStrengthValue;
            teamBStrength.textContent = teamBStrengthValue;
            
            // Add players to Team A display
            if (teams.teamA.length === 0) {
                teamAPlayers.innerHTML = '<p>No players in this team</p>';
            } else {
                teams.teamA.forEach(player => {
                    const playerElement = document.createElement('div');
                    playerElement.className = 'player-item';
                    playerElement.innerHTML = `
                        <div class="player-info">
                            <span class="player-name">${player.name}</span>
                            <span class="player-position">${player.position}</span>
                        </div>
                        <div class="player-skill">${player.skill}/10</div>
                    `;
                    teamAPlayers.appendChild(playerElement);
                });
            }
            
            // Add players to Team B display
            if (teams.teamB.length === 0) {
                teamBPlayers.innerHTML = '<p>No players in this team</p>';
            } else {
                teams.teamB.forEach(player => {
                    const playerElement = document.createElement('div');
                    playerElement.className = 'player-item';
                    playerElement.innerHTML = `
                        <div class="player-info">
                            <span class="player-name">${player.name}</span>
                            <span class="player-position">${player.position}</span>
                        </div>
                        <div class="player-skill">${player.skill}/10</div>
                    `;
                    teamBPlayers.appendChild(playerElement);
                });
            }
        }

        // Update status bar with current counts
        function updateStatusBar() {
            const statusItems = document.querySelectorAll('.status-item');
            statusItems[1].textContent = `${players.length} Players`;
        }

        // Clear the player form
        function clearPlayerForm() {
            playerNameInput.value = '';
            playerPositionSelect.value = '';
            playerSkillInput.value = '';
        }

        // Switch between tabs
        function switchTab(tabId) {
            // Update active tab
            tabs.forEach(tab => {
                if (tab.getAttribute('data-tab') === tabId) {
                    tab.classList.add('active');
                } else {
                    tab.classList.remove('active');
                }
            });
            
            // Show/hide panels
            panels.forEach(panel => {
                if (panel.id === `${tabId}-panel`) {
                    panel.classList.remove('hidden');
                } else if (panel.id && panel.id.includes('-panel')) {
                    panel.classList.add('hidden');
                }
            });
        }

        // Initialize the app when DOM is loaded
        document.addEventListener('DOMContentLoaded', init);
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

# Add all your existing routes (load-data, save-players, record-game, balance-teams, etc.)
# These remain the same as in previous versions

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
