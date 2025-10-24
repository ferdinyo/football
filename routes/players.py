# routes/players.py
from flask import Blueprint, request, jsonify

# Create a Blueprint for player-related routes
players_bp = Blueprint('players', __name__)

@players_bp.route('/load-data', methods=['GET'])
def load_data_route():
    try:
        # For now, just import and use the existing function from app.py
        from app import load_data
        data = load_data()
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
