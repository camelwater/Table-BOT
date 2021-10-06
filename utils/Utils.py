# -*- coding: utf-8 -*-
"""
Created on Sat Jun 5 15:30:03 2021

@author: ryanz
"""
import time
import os
import io
from typing import Dict, Tuple, List, Any
import re
from more_itertools import consecutive_groups
import itertools

###=================== discord utils =====================###

def create_temp_file(filename, content, dir='.', no_ret = False):
    with open(dir+filename, 'w', encoding='utf-8') as e_file:
        e_file.write(content)
    if no_ret: return
    return io.BytesIO(open(dir+filename, 'rb').read())

def delete_file(filename):
    try:
        os.remove(filename)
    except (FileNotFoundError,IsADirectoryError):
        pass

def get_errors_file(file): #ONLY FOR ?ERRORS
    file = './error_footers/'+ file

    if not os.path.exists(file):
        return "*No warnings or room errors.*"
    try:
        f = io.BytesIO(open(file, 'rb').read())
    except:
        return "Error while retrieving room errors file."
    return f

def destroy_temp_files(channel):
    for ind, dir in enumerate(['./error_footers/warnings_and_errors-']): # , './save_states/'
        delete_file(dir+channel+'.txt') # '.pickle' if ind==1 else 

def disc_clean(string:str):
    return string.replace("*", "\*").replace("`",'\`').replace("_", "\_").replace("~~", "\~~")

def backtick_clean(string: str):
    '''
    LMAOOOO
    '''
    # if '`' not in string:
    #     return string
    # ins_tick = '`' if string.count('`')%2!=0 else ''
    # if string[0] == '`':
    #     return f"{ins_tick} "+string+f"{ins_tick}"
    # elif string[-1]=='`':
    #     return f"{ins_tick}"+string+f" {ins_tick}"
    # else:
    #     return f'{ins_tick}'+string+f'{ins_tick}'
    return string.replace('`', '\'')


###======================================================###

def insert_formats(string: str):
    return string.replace('5', '5v5').replace('2', '2v2').replace('3','3v3').replace('4','4v4').replace('6','6v6').replace('1', 'FFA')
def remove_formats(string: str):
    return string.replace("5v5", '5').replace('2v2', '2').replace('3v3', '3').replace('4v4', '4').replace('6v6', '6').replace('ffa', '1')

def parse_ILT_setting(string: str, max_format=6, local_inject = False):
    args = remove_formats(string.strip().lower()).split(',')
    args = sorted(args)
    for indx, i in list(enumerate(args))[::-1]:
        i = i.strip()
        check = i.strip('+')
        if '-' not in check and (int(check)>max_format or int(check)<0): #check for illegal input
            raise ValueError

        if i=='1+': #always ignoreLargeTimes
            if local_inject: return list(range(1,max_format+1))
            return '1+'
        if i=='0': #never ignoreLargeTimes
            if local_inject: return list()
            return '0'

        if '-' in i: #range
            n_range = sorted([int(n) for n in i.split('-')])
            start, end = n_range[0], n_range[-1]
            # if start>max_format or start<1 or end<0 or end>max_format:
            if start>max_format or start<1 or end>max_format:
                raise ValueError
            args.pop(indx)
            args.extend(list(range(start, end+1)))
        elif i[-1] == '+': #range to end
            args.pop(indx)
            args.extend(list(range(int(i.rstrip('+')), max_format+1)))
        else: #only one format
            args[indx] = int(i)
    if local_inject:
        return args

    args = set(args)
    for i in args:
        if i>max_format or i<1:
            raise ValueError #bad input

    consecutives = []
    for group in consecutive_groups(args):
        g = list(group)
        if len(g)>2: consecutives.append(g)
    
    all_in_cons = list(itertools.chain.from_iterable(consecutives))
    args = [str(i) for i in args if i not in all_in_cons]
    for i in consecutives:
        if i[-1] == max_format: args.append(f"{i[0]}+")
        else: args.append(f"{i[0]}-{i[-1]}")
    
    return ', '.join(sorted(args))

def determine_ILT(setting, format) -> bool:
    '''
    determine whether large times should be ignored or not based on server settings and format
    '''
    format = convert_format(format)
    excludes = parse_ILT_setting(setting, local_inject=True)
    return format in excludes


###========================================================###

def is_rxx(arg: str):
    '''
    check if string is a roomID (if it is in rxx or xx00 format)
    '''
    return re.match('^r[0-9]{7}$|^[a-z]{2}[0-9]{2}$', arg.lower()) is not None

def flag_delta(num: str):
    return num=="—" or (isfloat(num) and (float(num)>7.0 or float(num)<-7.0))

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


def isfloat(n):
    try:
        float(n)
        return True
    except:
        return False

def convert_format(f: str) -> int:
    """
    get players per team based on format

    """
    f = f[0]
    if not f.isnumeric():
        return 1
    return int(f)

def full_format(f: str):
    if not f[0].isnumeric():
        return 'FFA'
    return '{}v{}'.format(int(f[0]), int(f[0]))

def isFFA(f: str):
    if not f[0].isnumeric():
        return True
    return False

def chunks(l, n):
    """
    split list into consecutive n-sized chunks
    """
    for i in range(0, len(l), n):
        yield l[i:i+n]

def find_if_edited(player, raceNum, ref):
    for i in ref[raceNum]:
        if "dc_" in i.get('type') and i.get('player') == player:
            return i.get("is_edited", False)

def warn_to_str(warning: Dict[str, Any]) -> str:                
    warning_type = warning.get('type')

    if "dc_" in warning_type:
        ret = ''
        is_edited = warning.get('is_edited', False)

        if "on" in warning_type:
            warning_type = warning_type+"_confirmed" if is_edited else warning_type
            race = warning.get('race')
            if race == 1:
                ret = WARNING_MAP.get((warning_type, race)).format(warning.get('player').getName(), warning.get('gp'), warning.get('gp')) 
            elif race == -1:
                ret = WARNING_MAP.get((warning_type, race)).format(warning.get('player').getName(), warning.get('gp'))
            else:
                ret = WARNING_MAP.get(warning_type).format(warning.get('player').getName(), warning.get('gp'), warning.get('pts'))
        
        else:
            race = warning.get('race')
            if race == 1:
                ret = WARNING_MAP.get((warning_type,race)).format(warning.get('player').getName(), warning.get('gp'), warning.get('gp'), warning.get('gp'))
            else:
                ret = WARNING_MAP.get(warning_type).format(warning.get('player').getName(), warning.get('gp'), warning.get('pts'))
    
        return ret + '{}'.format(" - determined by tabler" if is_edited else "")

    elif "mkwx_bug" in warning_type:
        if "_increase" in warning_type:
            return WARNING_MAP.get(warning_type).format(warning.get('orig_players'), warning.get('new_players'), ', '.join(map(str, warning.get('races'))))

        elif "_change" in warning_type:
            return WARNING_MAP.get(warning_type).format(warning.get('race'), warning.get('gp'))
        
        elif "_tr" in warning_type:
            return WARNING_MAP.get(warning_type).format(warning.get("aff_players"), warning.get("gp"))

        elif "_delta" in warning_type:
            return WARNING_MAP.get(warning_type).format(warning.get("aff_players"), warning.get('gp'))
        
        elif "_repeat" in warning_type:
            return WARNING_MAP.get(warning_type).format(warning.get("num_affected"), warning.get('race'), warning.get('gp'))

        else:
            return WARNING_MAP.get(warning_type).format(warning.get('gp'))

    elif warning_type == "missing":
        sup_players = warning.get('sup_players')
        cur_players = warning.get('cur_players')
        num_missing = sup_players - cur_players
        return WARNING_MAP.get(warning_type).format(warning.get('gp'), num_missing, cur_players, sup_players)
    
    elif warning_type == "missing_w_sub":
        return WARNING_MAP.get(warning_type).format(warning.get('gp'), warning.get('num_missing'), [i.getName() for i in warning.get('missing_players')])
    
    elif warning_type == "overflow":
        return WARNING_MAP.get(warning_type).format(warning.get('gp'), warning.get('cur_players'), warning.get('sup_players'))
    
    elif warning_type == "blank_time":
        return WARNING_MAP.get(warning_type).format(warning.get('player').getName())

    elif warning_type == "tie":
        return WARNING_MAP.get(warning_type).format([i.getName() for i in warning.get('players')], warning.get('time'))
    
    elif warning_type == "tie_dc":
        return WARNING_MAP.get(warning_type).format([i.getName() for i in warning.get('players')])

    elif warning_type == "sub":
        if warning.get('is_edited', False):
            return WARNING_MAP.get("sub_conf").format(warning.get('player').getName(), warning.get('sub_out').getName())
        else:
            return WARNING_MAP.get(warning_type).format(warning.get('player').getName())

    elif warning_type == "large_time":
        return WARNING_MAP.get(warning_type).format(warning.get('player').getName(), warning.get('time'))

    else:
        raise AssertionError("WARNING TYPE NOT FOUND:", warning_type)

def dc_to_str(dc: Dict[str, Any]) -> str:
        dc_type = dc.get('type')
        is_edited = dc.get('is_edited', False)
        race = dc.get('race', 0)
        ret = ""

        if '_on' in dc_type:
            dc_type = dc_type+'_confirmed' if is_edited else dc_type
            if race == 1:
                ret = DC_MAP.get((dc_type, 1)).format(dc.get('player').getName(), dc.get('gp'), dc.get('gp'))
            elif race == -1:
                ret = DC_MAP.get((dc_type, -1)).format(dc.get('player').getName(), dc.get('gp'))
            else:
                ret = DC_MAP.get(dc_type).format(dc.get('player').getName(), dc.get('gp'), dc.get('pts'))
        else:
            if race == 1:
                ret = DC_MAP.get((dc_type, 1)).format(dc.get('player').getName(), dc.get('gp'), dc.get('gp'), dc.get('gp'))
            else:
                ret = DC_MAP.get(dc_type).format(dc.get('player').getName(),  dc.get('gp'), dc.get('pts'))

        return ret + (' - edited by tabler' if is_edited else "")

        
### =================== MAPS ====================###

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

        "missing": "GP {} is missing {} player(s). GP started with {} players, but should've started with {} players.",
        "missing_w_sub": "GP {} is missing {} player(s): {}. Missing players either DCed or were subbed out.",
        "overflow": "GP {} has too many players. GP started with {} players, but should've started with {} players.",

        "blank_time": "{} had a blank race time and was on results. If this wasn't a DC, this is an MKWX ERROR.",

        "tie": "{} had tied race times ({}). Check [[/PREFIX\]]rr for errors.", 
        "tie_dc": "{} all DCed and were on results. Their positions could be wrong, so check [[/PREFIX\]]rr for errors.",

        "mkwx_bug_increase": "Room size increased mid-GP from {} to {}. This is impossible unless if there was a reset or mid-GP sub(s), and likely an MKWX ERROR. Affected races: {}. Run [[/PREFIX\]]changeroomsize to fix this.", 
        "mkwx_bug_change": "Players in the room changed mid-GP (race {}). Unless if there were mid-GP sub(s) this race or a reset, this is an MKWX ERROR. Table could be inaccurate for this GP ({}).", 
        "mkwx_bug_blank": "All players in the race had blank finish times. This is an MKWX ERROR if there was no room reset. Table is inaccurate for this GP ({}).", 
        "mkwx_bug_repeat": "{} player(s) had the same finish time as they had in a previous race (race {}). Check for errors as this is highly improbable and likely an MKWX ERROR. Table could be inaccurate for this GP ({}).",
        "mkwx_bug_tr":"Room had {} players with track errors. Check [[/PREFIX\]]rr for errors. Table could be inaccurate for this GP ({}).", 
        "mkwx_bug_delta": "Room had time delay (lag) errors - {} affected player(s). Check [[/PREFIX\]]rr for errors. Table could be inaccuate for this GP ({}).",

        "sub": "Potential sub detected  -  {}. If this player is a sub, use [[/PREFIX\]]sub.", 
        "sub_conf": "{} : subbed in for {}.",

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

# if __name__ == "__main__":
#     setting = "1,6-2-3"
#     setting = parse_ILT_setting(setting)
#     print(setting)
#     print(determine_ILT(setting, '3'))

#     i = "A◇山周回のれみ"
#     sans = []
#     t = time.time()
#     for _ in range(1000):
#         sans.append(sanitize_uni(i))
#     print(time.time()-t)
#     print(sans[0])
    