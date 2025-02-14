from pybaseball import statcast
from datetime import datetime, timedelta
import pandas as pd
from simulation_info import SimulationInfo
from game_engine import GameSimulator
from team import Team  # Import Team class

class SeasonSimulator:
    def __init__(self, training_start_dt: str, training_end_dt: str, 
                 season_start_dt: str, season_end_dt: str):
        """Initialize the season simulator with separate training and season periods.
        
        Args:
            training_start_dt: Start date for training data (format: YYYY-MM-DD)
            training_end_dt: End date for training data (format: YYYY-MM-DD)
            season_start_dt: Start date for season data (format: YYYY-MM-DD)
            season_end_dt: End date for season data (format: YYYY-MM-DD)
        """
        # Fetch training data
        self.training_statcast = statcast(start_dt=training_start_dt, end_dt=training_end_dt)
        
        # Fetch season data
        self.season_statcast = statcast(start_dt=season_start_dt, end_dt=season_end_dt)
        
        # Store date ranges
        self.training_start = datetime.strptime(training_start_dt, "%Y-%m-%d")
        self.training_end = datetime.strptime(training_end_dt, "%Y-%m-%d")
        self.season_start = datetime.strptime(season_start_dt, "%Y-%m-%d")
        self.season_end = datetime.strptime(season_end_dt, "%Y-%m-%d")
        
    def get_daily_matchups(self, date: datetime) -> list:
        """Get unique matchups for a specific date from season data.
        
        Args:
            date: The date to get matchups for
            
        Returns:
            List of tuples containing (home_team, away_team)
        """
        # Filter statcast data for the specific date
        date_str = date.strftime("%Y-%m-%d")
        daily_games = self.season_statcast[self.season_statcast['game_date'] == date_str]
        
        # Extract unique home and away team combinations
        matchups = daily_games[['home_team', 'away_team']].drop_duplicates().values.tolist()
        return matchups
        
    def run(self):
        """Process each day of the season and simulate games.
        
        Returns:
            Dictionary containing season results and statistics
        """
        current_date = self.season_start
        total_games = 0
        schedule = {}
        team_stats = {}  # Track stats for each team
        
        print(f"Processing season from {self.season_start.date()} to {self.season_end.date()}")
        print("-" * 50)
        
        while current_date <= self.season_end:
            date_str = current_date.strftime("%Y-%m-%d")
            matchups = self.get_daily_matchups(current_date)
            
            if matchups:
                print(f"\nGames on {date_str}:")
                daily_results = []
                
                for home_team, away_team in matchups:
                    # Get rosters for both teams from season data
                    try:
                        home_roster, home_pitcher_id = Team.get_roster(self.season_statcast, home_team, date_str)
                        away_roster, away_pitcher_id = Team.get_roster(self.season_statcast, away_team, date_str)
                    except Exception as e:
                        print(f"Warning: Could not get rosters for {away_team} @ {home_team} on {date_str}: {str(e)}")
                        continue

                    # Initialize SimulationInfo for this game with rosters and pitchers
                    try:
                        sim_info = SimulationInfo(
                            home_team=home_team,
                            away_team=away_team,
                            date=date_str,
                            home_roster=home_roster,
                            away_roster=away_roster,
                            home_pitcher_id=home_pitcher_id,
                            away_pitcher_id=away_pitcher_id,
                            stats=self.training_statcast  # Use training data for player probabilities
                        )
                    except ValueError as e:
                        print(f"Warning: Could not initialize simulation for {away_team} @ {home_team} on {date_str}: {str(e)}")
                        continue
                    
                    # Simulate the game
                    try:
                        game = GameSimulator(sim_info)
                        game.run()
                    except Exception as e:
                        print(f"Warning: Game simulation failed for {away_team} @ {home_team} on {date_str}: {str(e)}")
                        continue
                    
                    # Get final score
                    home_score = game.simulationInfo.home_team.score
                    away_score = game.simulationInfo.away_team.score
                    
                    # Update team stats
                    if home_team not in team_stats:
                        team_stats[home_team] = {"wins": 0, "losses": 0, "runs_for": 0, "runs_against": 0}
                    if away_team not in team_stats:
                        team_stats[away_team] = {"wins": 0, "losses": 0, "runs_for": 0, "runs_against": 0}
                    
                    # Update stats based on game result
                    if home_score > away_score:
                        team_stats[home_team]["wins"] += 1
                        team_stats[away_team]["losses"] += 1
                    else:
                        team_stats[away_team]["wins"] += 1
                        team_stats[home_team]["losses"] += 1
                    
                    team_stats[home_team]["runs_for"] += home_score
                    team_stats[home_team]["runs_against"] += away_score
                    team_stats[away_team]["runs_for"] += away_score
                    team_stats[away_team]["runs_against"] += home_score
                    
                    # Store game result
                    result = {
                        "home_team": home_team,
                        "away_team": away_team,
                        "home_score": home_score,
                        "away_score": away_score
                    }
                    daily_results.append(result)
                    
                    # Print game result
                    print(f"  {away_team} {away_score} @ {home_team} {home_score}")
                    total_games += 1
                
                schedule[date_str] = daily_results
            
            current_date += timedelta(days=1)
        
        # Calculate final standings
        standings = []
        for team, stats in team_stats.items():
            win_pct = stats["wins"] / (stats["wins"] + stats["losses"]) if (stats["wins"] + stats["losses"]) > 0 else 0
            run_diff = stats["runs_for"] - stats["runs_against"]
            standings.append({
                "team": team,
                "wins": stats["wins"],
                "losses": stats["losses"],
                "win_pct": win_pct,
                "runs_for": stats["runs_for"],
                "runs_against": stats["runs_against"],
                "run_diff": run_diff
            })
        
        # Sort standings by win percentage
        standings.sort(key=lambda x: x["win_pct"], reverse=True)
        
        print("\nFinal Standings:")
        print("-" * 50)
        print("Team  W-L    PCT    RF-RA   DIFF")
        for team in standings:
            print(f"{team['team']:<5} {team['wins']:>3}-{team['losses']:<3} {team['win_pct']:.3f} {team['runs_for']:>4}-{team['runs_against']:<4} {team['run_diff']:>4}")
        
        return {
            "total_games": total_games,
            "days_with_games": len(schedule),
            "schedule": schedule,
            "standings": standings,
            "season_start": self.season_start.strftime("%Y-%m-%d"),
            "season_end": self.season_end.strftime("%Y-%m-%d")
        }