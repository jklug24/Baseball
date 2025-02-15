from numpy import random
import numpy as np
import pandas as pd
from pybaseball import playerid_reverse_lookup
from db_manager import DatabaseManager

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
    _db = DatabaseManager()  # Class-level database manager
    
    def __init__(self, id, statcast):
        """Initialize a batter with their ID and statcast data.
        
        Args:
            id: MLB ID of the batter
            statcast: DataFrame containing statcast data
        """
        self.id = int(id)  # Convert numpy.int64 to int
        self._db = DatabaseManager()
        
        # Check all caches first
        in_play_probs = self._db.get_batter_probs_in_play(self.id)
        basic_probs = self._db.get_batter_probs_basic(self.id)
        global_probs = self._db.get_batter_probs_global(self.id)
        count_based_probs = self._db.get_batter_probs_count_based(self.id)
        name = self._db.get_player_name(self.id)
        
        # Only filter statcast data if we need to calculate any probabilities
        if not all([in_play_probs, basic_probs, global_probs, count_based_probs]):
            filtered_stats = statcast.loc[statcast.batter == id]
            
            if not in_play_probs:
                in_play_probs = self.__init_in_play_stats(filtered_stats)
                self._db.set_batter_probs_in_play(self.id, in_play_probs)
            
            if not basic_probs:
                basic_probs = self.__init_batter_outcome_probs_basic(filtered_stats)
                self._db.set_batter_probs_basic(self.id, basic_probs)
            
            if not global_probs:
                global_probs = self.__init_batter_outcome_probs_global(filtered_stats)
                self._db.set_batter_probs_global(self.id, global_probs)
            
            if not count_based_probs:
                count_based_probs = self.__init_batter_outcome_probs_count_based(filtered_stats)
                self._db.set_batter_probs_count_based(self.id, count_based_probs)
        
        # Set all probabilities
        self.in_play_probs = in_play_probs
        self.basic_probs = basic_probs
        self.global_outcome_probs = global_probs
        self.count_based_outcome_probs = count_based_probs
        
        # Handle player name
        if not name:
            lookup = playerid_reverse_lookup([self.id])
            if len(lookup):
                first_name = lookup.name_first[0]
                last_name = lookup.name_last[0]
                self._db.set_player_name(self.id, first_name, last_name)
                self.name = f"{first_name} {last_name}"
            else:
                self.name = "Unknown Player"
        else:
            first_name, last_name = name
            self.name = f"{first_name} {last_name}"

    def __init_in_play_stats(self, stats):
        """Initialize in-play probabilities and outcomes for a batter."""
        # Get value counts of events
        probs = stats['events'].value_counts(normalize=True)
        
        # Filter to only include hit outcomes and convert to dictionary
        hit_outcomes = ['field_out', 'single', 'double', 'triple', 'home_run']
        probs = probs[probs.index.isin(hit_outcomes)]
        
        # Convert to dictionary with all outcomes
        probs_dict = {outcome: 0.0 for outcome in hit_outcomes}
        probs_dict.update(probs.to_dict())
        
        # Normalize probabilities
        total = sum(probs_dict.values())
        if total > 0:
            probs_dict = {k: v/total for k, v in probs_dict.items()}
        else:
            # Use league average if no data
            probs_dict = dict(zip(hit_outcomes, LEAGUE_AVG_HIT_PROBS))
        
        return probs_dict

    def get_in_play_probs(self):
        """Get in-play probabilities."""
        return self.in_play_probs

    def __init_batter_outcome_probs_global(self, batter_data: pd.DataFrame):
        """
        Computes overall probabilities for all outcomes, regardless of pitch type or count.
        """
        return batter_data['description'].value_counts(normalize=True).to_dict()
            

    def __init_batter_outcome_probs_basic(self, batter_data: pd.DataFrame):
        """
        Computes overall outcome probabilities for each pitch type.
        """
        basic_outcome_probs = {}
        
        grouped = batter_data.groupby('pitch_type')['description'].value_counts(normalize=True)
        
        for pitch_type, outcome_probs in grouped.groupby(level=0):
            basic_outcome_probs[pitch_type] = outcome_probs.droplevel(0).to_dict()
        return basic_outcome_probs

    def __init_batter_outcome_probs_count_based(self, batter_data: pd.DataFrame):
        """
        Computes outcome probabilities for each pitch type based on count (balls-strikes).
        """
        count_based_outcome_probs = {}
        
        grouped = batter_data.groupby(['pitch_type', 'balls', 'strikes'])['description'].value_counts(normalize=True)
        
        for (pitch_type, balls, strikes), outcome_probs in grouped.groupby(level=[0, 1, 2]):
            if pitch_type not in count_based_outcome_probs:
                count_based_outcome_probs[pitch_type] = {}
            count_key = f"{balls}-{strikes}"  # Convert tuple to string key
            count_based_outcome_probs[pitch_type][count_key] = outcome_probs.droplevel([0, 1, 2]).to_dict()
        return count_based_outcome_probs


    def simulate_hit(self):
        try:
            outcomes = list(self.in_play_probs.keys())
            probs = list(self.in_play_probs.values())
            result = random.multinomial(1, probs).argmax()
            return outcomes[result]
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
        if pitch_type and balls is not None and strikes is not None and (pitch_type in self.count_based_outcome_probs and f"{balls}-{strikes}" in self.count_based_outcome_probs[pitch_type]):
            outcome_probs = self.count_based_outcome_probs[pitch_type][f"{balls}-{strikes}"]
        elif pitch_type and pitch_type in self.basic_probs:
            outcome_probs = self.basic_probs[pitch_type]
        else:
            outcome_probs = self.global_outcome_probs 
        
        # Ensure we have valid probabilities
        if not outcome_probs or len(outcome_probs) == 0:
            outcome_probs = LEAGUE_AVG_PROBS
        
        outcomes, probabilities = zip(*outcome_probs.items())
        outcome_index = np.random.multinomial(1, probabilities).argmax()
        return outcomes[outcome_index]