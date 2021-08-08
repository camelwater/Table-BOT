# -*- coding: utf-8 -*-
"""
Created on Sat Jun 5 15:30:03 2021

@author: ryanz
"""
import time
import os
import io

def create_temp_file(filename, content, dir='.', no_ret = False):
    with open(dir+filename, 'w', encoding='utf-8') as e_file:
        e_file.write(content)
    if no_ret: return
    return io.BytesIO(open(dir+filename, 'rb').read())

def delete_file(filename):
    try:
        os.remove(filename)
    except FileNotFoundError or IsADirectoryError:
        pass

def get_file_bytes(file):
    if not os.path.isfile(file):
        return "No room errors."
    try:
        f = io.BytesIO(open(file, 'rb').read())
    except:
        return "Error while retrieving room errors file."
    return f

def destroy_temp_files(channel):
    for dir in ['./error_footers/']: #can add more temp folders when needed
        delete_file(dir+("warnings_and_errors-" if dir=='./error_footers/' else "")+channel+'.txt')

import re

def is_rxx(arg):
    '''
    check if string is a roomID (if it is in rxx or xx00 format)
    '''
    return re.match('^r[0-9]{7}$|^[a-z]{2}[0-9]{2}$', arg.lower()) is not None
    # return (arg3[0]=='r' and len(arg3)==8) or (arg3[2:].isnumeric() and len(arg3)==4)

from more_itertools import consecutive_groups
import itertools

def insert_formats(string):
    return string.replace('5', '5v5').replace('2', '2v2').replace('3','3v3').replace('4','4v4').replace('6','6v6').replace('1', 'FFA')
def remove_formats(string):
    return string.replace("5v5", '5').replace('2v2', '2').replace('3v3', '3').replace('4v4', '4').replace('6v6', '6').replace('ffa', '1')

def parse_ILT_setting(string, local_inject = False):
    args = remove_formats(string.strip().lower()).split(',')
    for indx, i in list(enumerate(args))[::-1]:
        i = i.strip()
        check = i.rstrip('+')
        if '-' not in check and (int(check)>6 or int(check)<0):
            raise ValueError

        if i=='1+': #always ignoreLargeTimes
            if local_inject: return list(range(1,7))
            return '1+'
        if i=='0': #never ignoreLargeTimes
            if local_inject: return list()
            return '0'

        if '-' in i: #range
            start, end = i.split('-')
            start, end = int(start), int(end)
            if start>6 or start<1 or end<0 or end>6:
                raise ValueError
            args.pop(indx)
            args.extend(list(range(start, end+1)))
        elif i[-1] == '+': #range to end
            start = int(i.rstrip('+'))
            args.pop(indx)
            args.extend(list(range(start, 7)))
        else: #only one format
            args[indx] = int(i)
    if local_inject:
        return args

    args = set(args)
    for i in args:
        if i>6 or i<1:
            raise ValueError #bad input

    consecutives = []
    for group in consecutive_groups(args):
        g = list(group)
        if len(g)>2: consecutives.append(g)
    
    all_in_cons = list(itertools.chain.from_iterable(consecutives))
    args = [str(i) for i in args if i not in all_in_cons]
    for i in consecutives:
        if i[-1] == 6: args.append(f"{i[0]}+")
        else: args.append(f"{i[0]}-{i[-1]}")
    
    return ', '.join(sorted(args))

def determine_ILT(setting, format):
    '''
    determine whether large times should be ignored or not based on server settings and format
    '''
    format = convert_format(format)
    excludes = parse_ILT_setting(setting, local_inject=True)
    return format in excludes

#-------------- Table.py methods --------------#

#max teams based on format (ex. 6 teams for a 2v2, 2 teams for a 5v5)
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

def sanitize_uni(string, for_search = False):
    '''
    convert known/common un-unidecodable and unicode strings to ASCII and clean string for tag-matching

    '''
  
    ret= []
    for i in string:
        if i in MULT_CHAR_MAP:
            for char in MULT_CHAR_MAP[i]:
                ret.append(char)
            continue
        i = CHAR_MAP.get(i, i)
        if i in VALID_CHARS or is_CJK(i):
            ret.append(i)
            continue
        
        ret.append(" ")
        # n = unidecode(i)
        # if n=="":
        #     ret.append(" ")
        # elif n in VALID_CHARS:
        #     ret.append(n)
            
    if for_search:
        return ''.join(ret)

    while len(ret)>0:
        if ret[0] in PRE_REMOVE:
            ret.pop(0)
        elif ret[-1] in POST_REMOVE:
            ret.pop(-1)
        else:
            break

    return ''.join(ret)


def sanitize_tag_uni(string):
    '''
    get rid of non-unicode characters that cannot be converted, but keep convertable characters in original form
    '''
    string = [i for i in string if CHAR_MAP.get(i, i) in VALID_CHARS or is_CJK(i) or i in MULT_CHAR_MAP or (unidecode(i)!="" and unidecode(i) in VALID_CHARS)]
    while len(string)>0:
        if string[0] in PRE_REMOVE:
            string.pop(0)
        elif string[-1] in POST_REMOVE:
            string.pop(-1)
        else:
            break

    return ''.join(string)

def replace_brackets(string): #don't really need this anymore
    string = string.lstrip('[').lstrip(']').lstrip('(').lstrip(')').lstrip('{').lstrip('}')
    string = sanitize_uni(string)
    
    return string

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
        most_key = max(repetitions, key=repetitions.get)
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
    except ValueError:
        max_key = None

    return (True, {'race': len(prev_races)-max_key, 'num_aff': repetitions[max_key]}) if max_key else (False, {})



### constants + maps

VALID_CHARS = "/\*^+-_.!?@%&()\u03A9\u038F" + "abcdefghijklmnopqrstuvwxyz" + "abcdefghijklmnopqrstuvwxyz0123456789 ".upper()
PRE_REMOVE = "/\*^+-_.!?#%() "
POST_REMOVE = "/\*^+-.!?# "

CHAR_MAP = {
    "Λ": 'A', "λ": 'A', "@": 'A', "Δ": "A", "Ά": "A", "Ã": "A", "À": "A", "Á": "A", "Â": "A", "Ä": "A", "Å": "A", "ά": "a", "à": "a", "á": "a", "â": "a", "ä": "a", "å": "a", "ã": "a", "α": "a", "ª": "a",
    
    "♭": "b", "ß": "B", "β": "B",
    
    "¢": "c", "ς": "c", "ç": "c", "©": "c", "Ç": "C",
    
    "è": "e", "é": "e", "ê": "e", "ë": "e", "ε": "e", "ᵉ": "e", "έ": "E", "€": "E", "Ξ": "E", "ξ": "E", "Σ": "E", "£": "E", "Έ": "E", "È": "E", "É": "E", "Ê": "E", "Ë": "E",
    
    "Ή": "H",

    "ì": "i", "í": "i", "î": "i", "ï": "i", "ι": "i", "ΐ": "i", "ί": "i", "ϊ": "i", "Ϊ": "I", "Ì": "I", "Í": "I", "Î": "I", "Ί": "I", "Ï": "I",
    
    "κ": "k", 

    "ñ": "n", "η": "n", "ή": "n", "Ñ": "N", "Π": "N",

    "σ": "o", "○": "o", "º": "o", "ο": "o", "ò": "o", "ó": "o", "ό": "o", "ô": "o", "ö": "o", "ø": "o", "δ": "o", "õ": "o", "Ό": "O", "Ò": "O", "Ó": "O", "Ô": "O", "Ö": "O", "Ø": "O", "Õ": "O", "θ": "O", "φ": "O", "Θ": "O", "Φ": "O", "Ω": "O", "Ώ": "O", "◎": "O",
    
    "や": "P", "ρ": "p",
    
    "π": "r", "Г": "r", "®": "R",
    
    "$": "S", "§": "S",
    
    "τ": "t",
    
    "μ": "u", "ù": "u", "ú": "u", "û": "u", "ü": "u", "ϋ": "u", "ύ": "u", "Ù": "U", "Ú": "U", "Û": "U", "Ü": "U", "ΰ": "U", "υ": "u",
    
    "ν": "v",

    "ώ": "w", "Ψ": "w", "ω": "w", "ψ": "W",
    
    "χ": "X",
    
    "ý": "y", "ÿ": "y", "γ": "y", "¥": "Y", "Ύ": "Y", "Ϋ": "Y", "Ý": "Y", "Ÿ": "Y",
    
    "ζ": "Z", "Ζ": "Z",

    "「": "[", "」": "]", "『": "[", "』": "]"
}

MULT_CHAR_MAP = {
    "Æ": 'AE',
    "æ": "ae",

    "œ": "oe",
    "Œ": "OE",

    "™": "TM"
}


PTS_MAP =  { 
    12:{0:15, 1:12, 2:10, 3:8, 4:7, 5:6, 6:5, 7:4, 8:3, 9:2, 10:1, 11:0},
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

WARNING_MAP = {
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

        "tie": "{} had tied race times ({}). Check [[/PREFIX\]]rr for errors.", 

        "mkwx_bug_increase": "Room size increased mid-GP from {} to {}. This is impossible unless if there was a reset or mid-GP sub(s), and likely an MKWX ERROR. Affected races: {}. Run [[/PREFIX\]]changeroomsize to fix this.", 
        "mkwx_bug_change": "Players in the room changed mid-GP (race {}). Unless if there were mid-GP sub(s) this race or a reset, this is an MKWX ERROR. Table could be inaccurate for this GP ({}).", 
        "mkwx_bug_blank": "All players in the race had blank finish times. This is an MKWX ERROR if there was no room reset. Table is inaccurate for this GP ({}).", 
        "mkwx_bug_repeat": "{} player(s) had the same finish time as they had in a previous race (race {}). Check for errors as this is highly improbable and likely an MKWX ERROR. Table could be inaccurate for this GP ({}).",
        "mkwx_bug_tr":"Room had {} players with track errors. Check [[/PREFIX\]]rr for errors. Table could be inaccurate for this GP ({}).", 
        "mkwx_bug_delta": "Room had time delay (lag) errors - {} affected player(s). Check [[/PREFIX\]]rr for errors. Table could be inaccuate for this GP ({}).",

        "sub": "{}  -  Potential sub detected. If this player is a sub, use [[/PREFIX\]]sub.", 
        "sub_conf": "{} - subbed in for {}.",

        "large_time": "{} had a large finish time - {}. Check [[/PREFIX\]]rr for errors."
        }

DC_MAP = {
    "dc_on": "{}** - DCed during the race (on results), unless MKWX ERROR. Awarding 3 DC points per missing race in GP {} ({} pts).",
    ("dc_on", 1): "{}** - DCed during the first race of GP {} (on results), unless MKWX ERROR. 15 DC points for GP {}.",
    ("dc_on", -1): "{}** - DCed during the race (on results), unless MKWX ERROR. No DC points for GP {}.", 

    "dc_on_confirmed": "{}** - DCed during the race (on results). Awarding 3 DC points per missing race in GP {} ({} pts).",
    ("dc_on_confirmed", 1): "{}** - DCed during the first race of GP {} (on results). 15 DC points for GP {}.",
    ("dc_on_confirmed", -1): "{}** - DCed during the race (on results). No DC points for GP {}.", 

    "dc_before": "{}** - DCed before race. 3 DC points per missing race in GP {} ({} pts).", 
    ("dc_before", 1): "{}** - missing from GP {}. 18 DC points for GP {} (mogi), 15 DC points for GP {} (war)."
    }  

GRAPH_MAP = {
    1: {"table": "none", "type": "None"},
    2: {"table": "abs", "type": "Absolute"},
    3: {"table": "diff", "type": "Difference"}   
}

STYLE_MAP = {
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

IGNORE_LARGE_TIMES_MAP = {
    '0': "Never",
    '1+': "Always",
    '1': "FFA",
    '2': "2v2",
    '2+': "2v2+",
    '3': "3v3",
    '3+': "3v3+",
    '4': "4v4",
    '4+': "4v4+",
    '5': "5v5",
    '5+': "5v5+",
    '6': "6v6"
}

SETTINGS = {
    "IgnoreLargeTimes": IGNORE_LARGE_TIMES_MAP,
    "graph": GRAPH_MAP, 
    "style": STYLE_MAP
}

if __name__ == "__main__":
    setting = "1,+2++"
    setting = parse_ILT_setting(setting)
    print(setting)
    print(determine_ILT(setting, '4'))
        
    # i = "A◇山周回のれみ"
    # sans = []
    # t = time.time()
    # for _ in range(1000):
    #     sans.append(sanitize_uni(i))
    # print(time.time()-t)
    # print(sans[0])
    