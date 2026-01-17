# database.py - Database Management
import sqlite3
from datetime import datetime, timezone
from typing import Optional, List, Tuple

class Database:
    def __init__(self, db_name="kronoz_cafe.db"):
        self.db_name = db_name
        self.init_database()
    
    def get_connection(self):
        return sqlite3.connect(self.db_name)
    
    def init_database(self):
        """Initialize all database tables"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                discord_id INTEGER PRIMARY KEY,
                roblox_id INTEGER UNIQUE,
                roblox_username TEXT,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                current_rank TEXT,
                linked_at TIMESTAMP
            )
        ''')
        
        # Punishments table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS punishments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                reason TEXT NOT NULL,
                moderator_id INTEGER NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                active BOOLEAN DEFAULT 1,
                expires_at TIMESTAMP,
                removed_by INTEGER,
                removed_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(discord_id)
            )
        ''')
        
        # Rank history
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rank_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                old_rank TEXT,
                new_rank TEXT NOT NULL,
                changed_by INTEGER NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reason TEXT,
                FOREIGN KEY (user_id) REFERENCES users(discord_id)
            )
        ''')
        
        # Staff notes
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS staff_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                note TEXT NOT NULL,
                added_by INTEGER NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(discord_id)
            )
        ''')
        
        # LOA requests
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS loa_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                start_date TIMESTAMP NOT NULL,
                end_date TIMESTAMP NOT NULL,
                reason TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                reviewed_by INTEGER,
                reviewed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(discord_id)
            )
        ''')
        
        # Tickets
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_number INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                subject TEXT,
                status TEXT DEFAULT 'open',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                closed_at TIMESTAMP,
                closed_by INTEGER,
                handled_by INTEGER,
                FOREIGN KEY (user_id) REFERENCES users(discord_id)
            )
        ''')
        
        # Staff activity
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS staff_activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                staff_id INTEGER NOT NULL,
                action_type TEXT NOT NULL,
                target_user_id INTEGER,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (staff_id) REFERENCES users(discord_id)
            )
        ''')
        
        # Appeals
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS appeals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                punishment_id INTEGER NOT NULL,
                appeal_text TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                reviewed_by INTEGER,
                reviewed_at TIMESTAMP,
                decision TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(discord_id),
                FOREIGN KEY (punishment_id) REFERENCES punishments(id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    # ===== USER MANAGEMENT =====
    def get_user(self, discord_id: int) -> Optional[Tuple]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE discord_id = ?", (discord_id,))
        result = cursor.fetchone()
        conn.close()
        return result
    
    def create_or_update_user(self, discord_id: int, roblox_id: int = None, 
                             roblox_username: str = None) -> None:
        conn = self.get_connection()
        cursor = conn.cursor()
        
        existing = self.get_user(discord_id)
        if existing:
            if roblox_id and roblox_username:
                cursor.execute('''
                    UPDATE users SET roblox_id = ?, roblox_username = ?, linked_at = ?
                    WHERE discord_id = ?
                ''', (roblox_id, roblox_username, datetime.now(timezone.utc), discord_id))
        else:
            cursor.execute('''
                INSERT INTO users (discord_id, roblox_id, roblox_username, joined_at, linked_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (discord_id, roblox_id, roblox_username, 
                  datetime.now(timezone.utc), 
                  datetime.now(timezone.utc) if roblox_id else None))
        
        conn.commit()
        conn.close()
    
    def get_user_by_roblox_id(self, roblox_id: int) -> Optional[Tuple]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE roblox_id = ?", (roblox_id,))
        result = cursor.fetchone()
        conn.close()
        return result
    
    # ===== PUNISHMENT MANAGEMENT =====
    def add_punishment(self, user_id: int, punishment_type: str, reason: str, 
                      moderator_id: int, expires_at: datetime = None) -> int:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO punishments (user_id, type, reason, moderator_id, timestamp, expires_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, punishment_type, reason, moderator_id, 
              datetime.now(timezone.utc), expires_at))
        punishment_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return punishment_id
    
    def get_active_punishments(self, user_id: int, 
                              punishment_type: str = None) -> List[Tuple]:
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if punishment_type:
            cursor.execute('''
                SELECT * FROM punishments 
                WHERE user_id = ? AND type = ? AND active = 1
                ORDER BY timestamp DESC
            ''', (user_id, punishment_type))
        else:
            cursor.execute('''
                SELECT * FROM punishments 
                WHERE user_id = ? AND active = 1
                ORDER BY timestamp DESC
            ''', (user_id,))
        
        results = cursor.fetchall()
        conn.close()
        return results
    
    def get_all_punishments(self, user_id: int) -> List[Tuple]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM punishments 
            WHERE user_id = ?
            ORDER BY timestamp DESC
        ''', (user_id,))
        results = cursor.fetchall()
        conn.close()
        return results
    
    def remove_punishment(self, punishment_id: int, removed_by: int) -> None:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE punishments 
            SET active = 0, removed_by = ?, removed_at = ?
            WHERE id = ?
        ''', (removed_by, datetime.now(timezone.utc), punishment_id))
        conn.commit()
        conn.close()
    
    def get_punishment_count(self, user_id: int, punishment_type: str) -> int:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT COUNT(*) FROM punishments 
            WHERE user_id = ? AND type = ? AND active = 1
        ''', (user_id, punishment_type))
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def get_punishment_by_id(self, punishment_id: int) -> Optional[Tuple]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM punishments WHERE id = ?", (punishment_id,))
        result = cursor.fetchone()
        conn.close()
        return result
    
    # ===== STAFF NOTES =====
    def add_note(self, user_id: int, note: str, added_by: int) -> None:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO staff_notes (user_id, note, added_by, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (user_id, note, added_by, datetime.now(timezone.utc)))
        conn.commit()
        conn.close()
    
    def get_notes(self, user_id: int) -> List[Tuple]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM staff_notes WHERE user_id = ? ORDER BY timestamp DESC
        ''', (user_id,))
        results = cursor.fetchall()
        conn.close()
        return results
    
    # ===== LOA MANAGEMENT =====
    def create_loa(self, user_id: int, start_date: datetime, 
                   end_date: datetime, reason: str) -> int:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO loa_requests (user_id, start_date, end_date, reason)
            VALUES (?, ?, ?, ?)
        ''', (user_id, start_date, end_date, reason))
        loa_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return loa_id
    
    def update_loa_status(self, loa_id: int, status: str, 
                         reviewed_by: int, decision: str = None) -> None:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE loa_requests 
            SET status = ?, reviewed_by = ?, reviewed_at = ?
            WHERE id = ?
        ''', (status, reviewed_by, datetime.now(timezone.utc), loa_id))
        conn.commit()
        conn.close()
    
    def get_pending_loas(self) -> List[Tuple]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM loa_requests 
            WHERE status = 'pending'
            ORDER BY created_at ASC
        ''')
        results = cursor.fetchall()
        conn.close()
        return results
    
    def get_user_loas(self, user_id: int) -> List[Tuple]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM loa_requests 
            WHERE user_id = ?
            ORDER BY created_at DESC
        ''', (user_id,))
        results = cursor.fetchall()
        conn.close()
        return results
    
    # ===== TICKETS =====
    def create_ticket(self, user_id: int, channel_id: int, 
                     category: str, subject: str = None) -> int:
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get next ticket number
        cursor.execute("SELECT MAX(ticket_number) FROM tickets")
        max_num = cursor.fetchone()[0]
        ticket_number = (max_num or 0) + 1
        
        cursor.execute('''
            INSERT INTO tickets (ticket_number, user_id, channel_id, category, subject)
            VALUES (?, ?, ?, ?, ?)
        ''', (ticket_number, user_id, channel_id, category, subject))
        
        ticket_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return ticket_number
    
    def close_ticket(self, channel_id: int, closed_by: int) -> None:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE tickets 
            SET status = 'closed', closed_at = ?, closed_by = ?
            WHERE channel_id = ? AND status = 'open'
        ''', (datetime.now(timezone.utc), closed_by, channel_id))
        conn.commit()
        conn.close()
    
    def get_ticket_by_channel(self, channel_id: int) -> Optional[Tuple]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tickets WHERE channel_id = ?", (channel_id,))
        result = cursor.fetchone()
        conn.close()
        return result
    
    def get_open_tickets_count(self) -> int:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM tickets WHERE status = 'open'")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    # ===== STAFF ACTIVITY =====
    def log_staff_action(self, staff_id: int, action_type: str, 
                        target_user_id: int = None, details: str = None) -> None:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO staff_activity (staff_id, action_type, target_user_id, details, timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', (staff_id, action_type, target_user_id, details, datetime.now(timezone.utc)))
        conn.commit()
        conn.close()
    
    def get_staff_stats(self, staff_id: int, days: int = 30) -> List[Tuple]:
        conn = self.get_connection()
        cursor = conn.cursor()
        since = datetime.now(timezone.utc).timestamp() - (days * 86400)
        cursor.execute('''
            SELECT action_type, COUNT(*) as count
            FROM staff_activity
            WHERE staff_id = ? AND timestamp >= datetime(?, 'unixepoch')
            GROUP BY action_type
        ''', (staff_id, since))
        results = cursor.fetchall()
        conn.close()
        return results
    
    def get_all_staff_stats(self, days: int = 30) -> List[Tuple]:
        conn = self.get_connection()
        cursor = conn.cursor()
        since = datetime.now(timezone.utc).timestamp() - (days * 86400)
        cursor.execute('''
            SELECT staff_id, action_type, COUNT(*) as count
            FROM staff_activity
            WHERE timestamp >= datetime(?, 'unixepoch')
            GROUP BY staff_id, action_type
            ORDER BY count DESC
        ''', (since,))
        results = cursor.fetchall()
        conn.close()
        return results
    
    # ===== APPEALS =====
    def create_appeal(self, user_id: int, punishment_id: int, appeal_text: str) -> int:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO appeals (user_id, punishment_id, appeal_text)
            VALUES (?, ?, ?)
        ''', (user_id, punishment_id, appeal_text))
        appeal_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return appeal_id
    
    def update_appeal(self, appeal_id: int, status: str, reviewed_by: int, decision: str) -> None:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE appeals 
            SET status = ?, reviewed_by = ?, reviewed_at = ?, decision = ?
            WHERE id = ?
        ''', (status, reviewed_by, datetime.now(timezone.utc), decision, appeal_id))
        conn.commit()
        conn.close()
    
    def get_pending_appeals(self) -> List[Tuple]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM appeals 
            WHERE status = 'pending'
            ORDER BY created_at ASC
        ''')
        results = cursor.fetchall()
        conn.close()
        return results