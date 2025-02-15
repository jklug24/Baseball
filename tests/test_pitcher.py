import unittest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

# Add parent directory to path to import modules
sys.path.append(str(Path(__file__).parent.parent))

from pitcher import Pitcher, LEAGUE_AVG_PITCH_TYPES, LEAGUE_AVG_PITCH_PROBS

class TestPitcher(unittest.TestCase):
    def setUp(self):
        # Create sample statcast data
        self.sample_data = pd.DataFrame({
            'pitcher': [123456] * 100,
            'pitch_type': ['FF'] * 50 + ['SL'] * 30 + ['CH'] * 20,
            'balls': [0, 1, 2, 3] * 25,
            'strikes': [0, 1, 2] * 33 + [0],
            'events': ['field_out'] * 40 + ['single'] * 30 + ['double'] * 20 + ['home_run'] * 10,
            'batter': list(range(100))
        })
        self.pitcher = Pitcher(123456, self.sample_data)

    def test_init_basic_stats(self):
        """Test if basic pitch probabilities are calculated correctly"""
        # Check pitch types and probabilities
        expected_probs = {
            'FF': 0.5,
            'SL': 0.3,
            'CH': 0.2
        }
        
        # Check that all expected pitch types are present with correct probabilities
        for pitch_type, prob in expected_probs.items():
            self.assertIn(pitch_type, self.pitcher.basic_probs)
            self.assertAlmostEqual(self.pitcher.basic_probs[pitch_type], prob, places=5)
        
        # Check total probability sums to 1
        self.assertAlmostEqual(sum(self.pitcher.basic_probs.values()), 1.0, places=5)

    def test_count_based_probabilities(self):
        """Test if count-based probabilities are calculated correctly"""
        # Check if (0,0) count exists
        self.assertIn((0,0), self.pitcher.count_based_probs)
        
        # Check if probabilities for each count sum to 1
        for count_probs in self.pitcher.count_based_probs.values():
            self.assertAlmostEqual(sum(count_probs.values()), 1.0, places=5)

    def test_simulate_pitch_with_count(self):
        """Test pitch simulation with specific count"""
        # Set a random seed for reproducibility
        np.random.seed(42)
        
        # Simulate multiple pitches
        pitches = [self.pitcher.simulate_pitch(0, 0) for _ in range(100)]
        
        # Check if all simulated pitches are valid
        valid_pitches = set(['FF', 'SL', 'CH'])
        for pitch in pitches:
            self.assertIn(pitch, valid_pitches)

    def test_simulate_pitch_without_count(self):
        """Test pitch simulation without count"""
        # Set a random seed for reproducibility
        np.random.seed(42)
        
        # Simulate multiple pitches
        pitches = [self.pitcher.simulate_pitch() for _ in range(100)]
        
        # Check if all simulated pitches are valid
        valid_pitches = set(['FF', 'SL', 'CH'])
        for pitch in pitches:
            self.assertIn(pitch, valid_pitches)

    def test_empty_data_handling(self):
        """Test handling of empty statcast data"""
        empty_data = pd.DataFrame(columns=self.sample_data.columns)
        pitcher = Pitcher(999999, empty_data)
        
        # Should fall back to league average
        pitch = pitcher.simulate_pitch()
        self.assertIn(pitch, LEAGUE_AVG_PITCH_TYPES)

    def test_invalid_count_handling(self):
        """Test handling of invalid count"""
        # Test with invalid count (4,3)
        pitch = self.pitcher.simulate_pitch(4, 3)
        self.assertIn(pitch, self.pitcher.basic_probs.keys())

    def test_in_play_stats(self):
        """Test calculation of in-play statistics"""
        # Check if probabilities sum to 1
        self.assertAlmostEqual(sum(self.pitcher.in_play_probs.values()), 1.0, places=5)
        
        # Check if all necessary outcomes are present
        expected_outcomes = ['field_out', 'single', 'double', 'home_run']
        for outcome in expected_outcomes:
            self.assertIn(outcome, self.pitcher.in_play_probs)

if __name__ == '__main__':
    unittest.main()
