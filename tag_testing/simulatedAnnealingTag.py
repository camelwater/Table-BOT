#simulated annealing (SA) approach to tag algorithm

import random as rand
from math import exp
import copy
import Utils
from itertools import chain
from functools import partial, reduce
from typing import Iterator, Tuple, List
from os.path import commonprefix
import time

def squeeze_names(sol: List[Tuple[str, List[Tuple[str, str]]]]) -> List[Tuple[str, List[str]]]:
    for i in range(len(sol)):
        sol[i][1] = list(map(lambda l: l[1], sol[i][1]))

    return sol

def ngram(seq: str, n: int) -> Iterator[str]:
    return (seq[i: i+n] for i in range(0, len(seq)-n+1))

def allngram(seq: str, minn=1, maxn=None) -> Iterator[str]:
    lengths = range(minn, maxn+1) if maxn else range(minn, len(seq))
    ngrams = map(partial(ngram, seq), lengths)
    return set(chain.from_iterable(ngrams))

def commonaffix(group: List[str]) -> Tuple[bool, str]:
    maxn = min(map(len, group))
    seqs_ngrams = map(partial(allngram, maxn=maxn), group)
    intersection = reduce(set.intersection, seqs_ngrams)
    try:
        all_presub = sorted(intersection, key=len, reverse=True)
        for sub in all_presub:
            if all([i.startswith(sub) or i.endswith(sub) for i in group]):
                return True, sub

        return False, ""
    except:
        return False, ""

class SimulatedAnnealing:
    def __init__(self, players: List[Tuple[str, str]], per_team: int, temperature = 1.0, alpha = 0.9, iterations = 425):
        self.T = temperature
        self.ALPHA = alpha
        self.ITERS = iterations

        self.num_per_team = per_team
        self.players = players

    
    def init_state(self) -> List[Tuple[str, List[Tuple[str, str]]]]:
        '''
        initialize random state
        '''
        rand.shuffle(self.players)
        chunks = list(Utils.chunks(self.players, self.num_per_team))
        for i in range(len(chunks)):
            chunks[i] = ["" , chunks[i]]
        return chunks
    
    
    def findTag(self, group: Tuple[str, Tuple[str, str]]) -> Tuple[str, str, str]:
        #check prefix
        pre = commonprefix(group)
        
        #check suffix
        suf = commonprefix(list(map(lambda l: l[::-1], group)))[::-1]
        
        #check mixed affixes
        mixed = ''
        is_pre_suf, to_det = commonaffix(group)
        if is_pre_suf:
            mixed = to_det
        
        return pre.strip(), suf.strip(), mixed.strip()

    def tags_eval(self, state: List[Tuple[str, List[Tuple[str, str]]]]) -> float:
        seen_tags = []
        energy = 0.0

        for group in state:
            possible = self.findTag(list(map(lambda l: l[0], group[1])))
            longest_tag = possible[0] if len(possible[0])>0 else max(possible, key=len)
            group[0] = longest_tag
            if longest_tag =="":
                energy+=69.0
                continue
            
            if longest_tag in seen_tags:
                energy+=7.5 
            else:
                seen_tags.append(longest_tag) 

            add_energy, is_mixed = self.affix_score(possible, longest_tag)
            energy+=add_energy

            if is_mixed:
                for player in group[1]:
                    if not player[0].startswith(longest_tag):
                        energy+=.5

        return energy


    def affix_score(self, possible: List[str], longest_tag: str) -> Tuple[float, bool]:
        if possible.index(longest_tag)!=0:
            if possible.index(longest_tag) == 1:
                return 2.5, False  
            elif possible.index(longest_tag) == 2:
                return 1.75, True

        return 0.0, False
    
    def E(self, state: List[Tuple[str, List[Tuple[str, str]]]]) -> int:
        '''
        return energy (cost) of solution
        '''
        energy = self.tags_eval(state)

        return energy

    def P(self, old_E: float, new_E: float) -> float:
        '''
        return acceptance probability
        '''
        if new_E < old_E:
            return 1.0

        return exp(-(new_E - old_E) / self.T)

    def n_swap(self, state: List[Tuple[str, List[Tuple[str, str]]]]) -> List[Tuple[str, List[Tuple[str, str]]]]:
        '''
        randomly swap two strings' groupings
        '''
        neighbor_state = copy.deepcopy(state)
        swap_from = rand.randint(0, len(neighbor_state)-1)
        swap_to = rand.randint(0, len(neighbor_state)-1)
        ch1 = rand.choice(neighbor_state[swap_from][1])
        ch2 = rand.choice(neighbor_state[swap_to][1])
        
        neighbor_state[swap_from][1].remove(ch1)
        neighbor_state[swap_from][1].append(ch2)
        neighbor_state[swap_to][1].remove(ch2)
        neighbor_state[swap_to][1].append(ch1)

        return neighbor_state

    def anneal(self) -> Tuple[List[Tuple[str, List[str]]], int]:
        '''
        return a solution
        '''
        curr_solution = self.init_state()
        curr_energy = self.E(curr_solution)

        for _n in range(self.ITERS):
            new_solution = self.n_swap(curr_solution)
            new_energy = self.E(new_solution)
            
            acceptance_prob = self.P(curr_energy, new_energy)
            # print("AP:", acceptance_prob)
            if acceptance_prob > rand.random():
                curr_solution, curr_energy = new_solution, new_energy
            
            self.T*=self.ALPHA
            print(f"ITERATION {_n+1} -> Energy: {curr_energy}")
            if curr_energy<=0:
                break
        
        return squeeze_names(curr_solution), curr_energy

if __name__ == "__main__":
    players = ['λρ Tom', 'A*', 'v¢ sauzule', 'saharave', 'MKW 4Beans', 'cadavreMK', 'coci loko', 'C', 'So[LLLLLL]', 'Zjazca', 'Z- stavros', 'vc Dane']
    players = ['AYA hello', '!!m&m?!', 'mong', 'MV math', 'pringle@MV', '@*', 'AYAYA', 'i need ZZZ', 'Z - stop', 'USA h', 'USA K', 'ABBA']

    players = list(map(lambda l: (Utils.sanitize_uni(l.strip()).lower(), l), players))
    tag_algo = SimulatedAnnealing(players, per_team = 2)
    start = time.time()
    sol, energy = tag_algo.anneal()
    print('\n----------------------------------\n')
    print(sol)
    print("ENERGY:",energy)
    print('\nalgo time:', time.time()-start)
