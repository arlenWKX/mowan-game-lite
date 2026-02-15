import sqlite3
import bcrypt
from datetime import datetime
from config import Config

class Database:
    def __init__(self):
        self.db_path = Config.DATABASE
        self.init_db()
    
    def get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_db(self):
        conn = self.get_conn()
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                nickname TEXT NOT NULL,
                is_admin INTEGER DEFAULT 0,
                is_banned INTEGER DEFAULT 0,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                total_games INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Rooms table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rooms (
                id TEXT PRIMARY KEY,
                creator_id INTEGER NOT NULL,
                max_players INTEGER DEFAULT 2,
                status TEXT DEFAULT 'waiting',
                current_round INTEGER DEFAULT 0,
                current_turn INTEGER DEFAULT 0,
                turn_order TEXT,
                public_area TEXT DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (creator_id) REFERENCES users(id)
            )
        ''')
        
        # Room players table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS room_players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_id TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                player_order INTEGER DEFAULT -1,
                board TEXT DEFAULT '{}',
                eliminated TEXT DEFAULT '[]',
                is_ready INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (room_id) REFERENCES rooms(id),
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(room_id, user_id)
            )
        ''')
        
        # Game actions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS game_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_id TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                action_type TEXT NOT NULL,
                action_data TEXT,
                round_num INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (room_id) REFERENCES rooms(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        # Create default admin account
        cursor.execute('SELECT id FROM users WHERE username = ?', ('admin',))
        if not cursor.fetchone():
            hashed = bcrypt.hashpw('admin123'.encode(), bcrypt.gensalt())
            cursor.execute('''
                INSERT INTO users (username, password, nickname, is_admin)
                VALUES (?, ?, ?, 1)
            ''', ('admin', hashed.decode(), '管理员'))
        
        conn.commit()
        conn.close()
    
    # User methods
    def create_user(self, username, password, nickname):
        conn = self.get_conn()
        cursor = conn.cursor()
        try:
            hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
            cursor.execute('''
                INSERT INTO users (username, password, nickname)
                VALUES (?, ?, ?)
            ''', (username, hashed.decode(), nickname))
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None
        finally:
            conn.close()
    
    def verify_user(self, username, password):
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        conn.close()
        if user and bcrypt.checkpw(password.encode(), user['password'].encode()):
            return dict(user)
        return None
    
    def get_user_by_id(self, user_id):
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        user = cursor.fetchone()
        conn.close()
        return dict(user) if user else None
    
    def get_all_users(self):
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, nickname, is_admin, is_banned, wins, losses, total_games, created_at FROM users ORDER BY created_at DESC')
        users = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return users
    
    def update_user_ban(self, user_id, is_banned):
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET is_banned = ? WHERE id = ?', (is_banned, user_id))
        conn.commit()
        conn.close()
        return True
    
    def delete_user(self, user_id):
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM users WHERE id = ? AND is_admin = 0', (user_id,))
        conn.commit()
        conn.close()
        return True
    
    def update_user_stats(self, user_id, wins=0, losses=0):
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users 
            SET wins = wins + ?, losses = losses + ?, total_games = total_games + ?
            WHERE id = ?
        ''', (wins, losses, wins + losses, user_id))
        conn.commit()
        conn.close()
    
    # Room methods
    def create_room(self, room_id, creator_id, max_players=2):
        conn = self.get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO rooms (id, creator_id, max_players, status)
                VALUES (?, ?, ?, 'waiting')
            ''', (room_id, creator_id, max_players))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()
    
    def get_room(self, room_id):
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM rooms WHERE id = ?', (room_id,))
        room = cursor.fetchone()
        conn.close()
        return dict(room) if room else None
    
    def get_room_players(self, room_id):
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT rp.*, u.username, u.nickname 
            FROM room_players rp
            JOIN users u ON rp.user_id = u.id
            WHERE rp.room_id = ? AND rp.is_active = 1
            ORDER BY rp.player_order
        ''', (room_id,))
        players = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return players
    
    def join_room(self, room_id, user_id):
        conn = self.get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO room_players (room_id, user_id)
                VALUES (?, ?)
            ''', (room_id, user_id))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            conn.close()
            return False
        finally:
            conn.close()
    
    def leave_room(self, room_id, user_id):
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE room_players SET is_active = 0 
            WHERE room_id = ? AND user_id = ?
        ''', (room_id, user_id))
        conn.commit()
        conn.close()
    
    def kick_player(self, room_id, user_id):
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE room_players SET is_active = 0 
            WHERE room_id = ? AND user_id = ?
        ''', (room_id, user_id))
        conn.commit()
        conn.close()
    
    def update_room_status(self, room_id, status):
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute('UPDATE rooms SET status = ? WHERE id = ?', (status, room_id))
        conn.commit()
        conn.close()
    
    def update_player_order(self, room_id, user_id, order):
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE room_players SET player_order = ? 
            WHERE room_id = ? AND user_id = ?
        ''', (order, room_id, user_id))
        conn.commit()
        conn.close()
    
    def update_player_board(self, room_id, user_id, board, eliminated):
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE room_players SET board = ?, eliminated = ? 
            WHERE room_id = ? AND user_id = ?
        ''', (board, eliminated, room_id, user_id))
        conn.commit()
        conn.close()
    
    def update_room_game_state(self, room_id, turn_order, current_round, current_turn, public_area):
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE rooms 
            SET turn_order = ?, current_round = ?, current_turn = ?, public_area = ?
            WHERE id = ?
        ''', (turn_order, current_round, current_turn, public_area, room_id))
        conn.commit()
        conn.close()
    
    def record_action(self, room_id, user_id, action_type, action_data, round_num):
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO game_actions (room_id, user_id, action_type, action_data, round_num)
            VALUES (?, ?, ?, ?, ?)
        ''', (room_id, user_id, action_type, action_data, round_num))
        conn.commit()
        conn.close()
    
    def get_leaderboard(self, limit=20):
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT username, nickname, wins, losses, total_games,
                   CASE WHEN total_games > 0 THEN ROUND(wins * 100.0 / total_games, 1) ELSE 0 END as win_rate
            FROM users
            WHERE total_games > 0
            ORDER BY win_rate DESC, wins DESC
            LIMIT ?
        ''', (limit,))
        users = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return users

db = Database()