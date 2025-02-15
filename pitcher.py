from numpy import random
import numpy as np
import pandas as pd
from pybaseball import playerid_reverse_lookup
from db_manager import DatabaseManager

# League average pitch type distribution
LEAGUE_AVG_PITCH_TYPES = ['FF', 'SL', 'CH', 'CU', 'SI', 'FC']
LEAGUE_AVG_PITCH_PROBS = [0.35, 0.20, 0.15, 0.15, 0.10, 0.05]  # Matches order of types above

class Pitcher:
    _db = DatabaseManager()  # Class-level database manager
    
    def __init__(self, id, statcast: pd.DataFrame):
        self.id = int(id)  # Convert numpy.int64 to int
        
        # Check all caches first
        basic_probs = self._db.get_pitcher_basic_probs(self.id)
        count_based_probs = self._db.get_pitcher_count_based_probs(self.id)
        in_play_probs = self._db.get_pitcher_in_play_probs(self.id)
        name = self._db.get_player_name(self.id)
        
        # Only filter statcast data if we need to calculate any probabilities
        filtered_stats = None
        if not all([basic_probs, count_based_probs, in_play_probs]):
            filtered_stats = statcast.loc[statcast.pitcher == id]
            
            if not basic_probs:
                basic_probs = self.__init_pitch_stats_basic(filtered_stats)
                self._db.set_pitcher_basic_probs(self.id, basic_probs)
            
            if not count_based_probs:
                count_based_probs = self.__init_pitch_probs_count_based(filtered_stats)
                self._db.set_pitcher_count_based_probs(self.id, count_based_probs)
            
            if not in_play_probs:
                in_play_probs = self.init_in_play_stats(filtered_stats)
                self._db.set_pitcher_in_play_probs(self.id, in_play_probs)
        
        # Set all probabilities
        self.basic_probs = basic_probs
        self.count_based_probs = count_based_probs
        self.in_play_probs = in_play_probs
        
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

    def init_in_play_stats(self, stats):
        """Initialize in-play statistics with proper normalization.
        Returns a dictionary mapping outcomes to probabilities.
        """
        # Define possible outcomes
        hit_outcomes = ['field_out', 'single', 'double', 'triple', 'home_run']
        
        if len(stats) == 0:
            # Fallback to league average if no data
            return dict(zip(hit_outcomes, [0.69, 0.15, 0.09, 0.02, 0.05]))
        
        # Get value counts of events
        probs = stats['events'].value_counts(normalize=True)
        
        # Filter to only include hit outcomes and convert to dictionary
        probs = probs[probs.index.isin(hit_outcomes)]
        
        # Convert to dictionary with all outcomes
        probs_dict = {outcome: 0.0 for outcome in hit_outcomes}
        probs_dict.update(probs.to_dict())
        
        # Combine field_out related outcomes
        if 'fielders_choice' in stats['events'].unique():
            field_out_prob = probs_dict['field_out']
            fielders_choice_prob = stats['events'].value_counts(normalize=True).get('fielders_choice', 0)
            sac_fly_prob = stats['events'].value_counts(normalize=True).get('sac_fly', 0)
            probs_dict['field_out'] = field_out_prob + fielders_choice_prob + sac_fly_prob
        
        # Normalize probabilities
        total = sum(probs_dict.values())
        if total > 0:
            probs_dict = {k: v/total for k, v in probs_dict.items()}
        else:
            # Use league average if no data
            probs_dict = dict(zip(hit_outcomes, [0.69, 0.15, 0.09, 0.02, 0.05]))
        
        return probs_dict

    def get_in_play_probs(self):
        """Get in-play probabilities for this pitcher.
        Returns a dictionary mapping outcomes to probabilities.
        """
        return self.in_play_probs

    def __init_pitch_stats_basic(self, pitcher_data: pd.DataFrame):
        """
        Computes overall pitch probabilities from the DataFrame.
        Returns a dictionary mapping pitch types to probabilities.
        """
        pitch_counts = pitcher_data['pitch_type'].value_counts(normalize=True)
        return pitch_counts.to_dict()

    def __init_pitch_probs_count_based(self, pitcher_data: pd.DataFrame):
        """Initialize count-based pitch probabilities.
        Returns a dictionary mapping (balls, strikes) tuples to pitch type probabilities.
        """
        if len(pitcher_data) == 0:
            # Return a dictionary with league average probabilities for all counts
            return {(b,s): dict(zip(LEAGUE_AVG_PITCH_TYPES, LEAGUE_AVG_PITCH_PROBS)) 
                   for b in range(4) for s in range(3)}
        
        # Get basic probabilities to use as fallback for counts with no data
        basic_probs = self.__init_pitch_stats_basic(pitcher_data)
        
        # Get value counts for each count and pitch type combination
        count_probs = {}
        for balls in range(4):
            for strikes in range(3):
                count_data = pitcher_data[(pitcher_data.balls == balls) & 
                                       (pitcher_data.strikes == strikes)]
                
                if len(count_data) > 0:
                    pitch_counts = count_data.pitch_type.value_counts(normalize=True)
                    count_probs[(balls, strikes)] = pitch_counts.to_dict()
                else:
                    # Use pitcher's basic probabilities for counts with no data
                    count_probs[(balls, strikes)] = basic_probs.copy()
        
        return count_probs

    def simulate_pitch(self, balls: int = None, strikes: int = None): 
        """
        Predicts the next pitch. If count is provided, uses count-based probabilities.
        :param balls: (Optional) Current number of balls.
        :param strikes: (Optional) Current number of strikes.
        :return: The predicted pitch type.
        """
        try:
            if balls is not None and strikes is not None and (balls, strikes) in self.count_based_probs:
                probs = self.count_based_probs[(balls, strikes)]
            else:
                probs = self.basic_probs

            pitch_types, probabilities = zip(*probs.items())
            pitch_index = np.random.multinomial(1, probabilities).argmax()
            return pitch_types[pitch_index]
            
        except:
            # Fallback to league average if anything goes wrong
            return LEAGUE_AVG_PITCH_TYPES[np.random.multinomial(1, LEAGUE_AVG_PITCH_PROBS).argmax()]