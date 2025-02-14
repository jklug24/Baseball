from pybaseball import *
import pandas as pd
from numpy import random
import numpy as np
from pybaseball import *
from pitcher import Pitcher
from batter import Batter


class Team:
    def __init__(self, name, date, roster=None, statcast=None, backtest=False, pitcher_id=None):
        """Initialize a team with its roster and statistics.
        
        Args:
            name: Team name
            date: Game date
            roster: List of player IDs for the team's roster. If None, will be predicted or fetched.
            statcast: Statcast data for player statistics
            backtest: Whether this is a backtest simulation
            pitcher_id: ID of the starting pitcher. If None, will be predicted or fetched.
            
        Raises:
            ValueError: If required data is missing or invalid
        """
        if not name:
            raise ValueError("Team name is required")
        if not date:
            raise ValueError("Date is required")
        if statcast is None:
            raise ValueError("Statcast data is required")

        self.name = name
        self.date = date
        self._pitcher_id = pitcher_id  # Store the provided pitcher_id

        # Get roster and pitcher if not provided
        if roster is None:
            if backtest:
                try:
                    roster, fetched_pitcher_id = Team.get_roster(statcast, name, date)
                    statcast = statcast.loc[statcast.game_date != self.date]
                    # Only use fetched pitcher if none was provided
                    if self._pitcher_id is None:
                        self._pitcher_id = fetched_pitcher_id
                except Exception as e:
                    raise ValueError(f"Failed to get historical roster for {name} on {date}: {str(e)}")
            else:
                try:
                    roster = self.predict_roster(statcast)
                    if self._pitcher_id is None:
                        raise ValueError(f"pitcher_id is required when not in backtest mode")
                except Exception as e:
                    raise ValueError(f"Failed to predict roster for {name}: {str(e)}")

        # Validate roster
        if not roster:
            raise ValueError(f"No roster available for {name}")

        # Initialize players
        try:
            self.roster = [Batter(id, statcast) for id in roster]
        except Exception as e:
            raise ValueError(f"Failed to initialize batters for {name}: {str(e)}")

        # Initialize pitcher
        if not self._pitcher_id:
            raise ValueError(f"No pitcher ID available for {name}")
        try:
            self._pitcher = Pitcher(self._pitcher_id, statcast)
        except Exception as e:
            raise ValueError(f"Failed to initialize pitcher {self._pitcher_id} for {name}: {str(e)}")

        self.idx = 0
        self.score = 0
        self.stats = {}

    def next_idx(self):
        self.idx += 1
        if self.idx == len(self.roster):
            self.idx = 0

    def increment_score(self, score):
        self.score += score

    def predict_roster(self, statcast):
        stats = statcast.loc[((statcast.home_team == self.name) & (statcast.inning_topbot == 'Bot')) | ((statcast.away_team == self.name) & (statcast.inning_topbot == 'Top'))]
                
        df = stats.groupby(['game_date', 'batter'])['at_bat_number'].min().to_frame().reset_index()
        dfs = []
        for date in df['game_date'].unique():
            frame = df.loc[df.game_date == date].sort_values('at_bat_number', ignore_index = True)
            frame['idx'] = frame.index
            frame = frame.loc[frame.index <= 8]
            dfs.append(frame[['batter', 'idx']])

        equal = []
        for i in range(len(dfs)):
            count = 0
            for j in range(i + 1, len(dfs)):
                if dfs[i].equals(dfs[j]):
                    count += 1
            equal.append(count)

        return [i[0] for i in np.array(dfs)[np.array([i == max(equal) for i in equal])][-1]]

    @staticmethod
    def get_roster(statcast, name, date):
        pitchers = statcast.loc[(((statcast.home_team == name) & (statcast.inning_topbot == 'Top')) | ((statcast.away_team == name) & (statcast.inning_topbot == 'Bot'))) & (statcast.game_date == date)].iloc[0].pitcher
        stats = statcast.loc[(((statcast.home_team == name) & (statcast.inning_topbot == 'Bot')) | ((statcast.away_team == name) & (statcast.inning_topbot == 'Top'))) & (statcast.game_date == date)]
        return [x for x in stats.groupby(['game_date', 'batter'])['at_bat_number'].min().to_frame().reset_index().sort_values('at_bat_number', ignore_index = True)['batter']], pitchers

    def get_lineup(self):
        lineup = ''
        for i in self.roster:
            lineup = lineup + i.name + '\n'
        return lineup

    def batter(self):
        return self.roster[self.idx]

    def pitcher(self):
        return self._pitcher

    def recordStat(self, player, stat):
        if player not in self.stats:
            self.stats[player] = {}  # Create first level key if missing

        if stat not in self.stats[player]:
            self.stats[player][stat] = 1  # Initialize if missing
        else:
            self.stats[player][stat] += 1


