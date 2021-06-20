# -*- coding: utf-8 -*-
"""
Created on Sat Jun 5 15:30:03 2021

@author: ryanz
"""

#-------------- table_cog.py methods --------------#

#default max teams based on format (currently used for ffa format only)
def max_teams(f):
    f = f[0]
    if f == 'f':
        return 12
    else:
        f = int(f)
        return 12/f
    
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



#------------- Tabler.py methods --------------#

def convert_format(f):
    """
    get players per team based on format

    Parameters
    ----------
    f : format string

    Returns
    -------
    int of format(players per team)

    """
    f = f[0]
    if not f.isnumeric():
        return 1
    return int(f)

def full_format(f):
    if not f[0].isnumeric():
        return 'FFA'
    return '{}v{}'.format(int(f[0]), int(f[0]))

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
    used to find tags that are not prefixes are postfixes. 
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

import re 
from unidecode import unidecode

def strip_CJK(string):
    '''
    strip all cjk characters from string

    Returns
    -------
    string with no CJK characters

    '''
    string = list(string)
    ret = string
    for ind,i in enumerate(string):
        if is_CJK(i):
            del ret[ind]
    no_cjk = ''.join(ret)
    no_special = re.sub(r'\W+', '', no_cjk, re.UNICODE)
    return no_special


def replace_brackets(string):
    string = string.lstrip('[').lstrip(']').lstrip('(').lstrip(')').lstrip('{').lstrip('}')
    string = list(unidecode(string))
    ret = string
    for ind,i in enumerate(string):
        if not i.isalpha():
            del ret[ind]
    return ''.join(ret)

def dis_clean(string):
    return string.replace("*", "\*").replace("`",'\`').replace("_", "\_")
    