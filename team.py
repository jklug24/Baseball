from pybaseball import *
import pandas as pd
from numpy import random
import numpy as np
from pybaseball import *


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

# League average pitch type distribution
LEAGUE_AVG_PITCH_TYPES = ['FF', 'SL', 'CH', 'CU', 'SI', 'FC']
LEAGUE_AVG_PITCH_PROBS = [0.35, 0.20, 0.15, 0.15, 0.10, 0.05]  # Matches order of types above


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