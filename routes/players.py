@players_bp.route('/save-players', methods=['POST'])
def save_players():
    try:
        data = request.get_json()
        players_data = data['players']
        
        # Import the existing functions from app.py
        from app import load_data, save_data
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
