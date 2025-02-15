import unittest
import pandas as pd
from datetime import datetime, timedelta
from season import SeasonSimulator

class TestSeasonIntegration(unittest.TestCase):
    def setUp(self):
        """Set up test data for a 2-day season simulation"""
        # Create sample statcast data with all required columns
        game_dates = ['2024-04-01'] * 75 + ['2024-04-02'] * 75  # Split games between two days
        
        # Create more realistic player IDs for each team
        team_a_batters = [111111, 111112, 111113, 111114, 111115, 111116, 111117, 111118, 111119]
        team_a_pitchers = [111120, 111121, 111122]
        team_b_batters = [222111, 222112, 222113, 222114, 222115, 222116, 222117, 222118, 222119]
        team_b_pitchers = [222120, 222121, 222122]
        
        # Create sample data with proper player distribution
        rows = []
        for game_date in game_dates:
            # Add pitcher-batter matchups for each game
            for pitcher in team_a_pitchers:
                for batter in team_b_batters:
                    rows.extend([{
                        'game_date': game_date,
                        'pitcher': pitcher,
                        'batter': batter,
                        'home_team': 'Team A',
                        'away_team': 'Team B',
                        'inning_topbot': 'Top',
                        'pitch_type': pt,
                        'balls': b,
                        'strikes': s,
                        'events': e,
                        'description': d,
                        'at_bat_number': len(rows) + 1
                    } for pt, b, s, e, d in zip(
                        ['FF', 'SL', 'CH'] * 3,
                        [0, 1, 2, 3] * 2 + [0, 1],
                        [0, 1, 2] * 3,
                        ['field_out', 'single', 'double', 'home_run'] * 2 + ['field_out'],
                        ['ball', 'called_strike', 'hit_into_play'] * 3
                    )])
            
            # Add matchups with teams reversed
            for pitcher in team_b_pitchers:
                for batter in team_a_batters:
                    rows.extend([{
                        'game_date': game_date,
                        'pitcher': pitcher,
                        'batter': batter,
                        'home_team': 'Team B',
                        'away_team': 'Team A',
                        'inning_topbot': 'Top',
                        'pitch_type': pt,
                        'balls': b,
                        'strikes': s,
                        'events': e,
                        'description': d,
                        'at_bat_number': len(rows) + 1
                    } for pt, b, s, e, d in zip(
                        ['FF', 'SL', 'CH'] * 3,
                        [0, 1, 2, 3] * 2 + [0, 1],
                        [0, 1, 2] * 3,
                        ['field_out', 'single', 'double', 'home_run'] * 2 + ['field_out'],
                        ['ball', 'called_strike', 'hit_into_play'] * 3
                    )])
        
        self.sample_data = pd.DataFrame(rows)
        
        # Set up dates for simulator
        self.training_start = '2024-03-01'
        self.training_end = '2024-03-31'
        self.season_start = '2024-04-01'
        self.season_end = '2024-04-02'

    def test_two_day_season(self):
        """Test running a 2-day season simulation"""
        # Initialize season simulator
        simulator = SeasonSimulator(
            training_start_dt=self.training_start,
            training_end_dt=self.training_end,
            season_start_dt=self.season_start,
            season_end_dt=self.season_end
        )
        
        # Mock the training data since we can't fetch it in tests
        simulator.training_statcast = self.sample_data
        simulator.season_statcast = self.sample_data
        
        # Run simulation
        results = simulator.run()
        
        # Basic validation of results
        self.assertIn('schedule', results)
        self.assertIn('standings', results)
        self.assertIn('total_games', results)
        
        # Check schedule
        schedule = results['schedule']
        self.assertEqual(len(schedule), 2)  # Should have 2 days of results
        
        for date, games in schedule.items():
            # Each day should have at least one game
            self.assertGreater(len(games), 0)
            
            for game in games:
                # Validate game structure
                self.assertIn('home_team', game)
                self.assertIn('away_team', game)
                self.assertIn('home_score', game)
                self.assertIn('away_score', game)
                
                # Teams should exist in our data
                self.assertIn(game['home_team'], ['Team A', 'Team B'])
                self.assertIn(game['away_team'], ['Team A', 'Team B'])
                
                # Scores should be non-negative
                self.assertGreaterEqual(game['home_score'], 0)
                self.assertGreaterEqual(game['away_score'], 0)
                
                # Teams should be different
                self.assertNotEqual(game['home_team'], game['away_team'])
        
        # Check standings
        standings = results['standings']
        self.assertEqual(len(standings), 2)  # Should have 2 teams
        
        for team in standings:
            # Validate team stats
            self.assertIn('team', team)
            self.assertIn('wins', team)
            self.assertIn('losses', team)
            self.assertIn('win_pct', team)
            self.assertIn('runs_for', team)
            self.assertIn('runs_against', team)
            self.assertIn('run_diff', team)

if __name__ == '__main__':
    unittest.main()
