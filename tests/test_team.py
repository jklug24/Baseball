import unittest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

# Add parent directory to path to import modules
sys.path.append(str(Path(__file__).parent.parent))

from team import Team
from pitcher import Pitcher
from batter import Batter

class TestTeam(unittest.TestCase):
    def setUp(self):
        """Set up test data and initialize team"""
        # Create sample statcast data with all required columns
        self.sample_data = pd.DataFrame({
            'pitcher': [123456, 123456, 789012] * 50,
            'batter': [111111, 222222, 333333] * 50,
            'pitch_type': ['FF'] * 50 + ['SL'] * 50 + ['CH'] * 50,
            'balls': [0, 1, 2, 3] * 37 + [0, 1],
            'strikes': [0, 1, 2] * 50,
            'events': ['field_out'] * 60 + ['single'] * 40 + ['double'] * 30 + ['home_run'] * 20,
            'description': ['ball'] * 50 + ['called_strike'] * 50 + ['hit_into_play'] * 50,
            'game_date': ['2024-04-01'] * 150,  # Add game dates
            'home_team': ['Test Team'] * 75 + ['Away Team'] * 75,  # Add team names
            'away_team': ['Away Team'] * 75 + ['Test Team'] * 75,
            'inning_topbot': ['Bot'] * 75 + ['Top'] * 75,  # Add inning half
            'at_bat_number': list(range(1, 151))  # Add at-bat numbers
        })
        
        # Create roster for testing
        self.test_roster = [111111, 222222, 333333]
        
        # Initialize team with required parameters
        self.team = Team(
            name='Test Team',
            date='2024-04-02',  # Future date relative to sample data
            statcast=self.sample_data,
            backtest=False,
            pitcher_id=123456,  # Specify a starting pitcher
            roster=self.test_roster  # Provide roster to avoid prediction
        )

    def test_roster_initialization(self):
        """Test roster initialization"""
        # Check if roster was initialized correctly
        self.assertEqual(len(self.team.roster), len(self.test_roster))
        
        # Check if roster contains Batter objects
        for batter in self.team.roster:
            self.assertIsInstance(batter, Batter)
        
        # Check if pitcher was initialized correctly
        self.assertIsInstance(self.team.pitcher(), Pitcher)
        self.assertEqual(self.team.pitcher().id, 123456)

    def test_roster_prediction(self):
        """Test roster prediction"""
        # Create team without providing roster
        predicted_team = Team(
            name='Test Team',
            date='2024-04-02',
            statcast=self.sample_data,
            backtest=False,
            pitcher_id=123456
        )
        
        # Check if roster was predicted
        self.assertTrue(len(predicted_team.roster) > 0)
        for batter in predicted_team.roster:
            self.assertIsInstance(batter, Batter)

    def test_batter_selection(self):
        """Test batter selection and rotation"""
        # Test initial batter selection
        initial_batter = self.team.batter()
        self.assertIsInstance(initial_batter, Batter)
        self.assertEqual(initial_batter.id, self.test_roster[0])
        
        # Test batter rotation
        self.team.next_idx()
        next_batter = self.team.batter()
        self.assertEqual(next_batter.id, self.test_roster[1])
        
        # Test rotation back to start
        for _ in range(len(self.test_roster) - 1):
            self.team.next_idx()
        self.assertEqual(self.team.batter().id, self.test_roster[0])

    def test_pitcher_selection(self):
        """Test pitcher selection"""
        # Test getting pitcher
        pitcher = self.team.pitcher()
        self.assertIsInstance(pitcher, Pitcher)
        self.assertEqual(pitcher.id, 123456)

    def test_stats_tracking(self):
        """Test team statistics tracking"""
        # Test recording stats for a player
        player_id = self.test_roster[0]
        
        # Record some stats
        self.team.recordStat(player_id, 'hits')
        self.team.recordStat(player_id, 'hits')
        self.team.recordStat(player_id, 'at_bats')
        
        # Check stats were recorded correctly
        self.assertEqual(self.team.stats[player_id]['hits'], 2)
        self.assertEqual(self.team.stats[player_id]['at_bats'], 1)

    def test_score_tracking(self):
        """Test team score tracking"""
        # Test initial score
        self.assertEqual(self.team.score, 0)
        
        # Test incrementing score
        self.team.increment_score(1)
        self.assertEqual(self.team.score, 1)
        
        self.team.increment_score(2)
        self.assertEqual(self.team.score, 3)

    def test_get_lineup(self):
        """Test getting team lineup"""
        # Get lineup string
        lineup = self.team.get_lineup()
        
        # Check that it's a non-empty string
        self.assertIsInstance(lineup, str)
        self.assertTrue(len(lineup) > 0)
        
        # Check that it contains multiple lines
        self.assertTrue(len(lineup.split('\n')) > 1)

    def test_empty_team_handling(self):
        """Test handling of empty team"""
        empty_data = pd.DataFrame(columns=self.sample_data.columns)
        empty_roster = []
        
        # Test creating team with empty roster
        with self.assertRaises(ValueError):
            Team(
                name='Empty Team',
                date='2024-04-02',
                statcast=empty_data,
                backtest=False,
                pitcher_id=999999,
                roster=empty_roster
            )

if __name__ == '__main__':
    unittest.main()
