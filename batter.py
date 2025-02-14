from numpy import random
import numpy as np
import pandas as pd
from pybaseball import playerid_reverse_lookup

# League average probabilities (nerfed) for basic outcomes - define at module level
LEAGUE_AVG_PROBS = {
    'ball': 0.35,           # ~35% balls
    'called_strike': 0.17,  # ~17% called strikes
    'swinging_strike': 0.10,# ~10% swinging strikes
    'foul': 0.13,          # ~13% fouls
    'hit_into_play': 0.25   # ~25% balls in play
}

# League average hit constants
LEAGUE_AVG_OUTCOMES = ['field_out', 'single', 'double', 'triple', 'home_run']
LEAGUE_AVG_HIT_PROBS = [0.69, 0.15, 0.09, 0.02, 0.05]

class Batter:
    def __init__(self, id, statcast):
        """Initialize a batter with their statistics."""
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
        self.basic_outcome_probs = {}
        
        grouped = batter_data.groupby('pitch_type')['description'].value_counts(normalize=True)
        
        for pitch_type, outcome_probs in grouped.groupby(level=0):
            self.basic_outcome_probs[pitch_type] = outcome_probs.droplevel(0).to_dict()

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


    def simulate_hit(self):
        try:
            result = random.multinomial(1, self.in_play_probs).argmax()
            return self.ip_outcomes[result]
        except:
            # Fallback if anything goes wrong
            return LEAGUE_AVG_OUTCOMES[random.multinomial(1, LEAGUE_AVG_HIT_PROBS).argmax()]


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
        elif pitch_type and pitch_type in self.basic_outcome_probs:
            outcome_probs = self.basic_outcome_probs[pitch_type]
        else:
            outcome_probs = self.global_outcome_probs 
        
        # Ensure we have valid probabilities
        if not outcome_probs or len(outcome_probs) == 0:
            outcome_probs = LEAGUE_AVG_PROBS
        
        outcomes, probabilities = zip(*outcome_probs.items())
        outcome_index = np.random.multinomial(1, probabilities).argmax()
        return outcomes[outcome_index]