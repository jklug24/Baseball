import sqlite3
import json
import numpy as np
from pathlib import Path

class DatabaseManager:
    def __init__(self, db_path="baseball_stats.db"):
        """Initialize database connection and create tables if they don't exist.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create batter_probs_basic table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS batter_probs_basic (
                    batter_id INTEGER PRIMARY KEY,
                    probs_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create batter_probs_global table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS batter_probs_global (
                    batter_id INTEGER PRIMARY KEY,
                    probs_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create batter_probs_count_based table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS batter_probs_count_based (
                    batter_id INTEGER PRIMARY KEY,
                    probs_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create batter_probs_in_play table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS batter_probs_in_play (
                    batter_id INTEGER PRIMARY KEY,
                    probs_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create pitcher tables
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pitcher_basic_probs (
                    pitcher_id INTEGER PRIMARY KEY,
                    probs_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pitcher_count_based_probs (
                    pitcher_id INTEGER PRIMARY KEY,
                    probs_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pitcher_in_play_probs (
                    pitcher_id INTEGER PRIMARY KEY,
                    probs_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create player_names table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS player_names (
                    player_id INTEGER PRIMARY KEY,
                    first_name TEXT NOT NULL,
                    last_name TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
    
    def get_batter_probs_basic(self, batter_id):
        """Get basic probabilities for a batter.
        
        Args:
            batter_id: MLB ID of the batter
            
        Returns:
            dict: Dictionary of basic probabilities or None if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT probs_json FROM batter_probs_basic WHERE batter_id = ?",
                (batter_id,)
            )
            
            result = cursor.fetchone()
            if result:
                return json.loads(result[0])
            return None
    
    def set_batter_probs_basic(self, batter_id, probs_dict):
        """Store basic probabilities for a batter.
        
        Args:
            batter_id: MLB ID of the batter
            probs_dict: Dictionary of probabilities
        """
        # Convert numpy values to Python native types for JSON serialization
        cleaned_probs = {}
        for k, v in probs_dict.items():
            if isinstance(v, np.floating):
                cleaned_probs[k] = float(v)
            elif isinstance(v, np.integer):
                cleaned_probs[k] = int(v)
            else:
                cleaned_probs[k] = v
        
        # Convert batter_id to regular int if it's numpy integer
        if isinstance(batter_id, np.integer):
            batter_id = int(batter_id)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO batter_probs_basic (batter_id, probs_json)
                VALUES (?, ?)
            """, (batter_id, json.dumps(cleaned_probs)))
            
            conn.commit()
    
    def get_batter_probs_global(self, batter_id):
        """Get global probabilities for a batter.
        
        Args:
            batter_id: MLB ID of the batter
            
        Returns:
            dict: Dictionary of global probabilities or None if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT probs_json FROM batter_probs_global WHERE batter_id = ?",
                (batter_id,)
            )
            
            result = cursor.fetchone()
            if result:
                return json.loads(result[0])
            return None
            
    def set_batter_probs_global(self, batter_id, probs):
        """Set global probabilities for a batter.
        
        Args:
            batter_id: MLB ID of the batter
            probs: Dictionary of probabilities to store
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute(
                """
                INSERT OR REPLACE INTO batter_probs_global (batter_id, probs_json)
                VALUES (?, ?)
                """,
                (batter_id, json.dumps(probs))
            )
            
            conn.commit()
            
    def get_batter_probs_count_based(self, batter_id):
        """Get count-based probabilities for a batter.
        
        Args:
            batter_id: MLB ID of the batter
            
        Returns:
            dict: Dictionary of count-based probabilities or None if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT probs_json FROM batter_probs_count_based WHERE batter_id = ?",
                (batter_id,)
            )
            
            result = cursor.fetchone()
            if result:
                return json.loads(result[0])
            return None
            
    def set_batter_probs_count_based(self, batter_id, probs):
        """Set count-based probabilities for a batter.
        
        Args:
            batter_id: MLB ID of the batter
            probs: Dictionary of probabilities to store
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute(
                """
                INSERT OR REPLACE INTO batter_probs_count_based (batter_id, probs_json)
                VALUES (?, ?)
                """,
                (batter_id, json.dumps(probs))
            )
            
            conn.commit()
            
    def get_batter_probs_in_play(self, batter_id):
        """Get in-play probabilities for a batter.
        
        Args:
            batter_id: MLB ID of the batter
            
        Returns:
            dict: Dictionary of in-play probabilities or None if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT probs_json FROM batter_probs_in_play WHERE batter_id = ?",
                (batter_id,)
            )
            
            result = cursor.fetchone()
            if result:
                return json.loads(result[0])
            return None
            
    def set_batter_probs_in_play(self, batter_id, probs):
        """Set in-play probabilities for a batter.
        
        Args:
            batter_id: MLB ID of the batter
            probs: Dictionary of probabilities to store
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute(
                """
                INSERT OR REPLACE INTO batter_probs_in_play (batter_id, probs_json)
                VALUES (?, ?)
                """,
                (batter_id, json.dumps(probs))
            )
            
            conn.commit()
            
    def get_player_name(self, player_id):
        """Get player name from database.
        
        Args:
            player_id: MLB ID of the player
            
        Returns:
            Tuple of (first_name, last_name) if found, None if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT first_name, last_name FROM player_names
                WHERE player_id = ?
                """,
                (player_id,)
            )
            result = cursor.fetchone()
            return result if result else None
    
    def set_player_name(self, player_id, first_name, last_name):
        """Set player name in database.
        
        Args:
            player_id: MLB ID of the player
            first_name: Player's first name
            last_name: Player's last name
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO player_names (player_id, first_name, last_name)
                VALUES (?, ?, ?)
                """,
                (player_id, first_name, last_name)
            )
            
            conn.commit()
            
    def clear_batter_probs_basic(self):
        """Clear all entries from the batter_probs_basic table."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM batter_probs_basic")
            conn.commit()

    def clear_all_batter_probs_basic(self):
        """Clear all entries from the batter_probs_basic table."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM batter_probs_basic")
            conn.commit()

    def clear_all_tables(self):
        """Clear all tables in the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM batter_probs_basic")
            cursor.execute("DELETE FROM batter_probs_global")
            cursor.execute("DELETE FROM batter_probs_count_based")
            cursor.execute("DELETE FROM batter_probs_in_play")
            cursor.execute("DELETE FROM player_names")
            cursor.execute("DELETE FROM pitcher_basic_probs")
            cursor.execute("DELETE FROM pitcher_count_based_probs")
            cursor.execute("DELETE FROM pitcher_in_play_probs")
            
        # Then VACUUM outside the transaction
        with sqlite3.connect(self.db_path) as conn:
            conn.isolation_level = None
            cursor = conn.cursor()
            cursor.execute("VACUUM")

    def get_pitcher_basic_probs(self, pitcher_id):
        """Get basic probabilities for a pitcher."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT probs_json FROM pitcher_basic_probs WHERE pitcher_id = ?",
                (pitcher_id,)
            )
            result = cursor.fetchone()
            return json.loads(result[0]) if result else None

    def set_pitcher_basic_probs(self, pitcher_id, probs):
        """Store basic probabilities for a pitcher."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO pitcher_basic_probs (pitcher_id, probs_json) VALUES (?, ?)",
                (pitcher_id, json.dumps(probs))
            )
            conn.commit()

    def get_pitcher_count_based_probs(self, pitcher_id):
        """Get count-based probabilities for a pitcher."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT probs_json FROM pitcher_count_based_probs WHERE pitcher_id = ?",
                (pitcher_id,)
            )
            result = cursor.fetchone()
            if result:
                # Convert string tuple keys back to actual tuples
                probs = json.loads(result[0])
                return {eval(k): v for k, v in probs.items()}
            return None

    def set_pitcher_count_based_probs(self, pitcher_id, probs):
        """Store count-based probabilities for a pitcher."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Convert tuple keys to strings for JSON serialization
            probs_json = {str(k): v for k, v in probs.items()}
            cursor.execute(
                "INSERT OR REPLACE INTO pitcher_count_based_probs (pitcher_id, probs_json) VALUES (?, ?)",
                (pitcher_id, json.dumps(probs_json))
            )
            conn.commit()

    def get_pitcher_in_play_probs(self, pitcher_id):
        """Get in-play probabilities for a pitcher."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT probs_json FROM pitcher_in_play_probs WHERE pitcher_id = ?",
                (pitcher_id,)
            )
            result = cursor.fetchone()
            return json.loads(result[0]) if result else None

    def set_pitcher_in_play_probs(self, pitcher_id, probs):
        """Store in-play probabilities for a pitcher."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO pitcher_in_play_probs (pitcher_id, probs_json) VALUES (?, ?)",
                (pitcher_id, json.dumps(probs))
            )
            conn.commit()
