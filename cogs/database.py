# database.py - Enhanced Database with all new tables
import sqlite3
from typing import Any, List, Tuple, Optional

class Database:
    def __init__(self, db_path: str = "kronoz_cafe.db"):
        self.db_path = db_path
        self.connection = sqlite3.connect(db_path)
        self.cursor = self.connection.cursor()
        self.create_tables()
    
    def create_tables(self):
        """Create all necessary tables for the bot"""
        
        # Original tables (keeping your existing structure)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS punishments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                moderator_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                reason TEXT,
                duration INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                active INTEGER DEFAULT 1
            )
        """)
        
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id INTEGER UNIQUE NOT NULL,
                user_id INTEGER NOT NULL,
                category TEXT,
                status TEXT DEFAULT 'open',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                closed_at TIMESTAMP
            )
        """)
        
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS loa_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                reason TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                approved_by INTEGER,
                approved_at TIMESTAMP
            )
        """)
        
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS staff_activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                action_type TEXT NOT NULL,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS roblox_links (
                user_id INTEGER PRIMARY KEY,
                roblox_id INTEGER NOT NULL,
                roblox_username TEXT NOT NULL,
                verified INTEGER DEFAULT 0,
                linked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # NEW TABLES FOR ADDITIONAL FEATURES
        
        # Economy system
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS economy (
                user_id INTEGER PRIMARY KEY,
                balance INTEGER DEFAULT 0,
                last_daily TIMESTAMP,
                last_work TIMESTAMP,
                total_earned INTEGER DEFAULT 0,
                total_spent INTEGER DEFAULT 0
            )
        """)
        
        # Trivia scores
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS trivia_scores (
                user_id INTEGER PRIMARY KEY,
                points INTEGER DEFAULT 0,
                games_played INTEGER DEFAULT 0,
                correct_answers INTEGER DEFAULT 0,
                last_played TIMESTAMP
            )
        """)
        
        # Reminders
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                remind_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Purchases/shop
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                item_name TEXT NOT NULL,
                price INTEGER NOT NULL,
                purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Suggestions
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS suggestions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                suggestion TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reviewed_by INTEGER,
                reviewed_at TIMESTAMP,
                admin_response TEXT
            )
        """)
        
        # AFK users
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS afk_users (
                user_id INTEGER PRIMARY KEY,
                reason TEXT NOT NULL,
                since TIMESTAMP NOT NULL
            )
        """)
        
        # Warning logs (verbal warnings)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS warnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                moderator_id INTEGER NOT NULL,
                reason TEXT,
                is_verbal INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Auto-role configuration
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS auto_roles (
                guild_id INTEGER PRIMARY KEY,
                role_id INTEGER NOT NULL,
                enabled INTEGER DEFAULT 1
            )
        """)
        
        # Staff notes
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS staff_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                staff_id INTEGER NOT NULL,
                note TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Message logs for analytics
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS message_stats (
                user_id INTEGER PRIMARY KEY,
                message_count INTEGER DEFAULT 0,
                last_message TIMESTAMP,
                join_date TIMESTAMP
            )
        """)
        
        # Giveaway participants
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS giveaway_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                entered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(message_id, user_id)
            )
        """)
        
        # Custom commands (bonus feature)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS custom_commands (
                name TEXT PRIMARY KEY,
                response TEXT NOT NULL,
                created_by INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                use_count INTEGER DEFAULT 0
            )
        """)
        
        # Level system (bonus)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS levels (
                user_id INTEGER PRIMARY KEY,
                xp INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1,
                messages INTEGER DEFAULT 0,
                last_xp_gain TIMESTAMP
            )
        """)
        
        # Reaction roles
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS reaction_roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER NOT NULL,
                emoji TEXT NOT NULL,
                role_id INTEGER NOT NULL,
                UNIQUE(message_id, emoji)
            )
        """)
        
        self.connection.commit()
    
    def execute(self, query: str, params: Tuple = ()) -> sqlite3.Cursor:
        """Execute a query and return cursor"""
        try:
            result = self.cursor.execute(query, params)
            self.connection.commit()
            return result
        except Exception as e:
            print(f"Database error: {e}")
            self.connection.rollback()
            raise
    
    def fetchone(self, query: str, params: Tuple = ()) -> Optional[Tuple]:
        """Execute query and fetch one result"""
        return self.execute(query, params).fetchone()
    
    def fetchall(self, query: str, params: Tuple = ()) -> List[Tuple]:
        """Execute query and fetch all results"""
        return self.execute(query, params).fetchall()
    
    def close(self):
        """Close database connection"""
        self.connection.close()
    
    # Utility methods for common operations
    
    def get_user_balance(self, user_id: int) -> int:
        """Get user's economy balance"""
        result = self.fetchone("SELECT balance FROM economy WHERE user_id = ?", (user_id,))
        return result[0] if result else 0
    
    def update_balance(self, user_id: int, amount: int):
        """Update user balance (can be negative to subtract)"""
        self.execute(
            """INSERT INTO economy (user_id, balance) VALUES (?, ?) 
               ON CONFLICT(user_id) DO UPDATE SET balance = balance + ?""",
            (user_id, amount, amount)
        )
    
    def add_trivia_point(self, user_id: int):
        """Add a trivia point to user"""
        self.execute(
            """INSERT INTO trivia_scores (user_id, points, games_played, correct_answers) 
               VALUES (?, 1, 1, 1) 
               ON CONFLICT(user_id) DO UPDATE SET 
               points = points + 1, 
               games_played = games_played + 1,
               correct_answers = correct_answers + 1""",
            (user_id,)
        )
    
    def log_staff_activity(self, user_id: int, action_type: str, details: str = None):
        """Log staff activity"""
        self.execute(
            "INSERT INTO staff_activity (user_id, action_type, details) VALUES (?, ?, ?)",
            (user_id, action_type, details)
        )
    
    def create_ticket(self, channel_id: int, user_id: int, category: str) -> int:
        """Create a new ticket"""
        self.execute(
            "INSERT INTO tickets (channel_id, user_id, category) VALUES (?, ?, ?)",
            (channel_id, user_id, category)
        )
        return self.cursor.lastrowid
    
    def close_ticket(self, channel_id: int):
        """Close a ticket"""
        self.execute(
            "UPDATE tickets SET status = 'closed', closed_at = CURRENT_TIMESTAMP WHERE channel_id = ?",
            (channel_id,)
        )
    
    def add_punishment(self, user_id: int, moderator_id: int, punishment_type: str, 
                      reason: str = None, duration: int = None):
        """Add a punishment record"""
        self.execute(
            """INSERT INTO punishments (user_id, moderator_id, type, reason, duration) 
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, moderator_id, punishment_type, reason, duration)
        )
    
    def get_active_punishments(self, user_id: int) -> List[Tuple]:
        """Get active punishments for a user"""
        return self.fetchall(
            "SELECT * FROM punishments WHERE user_id = ? AND active = 1",
            (user_id,)
        )
    
class Database:
    def __init__(self, path):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()

    def execute(self, query, params=()):
        return self.cursor.execute(query, params)

    def commit(self):
        self.conn.commit()

    def fetchall(self):
        return self.cursor.fetchall()

    def fetchone(self):
        return self.cursor.fetchone()

    def __del__(self):
        """Cleanup on deletion"""
        if hasattr(self, 'connection'):
            self.connection.close()