# -*- coding: utf-8 -*-
import utils.Utils as Utils
import utils.tagUtils as tagUtils
from collections import defaultdict
import copy
import random as rand
from utils.tagUtils import commonaffix
import tag_testing.simulatedAnnealingTag as simAnl
from typing import Dict, Tuple, List, Set
import cProfile

class Tag:
    def __init__(self, tag: str, dup_num: int=None):
        tag = tag.strip()
        if dup_num is not None:
            self.tag = (tag, dup_num)
        else:
            self.tag = tag
        self.eq_tag: str = str(self.tag).lower()
        self.sanitized_tag: str = tagUtils.sanitize_uni(self.get_tag()).lower()

    def get_tag(self) -> str:
        if isinstance(self.tag, tuple):
            return self.tag[0]
        return self.tag
    
    def get_full_tag(self):
        if isinstance(self.tag, tuple):
            return f"{self.tag[0]}-{self.tag[1]}"
        return self.tag
    
    def get_sanitized(self):
        return self.sanitized_tag
    
    def is_dup(self):
        return isinstance(self.tag, tuple)
    
    def __eq__(self, o: object) -> bool:
        try:
            return self.eq_tag == o.eq_tag
        except:
            return False

    def __str__(self):
        return self.tag
    
    def __repr__(self):
        return self.get_full_tag()
    
    def __hash__(self):
        return hash((self.__class__, self.eq_tag))

def count_pre_tags(tag: Tag, players):
    count= 0
    for p in players:
        if p[0].startswith(tag.get_sanitized()):
            count+=1
    return count

def rank_tags(tag: Tag, players, per_team) -> int:
    '''
    rank tags based on how likely they are to be correct tags.

    prefix tags first, then suffix tags, then mixed tags
    '''

    pre_count = count_pre_tags(tag, players)
    post_count = len(players)-pre_count
    if pre_count==per_team:
        return per_team+1

    if post_count==per_team:
        return per_team

    return pre_count

def clean_subsets(all_tags: Dict[Tag, Set[Tuple[str, str]]]):
    '''
    get rid of tags that are subset of other tags (subset of players and subset of tag name)
    '''
    #ex. if tag `P` has the same players as tag `Pro`, then get rid of `P`

    i = 0
    while i<len(all_tags):
        # print(all_tags.keys())
        item2 = list(all_tags.items())[i]
        tag2, players2 = item2[0], item2[1]
        for tag, players in all_tags.items():
            if tag.get_tag()!=tag2.get_tag() and players2.issubset(players) and (tag2.get_tag().lower()==tag.get_tag().lower() 
                or (len(tag2.get_tag())<len(tag.get_tag()) and (tag.get_tag().lower().startswith(tag2.get_tag().lower()) or tag.get_tag().lower().endswith(tag2.get_tag().lower())))):
                    all_tags.pop(tag2)
                    i-=1
                    break
                
        i+=1

def overlaps(p: Tuple[str, str], tag: Tag, all_tags: Dict[str, Set[Tuple[str, str]]], per_team: int):
    num_overlaps_strict = 0
    num_overlaps_lenient = 0
    for x, x_players in all_tags.items():
        if x==tag: continue
        if p in x_players and len(x_players)>=per_team:
            if len(x_players)==per_team:
                num_overlaps_lenient+=1
            num_overlaps_strict+=1
    return num_overlaps_strict, num_overlaps_lenient

def check_isolated_overlaps(players: Set[Tuple[str, str]], tag: Tag, all_tags: Dict[Tag, Set[Tuple[str, str]]], per_team: int):
    def eval_tag_overlaps(comp_tag):
        return sum([overlaps(p, comp_tag, all_tags, per_team)[0] for p in all_tags[comp_tag]])

    if len(players)<=per_team: return
    
    count_overlaps = [(i, overlaps(i, tag, all_tags, per_team)) for i in players]
    count_overlaps = sorted(count_overlaps, key = lambda l: (1 if l[1][0]==1 else 0,
                                                        1 if l[1][1]==1 else 0, l[1]), reverse=True)
    
    for player, _ in count_overlaps:
        for comp_tag, comp_players in all_tags.items():
            if tag == comp_tag or player not in comp_players: continue
            if eval_tag_overlaps(comp_tag) <= len(players) // 2:
                all_tags[tag].discard(player)
                if len(all_tags[tag]) <=per_team:
                    return

def check_overlaps(players: Set[Tuple[str, str]], tag: Tag, all_tags: Dict[Tag, Set[Tuple[str, str]]], per_team: int):
    '''
    check if players in overflowing tags either:

    1. fit into a better sized team (correct number of players)

    2. fit into a better tagged team (location of another tag is better than current)
    '''
    def more_prefix(players, tag):
        return count_pre_tags(tag, players) >= len(players)//2
    def more_suffix(players, tag):
        return count_pre_tags(tag, players) < len(players)//2

    if len(players)<=per_team: return

    count_overlaps = [(i, overlaps(i, tag, all_tags, per_team)) for i in players]
    # non_overlapped = sorted([i for i in count_overlaps if i[1][1]==0], key=lambda l: l[1], reverse=True)
    strict_non_overlapped = [i[0] for i in count_overlaps if i[1][0]==0]
    
    if len(strict_non_overlapped)>=per_team:
        for i in copy.copy(players):
            if i not in strict_non_overlapped:
                all_tags[tag].discard(i)
        return

    iter = sorted(list(players), key=lambda l: (1 if overlaps(l, tag, all_tags, per_team)[1]==1 else 0, 1 if overlaps(l, tag, all_tags, per_team)[0]==1 else 0, 0 if l[0].startswith(tag.get_sanitized()) else 1))

    for comp_tag, tag_p in all_tags.items():
        if comp_tag == tag:
            continue

        for p in iter[::-1]:
            if p not in tag_p or len(tag_p)<per_team: 
                continue

            if len(comp_tag.get_tag())>len(tag.get_tag()) and (comp_tag.get_sanitized().startswith(tag.get_sanitized())
                                        or comp_tag.get_sanitized().endswith(tag.get_sanitized())):
                all_tags[tag].discard(p)
                iter.remove(p)
                if len(all_tags[tag])<=per_team:
                    return

            # elif not len(non_overlapped)<per_team and all([True if overlaps(i, tag, all_tags, per_team)==1 else False for i in tag_p]):
            #     all_tags[tag].discard(p)
            #     iter.remove(p)
                # if len(all_tags[tag])<=per_team:
                #         return

            elif p[0].startswith(comp_tag.get_sanitized()) and not p[0].startswith(tag.get_sanitized()) \
                    and more_prefix(all_tags[comp_tag], comp_tag) and not more_suffix(all_tags[tag], tag):
                if overlaps(p, tag, all_tags, per_team)[0]==1:
                    all_tags[tag].discard(p)
                    iter.remove(p)
                        
                elif len(tag_p)==per_team and len(all_tags[tag])>per_team:
                    all_tags[tag].discard(p)
                    iter.remove(p)
                    # if len(all_tags[tag])<=per_team:
                    #     return 
                if len(all_tags[tag])<=per_team:
                    return                             

            elif p[0].endswith(comp_tag.get_sanitized()) and not p[0].endswith(tag.get_sanitized()) \
                    and more_suffix(all_tags[comp_tag], comp_tag) and not more_prefix(all_tags[tag], tag):
                if overlaps(p, tag, all_tags, per_team)[0]==1:
                    all_tags[tag].discard(p)
                    iter.remove(p)
                elif len(tag_p)==per_team and len(all_tags[tag])>per_team:
                    all_tags[tag].discard(p)
                    iter.remove(p)
                if len(all_tags[tag])<=per_team:
                    return


def split_by_actual(players: Set[Tuple[str, str]], tag: Tag, per_team: int, all_tags: Dict[Tag, Set[Tuple[str, str]]]):
    '''
    split overflowing tags which have players who have different actual tag values and are supposed to have a different tag.
    '''
    #ex. 2 players currently in tag `A` are actually tag `λ`

    def actual_matches(p, diff_players):
        return len([1 for i in diff_players if tagUtils.common_actual_affix(p.lower(), i[1].lower())])

    diff_actual_players = []
    for p in players:
        p_a = p[1].strip().lower()
        if not (p_a.startswith(tag.get_full_tag().lower()) or p_a.endswith(tag.get_full_tag().lower())):
            diff_actual_players.append(p)
    
    if per_team<=len(diff_actual_players)<len(players) : # and len(players)-len(diff_actual_players)>=per_team
        if len(diff_actual_players)>per_team:
            diff_actual_players = sorted(diff_actual_players, key = lambda l: actual_matches(l[1], diff_actual_players), reverse=True)
            diff_actual_players = diff_actual_players[:per_team]
        temp_diff_players = list(map(lambda l: l[1], diff_actual_players))

        actual_tag = tagUtils.sanitize_tag_uni(commonaffix(temp_diff_players)).strip()
        if actual_tag=="":
            return
        for t in all_tags.keys():
            for i in diff_actual_players:
                all_tags[t].discard(i)

        all_tags[Tag(actual_tag)] = set(diff_actual_players)
    
        
def split_chunks(players: Set[Tuple[str, str]], tag: Tag, per_team: int, all_tags: Dict[Tag, Set[Tuple[str, str]]]):
    '''
    split tags with too many people into even chunks.

    prefix players and suffix players will try to be kept in their respective groupings
    '''
    # if tag has too many people at this point, then it is very likely that
    # there are duplicate tags, meaning more than one team has the same tag (obviously shouldn't happen and isn't allowed)

    def post_id(p):
        p = p[0]
        if p.startswith(tag.get_sanitized()):
            return 1
        return 0

    if len(players)<=per_team:
        return

    pre = []
    post = []
    mash = []
    # indx = (int(len(players)/per_team)-1)*per_team
    indx = per_team
    players = sorted(list(players), key=lambda l: (overlaps(l, tag, all_tags, per_team),post_id(l)), reverse=True)
    if indx == 0: indx = 1
    if len(players[indx:])<per_team:
        mash = players[indx:]
        post_chunks = list()
        pre_chunks = list()
        all_tags[tag] = set(players[:indx])
    else:
        for p in players[indx:]:
            if p[0].startswith(tag.get_sanitized()):
                pre.append(p)
            else:
                post.append(p)
        
        all_tags[tag] = set(players[:indx])
        while len(pre)%per_team!=0:
            mash.append(pre.pop(-1))
        while len(post)%per_team!=0:
            mash.append(post.pop(-1))
        pre_chunks = list(Utils.chunks(pre, per_team))
        post_chunks = list(Utils.chunks(post, per_team))

    for g in pre_chunks+post_chunks+[mash]:
        if len(g)==0: continue
        a = 1
        temp = tag
        while temp in all_tags:
            temp = Tag(tag.get_tag(), a)
            a+=1
        all_tags[temp] = set(g)


def handle_undetermined(teams: Dict[Tag, List[str]], un_players: List[Tuple[str, str]], per_team: int):
    '''
    try to tag players whose tags couldn't be determined.

    first, fill tags that aren't full. then, if necessary, create random groupings.
    '''
    def rand_split():
        split = list(Utils.chunks(un_players, per_team))
        for r_team in split:
            for ind,player in enumerate(r_team):
                try:
                    temp = check = Tag(player[0][0].upper()) #use first valid character from name as new tag
                except IndexError: #player has no valid characters in their name, so just use their first character
                    if ind+1<len(r_team):
                        continue
                    temp = check = Tag(player[1][0])

                d = 1
                while check in teams:
                    check = Tag(temp.get_tag(), d)
                    d+=1
                teams[check] = r_team
                break
                
    is_all_filled = False if len(list(teams.values())[-1])<per_team else True

    if not is_all_filled:
        for tag in list(teams.items())[::-1]:
            if not len(tag[1])<per_team:
                break
            while len(tag[1])<per_team and len(un_players)>0:
                tag[1].append(un_players.pop(0))
            if len(un_players)==0:
                return
        if len(un_players)>0:
            rand_split()
    else:
        rand_split()   

def assert_correct(teams, un_players, per_team, num_teams, num_teams_supposed):
    '''
    fix tags which have more players than allowed.
    '''
    found_num_teams = len(teams)
    corrupt_tags = []
    
    for tag, players in teams.items():
        if len(players)>per_team:
            corrupt_tags.append(tag)

    if (found_num_teams==num_teams_supposed or (found_num_teams<num_teams_supposed and \
        len(un_players)>=(per_team*(num_teams_supposed - found_num_teams)))) and len(corrupt_tags)==0:
        return
    if found_num_teams<=num_teams_supposed and len(corrupt_tags)==0:
        return

    if len(corrupt_tags) == 0:
        while len(teams)>num_teams_supposed:
            for tag, players in teams.items():
                if len(players)!=per_team:
                    popped = teams.pop(tag)
                    un_players.extend(popped)
                    break
    
    for tag in corrupt_tags:
        tag_players = teams[tag]
        while len(tag_players)>per_team:
            del_player = rand.choice(tag_players)
            if del_player not in un_players:
                un_players.append(del_player)
            teams[tag].remove(del_player)


def select_top(all_tags: Dict[Tag, Set[Tuple[str, str]]], per_team: int, num_teams: int, num_teams_supposed: int, teams: Dict[Tag, List[str]], players: List[Tuple[str, str]]):
    '''
    choose best combination of tags.

    first, resolve tag conflicts. then, go through tags and finalize top-ranked tags.
    '''
    all_tags = dict(sorted(all_tags.items(), key=lambda l: len(l[1]), reverse=True))
    # all_tags = dict(sorted(all_tags.items(), key=lambda l: len(l[0].get_tag()), reverse=True))
    for tag in copy.deepcopy(all_tags).keys():
        tag_players = all_tags[tag]
        if len(tag_players) <= per_team: continue

        split_by_actual(tag_players, tag, per_team, all_tags)
        check_overlaps(tag_players, tag, all_tags, per_team)
        check_isolated_overlaps(tag_players, tag, all_tags, per_team) 
        split_chunks(tag_players, tag, per_team, all_tags)

        if len(tag_players)<=per_team: continue  
        #just randomly get rid of someone at this point - either the format is wrong or the players' tags are bad (and impossible to get completely correct)
        tag_players = sorted(tag_players, key = lambda p: overlaps(p, tag, all_tags, per_team))
        while len(tag_players)>per_team: 
            tag_players.pop()
            
    for _ in range(num_teams_supposed):
        for x in list(all_tags.items())[::-1]:
            new_set = set([i for i in x[1] if i in players])
            if len(new_set)==0: 
                all_tags.pop(x[0])
            else:
                all_tags[x[0]] = new_set
        if len(all_tags)==0:
            break
        all_tags = dict(sorted(all_tags.items(), key=lambda tag: (len(tag[1]), rank_tags(tag[0],tag[1], per_team), len(tag[0].get_tag())), reverse=True))
        top_key = list(all_tags.keys())[0]
        teams[top_key] = list(all_tags[top_key])
        for p in all_tags[top_key]:
            players.remove(p)

        all_tags.pop(top_key)

def squeeze_player_names(teams: Dict[Tag, List[str]]):
    final_teams = {}
    for tag, p in teams.items():
        final_teams[tag.get_full_tag()] = list(map(lambda l: l[1], p))

    return final_teams

def fix_tags(teams: Dict[Tag, List[str]]):
    '''
    fix duplicate tag names conflicts.
    '''
    def dup_tag(t: Tag, add_self=False):
        count = 0
        for i in list(teams.keys()):
            i = i.get_full_tag()
            if i.strip().lower() == t.get_full_tag().strip().lower(): count+=1
        if add_self: count+=1 
        return count>1

    for tag in list(teams.keys())[::-1]:
        if not tag.is_dup() and dup_tag(tag):
            temp = tag
            a = 1
            while temp in teams:
                temp = Tag(tag.get_tag(), a)
                a+=1
            teams[temp] = teams.pop(tag)
        elif tag.is_dup():
            if not dup_tag(tag, add_self=True):
                teams[Tag(tag.get_tag())] = teams.pop(tag)
            # else:
            #     # n_tag = tag[0]+'-'+str(tag[1])
            #     teams[Tag(tag.tag)] = teams.pop(tag)
  
    
def get_all_tags(player: str) -> Set[str]:
    '''
    get every single tag combination for a player
    '''
    tags = set()
    san_name, name = tagUtils.get_player_tag(player, both=True)
    # for i in range(len(max(san_name, name, key=len))):
    for i in range(len(san_name)):
        tags.add(san_name[0:i+1])
        tags.add(san_name[-i-1:])
        # tags.add(san_name[0:i+1])
        # tags.add(san_name[-i-1:])
    return tags

def find_possible_tags(players: List[Tuple[str, str]]) -> Dict[Tag, Set[Tuple[str, str]]]:
    '''
    find all possible tag matches - any tag that has 2 or more matching players.
    '''
    all_tags = defaultdict(set)
    for player in players:
        player_tags = get_all_tags(player[1])
        for tag in player_tags:
            if len(tag)==1:
                tag = tag.upper()
            all_tags[Tag(tag)].add(player)
    all_tags = {k:v for k, v in all_tags.items() if len(v)>1}
    return all_tags

def convert_tags(all_tag_matches):
    for tag in list(all_tag_matches.keys())[::-1]:
        all_tag_matches[Tag(tag)] = all_tag_matches.pop(tag)

def tag_algo(o_players: List[str], per_team: int, num_teams: int) -> Dict[str, List[str]]:
    '''
    split players into { num_teams } teams of { per_team } based on their tags.
    '''

    formats = None
    target = False
    if isinstance(per_team, int):
        formats = [per_team]
        target = True
    else:
        if per_team is None:
            formats = [6,5,4,3,2]
        else:
            formats = per_team
    
        format_results = dict()

    for ind, p in enumerate(o_players):
            sanitized = tagUtils.sanitize_uni(p.strip())
            o_players[ind] = (sanitized.lower(), p) #, sanitized)

    for format in formats:
        teams = dict()
        players = copy.copy(o_players)
        supposed_teams = len(players) // format

        all_tag_matches = find_possible_tags(players)

        clean_subsets(all_tag_matches) #get rid of tags that have overlapping players (shorter tags with subset of players)
        select_top(all_tag_matches, format, num_teams, supposed_teams, teams, players) #select best tags that meet requirements
        # assert_correct(teams, players, per_team, num_teams, supposed_teams) #contingency in case of rare errors
        fix_tags(teams)

        if len(players)>0: #players who weren't tagged
            teams = dict(sorted(teams.items(), key=lambda l: len(l[1]), reverse=True))
            handle_undetermined(teams, players, format)
        
        teams = squeeze_player_names(teams)
        if target:
            return None, (teams, calc_cost(teams, format))
        bonus = 0
        if format == 5 and len(o_players) == 10:
            bonus = -2.5
        format_results[format] = (teams, max(calc_cost(teams, format)+bonus, 0))

    return select_best_format(format_results)

def select_best_format(results):
    for format, res in results.items():
        print(f"{format}v{format}: {res[1]}")
    print()
    return min(results.items(), key = lambda f: f[1][1])

def get_test_case(large = False):
    """
    return a test case for the tag algorithm (manual).

    `large` is for large performance testing - more than what is usually required of the algorithm.
    """
    if large:
        players5 = list({'x#*********************ATSDUAJSDGHASDUYkajsdhalkjdh1':0, 'awasasasdasdasddsdadsddasdsadd':0, 'Ryadadadadddanasdasd@X':0, '¢unasdklajsdkajsdhalkjsddsasdasdt':0, 'stop asd;liajds;aosdij;alskdj;alsdkasdasdman': 0, 'coolasdasd kasdlkajsd;laksjdasdsadid cool': 0, "GG EaslkdjahsldkjadshlkajsdhlaksjdahsdasdZ": 0, 'gas moasdalkdsja;lsdb':0, "gasseasdasddsasasdd up":0, "kaya kljaxdlasdkasjdhalksdjhkjyanar":0, "yaya kasdaasdljsdhaosduy98712sdanar":0, "ya123123313233asdASDASDkqeeqweqwea ranar":0}.keys())
        players6 = list({'helasasdndkzxdkzjxdnzddasdlo':0, 'stupasdalasdsdasda  asda ds adsdasid':0, 'asdl;lajsdhalksdjhlaskdjhaoisudyoaisduVA':0, 'banvannnnansdasdnansdnsdnasdndansdansdasndned':0, '09a8sd79as8d7a9s8d7a9sd87a9sd90':0, 'heaqoiu1p2oiu12981y49yoiusdasdll&*':0, 'whaasdasldajdsh;akjdhlaksjdhladsdsasdasddaat?':0, "a;lsdkja;sldkja;dlkaj;daaslkdja;lsdkjasd;l ad92y?":0, "λxasdasdasd12131311231asddade":0, 'Aaasd;lkasjd;alskdj;alskdjsdasdasAA':0, 'λp fraasdaskdkhalksdasdasdadud':0, 'AasdlkajdlaasdasdsdasdkdsjhlaksdBB':0}.keys())
        players9 = list({'helasasdndkzxdkzjxdnzddasdlo':0, 'stupasdalasdsdasda  asda ds adsdasid':0, 'asdl;lajsdhalksdjhlaskdjhaoisudyoaisduVA':0, 'banvannnnansdasdnansdnsdnasdndansdansdasndned':0, '09a8sd79as8d7a9s8d7a9sd87a9sd90':0, 'heaqoiu1p2oiu12981y49yoiusdasdll&*':0, 'whaasdasldajdsh;akjdhlaksjdhladsdsasdasddaat?':0, "a;lsdkja;sldkja;dlkaj;daaslkdja;lsdkjasd;l ad92y?":0, "λxasdasdasd12131311231asddade":0, 'Aaasd;lkasjd;alskdj;alskdjsdasdasAA':0, 'λp fraasdaskdkhalksdasdasdadud':0, 'AasdlkajdlaasdasdsdasdkdsjhlaksdBB':0}.keys())
        players7 = list({'he1273182376198237619283716932llo':0, 'heasdaklsdhalisduyaosidu123':0, 'borrowasalsdjhalsdkjalsdkjdasded time':0, 'bannasdasdaded':0, 'barasdasdrasda;klsdjakldsjhasd9o8yael':0, 
                    'hellas1o2y92yoiuasdasdasdasdasddlkjasdlkajdsl&*':0, 'whaskdjhadsklbccmzbnx,mzat?':0, "wasdasdasdlkahsdjho?":0, "λasdasdkjalshdlakshdo9yous&*^&(*&^(*^&%9aksjdhaasdlkasd9qweyasdxe":0, 'AAasldkjadslkjadkajhdslkajdhlaksjdhalsdkjhasdA':0, 'λpasdasdas asd;alisdha;lksdhlakdsfraud':0, 'whasd;laskdhasdkjhaosiduyas9od8as9d8yapsd9ere?':0}.keys())
        players8 = list({'helasdas1231y392y31o2dlo':0, 'stupasdaasasdasdasdddasddssdasid':0, 'asdl;lajsdhalksdjhlaskdjhaoisudyoaisduVA':0, 'banvannnnansdasdnansdnsdnasdndansdansdasndned':0, '09a8sd79as8d7a9s8d7a9sd87a9sd90':0, 'heaqoiu1p2oiu12981y49yoiusdasdll&*':0, 'whaasdasldajdsh;akjdhlaksjdhladsdsasdasddaat?':0, "whasdasdasdasdasdo?":0, "λxasdasdasdasddade":0, 'Aaasd;lkasjd;alskdj;alskdjsdasdasAA':0, 'λp fraasdahdsdo9oysda2eoiu oi u  lajsd lassdasdadud':0, 'Aasdlkasdlkj lkj asdadasdajdlakdsjhlaksdBB':0}.keys())
                    
        players4 = list({'pringleMVMMVMVMVMVMVMVMVMVMVMMVMV@MV':0,'5heaskdjhadslkajhdslakhdaiuyo876o876o8768asdadMV':0,'hellasjdhahksdjhalskdjhalsdkjhaldo LTA':0,'Lasdkjahdklajsdhaosd98odTAX':0,
                'jaja Lasdkjhdslaiusdyoasudyoasyasdya0sddTA':0,'stupasldasldkj;sdkaj;sdalkdsj;asldkid@LTA':0,'poop asdlakjdshlakjdshadssdMV':0,'MVMVMasdklahdsldssaadVMV':0,'LTA Vvalksjlpvalkjalksuqwealpo':0,"5 guys glajshdl asjh mom's spaghet":0}.keys())
        players = list({'x#*(*&(&(*&(*&(*&akjsdhasd87asd6a8sd11':0, 'xxxXXXXXXXXXXXXXXXXXXXXXXXXXXXXX':0, 'Ryan@XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX':0, '¢uuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuunt':0, 'coolllllllllllkjkjkjkj123l12jk1jlio': 0, 'cool k12o381 102u 2oi1u 2id cool': 0, "GG EZZZZZZZZZZZZZZZZZZZZZZZZZ": 0, 'gas masd12o31uy2398   asdasadsadadsaob':0, "gassessssssssssssssssssd up":0, "kayajksdhasuoday9y098709a yanar":0, "yaya kasmasklaslkadsljladskjldsanar":0, "yaka kakaakakakdskdskasdadsjdsakranar":0}.keys())
        players2 = ['asldkjadheaslkjdaskjdhlaksjdahdsllo', 'hasd123123213.kjadshaliskdjho876e123', 'borrowed timasd;laasdllndlksdhaposdu98q2ee', 'WAasd.kj.asdas.da.dsasd.asd.asd.a adshiaosda8dsX', 'basdkjasda  sda qe e j12oei1eahdlkajdsyao8ds7yarrel', 
                    'A-asdlkadslkajdhlla192837192akjsdh1', 'whasdoqiouewiuy12o13y4183476184716894124at?', "WWW.Pasdalj;lsdhaldksjhlkaH.COM", "λxeasdlkahdsasdsd ds adaalsda98", 'Aasdlkaskldjahsd9a8y-2', 'λp frasdjlhalkdsjsasdlaksjdhadsd90ayaud', 'WOwowowowowowowowowowoowowowowowowW!!']
        players3 = ['λρ ToOOOOOOOOOOOOOOoooooooooooom', 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA*', 'v¢ bvbvbvvvvvvvvvvvvvvvvvvvvvvvvvvvvvbvbvbvbvsauzule', 'sahasdjasdkjadshlkajsdhlakdsarave', 'MasdkjjdslakjdshlaksdjhKW 4Beans', 'cadasdasldhadjh9y01984y1944144avreMK', 'cocia;lskdhklajsdhasdo9y loko', 'Casdkjadhlajdasdasdhlkdsho9shap9sd8y', 'So[akjsdhakljdshaoisduyads8yLLLLLL]', 'Zjazasda,smdda   asddnadsasdasdca', 'Z- stavrosaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa']
        players+=players2+players7+players8+players4+players5+players6+players3+players9*44

        seen = []
        lengths = []
        for ind,i in enumerate(players):
            if i not in seen:
                seen.append(i)
                lengths.append(len(i))
            else:
                temp = i
                a =1
                while temp in seen:
                    temp = f'{i}-{a}'
                    a+=1
                seen.append(temp)
                players[ind] = temp
                lengths.append(len(temp))
        
    else:
        players = [
        list({'x#1':0, 'xxx':0, 'Ryan@X':0, '¢ant':0, 'coolio': 0, 'cool kid cool': 0, "GG EZ": 0, 'gas mob':0, "gassed up":0, "kaya yanar":0, "yaya kanar":0, "yaka ranar":0}.keys()),
        ['hello', 'he123', 'borrowed time', 'WAX', 'barrel', 
                    'A-1', 'what?', "WWW.PH.COM", "BWλHλHλ", 'Ã', 'λp fraud', 'WOW!!'],
        ['Mo taz', 'Mo Matt', 'Mo Jαggγ', 'Mo Sal', 'Mo Jos', 'Prιngle@MV', 'MV Noah', 'MV stripe', 'MV L-boaT', 'MV yax'],
        ['λρ Tom', 'A*', 'v¢ sauzule', 'saharave', 'MKW 4Beans', 'cadavreMK', 'coci loko', 'C', 'So[LLLLLL]', 'Zjazca', 'Z- stavros'],
        ['AYA hello', '!!m&m?!', 'mong', 'MV math', 'pringle@MV', '@*', 'AYAYA', 'i need ZZZ', 'Z - stop', 'USA H', 'USA K', 'ABBA'],
        ['Æ big', 'PP hi', 'PP powerplant', 'Æ oo', 'PP gerp', 'Æ hello', 'shuyx@Æ', 'PP POWERGRID', 'big PP', 'Æ vamp'],
        ['Ac☆Mirymeg', 'Z☆', 'WC top 2', 'Player', 'MonkeyTime', 'z おk', 'Ac Stubbz', 'Hosseini','MΞ☆Mγτh','Hτ chξΣ◇€£', 'Player', 'WC △△◎◎♪☆○'],
        ['X◇山周回のれみ','CRYLIXDAWN', 'さぼX', 'DG★mila*', 'C☆Latent', 'Player-1','Dovi', 'らいよんのRemi', 'にしのだいせんせい',
                    'Player-2', 'ライオンのRemi', 'だいせんせい', 'ωΖ hALr', '[ωZ] PogU', "Anairis", "A L I C E"],
        ['Anairis' ,'A L I C E', 'B frozen', 'Bayview', 'Get Candy△', 'GANK/FF@15', "m shix", "m¢ jipper", "Player", "Prayer", "Se Revan", 'sussy baka'],
        ["A☆", "A◇KA", "God's Λν", "Λν Nn", "◇B", "BSHU neK", "Dz FROZONE", "Dz frozone", "Fλ μ's", "F8l", "PlayeR", "Player"]
    ]

    return players, (lengths if large else None)

def calc_cost(teams, per_team):
    L = []
    for tag, p in teams.items():
        if tag.find('-')>=len(tag)//2 and tag[tag.find('-')+1:].isnumeric():
            tag = tag[:tag.find('-')]
        L.append([tagUtils.sanitize_uni(tag.strip()).lower(), list(map(lambda l: (tagUtils.sanitize_uni(l.strip()).lower()), p))])
    cost_check = simAnl.SimulatedAnnealing(L, per_team)
    return cost_check.E_check(L)

def exec_test(players, per_team, num_teams, lengths = None, large = False, batch=False):
    '''
    execute a singular test on one player set.
    '''
    rand.shuffle(players)

    if large:
        tick = time.perf_counter()
        prof = cProfile.Profile()
        prof.enable()
        format, (teams, cost) = tag_algo(players, per_team=per_team, num_teams=num_teams)
        prof.disable()
        prof.print_stats(sort='time')
        # print(dict(sorted(t.items(), key = lambda l: l[0])))
        print("\nPERFORMANCE: {:.7f}".format(time.perf_counter()-tick))
        print(f"avg length: {sum(lengths)/len(lengths):.3f}")
        print('# strings:', len(lengths))
        
        print("cost:", calc_cost(teams, per_team))

    elif not large and not batch: #select == True
        tick = time.perf_counter()
        format, (teams, cost) = tag_algo(players, per_team=per_team, num_teams=num_teams)
        print(teams)
        print("\nPERFORMANCE: {:.10f}".format(time.perf_counter()-tick))
        
        print("cost:", cost)
    
    elif not large and batch:
        tick = time.perf_counter()
        format, (teams, cost) = tag_algo(players, per_team=per_team, num_teams = num_teams)
        perf = time.perf_counter()-tick

        return calc_cost(teams, per_team), perf

def batch_test(players, batch_num=100):
    '''
    test each set `batch_num` times
    '''
    PASSES = [71.25, 17.25, 9.75, 3.0, 4.5, 6.0, 0.5, 7.25, 0.0, 2.25]
    TEAMS = [(2,6),(2,6),(2,6),(2,6),(2,6),(2,6),(2,6),(2,6),(2,6),(2,6)]
    PERF_PASS = 0.005
    results = list()
    for ind, set in enumerate(range(len(players))):
        set_res = list()
        for _ in range(batch_num):
            p_set = copy.copy(players[set])
            rand.shuffle(p_set)

            cost, perf = exec_test(p_set, TEAMS[set][0], TEAMS[set][1], batch=True)
            res = list()
            res.append(cost<=PASSES[set])
            res.append(perf<PERF_PASS)
            set_res.append(res)

        cost_passed = sum([1 for x in set_res if x[0]])
        perf_passed = sum([1 for x in set_res if x[1]])
        print(f"SET {ind+1} -> COSTS: {cost_passed}/{len(set_res)} passed; PERFS: {perf_passed}/{len(set_res)} passed")
        results.append(set_res)

    # for ind, set in enumerate(results):
    #     cost_passed = sum([1 for x in set if x[0]])
    #     perf_passed = sum([1 for x in set if x[1]])
    #     print(f"SET {ind+1} -> COSTS: {cost_passed}/{len(set)} passed; PERF: {perf_passed}/{len(set)} passed")


def create_test(large=False, batch=False, select = None, target_format = None):
    players, lengths = get_test_case(large=large)
    if not large:
        if batch:
            batch_test(players)
            
        else:
            if select is not None and select>0:
                players = players[select-1]
            else:
                players = rand.choice(players)
            exec_test(players, target_format if target_format is not None and len(target_format)>0 and set(target_format).issubset([2,3,4,5,6]) else None, 6)
    else:
        exec_test(players, target_format if target_format is not None and len(target_format)>0 and target_format[0] in {2,3,4,5,6} else 2, 6, lengths = lengths, large=True)
    

if __name__ == "__main__":
    import time

    large = True
    batch = False
    select = 7
    if batch: large=False
    create_test(large, batch, select = select, target_format = [])
