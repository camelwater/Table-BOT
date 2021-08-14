from collections import defaultdict
import aiohttp
from bs4 import BeautifulSoup
from typing import Tuple, Dict, Any, Optional
import utils.tagUtils as tagUtils


async def fetch(url, headers=None): 
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession() as session:
        if headers is None:
            try:
                async with session.get(url, timeout=timeout) as response:
                    if response.status!=200:
                        return 'response error'
                    return BeautifulSoup(await response.text(), 'html.parser')
            except:
                return 'timeout error'

        else:
            try:
                async with session.get(url, timeout=timeout, headers=headers) as response:
                    if response.status!=200:
                        return 'response error'
                    return BeautifulSoup(await response.text(), 'html.parser')
            except:
                return 'timeout error'

async def fetch_mkwx_JSON(url, headers=None):
    url+="?m=json"
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession() as session:
        if headers is None:
            try:
                async with session.get(url, timeout=timeout) as response:
                    if response.status!=200:
                        return 'response error'
                    return await response.json()
            except:
                return 'timeout error'

        else:
            try:
                async with session.get(url, timeout=timeout, headers=headers) as response:
                    if response.status!=200:
                        return 'response error'
                    return await response.json()
            except:
                return 'timeout error'

async def search_mii(mii, URL) -> Tuple[bool, Any]:
        '''
        find room on mkwx with given mii names

        returns
        ---
        rxx of found room
        '''
        rxxs = defaultdict(int)
        data = await fetch_mkwx_JSON(URL)
        if isinstance(data, str) and 'error' in data:
            if 'response' in data:
                return True, "Wiimmfi appears to be down. Try again later."
            else:
                return True, "I am currently experiencing some issues with Wiimmfi. Try again later."
        
        if len(data[1:-1])<1:
            return True, "I am currently experiencing some issues with Wiimmfi's API. Try again later."
        
        for room in data:
            if room.get("type")!="room": continue
            room_rxx = room.get("room_id")
            room_players = []
            for player in room.get("members", []):
                miiName = player.get('name')[0][0]
                if not miiName or miiName == "no name": miiName = "Player"
                room_players.append(tagUtils.sanitize_uni(miiName.strip(), for_search=True).lower())
            if set(map(lambda l: tagUtils.sanitize_uni(l.strip(), for_search=True).lower(),mii)).issubset(room_players):
                rxxs[room_rxx]+=1

        return False, rxxs

def check_repeat_times(race, prev_races) -> Tuple[bool, Optional[Dict[str, int]]]:
    race = [i for i in race[2]]
    prev_races = [i[2] for i in prev_races]
    repetitions = defaultdict(int)
    dc_repetitions = defaultdict(int)

    for c_indx, compare in enumerate(prev_races[::-1]):
        for player1, player2 in zip(race, compare):
            if player1[0] == player2[0]:
                if player1[1] != 'DC' and player1[1] == player2[1]:
                    repetitions[c_indx] += 1
                elif player1[1] == 'DC' and player1[1] == player2[1]:
                    dc_repetitions[c_indx]+=1

    repetitions = dict(repetitions)
    try:
        most_key = max(repetitions, key=repetitions.get)
    except ValueError:
        most_key = None

    if most_key is None:
        return False, None
    
    most_rep = repetitions[most_key] + dc_repetitions[most_key]
    return True, {'race': len(prev_races)-most_key, 'num_aff': most_rep}

def check_repeat_times_slow(race, prev_races):
    repetitions = {}
    race = [(i[0], i[1]) for i in race]
    prev_races = [[(i[0], i[1]) for i in r] for r in prev_races]

    for i, r in enumerate(prev_races[::-1]):
        cou = len([c for c in race if c in r])
        if cou>0:
            repetitions[i] = cou
    
    try:
        max_key = max(repetitions, key=repetitions.get)
    except ValueError:
        max_key = None

    return (True, {'race': len(prev_races)-max_key, 'num_aff': repetitions[max_key]}) if max_key else (False, {})
