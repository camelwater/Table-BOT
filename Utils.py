# -*- coding: utf-8 -*-
"""
Created on Sat Jun 5 15:30:03 2021

@author: ryanz
"""

#-------------- Table.py methods --------------#

#default max teams based on format 
def max_teams(f):
    f = f[0]
    if f == 'f':
        return 12
    else:
        f = int(f)
        return int(12/f)
    
#check if number of teams exceeds max possible teams for format
def check_teams(f, teams):
    max_t = max_teams(f)
    if teams>max_t: return True
    return False

def get_num_players(f, teams):
    f = f[0]
    if f == 'f':
        f = 1
    else: f = int(f)
    
    return teams*f



#============= tabler.py stuff ==============#

def isfloat(n):
    try:
        float(n)
        return True
    except:
        return False

def convert_format(f) -> int:
    """
    get players per team based on format

    """
    f = f[0]
    if not f.isnumeric():
        return 1
    return int(f)

def full_format(f):
    if not f[0].isnumeric():
        return 'FFA'
    return '{}v{}'.format(int(f[0]), int(f[0]))

def isFFA(f):
    if not f[0].isnumeric():
        return True
    return False

def chunks(l, n):
    """
    split list into smaller lists

    Parameters
    ----------
    l : list to split
    n : number of elements per sublist

    Yields
    ------
    smaller lists of l with len(n) each

    """
    for i in range(0, len(l), n):
        yield l[i:i+n]

def LCS(X, Y) -> str:
    """
    find longest common substring between two strings.
    used to find tags that are not prefixes nor suffixes. 
    currently only used for 2v2 tags.
    
    """
    
    m = len(X)
    n= len(Y)
    
    maxLength = 0           # stores the max length of LCS
    endingIndex = m         # stores the ending index of LCS in `X`
 
    # `lookup[i][j]` stores the length of LCS of substring `X[0…i-1]` and `Y[0…j-1]`
    lookup = [[0 for x in range(n + 1)] for y in range(m + 1)]
 
    # fill the lookup table in a bottom-up manner
    for i in range(1, m + 1):
        for j in range(1, n + 1):
 
            # if the current character of `X` and `Y` matches
            if X[i - 1] == Y[j - 1]:
                lookup[i][j] = lookup[i - 1][j - 1] + 1
 
                # update the maximum length and ending index
                if lookup[i][j] > maxLength:
                    maxLength = lookup[i][j]
                    endingIndex = i
 
    # return longest common substring having length `maxLength`
    return X[endingIndex - maxLength: endingIndex]

def is_CJK(char):
    return any([start <= ord(char) <= end for start, end in 
                [(4352, 4607), (11904, 42191), (43072, 43135), (44032, 55215), 
                 (63744, 64255), (65072, 65103), (65381, 65500), 
                 (131072, 196607)]
                ])

from unidecode import unidecode

def sanitize_uni(string):
    '''
    convert known/common un-unidecodable strings to unicode and clean string for tag-matching

    '''
    
    string = [CHAR_MAP.get(i, i) for i in string]
    # ret = list(unidecode(''.join(string)))
    ret= []
    for i in string:
        n = unidecode(i)
        if n!="" or i in VALID_CHARS: 
            ret.append(n)
        else: 
            ret.append(" ")

    ret = [i for i in ret if i in VALID_CHARS]
    while len(ret)>0:
        if ret[0] in PRE_REMOVE:
            ret.pop(0)
        else:
            break
    while len(ret)>0:
        if ret[-1] in POST_REMOVE:
            ret.pop(-1)
        else:
            break

    return ''.join(ret)


def sanitize_tag_uni(string):
    '''
    get rid of non-unicode characters that cannot be converted, but keep convertable characters in original form
    '''
    string = [i for i in string if CHAR_MAP.get(i, i) in VALID_CHARS or (unidecode(i)!="" and unidecode(i) in VALID_CHARS)]
    while len(string)>0:
        if string[0] in PRE_REMOVE:
            string.pop(0)
        else:
            break
    while len(string)>0:
        if string[-1] in POST_REMOVE:
            string.pop(-1)
        else:
            break

    return ''.join(string)

def replace_brackets(string):
    string = string.lstrip('[').lstrip(']').lstrip('(').lstrip(')').lstrip('{').lstrip('}')
    string = list(unidecode(sanitize_uni(string)))
    ret = [i for i in string if i in VALID_CHARS]
    
    return ''.join(ret)

def dis_clean(string):
    return string.replace("*", "\*").replace("`",'\`').replace("_", "\_").replace("~~", "\~~")

from collections import defaultdict

def check_repeat_times(race, prev_races):
    repetitions = defaultdict(int)
    dc_repetitions = defaultdict(int)

    for c_indx, compare in enumerate(prev_races[::-1]):
        for player1, player2 in zip(race, compare):
            if player1[2] == player2[2]:
                if player1[1] != 'DC' and player1[1] == player2[1]:
                    repetitions[c_indx] += 1
                elif player1[1] == 'DC' and player1[1] == player2[1]:
                    dc_repetitions[c_indx]+=1

    repetitions = dict(repetitions)
    try:
        most_key = max(repetitions.items(), key=repetitions.get)
    except ValueError:
        most_key = None

    if most_key:
        most_rep= repetitions[most_key] + dc_repetitions[most_key]
    return (True, {'race': len(prev_races)-most_key, 'num_aff': most_rep}) if most_key else (False, {})

def check_repeat_times_slow(race, prev_races):
    repetitions = {}
    race = [(i[2], i[1]) for i in race]
    prev_races = [[(i[2], i[1]) for i in r] for r in prev_races]

    for i, r in enumerate(prev_races[::-1]):
        cou = len([c for c in race if c in r])
        if cou>0:
            repetitions[i] = cou
    
    try:
        max_key = max(repetitions, key=repetitions.get)
    except:
        max_key = None

    return (True, {'race': len(prev_races)-max_key, 'num_aff': repetitions[max_key]}) if max_key else (False, {})



### map constants

VALID_CHARS = "/\*^+-_.!?@%&()\u03A9\u038F" + "abcdefghijklmnopqrstuvwxyz" + "abcdefghijklmnopqrstuvwxyz0123456789 ".upper()
PRE_REMOVE = "/\*^+-_.!?#%() "
POST_REMOVE = "/\*^+-.!?# "

CHAR_MAP = {
    "Λ": 'A',
    "λ": 'A',
    "@": 'A', # not sure about some of these conversions and char constants, but whatever (for now)
    "ß": "B",
    "¢": "c",
    "€": "C",
    "Ξ": "E",
    "ξ": "E",
    "Σ": "E",
    "£": "E",
    "σ": "o", 
    "や": "P",
    "ρ": "p",
    "$": "S",
    "μ": "u",
    "ν": "v", 
    "γ": "y"
}


pts_map =   { 12:{0:15, 1:12, 2:10, 3:8, 4:7, 5:6, 6:5, 7:4, 8:3, 9:2, 10:1, 11:0},
              11:{0:15, 1:12, 2:10, 3:8, 4:6, 5:5, 6:4, 7:3, 8:2, 9:1, 10:0},
              10:{0:15, 1:12, 2:10, 3:8, 4:6, 5:4, 6:3, 7:2, 8:1, 9:0},
              9:{0:15, 1:11, 2:8, 3:6, 4:4, 5:3, 6:2, 7:1, 8:0},
              8:{0:15, 1:11, 2:8, 3:6, 4:4, 5:2, 6:1, 7:0},
              7:{0:15, 1:10, 2:7, 3:5, 4:3, 5:1, 6:0},
              6:{0:15, 1:10, 2:6, 3:3, 4:1, 5:0},
              5:{0:15, 1:9, 2:5, 3:2, 4:1},
              4:{0:15, 1:9, 2:4, 3:1},
              3:{0:15, 1:8, 2:2},
              2:{0:15, 1:7},
              1:{0:15}
            }

warning_map = {
            "dc_on": "{} DCed during the race (on results), unless MKWX ERROR. Awarding 3 DC points per missing race in GP {} ({} pts).",
            ("dc_on", 1): "{} DCed during the first race of GP {} (on results), unless MKWX ERROR. 15 DC points for GP {}.",
            ("dc_on", -1): "{} DCed during the race (on results), unless MKWX ERROR. No DC points for GP {}.", 

            "dc_on_confirmed": "{} DCed during the race (on results). Awarding 3 DC points per missing race in GP {} ({} pts).",
            ("dc_on_confirmed", 1): "{} DCed during the first race of GP {} (on results). 15 DC points for GP {}.",
            ("dc_on_confirmed", -1): "{} DCed during the race (on results). No DC points for GP {}.",

            "dc_before": "{} DCed before race. Giving 3 DC points per missing race in GP {} ({} pts).", 
            ("dc_before", 1): "{} is missing from GP {}. 18 DC points for GP {} (mogi), 15 DC points for GP {} (war).", 

            "missing": "GP {} is missing player(s). GP started with {} players, but should've started with {} players.",
            "missing_w_sub": "GP {} is missing {} player(s): {}. Missing players either DCed or were subbed out.",
            "overflow": "GP {} has too many players. GP started with {} players, but should've started with {} players.",

            "blank_time": "{} had a blank race time and was on results. If this wasn't a DC, this is an MKWX ERROR.",

            "tie": "{} had tied race times ({}). Check ?rr for errors.", 

            "mkwx_bug_increase": "Room size increased mid-GP from {} to {}. This is impossible unless if there was a reset or mid-GP sub(s), and likely an MKWX ERROR. Affected races: {}. Run ?changeroomsize to fix this.", 
            "mkwx_bug_change": "Players in the room changed mid-GP (race {}). Unless if there were mid-GP sub(s) this race or a reset, this is an MKWX ERROR. Table could be inaccurate for this GP ({}).", 
            "mkwx_bug_blank": "All players in the race had blank finish times. This is an MKWX ERROR if there was no room reset. Table is inaccurate for this GP ({}).", 
            "mkwx_bug_repeat": "{} player(s) had the same finish as they had in a previous race (race {}). Check for errors as this is highly improbable and likely an MKWX ERROR. Table could be inaccurate for this GP ({}).",
            "mkwx_bug_tr":"Room had {} players with track errors. Check ?rr for errors. Table could be inaccurate for this GP ({}).", 
            "mkwx_bug_delta": "Room had time delay (lag) errors ({} player(s)). Check ?rr for errors. Table could be inaccuate for this GP ({}).",

            "sub": "{}  -  Potential sub detected. If this player is a sub, use ?sub.", 
            "sub_conf": "{} - subbed in for {}.",

            "large_time": "{} had a large finish time - {}. Check ?rr for errors."
        }

dc_map = {
            "dc_on": "{}** - DCed during the race (on results), unless MKWX ERROR. Awarding 3 DC points per missing race in GP {} ({} pts).",
            ("dc_on", 1): "{}** - DCed during the first race of GP {} (on results), unless MKWX ERROR. 15 DC points for GP {}.",
            ("dc_on", -1): "{}** - DCed during the race (on results), unless MKWX ERROR. No DC points for GP {}.", 

            "dc_on_confirmed": "{}** - DCed during the race (on results). Awarding 3 DC points per missing race in GP {} ({} pts).",
            ("dc_on_confirmed", 1): "{}** - DCed during the first race of GP {} (on results). 15 DC points for GP {}.",
            ("dc_on_confirmed", -1): "{}** - DCed during the race (on results). No DC points for GP {}.", 

            "dc_before": "{}** - DCed before race. 3 DC points per missing race in GP {} ({} pts).", 
            ("dc_before", 1): "{}** - missing from GP {}. 18 DC points for GP {} (mogi), 15 DC points for GP {} (war)."
        }  

graph_map = {
        1: {"table": "none", "type": "None"},
        2: {"table": "abs", "type": "Absolute"},
        3: {"table": "diff", "type": "Difference"}   
}

style_map = {
        1: {"table": "default", "type": "Default Style"},
        2: {"table": "dark", "type": "Dark Theme"},
        3: {"table": "rank", "type": "Color by Ranking"},
        4: {"table": "mku", "type": "Mario Kart Universal"},
        5: {"table": "200L", "type": "200 League"},
        6: {"table": "americas", "type": "Americas Cup"},
        7: {"table": "euro", "type": "EuroLeague"},
        8: {"table": "japan", "type": "マリオカートチームリーグ戦"},
        9: {"table": "cwl", "type": "Clan War League"},
        10: {"table": "runners", "type": "Runners Assemble"},
        11: {"table": "mkworlds", "type": "Mario Kart Worlds"},
}

settings = {
    "graph": graph_map, 
    "style": style_map
}

if __name__ == "__main__":
    i = "€ΣξMΞ☆Mγτh"
    print(sanitize_uni(i))
    
    