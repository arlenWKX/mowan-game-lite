import random
import json

class GameLogic:
    ROWS = 3
    COLS = 6
    COL_NAMES = ['A', 'B', 'C', 'D', 'E', 'F']
    ALL_NUMBERS = list(range(10))  # 0-9
    
    @staticmethod
    def generate_room_id():
        """Generate 4-char room ID with uppercase, lowercase, digits"""
        chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
        return ''.join(random.choices(chars, k=4))
    
    @staticmethod
    def is_valid_board(board):
        """Check if board has exactly 10 numbers placed"""
        count = sum(1 for cell in board.values() if cell is not None)
        return count == 10
    
    @staticmethod
    def get_cell_position(cell_id):
        """Parse cell ID like '1A' to (row, col)"""
        row = int(cell_id[0]) - 1
        col = GameLogic.COL_NAMES.index(cell_id[1])
        return row, col
    
    @staticmethod
    def get_cell_id(row, col):
        """Get cell ID from row, col"""
        return f"{row + 1}{GameLogic.COL_NAMES[col]}"
    
    @staticmethod
    def get_front_cell(cell_id):
        """Get the cell in front of current cell"""
        row, col = GameLogic.get_cell_position(cell_id)
        if row == 0:  # Already at front row
            return 'public'
        return GameLogic.get_cell_id(row - 1, col)
    
    @staticmethod
    def can_move_forward(board, cell_id):
        """Check if a piece can move forward"""
        if cell_id not in board or board[cell_id] is None:
            return False, "No piece at this position"
        
        front = GameLogic.get_front_cell(cell_id)
        if front == 'public':
            return True, front
        
        if front in board and board[front] is not None:
            return False, "Target cell is occupied"
        
        return True, front
    
    @staticmethod
    def get_available_numbers(board):
        """Get numbers not yet placed on board"""
        placed = set()
        for cell_id, num in board.items():
            if num is not None:
                placed.add(num)
        return [n for n in GameLogic.ALL_NUMBERS if n not in placed]
    
    @staticmethod
    def duel(num1, player1, num2, player2):
        """
        Duel between two numbers
        Returns: (winner_player_id or None for tie, eliminated_player_ids list)
        """
        # Special rules
        if num1 == num2:
            # Same number: both eliminated
            return None, [player1, player2]
        
        if (num1 == 0 and num2 in [6, 9]) or (num2 == 0 and num1 in [6, 9]):
            # 0 vs 6/9: both eliminated
            return None, [player1, player2]
        
        if num1 == 8 and num2 == 0:
            # 8 > 0
            return player1, [player2]
        
        if num2 == 8 and num1 == 0:
            # 8 > 0
            return player2, [player1]
        
        # General rule: reverse order (0 > 1 > 2 > ... > 9)
        if num1 < num2:  # Smaller number wins
            return player1, [player2]
        else:
            return player2, [player1]
    
    @staticmethod
    def resolve_public_area(public_area, turn_order):
        """
        Resolve duels in public area
        public_area: list of {'number': int, 'player_id': int}
        turn_order: list of player_ids in turn order
        Returns: (updated_public_area, eliminated list, extra_action_player or None)
        """
        if len(public_area) == 0:
            return [], [], None
        
        if len(public_area) == 1:
            # Single piece gets extra action
            return [], [], public_area[0]['player_id']
        
        eliminated = []
        current_area = public_area.copy()
        
        while len(current_area) >= 2:
            # Sort by turn order
            order_map = {pid: idx for idx, pid in enumerate(turn_order)}
            current_area.sort(key=lambda x: order_map.get(x['player_id'], 999))
            
            # Take first two
            p1 = current_area[0]
            p2 = current_area[1]
            
            winner, eliminated_ids = GameLogic.duel(
                p1['number'], p1['player_id'],
                p2['number'], p2['player_id']
            )
            
            # Remove dueling pieces
            current_area = current_area[2:]
            
            # Add eliminated players
            for eid in eliminated_ids:
                eliminated.append({
                    'number': p1['number'] if eid == p1['player_id'] else p2['number'],
                    'player_id': eid
                })
            
            # If there's a winner, they stay in public area
            if winner is not None:
                winner_piece = p1 if winner == p1['player_id'] else p2
                current_area.append(winner_piece)
            
            # Check if we can continue dueling
            if len(current_area) < 2:
                break
            
            # Check if any more duels possible (need at least 2 different players)
            players_in_area = set(p['player_id'] for p in current_area)
            if len(players_in_area) < 2:
                break
        
        return current_area, eliminated, None
    
    @staticmethod
    def check_winner(players_data):
        """
        Check if there's a winner
        players_data: dict of player_id -> {'board': {}, 'eliminated': []}
        Returns: winner player_id or None
        """
        active_players = []
        
        for player_id, data in players_data.items():
            # Count remaining pieces on board
            board_count = sum(1 for v in data['board'].values() if v is not None)
            # Count pieces in public area (will be returned)
            # This is handled separately
            
            if board_count > 0:
                active_players.append(player_id)
        
        if len(active_players) == 1:
            return active_players[0]
        return None
    
    @staticmethod
    def create_empty_board():
        """Create empty 3x6 board"""
        board = {}
        for row in range(1, 4):
            for col in GameLogic.COL_NAMES:
                board[f"{row}{col}"] = None
        return board
    
    @staticmethod
    def get_board_summary(board, reveal_all=False):
        """
        Get board summary for display
        If reveal_all is False, only show occupied cells, not numbers
        """
        if reveal_all:
            return board
        
        # Only show which cells are occupied
        summary = {}
        for cell_id, num in board.items():
            summary[cell_id] = 'occupied' if num is not None else None
        return summary