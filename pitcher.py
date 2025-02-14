from numpy import random
import numpy as np
import pandas as pd
from pybaseball import playerid_reverse_lookup

# League average pitch type distribution
LEAGUE_AVG_PITCH_TYPES = ['FF', 'SL', 'CH', 'CU', 'SI', 'FC']
LEAGUE_AVG_PITCH_PROBS = [0.35, 0.20, 0.15, 0.15, 0.10, 0.05]  # Matches order of types above

class Pitcher:
    def __init__(self, id, statcast: pd.DataFrame):
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
        try:
            if balls is not None and strikes is not None and (balls, strikes) in self.count_based_probs:
                count_probs = self.count_based_probs[(balls, strikes)]
                pitch_types, probabilities = zip(*count_probs.items())
            else:
                pitch_types, probabilities = self.pitch_types, self.probabilities

            pitch_index = np.random.multinomial(1, probabilities).argmax()
            return pitch_types[pitch_index]
        except:
            # Fallback to league average if anything goes wrong
            return LEAGUE_AVG_PITCH_TYPES[np.random.multinomial(1, LEAGUE_AVG_PITCH_PROBS).argmax()]