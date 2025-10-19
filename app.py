from flask import Flask, render_template, request, jsonify
import random
import math

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
    # [PASTE THE ENTIRE HTML CODE FROM THE PREVIOUS RESPONSE HERE]
    # This is too long to include twice, but use the complete HTML from our previous code
    return '''<!DOCTYPE html>...'''  # Your full HTML goes here

@app.route('/balance-teams', methods=['POST'])
def balance_teams():
    data = request.json
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
    
    # Convert players to dictionaries for JSON serialization
    team_a_dict = [{'name': p.name, 'position': p.position, 'skill_level': p.skill_level} for p in team_a]
    team_b_dict = [{'name': p.name, 'position': p.position, 'skill_level': p.skill_level} for p in team_b]
    
    strength_a = TeamBalancer.calculate_team_strength(team_a)
    strength_b = TeamBalancer.calculate_team_strength(team_b)
    
    return jsonify({
        'team_a': team_a_dict,
        'team_b': team_b_dict,
        'strength_a': strength_a,
        'strength_b': strength_b
    })

@app.route('/random-teams', methods=['POST'])
def random_teams():
    data = request.json
    players_data = data['players']
    
    players = []
    for player_data in players_data:
        player = Player(
            name=player_data['name'],
            position=player_data['position'],
            skill_level=player_data['skill_level']
        )
        players.append(player)
    
    # Simple random shuffle
    random.shuffle(players)
    split_point = len(players) // 2
    team_a = players[:split_point]
    team_b = players[split_point:]
    
    # Convert players to dictionaries for JSON serialization
    team_a_dict = [{'name': p.name, 'position': p.position, 'skill_level': p.skill_level} for p in team_a]
    team_b_dict = [{'name': p.name, 'position': p.position, 'skill_level': p.skill_level} for p in team_b]
    
    strength_a = TeamBalancer.calculate_team_strength(team_a)
    strength_b = TeamBalancer.calculate_team_strength(team_b)
    
    return jsonify({
        'team_a': team_a_dict,
        'team_b': team_b_dict,
        'strength_a': strength_a,
        'strength_b': strength_b
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
