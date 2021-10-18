#simulated annealing (SA) approach to tag algorithm

import random as rand
from math import exp
import copy
import utils.tagUtils as tagUtils
import utils.Utils as Utils
from itertools import chain
from functools import partial, reduce
from typing import Iterator, Tuple, List
from os.path import commonprefix
import time

def squeeze_names(sol: List[Tuple[str, List[Tuple[str, str]]]]) -> List[Tuple[str, List[str]]]:
    for i in range(len(sol)):
        sol[i][1] = list(map(lambda l: l[1], sol[i][1]))

    return sol

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
        is_pre_suf, to_det = tagUtils.commonaffix(group)
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

    def failed_matches(self, tag, group):
        num_failed = 0
        for i in group:
            if i.startswith(tag) or i.endswith(tag):
                continue
            else:
                num_failed+=1
        return num_failed

    def E_check(self, state) -> float:
        seen_tags = []
        energy = 0.0

        for group in state:
            tag = group[0]

            energy+=abs(self.num_per_team-len(group[1]))/self.num_per_team * 25.0

            failed = self.failed_matches(tag, group[1])
            energy += failed*(100.0/self.num_per_team)
            if len(group[1])>1 and len(group[1])-failed <=1: continue
            
            if tag in seen_tags:
                energy+=5.0
                pass
            else:
                seen_tags.append(tag) 

            # add_energy, is_mixed = self.affix_score(tag, group)
            # energy+=add_energy
            for player in group[1]:
                if not player.startswith(tag):
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
        # avg_len=sum([len(i[0]) for i in state])/len(state)
        # energy-=avg_len*0.25

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
    # players = ['λρ Tom', 'A*', 'v¢ sauzule', 'saharave', 'MKW 4Beans', 'cadavreMK', 'coci loko', 'C', 'So[LLLLLL]', 'Zjazca', 'Z- stavros']
    # # players = ['AYA hello', '!!m&m?!', 'mong', 'MV math', 'pringle@MV', '@*', 'AYAYA', 'i need ZZZ', 'Z - stop', 'USA h', 'USA K', 'ABBA']
    # players = list({'x#1':0, 'xxx':0, 'Ryan@X':0, '¢ant':0, 'coolio': 0, 'cool kid cool': 0, "GG EZ": 0, 'gas mob':0, "gassed up":0, "kaya yanar":0, "yaya kanar":0, "yaka ranar":0}.keys())
    # players5 = list({'x#*********************ATSDUAJSDGHASDUYkajsdhalkjdh1':0, 'awasasasdasdasddsdadsddasdsadd':0, 'Ryadadadadddanasdasd@X':0, '¢unasdklajsdkajsdhalkjsddsasdasdt':0, 'stop asd;liajds;aosdij;alskdj;alsdkasdasdman': 0, 'coolasdasd kasdlkajsd;laksjdasdsadid cool': 0, "GG EaslkdjahsldkjadshlkajsdhlaksjdahsdasdZ": 0, 'gas moasdalkdsja;lsdb':0, "gasseasdasddsasasdd up":0, "kaya kljaxdlasdkasjdhalksdjhkjyanar":0, "yaya kasdaasdljsdhaosduy98712sdanar":0, "ya123123313233asdASDASDkqeeqweqwea ranar":0}.keys())
    # players6 = list({'helasasdndkzxdkzjxdnzddasdlo':0, 'stupasdalasdsdasda  asda ds adsdasid':0, 'asdl;lajsdhalksdjhlaskdjhaoisudyoaisduVA':0, 'banvannnnansdasdnansdnsdnasdndansdansdasndned':0, '09a8sd79as8d7a9s8d7a9sd87a9sd90':0, 'heaqoiu1p2oiu12981y49yoiusdasdll&*':0, 'whaasdasldajdsh;akjdhlaksjdhladsdsasdasddaat?':0, "a;lsdkja;sldkja;dlkaj;daaslkdja;lsdkjasd;l ad92y?":0, "λxasdasdasd12131311231asddade":0, 'Aaasd;lkasjd;alskdj;alskdjsdasdasAA':0, 'λp fraasdaskdkhalksdasdasdadud':0, 'AasdlkajdlaasdasdsdasdkdsjhlaksdBB':0}.keys())
    # players9 = list({'helasasdndkzxdkzjxdnzddasdlo':0, 'stupasdalasdsdasda  asda ds adsdasid':0, 'asdl;lajsdhalksdjhlaskdjhaoisudyoaisduVA':0, 'banvannnnansdasdnansdnsdnasdndansdansdasndned':0, '09a8sd79as8d7a9s8d7a9sd87a9sd90':0, 'heaqoiu1p2oiu12981y49yoiusdasdll&*':0, 'whaasdasldajdsh;akjdhlaksjdhladsdsasdasddaat?':0, "a;lsdkja;sldkja;dlkaj;daaslkdja;lsdkjasd;l ad92y?":0, "λxasdasdasd12131311231asddade":0, 'Aaasd;lkasjd;alskdj;alskdjsdasdasAA':0, 'λp fraasdaskdkhalksdasdasdadud':0, 'AasdlkajdlaasdasdsdasdkdsjhlaksdBB':0}.keys())
    # players7 = list({'he1273182376198237619283716932llo':0, 'heasdaklsdhalisduyaosidu123':0, 'borrowasalsdjhalsdkjalsdkjdasded time':0, 'bannasdasdaded':0, 'barasdasdrasda;klsdjakldsjhasd9o8yael':0, 
    #             'hellas1o2y92yoiuasdasdasdasdasddlkjasdlkajdsl&*':0, 'whaskdjhadsklbccmzbnx,mzat?':0, "wasdasdasdlkahsdjho?":0, "λasdasdkjalshdlakshdo9yous&*^&(*&^(*^&%9aksjdhaasdlkasd9qweyasdxe":0, 'AAasldkjadslkjadkajhdslkajdhlaksjdhalsdkjhasdA':0, 'λpasdasdas asd;alisdha;lksdhlakdsfraud':0, 'whasd;laskdhasdkjhaosiduyas9od8as9d8yapsd9ere?':0}.keys())
    # players8 = list({'helasdas1231y392y31o2dlo':0, 'stupasdaasasdasdasdddasddssdasid':0, 'asdl;lajsdhalksdjhlaskdjhaoisudyoaisduVA':0, 'banvannnnansdasdnansdnsdnasdndansdansdasndned':0, '09a8sd79as8d7a9s8d7a9sd87a9sd90':0, 'heaqoiu1p2oiu12981y49yoiusdasdll&*':0, 'whaasdasldajdsh;akjdhlaksjdhladsdsasdasddaat?':0, "whasdasdasdasdasdo?":0, "λxasdasdasdasddade":0, 'Aaasd;lkasjd;alskdj;alskdjsdasdasAA':0, 'λp fraasdahdsdo9oysda2eoiu oi u  lajsd lassdasdadud':0, 'Aasdlkasdlkj lkj asdadasdajdlakdsjhlaksdBB':0}.keys())
                
    # players4 = list({'pringleMVMMVMVMVMVMVMVMVMVMVMMVMV@MV':0,'5heaskdjhadslkajhdslakhdaiuyo876o876o8768asdadMV':0,'hellasjdhahksdjhalskdjhalsdkjhaldo LTA':0,'Lasdkjahdklajsdhaosd98odTAX':0,
    #         'jaja Lasdkjhdslaiusdyoasudyoasyasdya0sddTA':0,'stupasldasldkj;sdkaj;sdalkdsj;asldkid@LTA':0,'poop asdlakjdshlakjdshadssdMV':0,'MVMVMasdklahdsldssaadVMV':0,'LTA Vvalksjlpvalkjalksuqwealpo':0,"5 guys glajshdl asjh mom's spaghet":0}.keys())
    # players = list({'x#*(*&(&(*&(*&(*&akjsdhasd87asd6a8sd11':0, 'xxxXXXXXXXXXXXXXXXXXXXXXXXXXXXXX':0, 'Ryan@XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX':0, '¢uuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuunt':0, 'coolllllllllllkjkjkjkj123l12jk1jlio': 0, 'cool k12o381 102u 2oi1u 2id cool': 0, "GG EZZZZZZZZZZZZZZZZZZZZZZZZZ": 0, 'gas masd12o31uy2398   asdasadsadadsaob':0, "gassessssssssssssssssssd up":0, "kayajksdhasuoday9y098709a yanar":0, "yaya kasmasklaslkadsljladskjldsanar":0, "yaka kakaakakakdskdskasdadsjdsakranar":0}.keys())
    # players2 = ['asldkjadheaslkjdaskjdhlaksjdahdsllo', 'hasd123123213.kjadshaliskdjho876e123', 'borrowed timasd;laasdllndlksdhaposdu98q2ee', 'WAasd.kj.asdas.da.dsasd.asd.asd.a adshiaosda8dsX', 'basdkjasda  sda qe e j12oei1eahdlkajdsyao8ds7yarrel', 
    #             'A-asdlkadslkajdhlla192837192akjsdh1', 'whasdoqiouewiuy12o13y4183476184716894124at?', "WWW.Pasdalj;lsdhaldksjhlkaH.COM", "λxeasdlkahdsasdsd ds adaalsda98", 'Aasdlkaskldjahsd9a8y-2', 'λp frasdjlhalkdsjsasdlaksjdhadsd90ayaud', 'WOwowowowowowowowowowoowowowowowowW!!']
    # players3 = ['λρ ToOOOOOOOOOOOOOOoooooooooooom', 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA*', 'v¢ bvbvbvvvvvvvvvvvvvvvvvvvvvvvvvvvvvbvbvbvbvsauzule', 'sahasdjasdkjadshlkajsdhlakdsarave', 'MasdkjjdslakjdshlaksdjhKW 4Beans', 'cadasdasldhadjh9y01984y1944144avreMK', 'cocia;lskdhklajsdhasdo9y loko', 'Casdkjadhlajdasdasdhlkdsho9shap9sd8y', 'So[akjsdhakljdshaoisduyads8yLLLLLL]', 'Zjazasda,smdda   asddnadsasdasdca', 'Z- stavrosaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa']
    # players+=players2+players7+players8+players4+players5+players6+players3+players9*25
    # players = list(map(lambda l: (Utils.sanitize_uni(l.strip()).lower(), l), players))
    players = ['Mo taz', 'Mo Matt', 'Mo Jαggγ', 'Mo Sal', 'Mo Jos', 'Prιngle@MV', 'MV Noah', 'MV stripe', 'MV L-boaT', 'MV yax']
    players = list(map(lambda l: (Utils.sanitize_uni(l.strip()).lower(), l), players))

    tag_algo = SimulatedAnnealing(players, per_team = 2, iterations = len(players)*25)
    start = time.time()
    sol, energy = tag_algo.anneal()
    print('\n----------------------------------\n')
    print(sol)
    print("ENERGY:",energy)
    print('\nalgo time:', time.time()-start)
