from enum import Enum, auto
from team import Team
from pybaseball import *

class Granularity(Enum):
    PITCH = auto()

class Count:
    def __init__(self):
        self.balls = 0
        self.strikes = 0

    def reset(self):
        self.balls = 0
        self.strikes = 0

    def strike(self): 
        self.strikes += 1

    def ball(self):
        self.balls += 1


# This will hold all the information for the game before starting
class SimulationInfo:
    def __init__(
        self, 
        home_team, 
        away_team, 
        date, 
        home_roster=None, 
        away_roster=None,
        home_pitcher_id=None,
        away_pitcher_id=None,
        stats=None, 
        backtest=False, 
        granularity: Granularity = Granularity.PITCH,
        pitchSimulator: str = 'basic',
        logLevel: int = 0
    ):
        """Initialize simulation info.
        
        Args:
            home_team: Name of home team
            away_team: Name of away team
            date: Game date
            home_roster: Optional roster for home team
            away_roster: Optional roster for away team
            home_pitcher_id: Optional starting pitcher ID for home team
            away_pitcher_id: Optional starting pitcher ID for away team
            stats: Optional Statcast data for both teams
            backtest: Whether this is a backtest simulation
            granularity: Simulation granularity level
            pitchSimulator: Pitch simulator to use
            logLevel: Log level
        """
        # Get statcast data if not provided
        if stats is None:
            stats = statcast(start_dt="2024-03-29", end_dt=date)

        # Initialize teams (they will extract what they need from stats)
        try:
            self.away_team = Team(
                name=away_team,
                date=date,
                roster=away_roster,
                pitcher_id=away_pitcher_id,
                statcast=stats,
                backtest=backtest
            )
        except ValueError as e:
            raise ValueError(f"Failed to initialize away team: {str(e)}")

        try:
            self.home_team = Team(
                name=home_team,
                date=date,
                roster=home_roster,
                pitcher_id=home_pitcher_id,
                statcast=stats,
                backtest=backtest
            )
        except ValueError as e:
            raise ValueError(f"Failed to initialize home team: {str(e)}")
        
        self.date = date
        self.granularity = granularity
        self.pitchSimulator = pitchSimulator
        self.logLevel = logLevel
        self._log = ''
        self.count = Count()
        self.inning = 1
        self.top = True

    def is_home(self, team: Team):
        return team.name == self.home_team.name

    def walk_off(self):
        return self.inning >= 9 and self.top == False and self.home_team.score > self.away_team.score

    def incrementInning(self):
        self.inning += 1
    
    def incrementFrame(self):
        self.top = not self.top

    def offense(self): return self.away_team if self.top else self.home_team
    def defense(self): return self.home_team if self.top else self.away_team

    def log(self, message: str, logLevel: int = 0):
        if logLevel <= 0: 
            self._log += ('\t'*(logLevel-1)) + message + '\n'