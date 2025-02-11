from pybaseball import *
import pandas as pd
from numpy import random
import numpy as np
from pybaseball import *


class Team:
    def __init__(self, name, date, roster, statcast, backtest):
        self.name = name
        self.date = date

        if (roster is None):
            if backtest:
                roster, pitcher_id = self.get_roster(statcast)
                statcast = statcast.loc[statcast.game_date != self.date]
            else:
                roster = self.predict_roster(statcast)

        self.roster = [Batter(id, statcast) for id in roster]
        self._pitcher = Pitcher(pitcher_id, statcast)

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

    def get_roster(self, statcast):
        pitchers = statcast.loc[(((statcast.home_team == self.name) & (statcast.inning_topbot == 'Top')) | ((statcast.away_team == self.name) & (statcast.inning_topbot == 'Bot'))) & (statcast.game_date == self.date)].iloc[0].pitcher
        stats = statcast.loc[(((statcast.home_team == self.name) & (statcast.inning_topbot == 'Bot')) | ((statcast.away_team == self.name) & (statcast.inning_topbot == 'Top'))) & (statcast.game_date == self.date)]
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



class Batter:
    def __init__(self, id, statcast):
        self.id = id
        name = playerid_reverse_lookup([id])
        if len(name):
            self.name = name.name_first[0] + ' ' + name.name_last[0]
        else:
            self.name = "Unknown Player"
        
        stats = statcast.loc[statcast.batter == id]
        self.in_play_probs, self.ip_outcomes = self.init_in_play_stats(stats.copy())
        self.__init_batter_outcome_probs_global(stats)
        self.__init_batter_outcome_probs_basic(stats)
        self.__init_batter_outcome_probs_count_based(stats)
    
    def init_in_play_stats(self, probs):
        outcome_list = ['field_out', 'fielders_choice', 'sac_fly', 'single', 'double', 'triple', 'home_run']
        probs = pd.crosstab(probs.batter, probs.events)

        for outcome in outcome_list:
            if outcome not in probs:
                probs[outcome] = 0

        probs['field_out'] = probs['field_out'] + probs['fielders_choice'] + probs['sac_fly']
        probs = probs[['field_out', 'single', 'double', 'triple', 'home_run']]

        probs = probs.div(probs.sum(axis=1), axis=0)

        outcomes = probs.columns.to_list()
        probs = probs.values.flatten().tolist()
        return probs, outcomes

    def get_in_play_probs(self):
        return self.in_play_probs, self.ip_outcomes

    def __init_batter_outcome_probs_global(self, batter_data: pd.DataFrame):
        """
        Computes overall probabilities for all outcomes, regardless of pitch type or count.
        """
        self.global_outcome_probs = batter_data['description'].value_counts(normalize=True).to_dict()


    def __init_batter_outcome_probs_basic(self, batter_data: pd.DataFrame):
        """
        Computes overall outcome probabilities for each pitch type.
        """
        self.outcome_probs = {}
        
        grouped = batter_data.groupby('pitch_type')['description'].value_counts(normalize=True)
        
        for pitch_type, outcome_probs in grouped.groupby(level=0):
            self.outcome_probs[pitch_type] = outcome_probs.droplevel(0).to_dict()

    def __init_batter_outcome_probs_count_based(self, batter_data: pd.DataFrame):
        """
        Computes outcome probabilities for each pitch type based on count (balls-strikes).
        """
        self.count_based_outcome_probs = {}
        
        grouped = batter_data.groupby(['pitch_type', 'balls', 'strikes'])['description'].value_counts(normalize=True)
        
        for (pitch_type, balls, strikes), outcome_probs in grouped.groupby(level=[0, 1, 2]):
            if pitch_type not in self.count_based_outcome_probs:
                self.count_based_outcome_probs[pitch_type] = {}
            self.count_based_outcome_probs[pitch_type][(balls, strikes)] = outcome_probs.droplevel([0, 1, 2]).to_dict()

    def get_pitch_probs(self, pitch):
        return self.pitch_probs.get(pitch, ([
            .1, .1, .1, .1, .1, .1
        ],[
            'ball',
            'called_strike',
            'foul',
            'foul_tip',
            'hit_into_play',
            'swinging_strike']))

    def simulate_hit(self):
        return self.ip_outcomes[random.multinomial(1, self.in_play_probs).tolist().index(1)]


    def get_pitch_result(self, pitch_type: str, balls: int = None, strikes: int = None) -> str:
        """
        Predicts the outcome of a pitch based on type and optionally count.
        :param pitch_type: The type of pitch thrown.
        :param balls: (Optional) Current number of balls.
        :param strikes: (Optional) Current number of strikes.
        :return: The predicted pitch outcome.
        """
        if pitch_type and balls is not None and strikes is not None and (pitch_type in self.count_based_outcome_probs and (balls, strikes) in self.count_based_outcome_probs[pitch_type]):
            outcome_probs = self.count_based_outcome_probs[pitch_type][(balls, strikes)]
        elif pitch_type and pitch_type in self.outcome_probs:
            outcome_probs = self.outcome_probs[pitch_type]
        else:
            outcome_probs = self.global_outcome_probs  # Fallback to global probabilities

        if not outcome_probs:
            return "Unknown Outcome"  # Fallback if data is missing
        
        outcomes, probabilities = zip(*outcome_probs.items())
        outcome_index = np.random.multinomial(1, probabilities).argmax()
        return outcomes[outcome_index]






class Pitcher:
    def __init__(self, id, statcast):
        self.id = id
        name = playerid_reverse_lookup([id])
        if len(name):
            self.name = name.name_first[0] + ' ' + name.name_last[0]
        else:
            self.name = "Unknown Player"
        
        self.stats = statcast.loc[statcast.pitcher == id]
        self.in_play_probs, self.ip_outcomes = self.init_in_play_stats(self.stats.copy())
        self.__init_pitch_stats_basic(self.stats)
        self.__init_pitch_probs_count_based(self.stats)

    def init_in_play_stats(self, probs):
        outcome_list = ['field_out', 'fielders_choice', 'sac_fly', 'single', 'double', 'triple', 'home_run']
        probs = pd.crosstab(probs.batter, probs.events)

        for outcome in outcome_list:
            if outcome not in probs:
                probs[outcome] = 0

        probs['field_out'] = probs['field_out'] + probs['fielders_choice'] + probs['sac_fly']
        probs = probs[['field_out', 'single', 'double', 'triple', 'home_run']]

        probs = probs.div(probs.sum(axis=1), axis=0)

        outcomes = probs.columns.to_list()
        probs = probs.values.flatten().tolist()
        return probs, outcomes

    def get_in_play_probs(self):
        return self.in_play_probs, self.ip_outcomes

    def __init_pitch_stats_basic(self, pitcher_data: pd.DataFrame):
        """
        Computes overall pitch probabilities from the DataFrame.
        """
        pitch_counts = pitcher_data['pitch_type'].value_counts(normalize=True)
        self.pitch_types = pitch_counts.index.tolist()  # List of pitch types
        self.probabilities = pitch_counts.values

    def __init_pitch_probs_count_based(self, pitcher_data: pd.DataFrame):
        """
        Computes pitch probabilities based on count (balls-strikes).
        """
        self.count_based_probs = {}
        
        grouped = pitcher_data.groupby(['balls', 'strikes'])['pitch_type'].value_counts(normalize=True)
        
        for (balls, strikes), pitch_probs in grouped.groupby(level=[0, 1]):
            self.count_based_probs[(balls, strikes)] = pitch_probs.droplevel([0, 1]).to_dict()

    def simulate_pitch(self, balls: int = None, strikes: int = None): 
        """
        Predicts the next pitch. If count is provided, uses count-based probabilities.
        :param balls: (Optional) Current number of balls.
        :param strikes: (Optional) Current number of strikes.
        :return: The predicted pitch type.
        """
        if balls is not None and strikes is not None and (balls, strikes) in self.count_based_probs:
            count_probs = self.count_based_probs[(balls, strikes)]
            pitch_types, probabilities = zip(*count_probs.items())
        else:
            pitch_types, probabilities = self.pitch_types, self.probabilities

        pitch_index = np.random.multinomial(1, probabilities).argmax()
        return pitch_types[pitch_index]