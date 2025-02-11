from simulation_info import SimulationInfo
from pitch_simulator import PitchSimulator
import numpy as np
from numpy import random
import copy
from collections import defaultdict



class BootstrapGame:
    def __init__(self, simulationInfo: SimulationInfo):
        self.simulationInfo = simulationInfo

    def run(self, games: int):
        home_wins = 0
        away_wins = 0
        homeScore = 0
        awayScore = 0
        homeStats = {}
        awayStats = {}
        for i in range(games):
            game = GameSimulator(copy.deepcopy(self.simulationInfo))
            game.run()

            homeScore += game.simulationInfo.home_team.score
            awayScore += game.simulationInfo.away_team.score
            homeStats = self.merge_stats(homeStats, game.simulationInfo.home_team.stats)
            awayStats = self.merge_stats(awayStats, game.simulationInfo.away_team.stats)

            if game.simulationInfo.home_team.score > game.simulationInfo.away_team.score:
                home_wins += 1
            else:
                away_wins += 1
        
        print('In {} simulations {} won {} and {} won {} with an average score of {} - {}'.format(
            games, self.simulationInfo.home_team.name, home_wins, 
            self.simulationInfo.away_team.name, away_wins, homeScore/games, awayScore/games
        ))
        print(homeStats)
        print(awayStats)

    def merge_stats(self, dict1, dict2):
        merged = defaultdict(dict)  # Using defaultdict to simplify merging

        # Get all unique keys from both dictionaries
        all_keys = set(dict1.keys()) | set(dict2.keys())

        for key in all_keys:
            # Merge inner dictionaries
            sub_keys = set(dict1.get(key, {}).keys()) | set(dict2.get(key, {}).keys())
            merged[key] = {
                sub_key: dict1.get(key, {}).get(sub_key, 0) + dict2.get(key, {}).get(sub_key, 0)
                for sub_key in sub_keys
            }

        return dict(merged)  # Convert back to a regular dictionary




class GameSimulator:
    def __init__(self, simulationInfo: SimulationInfo):
        self.simulationInfo = simulationInfo

    def run(self):
        home_team = self.simulationInfo.home_team
        away_team = self.simulationInfo.away_team

        game_log = ''
        self.simulationInfo.log('Home team: \n' + home_team.get_lineup(), logLevel=1)
        self.simulationInfo.log('Away team: \n' + away_team.get_lineup(), logLevel=1)

        while self.simulationInfo.inning <= 9 or home_team.score == away_team.score:
            self.simulate_inning()
            self.simulationInfo.incrementInning()
        
        if home_team.score > away_team.score:
            self.simulationInfo.log('{} wins {} to {}'.format(home_team.name, home_team.score, away_team.score), logLevel=1)
        else:
            self.simulationInfo.log('{} wins {} to {}'.format(away_team.name, away_team.score, home_team.score), logLevel=1)


    def simulate_inning(self):

        FrameSimulator(self.simulationInfo).run()
        self.simulationInfo.incrementFrame()

        FrameSimulator(self.simulationInfo).run()
        self.simulationInfo.incrementFrame()


class FrameSimulator:
    def __init__(self, simulationInfo: SimulationInfo, top=True):
        self.simulationInfo = simulationInfo
        self.top = top
        
    def run(self):
        outs = 0
        bases = Bases()
        self.simulationInfo.log('{} {}\n'.format('Top' if self.simulationInfo.top else 'Bottom', self.simulationInfo.inning), logLevel=1)

        while outs != 3 and not self.simulationInfo.walk_off():

            result = AtBatSimulator(self.simulationInfo).run()
            score, baseText = bases.advance_runners(result, self.simulationInfo.offense().batter())
            self.simulationInfo.offense().increment_score(score)
            self.simulationInfo.offense().recordStat(self.simulationInfo.offense().batter().name, result)

            if (score > 0):
                self.simulationInfo.log('{} {}.'.format(self.simulationInfo.offense().batter().name, result), logLevel=1)
            else:
                self.simulationInfo.log('{} {}.'.format(self.simulationInfo.offense().batter().name, result), logLevel=2)
                

            if result == 'field_out' or result == 'strikeout':
                outs += 1
            elif baseText != '':
                if score > 0:
                    self.simulationInfo.log( baseText, logLevel=1)
                    self.simulationInfo.log('{} - {}'.format(self.simulationInfo.home_team.score, self.simulationInfo.away_team.score), logLevel=1)
                else:
                    self.simulationInfo.log( baseText, logLevel=2)

            self.simulationInfo.offense().next_idx()
        self.simulationInfo.log('{} - {}\n'.format(self.simulationInfo.home_team.score, self.simulationInfo.away_team.score), logLevel=1)

class AtBatSimulator:
    def __init__(self, simulationInfo: SimulationInfo):
        self.simulationInfo = simulationInfo

    def run(self):
        batter = self.simulationInfo.offense().batter()
        count = self.simulationInfo.count
        count.reset()
        pitch_num = 1
        self.simulationInfo.log('{} up to bat.\n'.format(batter.name), logLevel=3)

        while count.strikes < 3 and count.balls < 4:
            pitch, result = PitchSimulator.init(self.simulationInfo).run()

            if result == 'ball':
                count.ball()
            elif result == 'called_strike' or result == 'swinging_strike':
                count.strike()
            elif result == 'foul' and count.strikes < 2:
                count.strike()
            elif result == 'hit_into_play':
                self.simulationInfo.log("{}. {}, {}".format(pitch_num, pitch, result), logLevel=3)
                return batter.simulate_hit()
            
            self.simulationInfo.log("{}. {}, {}\t{} - {}".format(pitch_num, pitch, result, count.balls, count.strikes), logLevel=3)
            pitch_num += 1
    
        if count.strikes == 3:
            return 'strikeout'
        elif count.balls == 4:
            return 'walk'



class Bases:
    def __init__(self, extra_runner=None):
        self.first = None
        self.second = extra_runner
        self.third = None

    def advance_runners(self, result, runner):
        extra_text = ""
        score = 0
        if result == 'walk':
            if self.first is None:
                self.first = runner
            elif self.second is None:
                extra_text = self.first.name + ' advances.'
                self.second = self.first
                self.first = runner
            elif self.third is None:
                extra_text = self.first.name + ' and ' + self.second.name + ' advance.'
                self.third = self.second
                self.second = self.first
                self.first = runner
            else:
                extra_text = self.first.name + ' and ' + self.second.name + ' advance. ' + self.third.name + ' scores.\n '
                self.third = self.second
                self.second = self.first
                self.first = runner

        elif result == 'single':
            score = 0
            if self.third:
                score += 1
                extra_text = self.third.name + ' scores.'

            self.third = self.second
            self.second = self.first
            self.first = runner

        elif result == 'double':
            if self.third:
                score += 1
                extra_text = self.third.name + ' scores. '
            if self.second:
                score += 1
                extra_text = extra_text + self.second.name + ' scores.'
            self.third = self.second
            self.second = runner
            self.first = None


        elif result == 'triple':
            if self.third:
                score += 1
                extra_text = extra_text + self.third.name + ' scores. '
            if self.second:
                score += 1
                extra_text = extra_text + self.second.name + ' scores. '
            if self.first:
                score += 1
                extra_text = extra_text + self.first.name + ' scores.'
            self.third = runner
            self.second = None
            self.first = None

        elif result == 'home_run':
            score += 1
            if self.third:
                score += 1
                extra_text = extra_text + self.third.name + ' scores. '
            if self.second:
                score += 1
                extra_text = extra_text + self.second.name + ' scores. '
            if self.first:
                score += 1
                extra_text = extra_text + self.first.name + ' scores.'
            self.third = None
            self.second = None
            self.first = None

        return score, extra_text

