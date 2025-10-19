from flask import Flask, request, jsonify
import random
import math
import traceback

app = Flask(__name__)

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
        'defender': 1.2,
        'midfielder': 1.5,
        'forward': 1.3
    }
    
    @staticmethod
    def calculate_team_strength(players):
        if not players:
            return 0
            
        strength = 0
        position_count = {'goalkeeper': 0, 'defender': 0, 'midfielder': 0, 'forward': 0}
        
        for player in players:
            strength += player.skill_level * TeamBalancer.POSITION_WEIGHTS.get(player.position, 1.0)
            position_count[player.position] += 1
        
        # Bonus for having a goalkeeper
        if position_count['goalkeeper'] > 0:
            strength += 2
        
        # Balance bonus for having multiple positions
        position_variety = len([count for count in position_count.values() if count > 0])
        strength += position_variety * 0.5
        
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
            
            # Try different split points for better balance
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
    <title>Advanced Football Team Splitter</title>
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
            max-width: 1400px;
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
        
        .app-container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin-bottom: 30px;
        }
        
        @media (max-width: 1024px) {
            .app-container {
                grid-template-columns: 1fr;
            }
        }
        
        .input-section, .teams-section {
            background: rgba(255, 255, 255, 0.1);
            padding: 25px;
            border-radius: 15px;
            backdrop-filter: blur(10px);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
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
        
        input, select {
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
        .position-mid { background: rgba(156, 39, 176, 0.3); }
        .position-fwd { background: rgba(255, 193, 7, 0.3); }
        
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
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>⚽ Advanced Team Splitter</h1>
            <p>Create balanced football teams based on player positions and skill levels</p>
        </header>
        
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
                    <!-- Player inputs will be added here -->
                </div>
                
                <div class="buttons">
                    <button onclick="addPlayerField()">➕ Add Player</button>
                    <button class="secondary-btn" onclick="addSampleTeam()">🎯 Add Sample Team</button>
                </div>
                
                <div class="buttons">
                    <button onclick="balanceTeams()" style="background:linear-gradient(45deg,#FF9800,#F57C00)">
                        ⚖️ Balance Teams
                    </button>
                    <button class="secondary-btn" onclick="randomizeTeams()">
                        🎲 Random Teams
                    </button>
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
        
        <div class="instructions">
            <h3>How It Works</h3>
            <ul>
                <li><strong>Positions Matter:</strong> Goalkeepers are weighted highest, followed by midfielders, defenders, and forwards</li>
                <li><strong>Skill Levels:</strong> Rate players from 1 (beginner) to 10 (expert) for more accurate balancing</li>
                <li><strong>Balanced Algorithm:</strong> The system considers both positions and skills to create fair teams</li>
                <li><strong>Position Distribution:</strong> Tries to ensure each team has a good mix of positions</li>
            </ul>
        </div>
    </div>

    <script>
        let playerCount = 0;
        
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
                    <option value="midfielder" ${position === 'midfielder' ? 'selected' : ''}>Midfielder</option>
                    <option value="forward" ${position === 'forward' ? 'selected' : ''}>Forward</option>
                </select>
                <input type="number" class="player-skill skill-input" min="1" max="10" value="${skill}">
                <button type="button" class="remove-btn" onclick="this.parentElement.remove()">✕</button>
            `;
            form.appendChild(div);
        }
        
        function addSampleTeam() {
            // Clear existing players
            document.getElementById('playerForm').querySelectorAll('.form-row:not(:first-child)').forEach(row => row.remove());
            playerCount = 0;
            
            const samplePlayers = [
                ['Alex', 'goalkeeper', 8],
                ['Ben', 'defender', 7],
                ['Chris', 'defender', 6],
                ['David', 'defender', 5],
                ['Eric', 'midfielder', 8],
                ['Frank', 'midfielder', 7],
                ['George', 'midfielder', 6],
                ['Henry', 'midfielder', 5],
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
                    displayTeams(data.team_a, data.team_b, data.strength_a, data.strength_b);
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
                    displayTeams(data.team_a, data.team_b, data.strength_a, data.strength_b);
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
            
            // Update team strengths with null checks
            if (teamAStrengthElement) {
                teamAStrengthElement.textContent = `Strength: ${strengthA.toFixed(1)}`;
            }
            if (teamBStrengthElement) {
                teamBStrengthElement.textContent = `Strength: ${strengthB.toFixed(1)}`;
            }
            
            // Calculate balance
            const balanceDiff = Math.abs(strengthA - strengthB);
            const isBalanced = balanceDiff < 3;
            
            if (balanceIndicator) {
                balanceIndicator.innerHTML = isBalanced ? 
                    `✅ Teams are well balanced! (Difference: ${balanceDiff.toFixed(1)})` :
                    `⚠️ Teams are somewhat unbalanced (Difference: ${balanceDiff.toFixed(1)})`;
                balanceIndicator.className = `balance-indicator ${isBalanced ? 'balanced' : 'unbalanced'}`;
            }
            
            // Display players
            if (teamAElement) {
                teamAElement.innerHTML = teamA.map(player => `
                    <li class="player-item">
                        <div class="player-info">
                            <div class="player-name">${player.name}</div>
                            <div class="player-details">
                                <span class="position-badge position-${player.position.substring(0, 3)}">${player.position}</span>
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
                                <span class="position-badge position-${player.position.substring(0, 3)}">${player.position}</span>
                                • Skill: ${player.skill_level}/10
                            </div>
                        </div>
                    </li>
                `).join('');
            }
        }
        
        // Initialize with some player fields
        window.onload = function() {
            addPlayerField();
            addPlayerField();
        }
    </script>
</body>
</html>
    '''

@app.route('/balance-teams', methods=['POST'])
def balance_teams():
    try:
        print("=== BALANCE TEAMS ENDPOINT CALLED ===")
        
        if not request.is_json:
            return jsonify({'error': 'Request must be JSON'}), 400
            
        data = request.get_json()
        print(f"Received data: {data}")
        
        if not data or 'players' not in data:
            print("No player data received")
            return jsonify({'error': 'No player data received'}), 400
            
        players_data = data['players']
        print(f"Processing {len(players_data)} players")
        
        if len(players_data) < 2:
            return jsonify({'error': 'Need at least 2 players'}), 400
        
        players = []
        for i, player_data in enumerate(players_data):
            print(f"Player {i}: {player_data}")
            # Validate required fields
            if 'name' not in player_data or 'position' not in player_data or 'skill_level' not in player_data:
                return jsonify({'error': f'Missing fields in player data: {player_data}'}), 400
                
            player = Player(
                name=str(player_data['name']),
                position=str(player_data['position']),
                skill_level=int(player_data['skill_level'])
            )
            players.append(player)
        
        print(f"Created {len(players)} player objects")
        team_a, team_b = TeamBalancer.balance_teams(players)
        print(f"Balanced into teams: {len(team_a)} vs {len(team_b)}")
        
        # Convert players to dictionaries for JSON serialization
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
        
        print(f"Returning response successfully")
        return jsonify(response)
        
    except Exception as e:
        error_msg = f"Error in balance_teams: {str(e)}"
        print(error_msg)
        print(traceback.format_exc())
        return jsonify({'error': error_msg}), 500

@app.route('/random-teams', methods=['POST'])
def random_teams():
    try:
        print("=== RANDOM TEAMS ENDPOINT CALLED ===")
        
        if not request.is_json:
            return jsonify({'error': 'Request must be JSON'}), 400
            
        data = request.get_json()
        print(f"Received data: {data}")
        
        if not data or 'players' not in data:
            print("No player data received")
            return jsonify({'error': 'No player data received'}), 400
            
        players_data = data['players']
        print(f"Processing {len(players_data)} players")
        
        if len(players_data) < 2:
            return jsonify({'error': 'Need at least 2 players'}), 400
        
        players = []
        for i, player_data in enumerate(players_data):
            print(f"Player {i}: {player_data}")
            # Validate required fields
            if 'name' not in player_data or 'position' not in player_data or 'skill_level' not in player_data:
                return jsonify({'error': f'Missing fields in player data: {player_data}'}), 400
                
            player = Player(
                name=str(player_data['name']),
                position=str(player_data['position']),
                skill_level=int(player_data['skill_level'])
            )
            players.append(player)
        
        print(f"Created {len(players)} player objects")
        # Simple random shuffle
        random.shuffle(players)
        split_point = len(players) // 2
        team_a = players[:split_point]
        team_b = players[split_point:]
        print(f"Randomized into teams: {len(team_a)} vs {len(team_b)}")
        
        # Convert players to dictionaries for JSON serialization
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
        
        print(f"Returning response successfully")
        return jsonify(response)
        
    except Exception as e:
        error_msg = f"Error in random_teams: {str(e)}"
        print(error_msg)
        print(traceback.format_exc())
        return jsonify({'error': error_msg}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
