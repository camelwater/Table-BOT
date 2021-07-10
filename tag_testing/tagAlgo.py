#genetic algorithm method to get tags (performance too slow unfortunately)

from os.path import commonprefix
from functools import partial, reduce
from itertools import chain
from typing import Iterator
import time
import Utils
import random as rand
import copy
from collections import Counter

def ngram(seq: str, n: int) -> Iterator[str]:
    return (seq[i: i+n] for i in range(0, len(seq)-n+1))

def allngram(seq: str, minn=1, maxn=None) -> Iterator[str]:
    lengths = range(minn, maxn+1) if maxn else range(minn, len(seq))
    ngrams = map(partial(ngram, seq), lengths)
    return set(chain.from_iterable(ngrams))

def commonsubstring(group):
    maxn = min(map(len, group))
    seqs_ngrams = map(partial(allngram, maxn=maxn), group)
    intersection = reduce(set.intersection, seqs_ngrams)
    try:
        check_presub = sorted(intersection, key=len, reverse=True)
        presuf = False
        ret = ""
        for sub in check_presub:
            count = 0
            for i in group:
                if i.startswith(sub) or i.endswith(sub):
                    count+=1
            if count==len(group):
                presuf=True
                ret = sub
                break
        if presuf:
            return True, ret

        sub = max(intersection, key=len)
        if len(sub)<=1:
            sub = ""
    except:
        sub = ""

    return False, sub

def pre_sub_check(m):
    if not m: return ''
    
    s1 = min(m)
    s2 = max(m)
    for i, c in enumerate(s1):
        if c != s2[i]:
            return s1[:i]
    return s1


class TagAlgo:
    def __init__(self, player_list, num_teams, per_team, generations = 50, size = 100, mut_rate = 0.1, top_select = 10):
        self.size = size
        self.generations = generations
        self.mut_rate = mut_rate
        self.top_select = top_select
        self.players = player_list
        self.num_per_team = per_team
        self.num_teams = num_teams

        self.solution = []
        self.last_fits = []
        self.solution_fit = 0

    def solve(self):
        population = self.init_pop(self.size)

        elite, top_fit = [], 9999999999
        for g in range(self.generations):
            fit = [self.fitness(c) for c in population]
            elite, top_fit = self.select_elite(population, fit)
            
            self.solution = elite[0]
            self.solution_fit = top_fit
            self.last_fits.append(top_fit)
            print(f"generation {g+1} -> best fitness: {top_fit}")
            if top_fit == 0:
                break
            if self.last_fits.count(top_fit)>self.generations/2:
                break

            population = self.breed(elite)
        
        return self.solution

    def init_pop(self, n):
        pop = []
        for _ in range(n):
            pop.append(self.random_chromosome())
        
        return pop

    def select_elite(self, population, fitness):
        indx = sorted(range(len(population)), key=lambda k: fitness[k])
        return [population[i] for i in indx[:self.top_select]], fitness[indx[0]]
    
    def select_top_mut(self, mutations, fitness):
        indx = sorted(range(len(mutations)), key=lambda k: fitness[k])
        return mutations[indx[0]], fitness[indx[0]]

    def random_chromosome(self):
        rand.shuffle(self.players)
        chunks = list(Utils.chunks(self.players, self.num_per_team))
        for i in range(len(chunks)):
            chunks[i] = ["" , chunks[i]]
        #print(chunks)
        return chunks
    
    def breed_elite(self, population, elite_muts = 3):
        for i,c in enumerate(population):
            muts = []
            for _ in range(elite_muts):
                muts.append(self.mutate(copy.deepcopy(c)))
            mut_fits = [self.fitness(m) for m in muts]
            fittest_mut, mut_fit = self.select_top_mut(muts, mut_fits)
            if mut_fit>self.fitness(c):
                print("DOES IT EVER GO HERE")
                population[i] = fittest_mut
        
        return population

    def breed(self, elite):
        #elite = copy.deepcopy(elite)
        elite = self.breed_elite(elite)

        tick = time.time()
        for c in range(self.size - len(elite)):
            #p1 = rand.choice(elite)
            #p2 = rand.choice(elite)
            #child = self.crossover(p1, p2)
            child = self.mutate(copy.deepcopy(rand.choice(elite)))
            
            elite.append(child)

        #print("breeding time:", time.time()-tick)
        return elite

    
    def fitness(self,chromosome, final_check = False):
        tick = time.time()
        fitness = 0
        seen_tags = []
        # all_players = []
        # for i in chromosome:
        #     all_players+=i[1]
        # num_dup= len([k for k,v in Counter(all_players).items() if v>1])
        # fitness+=5000*num_dup

        # if set(all_players) != set(self.players):
        #     fitness+=5000

        for group in chromosome:
            possible = self.findTag(group[1])
            longest_tag = max(possible, key=len)
            group[0] = longest_tag
            if longest_tag =="":
                fitness+=5000
            else:
                if longest_tag in seen_tags:
                    fitness+=500
                    if final_check:
                        print(longest_tag, seen_tags)
                    
                seen_tags.append(longest_tag)  
                if possible.index(longest_tag)!=0:
                    if possible.index(longest_tag) == 1:
                        fitness+=150
                        
                    elif possible.index(longest_tag) == 2:
                        fitness += 1000
                        
            
            if len(group[1])!=self.num_per_team:
                fitness+=1000
            
            for player in group[1]:
                if not player.startswith(longest_tag):
                    fitness+=50
                other_fit = self.fit_other_better(group, player, chromosome)
                if other_fit[0]:
                    fitness+=250*other_fit[1]
                    if final_check:
                        print(other_fit)
        
        if len(chromosome)<self.num_teams:
            fitness+=1000
            
        if len(chromosome)>self.num_teams:
            fitness+=2500
        
        #print("fitness check:", time.time()-tick)
        return fitness
    
    def findTag(self,group):
        #check prefix
        pre = commonprefix(group)
        
        #check suffix
        #suf = commonprefix(list(map(lambda l: l[::-1], group)))
        #suf = pre_suf_check(group)
        
        #check substring
        sub = ""
        suf = ""
        is_pre_suf, to_det = commonsubstring(group)
        if is_pre_suf:
            if len(pre)==0:
                pre = to_det
            else:
                suf = to_det
        else:
            sub = to_det
        
        return [pre.strip()] + ([suf.strip(),sub.strip()] if pre.strip()=="" else [])
    
    def fit_other_better(self,cur_group, player, chromosome):
        cur_tag = cur_group[0]
        count = 0
        for group in chromosome:
            if group==cur_group: continue

            possible_fit = max(self.findTag([group[0], player]), key=len)
            if len(possible_fit)>len(cur_tag) and len(possible_fit)>= len(group[0]):
                count+=1
        
        return (True, count) if count>0 else (False, 0)

    def crossover(self, p1, p2):
        r = rand.random()
        use_cut = p1 if r<0.5 else p2
        cutoff = rand.randint(0, len(use_cut)-1)
        return p1[:cutoff] + p2[cutoff:]
    
    def mutate(self, chromosome):
        tick = time.perf_counter_ns()
        if rand.random()<self.mut_rate:
            swap_from = rand.randint(0, len(chromosome)-1)
            swap_to = rand.randint(0, len(chromosome)-1)
            
            ch1 = rand.choice(chromosome[swap_from][1])
            ch2 = rand.choice(chromosome[swap_to][1])
            
            chromosome[swap_from][1].remove(ch1)
            chromosome[swap_from][1].append(ch2)
            chromosome[swap_to][1].remove(ch2)
            chromosome[swap_to][1].append(ch1)
        
        #print("mut time:", time.perf_counter_ns()-tick)
        return chromosome


if __name__ == "__main__":

    #players = ["MV boob", "pringle@MV", "LTA", "LTA HELLO", "MVMVMV", "LTAX", "MV help", "val LTA", "poo LTA", "5headMV"]
    #players = list({'x#1':0, 'xxx':0, 'Ryan@X':0, '¢unt':0, 'coolio': 0, 'cool kid': 0, "GG EZ": 0, 'gas mob':0, "gassed up":0, "bb":0, "bro123":0, "batman":0}.keys())
    players = [('1', "x#1"), ('2', "xxx"), ('3', "ryan@x"), ('4', "¢unt"), ('5', "cool kid cool"), 
           ('6', "coolio"), ('7', "GG EZ"), ('8', "gassed up"), ('9', "gas mob"), ('10', "caya kanar"), ('11', "kaya yanar"), ('12', "yaka ranar")]
    players = [o[1] for o in players]
    players = list(map(lambda l: Utils.sanitize_uni(l.strip().lower()), players))
    tagalgo = TagAlgo(players, 4, 3)
    tick = time.time()
    final = tagalgo.solve()
    print('solution:', final)
    #print(tagalgo.fitness(final, final_check=True))
    
    print("algo time:", time.time()-tick)
    
    