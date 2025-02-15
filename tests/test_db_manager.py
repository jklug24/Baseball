import unittest
import os
import tempfile
from db_manager import DatabaseManager
import numpy as np

class TestDatabaseManager(unittest.TestCase):
    def setUp(self):
        # Create a temporary database file
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_baseball_stats.db")
        self.db = DatabaseManager(self.db_path)
        
    def tearDown(self):
        # Clean up the temporary database
        os.remove(self.db_path)
        os.rmdir(self.temp_dir)
    
    def test_batter_probs_basic_crud(self):
        """Test create, read, update, delete operations for batter_probs_basic."""
        # Test data
        batter_id = 123456
        probs = {
            'ball': 0.35,
            'called_strike': 0.17,
            'swinging_strike': 0.10,
            'foul': 0.13,
            'hit_into_play': 0.25
        }
        
        # Test create
        self.db.set_batter_probs_basic(batter_id, probs)
        
        # Test read
        stored_probs = self.db.get_batter_probs_basic(batter_id)
        self.assertIsNotNone(stored_probs)
        self.assertEqual(stored_probs, probs)
        
        # Test update
        updated_probs = probs.copy()
        updated_probs['ball'] = 0.40
        self.db.set_batter_probs_basic(batter_id, updated_probs)
        stored_probs = self.db.get_batter_probs_basic(batter_id)
        self.assertEqual(stored_probs, updated_probs)
        
        # Test delete (via clear)
        self.db.clear_batter_probs_basic()
        stored_probs = self.db.get_batter_probs_basic(batter_id)
        self.assertIsNone(stored_probs)
    
    def test_numpy_value_handling(self):
        """Test handling of numpy values in probabilities."""
        batter_id = 789012
        probs = {
            'ball': np.float64(0.35),
            'called_strike': np.float32(0.17),
            'swinging_strike': np.int64(0),
            'foul': 0.13,  # regular Python float
            'hit_into_play': 0.25
        }
        
        # Should not raise any JSON serialization errors
        self.db.set_batter_probs_basic(batter_id, probs)
        
        # Should retrieve equivalent values
        stored_probs = self.db.get_batter_probs_basic(batter_id)
        self.assertAlmostEqual(stored_probs['ball'], float(probs['ball']))
        self.assertAlmostEqual(stored_probs['called_strike'], float(probs['called_strike']))
        self.assertEqual(stored_probs['swinging_strike'], int(probs['swinging_strike']))
    
    def test_nonexistent_batter(self):
        """Test getting probabilities for a nonexistent batter."""
        stored_probs = self.db.get_batter_probs_basic(999999)
        self.assertIsNone(stored_probs)

if __name__ == '__main__':
    unittest.main()
