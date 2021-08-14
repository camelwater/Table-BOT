# -*- coding: utf-8 -*-
import utils.Utils as Utils
import utils.tagUtils as tagUtils
# from os.path import commonprefix
from collections import defaultdict
import copy
import random as rand
from itertools import chain
from functools import reduce, partial
import tag_testing.simulatedAnnealingTag as simAnl
from typing import Dict, Tuple, List, Set

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
        players = list({'x#1':0, 'xxx':0, 'Ryan@X':0, '¢ant':0, 'coolio': 0, 'cool kid cool': 0, "GG EZ": 0, 'gas mob':0, "gassed up":0, "kaya yanar":0, "yaya kanar":0, "yaka ranar":0}.keys())
        # players = ['hello', 'he123', 'borrowed time', 'WAX', 'barrel', 
        #             'A-1', 'what?', "WWW.PH.COM", "BWλHλHλ", 'Ã', 'λp fraud', 'WOW!!']
        # players = ['Mo taz', 'Mo Matt', 'Mo Jαggγ', 'Mo Sal', 'Mo Jos', 'Prιngle@MV', 'MV Noah', 'MV stripe', 'MV L-boaT', 'MV yax']
        # players = ['λρ Tom', 'A*', 'v¢ sauzule', 'saharave', 'MKW 4Beans', 'cadavreMK', 'coci loko', 'C', 'So[LLLLLL]', 'Zjazca', 'Z- stavros']
        # players = ['AYA hello', '!!m&m?!', 'mong', 'MV math', 'pringle@MV', '@*', 'AYAYA', 'i need ZZZ', 'Z - stop', 'USA h', 'USA K', 'ABBA']
        # players = ['Æ big', 'PP hi', "PP powerplant", 'PP POWERGRID', 'Æ vamp', 'PP ger', 'Æ hello', 'Æ oo', 'big PP', 'shuyx@Æ']
        # players = ['Ac☆Mirymeg', 'Z☆', 'WC top 2', 'Player', 'MonkeyTime', 'z おk', 'Ac Stubbz', 'Hosseini','MΞ☆Mγτh','Hτ chξΣ◇€£', 'Player', 'WC △△◎◎♪☆○']
        # players= ['X◇山周回のれみ','CRYLIXDAWN', 'さぼX', 'DG★mila*', 'C☆Latent', 'Player-1','Dovi', 'らいよんのRemi', 'にしのだいせんせい',
        #             'Player-2', 'ライオンのRemi', 'だいせんせい', 'ωΖ hALr', '[ωZ] PogU', "Anairis", "A L I C E"]
        # players = ['Anairis' ,'A L I C E', 'B frozen', 'Bayview', 'Get Candy△', 'GANK/FF@15', "m shix", "m¢ jipper", "Player", "Prayer", "Se Revan", 'sussy baka']

    return players, (lengths if large else None)

def count_pre_tags(tag, players):
    count= 0
    for p in players:
        if p[0].startswith(tagUtils.sanitize_uni(tag).lower()):
            count+=1
    return count

def rank_tags(tag, players, per_team) -> int:
    '''
    rank tags based on how likely they are to be correct tags.

    prefix tags first, then suffix tags, then mixed tags
    '''
    if isinstance(tag, tuple):
        tag = tag[0]

    pre_count = count_pre_tags(tag, players)
    post_count = len(players)-pre_count
    if pre_count==per_team:
        return per_team+1

    if post_count==per_team:
        return per_team

    return pre_count

def clean_subsets(all_tags):
    '''
    get rid of tags that are subset of other tags (subset of players and subset of tag name)
    '''
    #ex. if tag `P` has the same players as tag `Pro`, then get rid of `P`

    i = 0
    while i<len(all_tags):
        item = list(all_tags.items())[i]
        tag2, players2 = item[0], item[1]
        for tag, players in all_tags.items():
            if tag!=tag2 and players2.issubset(players) and (tag2.lower()==tag.lower() or (len(tag2)<len(tag) and \
                (tag.lower().startswith(tag2.lower()) or tag.lower().endswith(tag2.lower())))):
                all_tags.pop(tag2)
                i-=1
                break
        i+=1

def overlaps(p: Tuple[str, str], tag: str, all_tags: Dict[str, Set[Tuple[str, str]]], per_team: int):
    num_overlaps_strict = 0
    num_overlaps_lenient = 0
    for x, x_players in all_tags.items():
        if x==tag: continue
        if p in x_players and len(x_players)>=per_team:
            if len(x_players)==per_team:
                num_overlaps_lenient+=1
            num_overlaps_strict+=1
    return num_overlaps_strict, num_overlaps_lenient

def check_overlaps(players: Set[Tuple[str, str]], tag: str, all_tags: Dict[str, Set[Tuple[str, str]]], per_team: int):
    '''
    check if players in overflowing tags either:

    1. fit into a better sized team (correct number of players)

    2. fit into a better tagged team (location of another tag is better than current)
    '''
    def more_prefix(players, tag):
        return count_pre_tags(tag, players) >= int(len(players)/2)
    def more_suffix(players, tag):
        return count_pre_tags(tag, players) < int(len(players)/2)

    if len(players)<=per_team: return

    count_overlaps = [(i, overlaps(i, tag, all_tags, per_team)) for i in players]
    # non_overlapped = sorted([i for i in count_overlaps if i[1][1]==0], key=lambda l: l[1], reverse=True)
    strict_non_overlapped = [i[0] for i in count_overlaps if i[1][0]==0]
    
    if len(strict_non_overlapped)>=per_team:
        for i in copy.copy(players):
            if i not in strict_non_overlapped:
                all_tags[tag].discard(i)
        return
    # elif len(non_overlapped)>=per_team:
    #     pass

    iter = sorted(list(players), key=lambda l: (1 if overlaps(l, tag, all_tags, per_team)[1]==1 else 0, 1 if overlaps(l, tag, all_tags, per_team)[0]==1 else 0, 0 if l[0].startswith(tag.lower()) else 1))

    for comp_tag, tag_p in all_tags.items():
        if comp_tag == tag:
            continue
        if isinstance(comp_tag, tuple): 
            comp_tag = comp_tag[0]

        comp_tag_uni = tagUtils.sanitize_uni(comp_tag).lower()
        for p in iter[::-1]:
            if p in tag_p and len(tag_p)>=per_team: 
                if len(comp_tag)>len(tag) and (comp_tag_uni.startswith(tag.lower())
                                            or comp_tag_uni.endswith(tag.lower())):
                    all_tags[tag].discard(p)
                    iter.remove(p)
                    if len(all_tags[tag])<=per_team:
                        return

                # elif not len(non_overlapped)<per_team and all([True if overlaps(i, tag, all_tags, per_team)==1 else False for i in tag_p]):
                #     all_tags[tag].discard(p)
                #     iter.remove(p)
                    # if len(all_tags[tag])<=per_team:
                    #         return

                elif p[0].startswith(comp_tag_uni) and not p[0].startswith(tag.lower()) \
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

                elif p[0].endswith(comp_tag_uni) and not p[0].endswith(tag.lower()) \
                        and more_suffix(all_tags[comp_tag], comp_tag) and not more_prefix(all_tags[tag], tag):
                    if overlaps(p, tag, all_tags, per_team)[0]==1:
                        all_tags[tag].discard(p)
                        iter.remove(p)
                    elif len(tag_p)==per_team and len(all_tags[tag])>per_team:
                        all_tags[tag].discard(p)
                        iter.remove(p)
                    if len(all_tags[tag])<=per_team:
                        return
                
                
def ngram(seq: str, n: int):
    return (seq[i: i+n] for i in range(0, len(seq)-n+1))

def allngram(seq: str, minn=1, maxn=None):
    lengths = range(minn, maxn+1) if maxn else range(minn, len(seq))
    ngrams = map(partial(ngram, seq), lengths)
    return set(chain.from_iterable(ngrams))

def commonaffix(group):
    maxn = min(map(len, group))
    seqs_ngrams = map(partial(allngram, maxn=maxn), group)
    intersection = reduce(set.intersection, seqs_ngrams)
    try:
        all_presub = sorted(intersection, key=len, reverse=True)
        for sub in all_presub:
            if all([i.startswith(sub) or i.endswith(sub) for i in group]):
                return sub

        return ""
    except:
        return ""

def split_by_actual(players: Set[Tuple[str, str]], tag: str, per_team: int, all_tags: Dict[str, Set[Tuple[str, str]]]):
    '''
    split overflowing tags which have players who have different actual tag values and are supposed to have a different tag.
    '''
    #ex. 2 players currently in tag `A` are actually tag `λ`

    def actual_matches(p, diff_players):
        return len([i for i in diff_players if commonaffix([p, i[1]])!=""])

    diff_actual_players = []
    for p in players:
        p_a = p[1].strip().lower()
        if not (p_a.startswith(tag.lower()) or p_a.endswith(tag.lower())):
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

        all_tags[actual_tag] = set(diff_actual_players)
    
        
def split_chunks(players: Set[Tuple[str, str]], tag: str, per_team: int, all_tags: Dict[str, Set[Tuple[str, str]]]):
    '''
    split tags with too many people into even chunks.

    prefix players and suffix players will try to be kept in their respective groupings
    '''
    # if tag has too many people at this point, then it is very likely that
    # there are duplicate tags, meaning more than one team has the same tag (obviously shouldn't happen and isn't allowed)

    def post_id(p) :
        p = p[0]
        if p.startswith(tag.lower()):
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
        post_chunks = []
        pre_chunks = []
        all_tags[tag] = set(players[:indx])
    else:
        for p in players[indx:]:
            if p[0].startswith(tag.lower()):
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
            temp = (tag, a) #tuple for duplicate tags (a bit annoying)
            a+=1
        all_tags[temp] = set(g)


def handle_undetermined(teams: Dict[str, List[str]], un_players: List[Tuple[str, str]], per_team: int):
    '''
    try to tag players whose tags couldn't be determined.

    first, fill tags that aren't full. then, if necessary, create random groupings.
    '''
    #substring tag for 2v2s check
    # if len(un_players)>0 and per_team==2:
    #     find_substring_tags(un_players, teams)

    def rand_split():
        split = list(Utils.chunks(un_players, per_team))
        for r_team in split:
            for ind,player in enumerate(r_team):
                try:
                    temp = check = tagUtils.sanitize_uni(player[1])[0] #use first valid character from name as new tag
                    d = 1
                    while check.lower() in map(lambda o: o.lower(), teams.keys()):
                        check = f"{temp}-{d}"
                        d+=1
                    teams[check] = r_team
                    break
                
                except: #player has no valid characters in their name 
                    if ind+1==len(r_team):
                        temp = check = player[1][0]
                        d = 1
                        while check.lower() in map(lambda o: o.lower(), teams.keys()):
                            check = f"{temp}-{d}"
                            d+=1
                        teams[check] = r_team

    is_all_filled = False if len(list(teams.values())[-1])<per_team else True
    # is_all_filled=True
    # for tag in list(teams.items())[::-1]:
    #     if len(tag[1])<per_team:
    #         is_all_filled = False
    #         break

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


def select_top(all_tags: Dict[str, Set[Tuple[str, str]]], per_team: int, num_teams: int, num_teams_supposed: int, teams: Dict[str, List[str]], players: List[Tuple[str, str]]):
    '''
    choose best combination of tags.

    first, resolve tag conflicts. then, go through tags and finalize top-ranked tags.
    '''
    # all_tags = dict(sorted(all_tags.items(), key=lambda l: len(l[1]), reverse=True))
    for tag, tag_players in copy.deepcopy(all_tags).items():
        tag_players = all_tags[tag]
        if len(tag_players) <= per_team: continue

        split_by_actual(tag_players, tag, per_team, all_tags)
        check_overlaps(tag_players, tag, all_tags, per_team) 
        split_chunks(tag_players, tag, per_team, all_tags)

        if len(tag_players)<=per_team: continue  
        #just randomly get rid of someone at this point - either the format is wrong or the players' tags are bad (and impossible to get completely correct)
        # overlapped_players = [i for i in tag_players if overlaps(i, tag, all_tags, per_team[1][])>0]
        tag_players = sorted(tag_players, key = lambda p: overlaps(p, tag, all_tags, per_team))
        while len(tag_players)>per_team: 
            tag_players.pop()
            # if len(overlapped_players)>0:
            #     tag_players.discard(overlapped_players.pop(-1))
            # else:
            #     tag_players.pop()
    for _ in range(num_teams_supposed):
        for x in list(all_tags.items())[::-1]:
            new_set = set([i for i in x[1] if i in players])
            if len(new_set)==0: 
                all_tags.pop(x[0])
            else:
                all_tags[x[0]] = new_set
        if len(all_tags)==0:
            break
        all_tags = dict(sorted(all_tags.items(), key=lambda tag: (len(tag[1]), rank_tags(tag[0],tag[1], per_team), len(tag[0])), reverse=True))
        top_key = list(all_tags.keys())[0]
        teams[top_key] = list(all_tags[top_key])
        for p in all_tags[top_key]:
            players.remove(p)

        all_tags.pop(top_key)

def squeeze_player_names(teams: Dict[str, List[str]]):
    for tag, p in teams.items():
        teams[tag] = list(map(lambda l: l[1], p))

def fix_tags(teams: Dict[str, List[str]]):
    '''
    fix duplicate tag names conflicts.
    '''
    def dup_tag(t: str, add_self=False):
        count = 0
        for i in list(teams.keys()):
            if isinstance(i, tuple): 
                i = i[0]+'-'+str(i[1])
            if i.strip().lower() == t.strip().lower(): count+=1
        if add_self: count+=1 
        return count>1

    for tag in list(teams.keys())[::-1]:
        if not isinstance(tag, tuple) and dup_tag(tag):
            temp = tag
            a = 1
            while temp in teams:
                temp = f'{tag}-{a}'
                a+=1
            teams[temp] = teams.pop(tag)
        elif isinstance(tag, tuple):
            if not dup_tag(tag[0], add_self=True):
                teams[tag[0]] = teams.pop(tag)
            else:
                n_tag = tag[0]+'-'+str(tag[1])
                teams[n_tag] = teams.pop(tag)
            
  
def find_possible_tags(players: List[Tuple[str, str]]):
    '''
    find all possible tag matches - any tag that has 2 or more matching players.
    '''
    #this does find duplicates, which makes it inefficient 
    all_tag_matches = defaultdict(set)

    for i in range(len(players)):
        tag_matches = defaultdict(set)
        
        orig_i = players[i][1]
        i_tag = players[i][0]
        for temp_indx in range(len(i_tag), 0, -1):
            for j in range(len(players)):
                if i==j: continue

                j_tag = players[j][0]
                
                if (i_tag[:temp_indx] == j_tag[:temp_indx] or i_tag[:temp_indx] == j_tag[-temp_indx:]):
                    m_tag = tagUtils.sanitize_uni(orig_i)[:temp_indx].strip()
                    if len(m_tag)>0:
                        if len(m_tag) == 1: 
                            m_tag = m_tag.upper()
                        if m_tag[-1] == '-':
                            m_tag = m_tag[:-1]
                        
                        tag_matches[m_tag].add(players[i])
                        tag_matches[m_tag].add(players[j])

                if (i_tag[-temp_indx:] == j_tag[-temp_indx:] or i_tag[-temp_indx:] == j_tag[:temp_indx]):
                    m_tag = tagUtils.sanitize_uni(orig_i)[-temp_indx:].strip()
                    if len(m_tag)==0: continue
                    if len(m_tag) == 1: 
                        m_tag = m_tag.upper()
                    if m_tag[-1] == '-':
                        m_tag = m_tag[:-1]
                
                    tag_matches[m_tag].add(players[i])
                    tag_matches[m_tag].add(players[j])
                    
            
        for tag, tagged_players in tag_matches.items():
            if not (tagged_players.issubset(all_tag_matches[tag])):
                all_tag_matches[tag].update(tagged_players) #adding possible combination for this tag
    return all_tag_matches


def tag_algo(players: List[str], per_team: int, num_teams: int) -> Dict[str, List[str]]:
    '''
    split players into { num_teams } teams of { per_team } based on their tags.
    '''
    teams = {}
    supposed_teams = int(len(players)/per_team)

    for ind, p in enumerate(players):
        players[ind] = (tagUtils.sanitize_uni(p.strip()).lower(), p)

    all_tag_matches = find_possible_tags(players)

    clean_subsets(all_tag_matches) #get rid of tags that have overlapping players (shorter tags with subset of players)
    select_top(all_tag_matches, per_team, num_teams, supposed_teams, teams, players) #select best tags that meet requirements
    # assert_correct(teams, players, per_team, num_teams, supposed_teams) #contingency in case of rare errors
    fix_tags(teams)

    if len(players)>0: #players who weren't tagged
        teams = dict(sorted(teams.items(), key=lambda l: len(l[1]), reverse=True))
        handle_undetermined(teams, players, per_team)
    
    squeeze_player_names(teams)

    return teams

if __name__ == "__main__":
    import time
    
    large = False
    players, lengths = get_test_case(large=large)
    rand.shuffle(players)
    # print(players)
    #find_possible_tags faster than commonaffix (maybe should change for split_acutal_tag)

    tick = time.perf_counter()
    per_team = 2
    teams = tag_algo(players, per_team=per_team, num_teams=6)
    # print(dict(sorted(t.items(), key = lambda l: l[0])))
    if not large: print(teams)
    print("\nPERFORMANCE: {:.15f}".format(time.perf_counter()-tick))
    
    if lengths:
        print('avg length:', sum(lengths)/len(lengths))
        print(len(lengths))
    
    L = []
    for tag, p in teams.items():
        if tag.find('-')>=len(tag)/2 and tag[tag.find('-'):].isnumeric():
            tag = tag[tag.find('-')]
        L.append([tagUtils.sanitize_uni(tag).lower(), list(map(lambda l: (tagUtils.sanitize_uni(l.strip()).lower(), l), p))])
    cost_check = simAnl.SimulatedAnnealing(L, per_team)
    print("cost:",cost_check.E(L))
