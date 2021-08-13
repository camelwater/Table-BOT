from typing import List, Tuple, Dict
from classes.Player import Player
#TODO: finish and implement

class Race:
    def __init__(self, raceID, track, cc, placements=None):
        self.raceID = raceID
        self.track = track
        self.cc = cc
        self.placements: List[Tuple] = placements

    def getTrack(self):
        return self.track
    def get_raceID(self):
        return self.raceID
    def getClass(self):
        return self.cc
    
    def get_finish_times(self) -> Dict[Player, str]:
        '''
        return dictionary mapping Player to their finish time for this race
        '''
        pass

    def change_placement(self, fc, orig_pos, cor_pos):
        '''
        change a players placement from { orig_pos } to { cor_pos }

        used for ?editrace
        '''
        pass
