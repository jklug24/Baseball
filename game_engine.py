from batter_engine import Batter, Team
from pybaseball import *
import numpy as np
from numpy import random
from enum import Enum, auto

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
        granularity: Granularity = Granularity.PITCH
    ):
        self.date = date
        self.statcast = statcast(start_dt="2024-03-29", end_dt=date)
        self.away_team = Team(away_team, date, away_roster, self.statcast, backtest=backtest)
        self.home_team = Team(home_team, date, home_roster, self.statcast, backtest=backtest)
        self.inning = 1
        self.top = True
        self.granularity = granularity

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


class BootstrapGame:
    def __init__(self, simulationInfo: SimulationInfo):
        self.simulationInfo = simulationInfo

    def run(self, games: int):
        home_wins = 0
        away_wins = 0
        for i in range(games):
            game = GameSimulator(copy.deepcopy(simulationInfo))
            if game.home_team.score > game.away_team.score:
                home_wins += 1
            else:
                away_wins += 1
        
        print('In {} simulations {} won {} and {} won {}'.format(n, self.home_team.name, home_wins, self.away_team.name, away_wins))


class GameSimulator:
    def __init__(self, simulationInfo: SimulationInfo):
        self.simulationInfo = simulationInfo

    def run(self):
        home_team = self.simulationInfo.home_team
        away_team = self.simulationInfo.away_team

        game_log = ''

        game_log = game_log + 'Home team: \n' + home_team.get_lineup() + '\n\n'
        game_log = game_log + 'Away team: \n' + away_team.get_lineup() + '\n\n'


        while self.simulationInfo.inning <= 9 or home_team.score == away_team.score:
            game_log = game_log + self.simulate_inning()
            self.simulationInfo.incrementInning()
        if home_team.score > away_team.score:
            game_log = game_log + '{} wins {} to {}'.format(home_team.name, home_team.score, away_team.score)
        else:
            game_log = game_log + '{} wins {} to {}'.format(away_team.name, away_team.score, home_team.score)
        return game_log


    def simulate_inning(self):
        inning_log = 'Top {}\n'.format(self.simulationInfo.inning)
        inning_log = inning_log + FrameSimulator(self.simulationInfo).run()
        self.simulationInfo.incrementFrame()
        inning_log = inning_log + FrameSimulator(self.simulationInfo).run()
        self.simulationInfo.incrementFrame()
        return inning_log


class FrameSimulator:
    def __init__(self, simulationInfo: SimulationInfo, top=True):
        self.simulationInfo = simulationInfo
        self.top = top
        
    def run(self):
        outs = 0
        bases = Bases()
        frame_log = '{} {}\n'.format('Top' if self.simulationInfo.top else 'Bottom', self.simulationInfo.inning)

        while outs != 3 and not self.simulationInfo.walk_off():
            extra_text = ''

            result, bat_text = AtBatSimulator(self.simulationInfo).run()

            if result == 'field_out' or result == 'strikeout':
                outs += 1

            else:
                score, extra_text = bases.advance_runners(result, self.simulationInfo.offense().nextBatter())
                self.simulationInfo.offense().increment_score(score)

            frame_log = frame_log + bat_text + self.simulationInfo.offense().nextBatter().name + ' ' + result + '. ' + extra_text + '\n'
            self.simulationInfo.offense().next_idx()
        frame_log = frame_log + '{} - {} \n'.format(self.simulationInfo.home_team.score, self.simulationInfo.away_team.score)
        return frame_log

class AtBatSimulator:
    def __init__(self, simulationInfo: SimulationInfo):
        self.simulationInfo = simulationInfo

    def run(self):
        batter = self.simulationInfo.offense().nextBatter()
        pitcher = self.simulationInfo.defense().pitcher
        strikes = 0
        balls = 0
        extra_text = '{} up to bat.\n'.format(batter.name)
        pitch_num = 1

        while strikes < 3 and balls < 4:
            pitch = pitcher.pitch_types[random.multinomial(1, pitcher.pitch_rates).tolist().index(1)]

            batter_rates, batter_pitch_type = batter.get_pitch_probs(pitch)

            result = batter_pitch_type[random.multinomial(1, batter_rates).tolist().index(1)]

            extra_text += "{}. {}, {}".format(pitch_num, pitch, result)

            if result == 'ball':
                balls += 1
            elif result == 'called_strike' or result == 'swinging_strike':
                strikes += 1
            elif result == 'foul' and strikes < 2:
                strikes += 1
            elif result == 'hit_into_play':
                extra_text += '\n'
                return batter.ip_outcomes[random.multinomial(1, batter.ip_probs).tolist().index(1)], extra_text
            extra_text += " {} - {}\n".format(balls, strikes)
            pitch_num += 1
    
        if strikes == 3:
            return 'strikeout', extra_text
        elif balls == 4:
            return 'walk', extra_text



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
                extra_text = ' ' + self.first.name + ' advances.'
                self.second = self.first
                self.first = runner
            elif self.third is None:
                extra_text = ' ' + self.first.name + ' and ' + self.second.name + ' advance.'
                self.third = self.second
                self.second = self.first
                self.first = runner
            else:
                extra_text = ' ' + self.first.name + ' and ' + self.second.name + ' advance. ' + self.third.name + ' scores.\n '
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
            extra_text = extra_text + runner.name + ' scores.'
            self.third = None
            self.second = None
            self.first = None

        return score, extra_text

