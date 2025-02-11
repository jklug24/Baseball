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
            "basic": BasicPitchSimulator,
            "count": CountBasedPitchSimulator
        }

        if simulationInfo.pitchSimulator not in simulations:
            raise ValueError(f"Unknown simulation type: {simulationInfo.pitchSimulator}")
        
        return simulations[simulationInfo.pitchSimulator](simulationInfo) 

class BasicPitchSimulator(PitchSimulator):
    def __init__(self, simulationInfo: SimulationInfo):
        self.simulationInfo = simulationInfo

    def run(self):
        batter = self.simulationInfo.offense().batter()
        pitcher = self.simulationInfo.defense().pitcher()

        pitch = pitcher.simulate_pitch_basic()
        result = batter.get_pitch_result(pitch)
        return pitch, result

class CountBasedPitchSimulator(PitchSimulator):
    def __init__(self, simulationInfo: SimulationInfo):
        self.simulationInfo = simulationInfo

    def run(self):
        batter = self.simulationInfo.offense().batter()
        pitcher = self.simulationInfo.defense().pitcher()

        pitch = pitcher.simulate_pitch(self.simulationInfo.count.balls, self.simulationInfo.count.strikes)
        result = batter.get_pitch_result(pitch, self.simulationInfo.count.balls, self.simulationInfo.count.strikes)
        return pitch, result