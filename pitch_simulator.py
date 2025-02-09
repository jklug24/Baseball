from simulation_info import SimulationInfo
from numpy import random
from abc import ABC, abstractmethod

class PitchSimulator(ABC):
    
    @abstractmethod
    def run(self):
        pass

    @staticmethod
    def init(simulationInfo: SimulationInfo):
        simulations = {
            "basic": BasicPitchSimulator
        }

        if simulationInfo.pitchSimulator not in simulations:
            raise ValueError(f"Unknown simulation type: {simulationInfo.pitchSimulator}")
        
        return simulations[simulationInfo.pitchSimulator](simulationInfo) 

class BasicPitchSimulator(PitchSimulator):
    def __init__(self, simulationInfo: SimulationInfo):
        self.simulationInfo = simulationInfo

    def run(self):
        batter = self.simulationInfo.offense().nextBatter()
        pitcher = self.simulationInfo.defense().pitcher

        pitch = pitcher.pitch_types[random.multinomial(1, pitcher.pitch_rates).tolist().index(1)]
        batter_rates, batter_pitch_type = batter.get_pitch_probs(pitch)
        result = batter_pitch_type[random.multinomial(1, batter_rates).tolist().index(1)]

        return pitch, result