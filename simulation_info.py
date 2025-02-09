from enum import Enum, auto
from batter_engine import Team
from pybaseball import *

class Granularity(Enum):
    PITCH = auto()


# This will hold all the information for the game before starting
class SimulationInfo:
    def __init__(
        self, 
        home_team, 
        away_team, 
        date, 
        home_roster=None, 
        away_roster=None, 
        backtest=False, 
        granularity: Granularity = Granularity.PITCH,
        pitchSimulator: str = 'basic',
        logLevel: int = 0
    ):
        self.date = date
        self.statcast = statcast(start_dt="2024-03-29", end_dt=date)
        self.away_team = Team(away_team, date, away_roster, self.statcast, backtest=backtest)
        self.home_team = Team(home_team, date, home_roster, self.statcast, backtest=backtest)
        self.inning = 1
        self.top = True
        self.granularity = granularity
        self.logLevel = logLevel
        self.pitchSimulator = pitchSimulator
        self._log = ''

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