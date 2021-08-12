from typing import List, Tuple
#TODO: finish and implement

class Race:
    def __init__(self, raceID, track, placements=None):
        self.raceID = raceID
        self.track = track
        self.placements: List[Tuple] = placements

    def getTrack(self):
        return self.track
    def get_raceID(self):
        return self.raceID

    def change_placement(self, fc, orig_pos, cor_pos):
        pass
