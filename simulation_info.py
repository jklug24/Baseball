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
        stats = None, 
        backtest=False, 
        granularity: Granularity = Granularity.PITCH,
        pitchSimulator: str = 'basic',
        logLevel: int = 0
    ):
        if stats is None:
            self.statcast = statcast(start_dt="2024-03-29", end_dt=date)
        else: 
            self.statcast = stats

        try:
            self.away_team = Team(
                name=away_team,
                date=date,
                roster=away_roster,
                pitcher_id=away_pitcher_id,
                statcast=self.statcast,
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
                statcast=self.statcast,
                backtest=backtest
            )
        except ValueError as e:
            raise ValueError(f"Failed to initialize home team: {str(e)}")
        
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
        if logLevel <= self.logLevel: 
            self._log += ('\t'*(logLevel-1)) + message + '\n'