from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from datetime import datetime
import json
import random

from config import Config
from database import db
from game_logic import GameLogic

app = Flask(__name__)
app.config.from_object(Config)
CORS(app)
jwt = JWTManager(app)

# In-memory game state cache (for active games)
active_rooms = {}

# ============ Auth Routes ============

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')
    nickname = data.get('nickname', '').strip()
    
    if not username or not password or not nickname:
        return jsonify({'error': 'Username, password and nickname are required'}), 400
    
    if len(username) < 3 or len(password) < 6:
        return jsonify({'error': 'Username must be at least 3 chars, password at least 6 chars'}), 400
    
    user_id = db.create_user(username, password, nickname)
    if not user_id:
        return jsonify({'error': 'Username already exists'}), 409
    
    return jsonify({'message': 'User created successfully', 'user_id': user_id}), 201

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username', '')
    password = data.get('password', '')
    
    user = db.verify_user(username, password)
    if not user:
        return jsonify({'error': 'Invalid credentials'}), 401
    
    if user.get('is_banned'):
        return jsonify({'error': 'Account has been banned'}), 403
    
    access_token = create_access_token(identity=user['id'])
    return jsonify({
        'access_token': access_token,
        'user': {
            'id': user['id'],
            'username': user['username'],
            'nickname': user['nickname'],
            'is_admin': user.get('is_admin', 0) == 1
        }
    }), 200

@app.route('/api/auth/me', methods=['GET'])
@jwt_required()
def get_current_user():
    user_id = get_jwt_identity()
    user = db.get_user_by_id(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({
        'id': user['id'],
        'username': user['username'],
        'nickname': user['nickname'],
        'is_admin': user.get('is_admin', 0) == 1
    }), 200

# ============ Admin Routes ============

@app.route('/api/admin/users', methods=['GET'])
@jwt_required()
def get_all_users():
    user_id = get_jwt_identity()
    user = db.get_user_by_id(user_id)
    if not user or user.get('is_admin', 0) != 1:
        return jsonify({'error': 'Admin access required'}), 403
    
    users = db.get_all_users()
    return jsonify(users), 200

@app.route('/api/admin/users/<int:target_id>/ban', methods=['POST'])
@jwt_required()
def ban_user(target_id):
    user_id = get_jwt_identity()
    user = db.get_user_by_id(user_id)
    if not user or user.get('is_admin', 0) != 1:
        return jsonify({'error': 'Admin access required'}), 403
    
    db.update_user_ban(target_id, 1)
    return jsonify({'message': 'User banned'}), 200

@app.route('/api/admin/users/<int:target_id>/unban', methods=['POST'])
@jwt_required()
def unban_user(target_id):
    user_id = get_jwt_identity()
    user = db.get_user_by_id(user_id)
    if not user or user.get('is_admin', 0) != 1:
        return jsonify({'error': 'Admin access required'}), 403
    
    db.update_user_ban(target_id, 0)
    return jsonify({'message': 'User unbanned'}), 200

@app.route('/api/admin/users/<int:target_id>', methods=['DELETE'])
@jwt_required()
def delete_user(target_id):
    user_id = get_jwt_identity()
    user = db.get_user_by_id(user_id)
    if not user or user.get('is_admin', 0) != 1:
        return jsonify({'error': 'Admin access required'}), 403
    
    db.delete_user(target_id)
    return jsonify({'message': 'User deleted'}), 200

# ============ Room Routes ============

@app.route('/api/rooms', methods=['POST'])
@jwt_required()
def create_room():
    user_id = get_jwt_identity()
    data = request.get_json()
    max_players = data.get('max_players', 2)
    
    if max_players < 2 or max_players > 5:
        return jsonify({'error': 'Player count must be 2-5'}), 400
    
    # Generate unique room ID
    for _ in range(100):
        room_id = GameLogic.generate_room_id()
        existing = db.get_room(room_id)
        if not existing:
            break
    else:
        return jsonify({'error': 'Failed to generate room ID'}), 500
    
    success = db.create_room(room_id, user_id, max_players)
    if not success:
        return jsonify({'error': 'Failed to create room'}), 500
    
    # Creator joins room
    db.join_room(room_id, user_id)
    
    return jsonify({
        'room_id': room_id,
        'message': 'Room created successfully'
    }), 201

@app.route('/api/rooms/<room_id>', methods=['GET'])
def get_room_info(room_id):
    room = db.get_room(room_id)
    if not room:
        return jsonify({'error': 'Room not found'}), 404
    
    players = db.get_room_players(room_id)
    return jsonify({
        'room': {
            'id': room['id'],
            'creator_id': room['creator_id'],
            'max_players': room['max_players'],
            'status': room['status'],
            'current_round': room['current_round'],
            'current_turn': room['current_turn']
        },
        'players': players
    }), 200

@app.route('/api/rooms/<room_id>/join', methods=['POST'])
@jwt_required()
def join_room(room_id):
    user_id = get_jwt_identity()
    room = db.get_room(room_id)
    
    if not room:
        return jsonify({'error': 'Room not found'}), 404
    
    if room['status'] != 'waiting':
        return jsonify({'error': 'Game already started'}), 400
    
    players = db.get_room_players(room_id)
    if len(players) >= room['max_players']:
        return jsonify({'error': 'Room is full'}), 400
    
    # Check if already in room
    for p in players:
        if p['user_id'] == user_id:
            return jsonify({'message': 'Already in room'}), 200
    
    success = db.join_room(room_id, user_id)
    if not success:
        return jsonify({'error': 'Failed to join room'}), 500
    
    return jsonify({'message': 'Joined room successfully'}), 200

@app.route('/api/rooms/<room_id>/leave', methods=['POST'])
@jwt_required()
def leave_room(room_id):
    user_id = get_jwt_identity()
    db.leave_room(room_id, user_id)
    return jsonify({'message': 'Left room'}), 200

@app.route('/api/rooms/<room_id>/kick/<int:target_id>', methods=['POST'])
@jwt_required()
def kick_player(room_id, target_id):
    user_id = get_jwt_identity()
    room = db.get_room(room_id)
    
    if not room:
        return jsonify({'error': 'Room not found'}), 404
    
    if room['creator_id'] != user_id:
        return jsonify({'error': 'Only creator can kick players'}), 403
    
    db.kick_player(room_id, target_id)
    return jsonify({'message': 'Player kicked'}), 200

# ============ Game Routes ============

@app.route('/api/rooms/<room_id>/ready', methods=['POST'])
@jwt_required()
def player_ready(room_id):
    user_id = get_jwt_identity()
    data = request.get_json()
    board = data.get('board', {})
    
    if not GameLogic.is_valid_board(board):
        return jsonify({'error': 'Board must have exactly 10 numbers placed'}), 400
    
    # Store board
    eliminated = json.dumps([])
    db.update_player_board(room_id, user_id, json.dumps(board), eliminated)
    
    return jsonify({'message': 'Board deployed'}), 200

@app.route('/api/rooms/<room_id>/start', methods=['POST'])
@jwt_required()
def start_game(room_id):
    user_id = get_jwt_identity()
    room = db.get_room(room_id)
    
    if not room:
        return jsonify({'error': 'Room not found'}), 404
    
    if room['creator_id'] != user_id:
        return jsonify({'error': 'Only creator can start game'}), 403
    
    players = db.get_room_players(room_id)
    if len(players) < 2:
        return jsonify({'error': 'Need at least 2 players'}), 400
    
    # Random turn order
    turn_order = [p['user_id'] for p in players]
    random.shuffle(turn_order)
    
    # Assign player orders
    for idx, pid in enumerate(turn_order):
        db.update_player_order(room_id, pid, idx)
    
    # Update room status
    db.update_room_status(room_id, 'playing')
    db.update_room_game_state(room_id, json.dumps(turn_order), 1, 0, '[]')
    
    # Initialize game state cache
    active_rooms[room_id] = {
        'turn_order': turn_order,
        'current_round': 1,
        'current_turn': 0,
        'public_area': [],
        'extra_action_player': None,
        'phase': 'action'  # action, settlement, finished
    }
    
    return jsonify({
        'message': 'Game started',
        'turn_order': turn_order
    }), 200

@app.route('/api/rooms/<room_id>/state', methods=['GET'])
@jwt_required()
def get_game_state(room_id):
    user_id = get_jwt_identity()
    room = db.get_room(room_id)
    
    if not room:
        return jsonify({'error': 'Room not found'}), 404
    
    players = db.get_room_players(room_id)
    turn_order = json.loads(room['turn_order'] or '[]')
    public_area = json.loads(room['public_area'] or '[]')
    
    # Build player boards (hide numbers from other players)
    player_boards = {}
    for p in players:
        board = json.loads(p['board'] or '{}')
        eliminated = json.loads(p['eliminated'] or '[]')
        
        if p['user_id'] == user_id:
            # Show own board fully
            player_boards[p['user_id']] = {
                'board': board,
                'eliminated': eliminated,
                'nickname': p['nickname']
            }
        else:
            # Show only occupied status
            summary = {}
            for cell_id, num in board.items():
                summary[cell_id] = 'occupied' if num is not None else None
            player_boards[p['user_id']] = {
                'board': summary,
                'eliminated': eliminated,
                'nickname': p['nickname']
            }
    
    return jsonify({
        'room_status': room['status'],
        'current_round': room['current_round'],
        'current_turn': room['current_turn'],
        'turn_order': turn_order,
        'public_area': public_area,
        'player_boards': player_boards,
        'your_turn': turn_order[room['current_turn']] == user_id if turn_order and room['status'] == 'playing' else False
    }), 200

@app.route('/api/rooms/<room_id>/action', methods=['POST'])
@jwt_required()
def game_action(room_id):
    user_id = get_jwt_identity()
    room = db.get_room(room_id)
    
    if not room or room['status'] != 'playing':
        return jsonify({'error': 'Game not in progress'}), 400
    
    turn_order = json.loads(room['turn_order'] or '[]')
    current_turn_idx = room['current_turn']
    
    if turn_order[current_turn_idx] != user_id:
        return jsonify({'error': 'Not your turn'}), 403
    
    data = request.get_json()
    action_type = data.get('action_type')
    action_data = data.get('action_data', {})
    
    players = db.get_room_players(room_id)
    current_player = next((p for p in players if p['user_id'] == user_id), None)
    
    if not current_player:
        return jsonify({'error': 'Player not found'}), 404
    
    board = json.loads(current_player['board'] or '{}')
    public_area = json.loads(room['public_area'] or '[]')
    
    if action_type == 'forward':
        cell_id = action_data.get('cell_id')
        can_move, result = GameLogic.can_move_forward(board, cell_id)
        
        if not can_move:
            return jsonify({'error': result}), 400
        
        # Move piece
        number = board[cell_id]
        board[cell_id] = None
        
        if result == 'public':
            public_area.append({'number': number, 'player_id': user_id})
        else:
            board[result] = number
        
        # Save state
        db.update_player_board(room_id, user_id, json.dumps(board), current_player['eliminated'])
        db.update_room_game_state(room_id, room['turn_order'], room['current_round'], 
                                   room['current_turn'], json.dumps(public_area))
        
        # Record action
        db.record_action(room_id, user_id, 'forward', json.dumps(action_data), room['current_round'])
        
    elif action_type == 'challenge':
        # 单挑 - requires extra action
        target_id = action_data.get('target_id')
        target_cell = action_data.get('target_cell')
        
        # Find target player
        target_player = next((p for p in players if p['user_id'] == target_id), None)
        if not target_player:
            return jsonify({'error': 'Target player not found'}), 404
        
        target_board = json.loads(target_player['board'] or '{}')
        if target_cell not in target_board or target_board[target_cell] is None:
            return jsonify({'error': 'Invalid target cell'}), 400
        
        # Move target piece to public area
        number = target_board[target_cell]
        target_board[target_cell] = None
        public_area.append({'number': number, 'player_id': target_id})
        
        # Trigger settlement
        public_area, eliminated, extra = GameLogic.resolve_public_area(public_area, turn_order)
        
        # Update eliminated
        for e in eliminated:
            e_player = next((p for p in players if p['user_id'] == e['player_id']), None)
            if e_player:
                e_eliminated = json.loads(e_player['eliminated'] or '[]')
                e_eliminated.append(e['number'])
                db.update_player_board(room_id, e['player_id'], e_player['board'], json.dumps(e_eliminated))
        
        # Save boards
        db.update_player_board(room_id, target_id, json.dumps(target_board), target_player['eliminated'])
        db.update_room_game_state(room_id, room['turn_order'], room['current_round'],
                                   room['current_turn'], json.dumps(public_area))
        
        db.record_action(room_id, user_id, 'challenge', json.dumps(action_data), room['current_round'])
        
    elif action_type == 'recycle':
        # 回收 - requires extra action
        if len(public_area) == 0:
            return jsonify({'error': 'Public area is empty'}), 400
        
        # Find player's piece in public area
        player_pieces = [(i, p) for i, p in enumerate(public_area) if p['player_id'] == user_id]
        if not player_pieces:
            return jsonify({'error': 'No piece in public area'}), 400
        
        piece_idx = action_data.get('piece_index', 0)
        if piece_idx >= len(player_pieces):
            return jsonify({'error': 'Invalid piece index'}), 400
        
        idx, piece = player_pieces[piece_idx]
        target_cell = action_data.get('target_cell')
        
        if target_cell not in board or board[target_cell] is not None:
            return jsonify({'error': 'Invalid target cell'}), 400
        
        # Remove from public area and place on board
        public_area.pop(idx)
        board[target_cell] = piece['number']
        
        db.update_player_board(room_id, user_id, json.dumps(board), current_player['eliminated'])
        db.update_room_game_state(room_id, room['turn_order'], room['current_round'],
                                   room['current_turn'], json.dumps(public_area))
        
        db.record_action(room_id, user_id, 'recycle', json.dumps(action_data), room['current_round'])
        
    elif action_type == 'pass':
        db.record_action(room_id, user_id, 'pass', '{}', room['current_round'])
    
    else:
        return jsonify({'error': 'Invalid action type'}), 400
    
    # Move to next turn
    next_turn = (current_turn_idx + 1) % len(turn_order)
    next_round = room['current_round']
    
    # If round complete, trigger settlement
    if next_turn == 0:
        next_round += 1
        # Settlement phase
        public_area, eliminated, extra_player = GameLogic.resolve_public_area(public_area, turn_order)
        
        # Update eliminated
        for e in eliminated:
            e_player = next((p for p in players if p['user_id'] == e['player_id']), None)
            if e_player:
                e_eliminated = json.loads(e_player['eliminated'] or '[]')
                e_eliminated.append(e['number'])
                db.update_player_board(room_id, e['player_id'], e_player['board'], json.dumps(e_eliminated))
        
        # Return remaining public area pieces to owners
        for piece in public_area:
            owner = next((p for p in players if p['user_id'] == piece['player_id']), None)
            if owner:
                owner_board = json.loads(owner['board'] or '{}')
                # Find empty cell in back row (row 3)
                for col in GameLogic.COL_NAMES:
                    cell_id = f"3{col}"
                    if owner_board.get(cell_id) is None:
                        owner_board[cell_id] = piece['number']
                        break
                db.update_player_board(room_id, piece['player_id'], json.dumps(owner_board), owner['eliminated'])
        
        public_area = []
        
        # Check for winner
        players_data = {}
        updated_players = db.get_room_players(room_id)
        for p in updated_players:
            players_data[p['user_id']] = {
                'board': json.loads(p['board'] or '{}'),
                'eliminated': json.loads(p['eliminated'] or '[]')
            }
        
        winner = GameLogic.check_winner(players_data)
        if winner:
            db.update_room_status(room_id, 'finished')
            # Update stats
            for p in updated_players:
                if p['user_id'] == winner:
                    db.update_user_stats(p['user_id'], wins=1)
                else:
                    db.update_user_stats(p['user_id'], losses=1)
            
            return jsonify({
                'message': 'Game finished',
                'winner': winner
            }), 200
    
    db.update_room_game_state(room_id, room['turn_order'], next_round, next_turn, json.dumps(public_area))
    
    return jsonify({
        'message': 'Action processed',
        'next_turn': next_turn,
        'next_round': next_round
    }), 200

# ============ Leaderboard Routes ============

@app.route('/api/leaderboard', methods=['GET'])
def get_leaderboard():
    limit = request.args.get('limit', 20, type=int)
    users = db.get_leaderboard(limit)
    return jsonify(users), 200

# ============ Health Check ============

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)