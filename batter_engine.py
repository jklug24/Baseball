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
        self.pitcher = Pitcher(pitcher_id, statcast)

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

    def nextBatter(self):
        return self.roster[self.idx]

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
        self.ip_probs, self.ip_outcomes = self.init_ip_stats(stats.copy())
        self.pitch_probs = self.init_pitch_stats(stats.copy())
    
    def init_ip_stats(self, probs):
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

    def get_ip_probs(self):
        return self.ip_probs, self.ip_outcomes

    def init_pitch_stats(self, probs):
        ps = {}

        for pitch in probs.pitch_type.unique():
            p = probs.loc[probs.pitch_type == pitch]
            p = pd.crosstab(p.pitch_type, p.description)

            p = p.div(p.sum(axis=1), axis=0)

            outcomes = p.columns.to_list()
            p = p.values.flatten().tolist()
            ps[pitch] = p, outcomes
        return ps

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

    def simulate_at_bat(self):
        return self.ip_outcomes[random.multinomial(1, self.ip_probs).tolist().index(1)]





class Pitcher:
    def __init__(self, id, statcast):
        self.id = id
        name = playerid_reverse_lookup([id])
        if len(name):
            self.name = name.name_first[0] + ' ' + name.name_last[0]
        else:
            self.name = "Unknown Player"
        
        stats = statcast.loc[statcast.pitcher == id]
        self.ip_probs, self.ip_outcomes = self.init_ip_stats(stats.copy())
        self.pitch_probs, self.pitch_types, self.pitch_rates = self.init_pitch_stats(stats.copy())

    def init_ip_stats(self, probs):
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

    def get_ip_probs(self):
        return self.ip_probs, self.ip_outcomes

    def init_pitch_stats(self, probs):
        ps = {}
        pitches = []
        count = []

        for pitch in probs.pitch_type.unique():
            pitches.append(pitch)
            p = probs.loc[probs.pitch_type == pitch]
            count.append(len(p))
            p = pd.crosstab(p.pitch_type, p.description)
            p = p.div(p.sum(axis=1), axis=0)

            outcomes = p.columns.to_list()
            p = p.values.flatten().tolist()
            ps[pitch] = p, outcomes\
        
        count = [c/sum(count) for c in count]
        return ps, pitches, count