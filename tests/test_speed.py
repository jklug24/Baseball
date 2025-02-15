import pytest
import pandas as pd
import time
import os
from pybaseball import statcast
from datetime import datetime, timedelta
from team import Team
from db_manager import DatabaseManager
from simulation_info import SimulationInfo
from game_engine import GameSimulator

@pytest.mark.skipif(
    not os.environ.get('RUN_SPEED_TEST'),
    reason="Speed test is slow and requires fetching MLB data. Set RUN_SPEED_TEST=1 to run it."
)
class TestSpeed:
    @classmethod
    def setup_class(cls):
        """Set up test data by fetching real statcast data"""
        # Get data from a real game date
        cls.game_date = "2023-04-15"  # A regular season game date
        start_date = (datetime.strptime(cls.game_date, "%Y-%m-%d") - timedelta(days=14)).strftime("%Y-%m-%d")
        end_date = cls.game_date
        
        # Fetch real statcast data
        cls.statcast_data = statcast(start_dt=start_date, end_dt=end_date)
        
        # Clear the database before speed test
        db = DatabaseManager()
        db.clear_all_tables()
    
    def test_game_simulation_speed(self):
        """Test the speed of running the same game multiple times with caching"""
        # Find a game date with data
        game_data = self.statcast_data[self.statcast_data.game_date == self.game_date]
        if len(game_data) == 0:
            # If no data for target date, use the most recent date in our data
            self.game_date = self.statcast_data.game_date.iloc[-1]
            game_data = self.statcast_data[self.statcast_data.game_date == self.game_date]
        
        # Get the first available matchup
        home_team = game_data.home_team.iloc[0]
        away_team = game_data.away_team.iloc[0]
        
        # Get rosters for both teams
        home_roster = list(game_data[game_data.home_team == home_team].batter.unique())[:9]
        away_roster = list(game_data[game_data.away_team == away_team].batter.unique())[:9]
        
        # Get pitchers for both teams
        home_pitcher = int(game_data[game_data.home_team == home_team].pitcher.iloc[0])
        away_pitcher = int(game_data[game_data.away_team == away_team].pitcher.iloc[0])
        
        times = []
        scores = []
        
        print(f"\nRunning speed test with 4 iterations:")
        print(f"Game: {away_team} @ {home_team} on {self.game_date}")
        for i in range(4):
            start_time = time.time()
            
            # Create simulation info
            sim_info = SimulationInfo(
                home_team=home_team,
                away_team=away_team,
                date=self.game_date,
                home_roster=home_roster,
                away_roster=away_roster,
                home_pitcher_id=home_pitcher,
                away_pitcher_id=away_pitcher,
                stats=self.statcast_data,
                backtest=False,
                logLevel=0
            )
            
            # Run game simulation
            game = GameSimulator(sim_info)
            game.run()
            
            end_time = time.time()
            elapsed = end_time - start_time
            times.append(elapsed)
            scores.append((game.simulationInfo.home_team.score, game.simulationInfo.away_team.score))
            
            print(f"Iteration {i+1}:")
            print(f"  Time: {elapsed:.2f} seconds")
            print(f"  Score: {home_team} {game.simulationInfo.home_team.score} - {game.simulationInfo.away_team.score} {away_team}")
        
        print("\nSpeed Test Summary:")
        print(f"First run (cold cache): {times[0]:.2f} seconds")
        print(f"Average of subsequent runs: {sum(times[1:]) / len(times[1:]):.2f} seconds")
        improvement = ((times[0] - (sum(times[1:]) / len(times[1:]))) / times[0] * 100)
        print(f"Speed improvement: {improvement:.1f}%")
        
        # Assert that caching provides significant speed improvement
        assert improvement > 50, f"Expected at least 50% speed improvement with caching, but got {improvement:.1f}%"
