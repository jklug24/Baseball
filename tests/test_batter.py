import unittest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

# Add parent directory to path to import modules
sys.path.append(str(Path(__file__).parent.parent))

from batter import Batter
from db_manager import DatabaseManager

class TestBatter(unittest.TestCase):
    def setUp(self):
        # Create sample statcast data
        self.sample_data = pd.DataFrame({
            'batter': [123456] * 100,
            'pitch_type': ['FF'] * 50 + ['SL'] * 30 + ['CH'] * 20,
            'balls': [0, 1, 2, 3] * 25,
            'strikes': [0, 1, 2] * 33 + [0],
            'events': ['field_out'] * 40 + ['single'] * 30 + ['double'] * 20 + ['home_run'] * 10,
            'description': ['ball'] * 35 + ['called_strike'] * 17 + ['swinging_strike'] * 10 + 
                         ['foul'] * 13 + ['hit_into_play'] * 25
        })
        
        # Clear any existing data for this batter
        self._db = DatabaseManager()
        self._db.clear_batter_probs_basic()
        
        self.batter = Batter(123456, self.sample_data)

    def tearDown(self):
        # Clean up database after test
        self._db.clear_batter_probs_basic()

    def test_init_in_play_stats(self):
        """Test if in-play statistics are calculated correctly"""
        # Check if probabilities sum to 1
        self.assertAlmostEqual(sum(self.batter.in_play_probs.values()), 1.0, places=5)
        
        # Check if outcomes match expected
        expected_outcomes = ['field_out', 'single', 'double', 'triple', 'home_run']
        self.assertEqual(set(self.batter.in_play_probs.keys()), set(expected_outcomes))
        
        # Check probability distribution based on our sample data
        # With our sample data:
        # 40 field outs, 30 singles, 20 doubles, 0 triples, 10 home runs
        total_hits = 100
        self.assertAlmostEqual(self.batter.in_play_probs['field_out'], 40/total_hits, places=2)
        self.assertAlmostEqual(self.batter.in_play_probs['single'], 30/total_hits, places=2)
        self.assertAlmostEqual(self.batter.in_play_probs['double'], 20/total_hits, places=2)
        self.assertAlmostEqual(self.batter.in_play_probs['triple'], 0/total_hits, places=2)
        self.assertAlmostEqual(self.batter.in_play_probs['home_run'], 10/total_hits, places=2)

    def test_global_outcome_probs(self):
        """Test if global outcome probabilities are calculated correctly"""
        # Check if probabilities sum to 1
        self.assertAlmostEqual(sum(self.batter.global_outcome_probs.values()), 1.0, places=5)
        
        # Check individual probabilities
        expected_probs = {
            'ball': 0.35,
            'called_strike': 0.17,
            'swinging_strike': 0.10,
            'foul': 0.13,
            'hit_into_play': 0.25
        }
        
        for outcome, expected_prob in expected_probs.items():
            self.assertAlmostEqual(
                self.batter.global_outcome_probs[outcome], 
                expected_prob, 
                places=2,
                msg=f"Probability for {outcome} doesn't match"
            )

    def test_basic_probs(self):
        """Test if basic outcome probabilities per pitch type are calculated correctly"""
        # Check if we have probabilities for each pitch type
        expected_pitch_types = set(['FF', 'SL', 'CH'])
        self.assertEqual(set(self.batter.basic_probs.keys()), expected_pitch_types)
        
        # Check if probabilities for each pitch type sum to 1
        for pitch_type in self.batter.basic_probs:
            probs = self.batter.basic_probs[pitch_type]
            self.assertAlmostEqual(sum(probs.values()), 1.0, places=5)

    def test_count_based_outcome_probs(self):
        """Test if count-based outcome probabilities are calculated correctly"""
        # Check if we have probabilities for each pitch type
        expected_pitch_types = set(['FF', 'SL', 'CH'])
        self.assertEqual(set(self.batter.count_based_outcome_probs.keys()), expected_pitch_types)
        
        # Check each count's probabilities
        for pitch_type in self.batter.count_based_outcome_probs:
            for count in self.batter.count_based_outcome_probs[pitch_type]:
                probs = self.batter.count_based_outcome_probs[pitch_type][count]
                self.assertAlmostEqual(sum(probs.values()), 1.0, places=5)

    def test_simulate_hit(self):
        """Test hit simulation"""
        # Set random seed for reproducibility
        np.random.seed(42)
        
        # Simulate multiple hits
        hits = [self.batter.simulate_hit() for _ in range(100)]
        
        # Check if all outcomes are valid
        valid_outcomes = set(['field_out', 'single', 'double', 'triple', 'home_run'])
        for hit in hits:
            self.assertIn(hit, valid_outcomes)
        
        # Check rough distribution (allowing for some randomness)
        outcome_counts = pd.Series(hits).value_counts(normalize=True)
        
        # Get frequencies, defaulting to 0 for missing outcomes
        field_out_freq = outcome_counts.get('field_out', 0.0)
        single_freq = outcome_counts.get('single', 0.0)
        double_freq = outcome_counts.get('double', 0.0)
        triple_freq = outcome_counts.get('triple', 0.0)
        homer_freq = outcome_counts.get('home_run', 0.0)
        
        # Check each outcome matches expected frequency
        self.assertAlmostEqual(field_out_freq, 0.4, places=1)
        self.assertAlmostEqual(single_freq, 0.3, places=1)
        self.assertAlmostEqual(double_freq, 0.2, places=1)
        self.assertAlmostEqual(triple_freq, 0.0, places=1)
        self.assertAlmostEqual(homer_freq, 0.1, places=1)

    def test_get_pitch_result(self):
        """Test pitch result prediction"""
        # Test with specific count
        result = self.batter.get_pitch_result('FF', 0, 0)
        self.assertIn(result, ['ball', 'called_strike', 'swinging_strike', 'foul', 'hit_into_play'])
        
        # Test without count
        result = self.batter.get_pitch_result('FF')
        self.assertIn(result, ['ball', 'called_strike', 'swinging_strike', 'foul', 'hit_into_play'])
        
        # Test with invalid pitch type (should fall back to global probs)
        result = self.batter.get_pitch_result('XX')
        self.assertIn(result, ['ball', 'called_strike', 'swinging_strike', 'foul', 'hit_into_play'])

    def test_empty_data_handling(self):
        """Test handling of empty data"""
        empty_data = pd.DataFrame(columns=self.sample_data.columns)
        batter = Batter(999999, empty_data)
        
        # Test hit simulation with empty data
        hit = batter.simulate_hit()
        self.assertIn(hit, ['field_out', 'single', 'double', 'triple', 'home_run'])
        
        # Test pitch result with empty data
        result = batter.get_pitch_result('FF')
        self.assertIn(result, ['ball', 'called_strike', 'swinging_strike', 'foul', 'hit_into_play'])

if __name__ == '__main__':
    unittest.main()
