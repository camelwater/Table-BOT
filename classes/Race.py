from typing import List, Tuple, Dict
from classes.Player import Player
from utils.Utils import PTS_MAP
#TODO: finish and implement

class Race:
    def __init__(self, raceID, track, cc, placements=list):
        self.raceID = raceID
        self.track = track
        self.cc = cc
        self.placements: List[Tuple] = placements #each placement is a 4-tuple (player, time, tr, delta)

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
        return {player[0]: player[1] for player in self.placements}

    def get_players(self):
        '''
        return all Players who were in the race (includes added players by ?dc)
        '''
        return [player[0] for player in self.placements]

    def get_placements(self):
        return self.placements
    
    def get_pos(self, player):
        '''
        return player's placement in race (index not actual placement)
        '''
        for pos, placement in enumerate(self.placements):
            if placement[0] == player:
                return pos
        return None
    
    def room_size(self):
        return len(self.placements)
    
    def add_placement(self, player):
        self.placements.append(player)
    
    def resize(self, size):
        self.placements = self.placements[:size]

    def change_placement(self, player, correct_pos):
        '''
        change a player's placement to `cor_pos` and shift up/down accordingly

        used for ?editrace
        '''
        orig_pos = self.get_pos(player)
        orig_pts = PTS_MAP[len(self.placements)][orig_pos]
        try:   
            cor_pts = PTS_MAP[len(self.placements)][int(correct_pos)]
        except KeyError:
            raise KeyError
        
        if orig_pos<correct_pos:
            aff = [self.placements[i][0] for i in range(orig_pos+1,correct_pos+1)]
        else:
            aff = [self.placements[i][0] for i in range(correct_pos,orig_pos)]
            
        aff_orig_pts = {}
        for a in aff:
            aff_orig_pts[a] = PTS_MAP[len(self.placements)][self.get_pos(a)]
        
        self.placements.insert(correct_pos, self.placements.pop(orig_pos))

        aff_new_pts = {}
        
        for a in aff:
            aff_new_pts[a] = PTS_MAP[len(self.placements)][self.get_pos(a)]
        
        return orig_pos, orig_pts, cor_pts, aff_orig_pts, aff_new_pts

