from dataclasses import dataclass, field
from collections import defaultdict
from typing import Tuple, List, Dict


@dataclass(unsafe_hash=True)
class Player:
    '''
    Player object

    fc, name, scores, edited_scores, flag, dc_pts, pens
    '''
    fc: str
    name: str = field(default="", hash=False)
    tag: str = field(default="", repr=False, hash=False)
    pens: int = field(default=0,hash=False, repr=False)
    scores: list = field(default_factory=list, hash=False, repr=False)
    edited_scores: Dict[int, int] = field(default_factory=lambda : defaultdict(int), hash=False, repr=False)
    flag_code: str = field(default="", hash=False, repr=False)
    dc_pts: list = field(default_factory=list, hash=False, repr=False)
    subs: List[Tuple['Player', int]] = field(default_factory=list, hash=False, repr=False) #players this player has subbed in for
    __races_played: int = field(default=None, hash=False, repr=False)

    def __eq__(self, o: object) -> bool:
        try:
            return o.getFC() == self.getFC()
        except:
            return False
    def getFC(self) -> str:
        return self.fc

    def getName(self) -> str:
        return self.name

    def get_full_name(self, num_races=0) -> str:
        '''
        get the player's name, with subs included (if applicable)
        '''
        if len(self.subs)==0:
            return self.getName()
        full_name = []
        sub_races = 0
        for sub in self.subs:
            for rec_sub in sub[0].getSubs():
                sub_races+=rec_sub[1]
            sub_races+=sub[1]
            full_name.append(f"{sub[0].get_full_name(-1)}({sub[1]})")
        
        full_name.append(f"{self.name}{self.__figure_out_num_races(num_races, sub_races)}")
        return '/'.join(full_name)
    
    def __figure_out_num_races(self, num_races, sub_races):
        if num_races == -1: #don't include num_races in full_name
            return ""
        this_races = (num_races-sub_races) if self.__races_played is None else self.__races_played
        return f"({this_races})"
    
    def get_score_str(self, by_race=False) -> str:
        scores_iter = self.scores[2] if by_race else self.scores[1]

        ret = ''
        for num, gp in enumerate(scores_iter):
            if by_race:
                if int(num/4)+1 in self.edited_scores:
                    if num/4 +1 in self.edited_scores:
                        ret+="{}".format(self.edited_scores[int(num/4)+1])
                    else:
                        ret+='0'
                    if num+1!=len(scores_iter):
                        ret+='|'
                    continue
            else:
                if num+1 in self.edited_scores:
                    ret+='{}'.format(self.edited_scores[num+1])
                    if num+1!=len(scores_iter):
                        ret+='|'
                    continue

            ret+="{}".format(gp)
            if num+1!=len(scores_iter):
                ret+='|'
        
        if self.pens>0:
            ret+='-{}'.format(self.pens)
        return ret

    def getFlag(self) -> str:
        return self.flag_code
    
    def getPens(self) -> int:
        return self.pens

    def getSubs(self) -> List[Tuple['Player', int]]:
        '''
        get the players who this player has subbed in for
        '''
        return self.subs
    
    def add_sub(self, out_player: 'Player', out_races_played: int):
        self.subs.append((out_player, out_races_played))
        self.combine_scores(out_player)
        self.combine_pens(out_player)
    
    def remove_last_sub(self, out_player: 'Player'):
        self.subs.pop(-1)
        self.scores[1] = [a-b for a, b in zip(self.scores[1], out_player.scores[1])]
        self.scores[2] = [a-b for a, b in zip(self.scores[2], out_player.scores[2])]
        self.scores[0] = self.scores[0] - out_player.scores[0] 
        self.pens -= out_player.getPens()

    
    def combine_scores(self, out_player: 'Player'):
        self.scores[0] += out_player.scores[0]
        self.scores[1] = [a+b for a, b in zip(self.scores[1], out_player.scores[1])]
        self.scores[2] = [a+b for a, b in zip(self.scores[2], out_player.scores[2])]

        for gp, score in out_player.edited_scores.items():
            if gp in self.edited_scores:
                self.edited_scores[gp] += score
            else:
                self.edited_scores[gp] = score

    def combine_pens(self, out_player: 'Player'):
        self.pens+=out_player.getPens()
    

# if __name__ == "__main__":
#     player1 = Player("1234-5678-9999", name="Ryan Zhao")
#     print(player1)
#     x = {player1: "poo"}
#     player1.name = "POO"
#     player1 = Player("1234-5678-9999", name="poo")
#     print(x)
#     print(player1.__dict__)