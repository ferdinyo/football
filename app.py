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
    <title>Team Splitter App</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f8f9fa;
            color: #333;
        }

        .container {
            max-width: 1000px;
            margin: 40px auto;
            padding: 20px;
            background-color: white;
            border-radius: 10px;
            box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
        }

        h1 {
            text-align: center;
            margin-bottom: 20px;
        }

        /* Tabs */
        .tab-container {
            display: flex;
            justify-content: space-around;
            border-bottom: 2px solid #ccc;
            margin-bottom: 20px;
        }

        .tab {
            padding: 10px 20px;
            cursor: pointer;
            font-weight: bold;
        }

        .tab.active {
            border-bottom: 3px solid #007bff;
            color: #007bff;
        }

        .tab-content {
            display: none;
        }

        .tab-content.active {
            display: block;
        }

        /* Forms and Buttons */
        .form-row {
            display: flex;
            gap: 10px;
            margin-bottom: 10px;
        }

        input, select, button {
            padding: 8px;
            border-radius: 5px;
            border: 1px solid #ccc;
        }

        button {
            background-color: #007bff;
            color: white;
            cursor: pointer;
            border: none;
        }

        button:hover {
            background-color: #0056b3;
        }

        .results, .game-history {
            margin-top: 20px;
        }

        .team-container {
            display: flex;
            justify-content: space-around;
        }

        .team {
            width: 45%;
        }

        .team h3 {
            text-align: center;
        }

        .export-import {
            display: flex;
            gap: 10px;
            margin-top: 10px;
        }

        textarea {
            width: 100%;
            height: 200px;
        }

        hr {
            margin: 20px 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Team Splitter App</h1>

        <!-- Tabs -->
        <div class="tab-container">
            <div class="tab active" onclick="switchTab(this, 'team-splitter')">Team Splitter</div>
            <div class="tab" onclick="switchTab(this, 'game-tracker')">Game Tracker</div>
            <div class="tab" onclick="switchTab(this, 'player-stats')">Player Statistics</div>
            <div class="tab" onclick="switchTab(this, 'game-history')">Game History</div>
            <div class="tab" onclick="switchTab(this, 'data-management')">Data Management</div>
        </div>

        <!-- TEAM SPLITTER -->
        <div id="team-splitter" class="tab-content active">
            <h2>Team Splitter</h2>

            <div id="playerForm">
                <div class="form-row">
                    <input type="text" placeholder="Player Name">
                    <select>
                        <option value="">Position</option>
                        <option value="Forward">Forward</option>
                        <option value="Midfielder">Midfielder</option>
                        <option value="Defender">Defender</option>
                        <option value="Goalkeeper">Goalkeeper</option>
                    </select>
                    <input type="number" min="1" max="10" placeholder="Skill (1-10)">
                </div>
            </div>

            <button onclick="addPlayerField()">➕ Add Player</button>
            <button onclick="addSampleTeam()">🧩 Add Sample Team</button>
            <button onclick="loadSavedPlayers()">📂 Load Saved Players</button>
            <button onclick="balanceTeams()">⚖️ Balance Teams</button>
            <button onclick="randomizeTeams()">🎲 Random Teams</button>
            <button onclick="saveCurrentPlayers()">💾 Save Players</button>

            <div class="results">
                <h3>Team Results</h3>
                <div class="team-container">
                    <div class="team" id="teamA"><h3>Team A</h3></div>
                    <div class="team" id="teamB"><h3>Team B</h3></div>
                </div>
                <div id="teamStats"></div>
            </div>
        </div>

        <!-- GAME TRACKER -->
        <div id="game-tracker" class="tab-content">
            <h2>Game Tracker</h2>
            <form id="gameForm">
                <label>Team A Score:</label>
                <input type="number" id="scoreA" min="0">
                <label>Team B Score:</label>
                <input type="number" id="scoreB" min="0">
                <button type="button" onclick="saveGameResult()">Save Game Result</button>
            </form>
        </div>

        <!-- PLAYER STATS -->
        <div id="player-stats" class="tab-content">
            <h2>Player Statistics</h2>
            <div id="playerStatsContainer"></div>
        </div>

        <!-- GAME HISTORY -->
        <div id="game-history" class="tab-content">
            <h2>Game History</h2>
            <div id="gameHistoryContainer"></div>
        </div>

        <!-- DATA MANAGEMENT -->
        <div id="data-management" class="tab-content">
            <h2>Data Management</h2>
            <div class="export-import">
                <button onclick="exportData()">📤 Export Data</button>
                <button onclick="importData()">📥 Import Data</button>
                <button onclick="clearAllData()">🧹 Clear All Data</button>
            </div>
            <textarea id="dataArea" placeholder="Exported/Imported Data"></textarea>
        </div>
    </div>

    <script>
        /* ✅ Fixed Tab Switching Function */
        function switchTab(tabElement, tabName) {
            document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
            document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));

            document.getElementById(tabName).classList.add('active');
            tabElement.classList.add('active');
        }

        /* 🧩 Placeholder JavaScript Functions — these need backend linkage */
        function addPlayerField() {
            const playerForm = document.getElementById('playerForm');
            const row = document.createElement('div');
            row.className = 'form-row';
            row.innerHTML = `
                <input type="text" placeholder="Player Name">
                <select>
                    <option value="">Position</option>
                    <option value="Forward">Forward</option>
                    <option value="Midfielder">Midfielder</option>
                    <option value="Defender">Defender</option>
                    <option value="Goalkeeper">Goalkeeper</option>
                </select>
                <input type="number" min="1" max="10" placeholder="Skill (1-10)">
            `;
            playerForm.appendChild(row);
        }

        function balanceTeams() {
            alert("⚖️ Balancing Teams... (function placeholder)");
        }

        function randomizeTeams() {
            alert("🎲 Randomizing Teams... (function placeholder)");
        }

        function saveCurrentPlayers() {
            alert("💾 Saving Players... (function placeholder)");
        }

        function addSampleTeam() {
            alert("🧩 Adding Sample Team... (function placeholder)");
        }

        function loadSavedPlayers() {
            alert("📂 Loading Saved Players... (function placeholder)");
        }

        function saveGameResult() {
            alert("🏁 Game result saved! (function placeholder)");
        }

        function exportData() {
            alert("📤 Exporting Data... (function placeholder)");
        }

        function importData() {
            alert("📥 Importing Data... (function placeholder)");
        }

        function clearAllData() {
            alert("🧹 Clearing Data... (function placeholder)");
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
