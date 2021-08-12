# -*- coding: utf-8 -*-
"""
Created on Tue May 18 15:05:35 2021

@author: ryanz
"""
from bs4 import BeautifulSoup
from typing import Tuple, List, Dict, Any
import copy
#from PIL import Image
from io import BytesIO
from urllib.parse import quote
import aiohttp
import concurrent.futures
# from urllib.request import urlopen
import datetime
import discord
from discord.ext import tasks, commands
import time as timer
from unidecode import unidecode
from collections import defaultdict, Counter
from find_tags import tag_algo
import tag_testing.simulatedAnnealingTag as simAnl
from utils.WiimmfiMii import get_wiimmfi_mii, get_wiimmfi_mii_async
import utils.Utils as Utils
from utils.Utils import isFFA, WARNING_MAP, DC_MAP, STYLE_MAP, PTS_MAP
from utils.Utils import GRAPH_MAP as GM
from Player import Player

# TODO: maybe automate first race dcs (18 and 15 pts) 

class Table():
    def __init__(self, ctx = None, bot = None, testing = False):
        self.TESTING = testing
        self.IGNORE_FCS = False
        if self.TESTING:
            self.init_testing()
        
        self.URL = "https://wiimmfi.de/stats/mkwx"
        self.ROOM_URL = "https://wiimmfi.de/stats/mkwx/list/{}"
        self.current_url = ""
        self.last_race_update = None #timestamp of last auto-update table
        
        self.modifications: List[List[Tuple]] = [] #keep track of all user modifications to the table
        self.undos: List[List[Tuple]] = [] #keep track of all user undos of modifications to the table
        
        self.recorded_elems: List[str] = [] #don't record races that have already been recorded
        self.players: List[Player] = [] #dictionary of players: holds their total score, gp scores, and race scores
        self.races: List[Tuple[str, str, List]] = [] #list (race) of lists (placements for each race) 
        self.team_pens = {} #mapping penalties to teams
        self.player_ids: Dict[int, Player] = {} #used to map player ids to players (player id from bot)
        self.all_players: List[Player] = [] #list of every player who has been in the room
        self.subs: List[Dict[str, Any]] = [] #players who have been subbed out 
        self.deleted_players: List[Player] = [] #players who have been removed from table through ?changename
       
        self.warnings = defaultdict(list) #race: list of warnings
        self.manual_warnings = defaultdict(list) #warnings of manual changes to the table

        self.dc_list = defaultdict(list) # race: list of player dcs (?dcs)
        self.dup_names: List[str] = [] #in case some players have same mii name. fc: edited mii name (ex. 'Player-1' instead of 'Player') for clarity purposes on table
        self.names: List[str] = []
        self.gp_dcs: Dict[int, List[Player]] = {} #gp: list of players who have dced in gp (to ensure dc warnings are simplified in embed)
        self.dc_list_ids: Dict[int, Tuple[Player, int]] = {} #mapping dcs to an id (used for the command ?dcs)
        self.temp_dc_list = []
        
        self.removed_races: Dict[int, List] = {} #races removed with ?removerace (for restoring from ?undo)
        self.removed_warn_dcs = {} #for restoring when ?removerace undone
        
        self.room_sizes = [] #list of room sizes for different gps (check if room size increases mid-gp, to send warning message - ?changeroomsize might be necessary)
        self.room_players = [] #list of lists of players at beginning of GP (check if room changes mid-gp, send warning)
        self.room_sizes_error_affected = [] #races affected by mkwx messing up room sizes
        self.room_error_index = [] #to update room size warnings
        
        self.changed_room_sizes = defaultdict(list) #races that have edited room sizes (?changeroomsize)
        self.edited_scores = defaultdict(lambda: defaultdict(int)) #players with edited gp scores
                   
        self.tags: Dict[str, List[Player]] = {} #list of team tags and their respective players
        self.table_str = "" #argument for data (to get pic from gb.hlorenzi.com)
        self.graph_map = copy.deepcopy(GM)
        self.graph = None #table picture graph
        self.style = None #table picture theme/style
        self.table_img = None
        self.table_link = '' #gb.hlorenzi image URI link
        self.sui = False #whether should ignore large finish times or not
        
        self.prev_rxxs: List[List[str]] = [] # for rooms that have been merged
        self.prev_elems: List[List[str]] = [] #prev elems of rooms before merge
        self.current_elems: List[str] = [] #elem list of current room
        # self.restore_merged = []
        
        self.format = "" #format (FFA, 2v2, etc.)
        self.teams = 0 #number of teams
        self.gps = 3 #number of total gps
        self.rxx = '' #rxx that table is watching
        self.gp = 0 #current gp
        self.num_players = 0 #number of players room is supposed to have (based on format and teams)
        
        ##### Stuff for bot instances #####
        self.choose_message = ""
        self.searching_room = False
        self.confirm_room = False
        self.confirm_reset = False
        self.reset_args = None
        self.table_running = False
        self.picture_running = False
        self.ctx: commands.Context = ctx
        self.prefix = ctx.prefix
        self.bot: commands.Bot = bot
        self.last_command_sent = None
        ##### Stuff for bot instances #####
        
    def init_testing(self):

        # self.players = {'pringle@MV':0,'5headMV':0,'hello LTA':0,'LTAX':0,
        #     'jaja LTA':0,'stupid@LTA':0,'poop MV':0,'MVMVMVMV':0,'LTA Valpo':0,"5 guys mom's spaghet":0}
        # self.players = {'x#1':0, 'awd':0, 'Ryan@X':0, '¢unt':0, 'stop man': 0, 'cool kid cool': 0, "GG EZ": 0, 'gas mob':0, "gassed up":0, "kaya yanar":0, "yaya kanar":0, "yaka ranar":0}
        # self.players = {'hello':0, 'stupid':0, 'VA':0, 'banned':0, '090':0, 'hell&*':0, 'what?':0, "who?":0, "λxe":0, 'AAA':0, 'λp fraud':0, 'ABB':0}
        self.players = {'hello':0, 'he123':0, 'borrowed time':0, 'banned':0, 'barrel':0, 
                'hell&*':0, 'what?':0, "who?":0, "λxe":0, 'AAA':0, 'λp fraud':0, 'where?':0}
        
        self.IGNORE_FCS = True
        self.split_teams('3', 4)
    
    async def search_mii(self, mii) -> Tuple[bool, Any]:
        '''
        find room on mkwx with given mii names\n
        returns
        --
        rxx of found room
        '''
        rxxs = defaultdict(int)
        data = await self.fetch_mkwx_JSON(self.URL)
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
                room_players.append(Utils.sanitize_uni(miiName.strip(), for_search=True).lower())
            if set(map(lambda l: Utils.sanitize_uni(l.strip(), for_search=True).lower(),mii)).issubset(room_players):
                rxxs[room_rxx]+=1

        return False, rxxs

    async def find_room_to_merge(self, rid: str=None, mii: List[str]=None, redo=False) -> Tuple[bool, str]:
        '''
        find room when `merge` command is used
        '''
        if rid is None: #mii names search
            ret_error, rxxs = await self.search_mii(mii)
            if ret_error:
                return True, rxxs
    
            if len(rxxs)==0:
                return True, "{} {} not found in any rooms.\nMake sure all mii names are correct.".format(', '.join(map(lambda l: f"`{Utils.backtick_clean(l)}`",mii)), "were" if len(mii)>1 else "was")
            if len(rxxs)>1:
                if len(mii)==1:
                    return True, "`{}` was found in multiple rooms: {}.\nTry again with a more refined search.".format(Utils.backtick_clean(mii)[0], list(rxxs.keys()))
                rxx = [keys for keys,values in rxxs.items() if values == max(rxxs.values())]
                if len(rxx)>1:
                    return True, "{} {} found in multiple rooms: {}.\nTry again with a more refined search.".format(', '.join(map(lambda l: f"`{Utils.backtick_clean(l)}`",mii)), "were" if len(mii)>1 else "was", rxx)
            
            rxx = 'r'+ str(max(rxxs, key=rxxs.get))
            if rxx==self.rxx or rxx in self.prev_rxxs:
                return True, "This room is already part of this table. Merge cancelled."
            
            room_url = "https://wiimmfi.de/stats/mkwx/list/{}".format(rxx)
            
            soup = await self.fetch(room_url)
            if isinstance(soup, str) and 'error' in soup:
                if 'response' in soup:
                    return True, "Wiimmfi appears to be down. Try again later."
                else:
                    return True, "I am currently experiencing some issues with Wiimmfi. Try again later."
                
            if "No match found!" in list(soup.stripped_strings):
                return True, f"The room ({rxx}) hasn't finished a race yet.\nRetry `{self.prefix}mergeroom` when the room has finished one race."
            
            if not redo:
                self.modifications.append([("mergeroom {}".format(', '.join(mii)), len(self.prev_elems), rxx)])
                self.undos.clear()
            
        else: #rxx search
            rxx = rid[0]
            if len(rxx) == 4: rxx = rxx.upper()

            if rxx==self.rxx or rxx in self.prev_rxxs:
                return True, "This room is already part of this table. Merge cancelled."
            room_url = "https://wiimmfi.de/stats/mkwx/list/{}".format(rxx)
            
            soup = await self.fetch(room_url)
            if isinstance(soup, str) and 'error' in soup:
                if 'response' in soup:
                    return True, "Wiimmfi appears to be down. Try again later."
                else:
                    return True, "I am currently experiencing some issues with Wiimmfi. Try again later."
            
            stripped = list(soup.stripped_strings)
            if "No match found!" in stripped:
                return True, f"The room ({rxx}) either doesn't exist or hasn't finished a race yet.\nRetry `{self.prefix}mergeroom` when the room has finished at least one race and ensure that the room id is in *rxx* or *XX00* format."
            
            if not redo:
                self.modifications.append([(f"mergeroom {rxx}", len(self.prev_elems), rxx)])
                self.undos.clear()

        self.current_url = room_url
        self.prev_rxxs.append(self.rxx)
        self.prev_elems.append(self.current_elems)
        self.current_elems=[]
        self.rxx = rxx
        self.last_race_update = None
        new_elems = soup.select('tr[id*=r]')
        return False, f"Rooms have successfully merged. Now watching room {self.rxx}. {len(self.races)+len(new_elems)} races played."
            
    async def find_room(self, rid: str = None, mii: List[str] = None) -> Tuple[bool, str]:
        """
        find mkwx room using either rxx or mii name search
        """
        if rid is None: #mii names search
            ret_err, rxxs = await self.search_mii(mii)
            if ret_err:
                return True, rxxs
            
            if len(rxxs)==0:
                return True, "{} {} not found in any rooms.\nMake sure all mii names are correct.".format(', '.join(map(lambda l: f"`{Utils.backtick_clean(l)}`",mii)), "were" if len(mii)>1 else "was")
            if len(rxxs)>1:
                if len(mii)==1:
                    return True, "`{}` was found in multiple rooms: {}.\nTry again with a more refined search.".format(Utils.backtick_clean(mii[0]), list(rxxs.keys()))
                rxx = [keys for keys,values in rxxs.items() if values == max(rxxs.values())]
                if len(rxx)>1:
                    return True, "{} {} found in multiple rooms: {}.\nTry again with a more refined search.".format(', '.join(map(lambda l: f"`{Utils.backtick_clean(l)}`",mii)), "were" if len(mii)>1 else "was", ', '.join(map(str,rxx)))
            
            rxx = 'r' + str(max(rxxs, key=rxxs.get))
            self.rxx = rxx

            room_url = "https://wiimmfi.de/stats/mkwx/list/{}".format(self.rxx)
            soup = await self.fetch(room_url)

            if isinstance(soup, str) and 'error' in soup:
                if 'response' in soup:
                    return True, "Wiimmfi appears to be down. Try again later."
                else:
                    return True, "I am currently experiencing some issues with Wiimmfi. Try again later."

            if "No match found!" in list(soup.stripped_strings):
                return True, "The room hasn't finished a race yet.\nRetry when the room has finished one race."    
            
        else: #room id search
            rid = rid[0]
            self.rxx = rid
            if len(rid)==4: self.rxx = self.rxx.upper()
            
            room_url = "https://wiimmfi.de/stats/mkwx/list/{}".format(rid)
            soup = await self.fetch(room_url)

            if isinstance(soup, str) and 'error' in soup:
                if 'response' in soup:
                    return True, "Wiimmfi appears to be down. Try again later."
                else:
                    return True, "I am currently experiencing some issues with Wiimmfi. Try again later."
            
            if "No match found!" in list(soup.stripped_strings):
                return True, f"The room either doesn't exist or hasn't finished a race yet.\nRetry when the room has finished a race and make sure the room id is in *rxx* or *XX00* format."
        
        self.find_players(room_url, soup)
        self.split_teams(self.format, self.teams)
        self.current_url = room_url
        string = self.room_list_str()

        return False, f"Room {self.rxx} found.\n{string}\n\n**Is this room correct?** (`{self.prefix}yes` / `{self.prefix}no`)"

    def populate_table_flags(self, subs=None):
        '''
        get Miis of all players and get their region codes
        '''
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:
            futures = {executor.submit(get_wiimmfi_mii, player.getFC()): player for player in (self.players if subs is None else subs)}
            for future in concurrent.futures.as_completed(futures):
                player: Player = futures[future]
                try:
                    mii_result = future.result()
                    if mii_result: player.flag_code = mii_result.countryCode
                except Exception as e:
                    raise e
    
    def room_list_str(self) -> str:
        string = ""
        counter = 1
        if isFFA(self.format):
            string+='\n__FFA__'
            for p in self.players:
                string+=f"\n{counter}. {Utils.disc_clean(p.getName())}"
                self.player_ids[str(counter)] = p
                counter+=1          
        else:
            self.tags = dict(sorted(self.tags.items(), key=lambda item: Utils.sanitize_uni(item[0].upper())))
            for tag in self.tags.keys():
                string+=f'\n**Tag: {Utils.disc_clean(tag)}**'
                for p in self.tags[tag]:
                    string+=f"\n\t{counter}. {Utils.disc_clean(p.getName())}"
                    self.player_ids[str(counter)] = p
                    counter+=1
        return string

    def split_teams(self, f, num_teams):
        """
        split players into teams based on tags
        """
        
        tick=timer.time()
        f = f[0]
        if not f.isnumeric():
            return
        per_team = int(f)
        name_to_player = {}
        for i in self.players:
            name_to_player[i.getName()] = i
        player_copy = list(name_to_player.keys()) if not self.IGNORE_FCS else list(copy.deepcopy(self.players).keys())
        
        teams = tag_algo(player_copy, per_team = per_team, num_teams = num_teams)
        
        if self.TESTING:
            L = []
            for i in teams.items():
                L.append([Utils.sanitize_uni(i[0]).lower(), list(map(lambda l: (Utils.sanitize_uni(l.strip()).lower(), l), i[1]))])
            cost_check = simAnl.SimulatedAnnealing(L, per_team)
            print("cost:", cost_check.E(L))

        if not self.IGNORE_FCS:
            print(teams)
            for t, ps in teams.items():
                teams[t] = [name_to_player[name] for name in ps]

        self.tags = teams
        self.tags = dict(sorted(self.tags.items(), key=lambda item: Utils.sanitize_uni(item[0].lower())))
        self.tags = {("NO TEAM" if k.strip()=="" else k.strip()): v for (k, v) in self.tags.items()}

        print()
        print(self.tags)
        print("tag algo time:",timer.time()-tick)
        

    def warn_to_str(self, warning: Dict[str, Any]) -> str:                
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
            return WARNING_MAP.get(warning_type).format(warning.get('gp'), warning.get('cur_players'), warning.get('sup_players'))
        
        elif warning_type == "missing_w_sub":
            return WARNING_MAP.get(warning_type).format(warning.get('gp'), warning.get('num_missing'), [i.getName() for i in warning.get('missing_players')])
        
        elif warning_type == "overflow":
            return WARNING_MAP.get(warning_type).format(warning.get('gp'), warning.get('cur_players'), warning.get('sup_players'))
        
        elif warning_type == "blank_time":
            return WARNING_MAP.get(warning_type).format(warning.get('player').getName())

        elif warning_type == "tie":
            return WARNING_MAP.get(warning_type).format([i.getName() for i in warning.get('players')], warning.get('time'))

        elif warning_type == "sub":
            if warning.get('is_edited', False):
                return WARNING_MAP.get("sub_conf").format(warning.get('player').getName(), warning.get('sub_out').getName())
            else:
                return WARNING_MAP.get(warning_type).format(warning.get('player').getName())

        elif warning_type == "large_time":
            return WARNING_MAP.get(warning_type).format(warning.get('player').getName(), warning.get('time'))

        else:
            print("WARNING TYPE NOT FOUND:", warning_type)
            raise AssertionError

    def get_warnings(self, show_large_times = None, override=False) -> Tuple[bool, str, str]:
        if override is True: show_large_times = True
        warnings = defaultdict(list)

        if show_large_times is False:
            warnings[-1].insert(0, 'Large finish times occurred, but are being ignored. Table could be inaccurate.')
        elif show_large_times is None and self.sui:
            warnings[-1].insert(0, 'Large finish times occurred, but are being ignored. Table could be inaccurate.')

        #merging self.warnings with self.manual_warnings
        for race, warn_list in self.manual_warnings.items():
            warnings[race] += warn_list

        for race, warn_list in self.warnings.items():
            if race ==-1:
                warnings[race] = warn_list + warnings[race]
            else:
                warn_list_copy = copy.copy(warn_list)
                for indx,w in list(enumerate(warn_list_copy))[::-1]:
                    if isinstance(w, dict) and w.get('type')=='large_time':
                        if show_large_times is False:
                            warn_list_copy.pop(indx)
                        elif show_large_times is None and self.sui:
                            warn_list_copy.pop(indx)
                warnings[race]+=warn_list_copy

        actual_warn_len = sum([len(i[1]) for i in warnings.items()])
        if actual_warn_len==0:
            if override: return "No warnings or room errors. Table should be accurate."
            return False, "No warnings or room errors. Table should be accurate.", None
            
        warnings = defaultdict(list,dict(sorted(warnings.items(), key=lambda item: item[0])))
        ret = 'Room warnings/errors{}:\n'.format(f" ({self.prefix}dcs to fix dcs)" if len(self.dc_list)>0 else "")
        
        for indx,i in enumerate(warnings[-1]):
            if "scores have been manually modified" in i:
                warnings[-1].append(warnings[-1].pop(indx))

        for i in warnings.items():
            if len(i[1])==0:
                continue
            if i[0]==-1:
                for warning in i[1]:
                    ret+=f'     - {warning}\n'
                continue
            ret+=f"     Race #{i[0]}: {self.races[i[0]-1][1]}\n"
            for warning in i[1]:
                ret+=f"       \t- {self.warn_to_str(warning) if isinstance(warning, dict) else warning}\n"

        ret = ret.replace("[[/PREFIX\]]", self.prefix)
        if override: return ret
        if len(ret)>2020:
            fixed_ret = ret[:2020]
            fixed_ret+="... (full errors in file)"
            return True, fixed_ret, ret
        
        return False, ret, None
    
    def set_sui(self, sui_setting):
        try:
            self.sui = Utils.determine_ILT(sui_setting, self.format)
        except (ValueError, IndexError):
            pass #I don't think it will ever reach here, but just in case

    def check_num_teams(self):
        if len(self.tags)!=self.teams:
            self.set_teams(len(self.tags))

    def set_teams(self, teams):
        self.teams = teams
        if self.teams!=2 and 3 in self.graph_map:
            self.graph_map.pop(3)
            if self.graph and self.graph.get('table') == 'diff':
                # self.graph_map = copy.deepcopy(self.graph)
                self.graph = None
        elif self.teams==2 and 3 not in self.graph_map:
            self.graph_map[3] = copy.copy(GM[3])

    def style_options(self):
        ret = 'Table style options:'
        for num,style in STYLE_MAP.items():
            ret+="\n   {} {}".format("**{}.**".format(num) if self.style and self.style.get('type') == style.get('type') else "`{}.`".format(num), style.get('type'))
        return ret
    
    def graph_options(self):
        ret = 'Table graph options:'
        for num,graph in self.graph_map.items():
            ret+="\n   {} {}".format("**{}.**".format(num) if self.graph and self.graph.get('type') == graph.get('type') else "`{}.`".format(num), graph.get('type'))
        return ret

    def change_style(self, choice: str, reundo=False):
        if choice is None:
            self.style=choice
            return

        if choice.lstrip('+').lstrip('-').isnumeric():
            c_indx = int(choice)
            choice = STYLE_MAP.get(c_indx, None)
            if not choice:
                return f"`{c_indx}` is not a valid style number. The style number must be from 1-{len(STYLE_MAP)}. Look at `{self.prefix}style` for reference."
            
            if not reundo:
                self.modifications.append([(f"style {c_indx}", self.style.get('type') if self.style is not None else None, choice.get('type'))])
                self.undos.clear()
            
            self.style = choice
            return "Table style set to `{}`.".format(choice.get('type'))

        else:
            o_choice = choice
            not_in = True
            for i in list(STYLE_MAP.values()):
                if choice.lower() in map(lambda l: l.lower(), i.values()):
                    not_in=False
                    break
            if not_in:
                options = ''
                for i in list(STYLE_MAP.values()):
                    options+='   - {}\n'.format(" | ".join(map(lambda orig: "`{}`".format(orig), i.values())))
                    
                return "`{}` is not a valid style. The following are the only available style options:\n".format(o_choice)+options
            
            for i in list(STYLE_MAP.values()):
                if choice.lower() in map(lambda l: l.lower(), i.values()):
                    choice = i
                    break
            
            if not reundo:
                self.modifications.append([(f"style {o_choice}", self.style.get('type') if self.style is not None else None, choice.get('type'))])
                self.undos.clear()
            
            self.style = choice
            return "Table style set to `{}`.".format(choice.get('type'))

    def change_graph(self, choice: str, reundo=False):
        if choice is None:
            self.graph = choice
            return
     
        if choice.lstrip('+').lstrip('-').isnumeric():
            c_indx = int(choice)
            choice = self.graph_map.get(c_indx, None)
            if not choice:
                return "`{}` is not a valid graph number. The graph number must be from 1-{}. Look at `{}graph` for reference.".format(c_indx, len(self.graph_map), self.prefix)
            
            if self.teams != 2 and choice.get('table') == 'diff':
                return "The graph type `{}` can only be used when there are two teams.".format('Difference')

            if not reundo:
                self.modifications.append([(f"graph {c_indx}", self.graph.get('type') if self.graph is not None else None, choice.get('type'))])
                self.undos.clear()
            
            self.graph = choice
            return "Table graph set to `{}`.".format(choice.get('type'))

        else:
            o_choice = choice
            not_in = True
            for i in list(self.graph_map.values()):
                if choice.lower() in map(lambda l: l.lower(), i.values()):
                    not_in=False
                    break
            if not_in:
                options = ''
                for i in list(self.graph_map.values()):
                    options+='   - {}\n'.format(" | ".join(map(lambda orig: "`{}`".format(orig), i.values())))
                    
                return "`{}` is not a valid graph. The following are the only available graph options:\n".format(o_choice)+options
            
            for i in list(self.graph_map.values()):
                if choice.lower() in map(lambda l: l.lower(), i.values()):
                    choice = i
                    break
            
            if self.teams != 2 and choice.get('table') == 'diff':
                return "The graph type `{}` can only be used when there are two teams.".format('Difference')
            
            if not reundo:
                self.modifications.append([(f"graph {o_choice}", self.graph.get('type') if self.graph is not None else None, choice.get('type'))])
                self.undos.clear()
            
            self.graph= choice
            return "Table graph set to `{}`.".format(choice.get('type'))

    def title_str(self) -> str:
        ret = f'{Utils.full_format(self.format)}{"" if Utils.full_format(self.format)=="FFA" else ":"} '
        tags_copy = list(self.tags.keys())
        try:
            tags_copy.remove("SUBS")
        except ValueError:
            pass
        try:
            tags_copy.remove("")
        except ValueError:
            pass
        for index, i in enumerate(tags_copy):
                if index==len(tags_copy)-1:
                    ret+=f"`{i}` "
                else:
                    ret+=f"`{i}` vs "
        ret+=f"({len(self.races)} {'race' if len(self.races)==1 else 'races'})"
        return ret
    
    def check_tags(self, tag) -> str:
        x=1
        new = tag
        if tag in self.tags:
            new = tag+'-'+str(x)
            x+=1
        return new

    def edit_tag_name(self, l, reundo=False):  
        ret = ''
        for num,e in enumerate(l):
            orig = t_orig = e[0]
            new = e[1]
            if orig.isnumeric():
                try:
                    orig = list(self.tags.keys())[int(orig)-1]
                except IndexError:
                    return f"Tag index `{orig}` is out of range. The tag number must be from 1-{len(self.tags)}"
                data = self.tags.pop(orig)
                new = self.check_tags(new)
                self.tags[new]= data
                ret+= f"Edited tag `{Utils.backtick_clean(orig)}` to `{Utils.backtick_clean(new)}`."+ ('\n' if len(l)>1 and num <len(l)-1 else '')
                
            else:
                comp = orig.upper()
                actual_orig = orig
                try:
                    data = None
                    for i in self.tags.keys():
                        if comp == i.upper():
                            data = self.tags.pop(i)
                            actual_orig = i
                            break
                    assert(data is not None)
                except AssertionError:
                    string = f"Tag `{Utils.backtick_clean(orig)}` is not a valid tag. The tag to edit must be one of the following:\n"
                    for i in list(self.tags.keys()):
                        string+='   - `{}`\n'.format(i)
                    return string
                new = self.check_tags(new)
                self.tags[new] = data
                ret+= f"Edited tag `{Utils.backtick_clean(actual_orig)}` to `{Utils.backtick_clean(new)}`."+ ('\n' if len(l)>1 and num <len(l)-1 else '')
                
            if not reundo and self.table_running:
                self.modifications.append([(f'edittag {t_orig} {new}', new, actual_orig)])
                self.undos.clear()

        return ret
    
    def tracklist(self):
        ret = ''
        for i, race in enumerate(self.races):
            track = race[1]
            ret+=f'Race #{i+1}: {track}\n'
        return ret
    
    def get_finish_times(self, index) -> Dict[Player, str]:
        race = self.races[index]
        return {player[0]: player[1] for player in race[2]}

    def race_results(self,race) -> Tuple[bool, str]:
        ret = ''
        results = {}
        tag_places = defaultdict(list)
        if race==-1:
            race = len(self.races)
            results = self.get_finish_times(race-1)

        else: 
            if race > len(self.races):
                return True, f"Race `{race}` doesn't exist. The race number should be from 1-{len(self.races)}."
            results = self.get_finish_times(race-1)
       
        count = 0
        ret+=f"Race #{race} - {self.races[race-1][1]}:\n"
        for player, time in list(results.items()):
            count+=1
            ret+=f"   {count}. {Utils.disc_clean(player.getName())} - {time}\n"
            if not isFFA(self.format):
                for t in self.tags.items():
                    if player in t[1]:
                        tag_places[t[0]].append(count)
            
        if not isFFA(self.format):
            tag_places = dict(sorted(tag_places.items(), key=lambda item: sum([PTS_MAP[count][i-1] for i in item[1]]), reverse=True))

            ret+="\n"
            for tag, placements in tag_places.items():
                ret+=f"**{tag}** -"
                for p in placements:
                    ret+=f" {p}{'' if p==placements[-1] else ' ,'}"
                pts_sum = sum([PTS_MAP[count][i-1] for i in placements])
                ret+=f" (**{pts_sum}** {'pt' if pts_sum == 1 else 'pts'})"
                ret+= "" if tag==list(tag_places.items())[-1][0] else "   |   "
        return False,ret
    
    def change_tag(self, player: str, tag: str, restore_indx = None,reundo=False):
        if not reundo:
            p_indx=player
            try:
                player: Player = self.player_ids[player]
            except KeyError:
                return f"Player number `{player}` is not valid. It must be from {1}-{len(self.players)}."
        old_tag = ""
        for i in self.tags.items():
            if player in i[1]:
                old_tag = i[0]
                old_indx = i[1].index(player)
                i[1].remove(player)
        existing_tag = None
        if tag in self.tags:
            existing_tag = tag
        else:
            for indx, i in enumerate(list(map(lambda l: Utils.sanitize_uni(l.strip()).lower(),self.tags.keys()))):
                if tag.lower() == i:
                    existing_tag = list(self.tags.keys())[indx]
                    break
            
        if existing_tag:
            if reundo and restore_indx is not None:
                self.tags[existing_tag].insert(restore_indx, player)
            else:
                self.tags[existing_tag].append(player)
        else:
            self.tags[tag] = [player]

        empty_keys = [k[0] for k in list(self.tags.items()) if len(k[1])==0]
        for k in empty_keys:
            del self.tags[k]

        if not reundo and self.table_running:
            self.modifications.append([(f"changetag {p_indx} {tag}", player, tag, old_tag, old_indx)])

        return f"`{Utils.backtick_clean(player.getName())}` tag changed from `{Utils.backtick_clean(old_tag)}` to `{Utils.backtick_clean(existing_tag if existing_tag else tag)}`."
       
    def group_tags(self, dic, redo=False):
        if not redo:
            orig_tags = copy.deepcopy(self.tags)
            dic_str = ''
            for ind, i in enumerate(list(dic.items())):
                dic_str+="{} ".format(i[0])
                for j in i[1]:
                    dic_str+='{} '.format(j)
                if ind!=len(dic)-1: dic_str+="/ "

        affected_players = []
        for i in dic.items():
            for j in range(len(i[1])):
                try:
                    affected_players.append(self.player_ids[i[1][j]])
                    i[1][j] = self.player_ids[i[1][j]]
                except KeyError:
                    del i[1][j]
        for i in self.tags.items():
            for j in affected_players:
                if j in i[1]:
                    i[1].remove(j)
        leftovers = []
        for i in dic.items():
            if i[0] not in self.tags:
                self.tags[i[0]] = i[1]
            else:
                for j in self.tags[i[0]]:
                    if j not in i[1] and j not in affected_players:
                        leftovers.append(j)
                self.tags[i[0]] = i[1]
        
        per_team = Utils.convert_format(self.format)
        if len(leftovers)>0:
            for i in self.tags.items():
                while len(i[1])!=per_team:
                    try:
                        i[1].append(leftovers.pop(0))
                    except IndexError:
                        break
        removal = []
        for x in self.tags.items():
            if len(x[1])==0: removal.append(x[0])
        for i in removal:
            self.tags.pop(i)
        
        if not redo and self.table_running:
            self.modifications.append([(f"tags {dic_str}", orig_tags, dic)])
        
        return "Tags updated."
    
    def undo_group_tags(self, restore_tags):
        for tag, tag_players in self.tags.items():
            if tag == "SUBS" or "":
                restore_tags[tag].extend(tag_players)
        self.tags = restore_tags

    def change_name(self, l, redo=False): 
        ret = ''
        for j in l:
            player = p_indx = j[0]
            if not redo:
                try:
                    player: Player = self.player_ids[player]
                except KeyError:
                    ret+=f"Invalid player number `{player}`."
            old_name = player.getName() 
            if len(j)<2:
                new_name='#'
            else:
                new_name = j[1]
            new_name = self.check_name(new_name)
            self.names.append(new_name)

            should_del = False
            if new_name[0] in ['#','-']:
                should_del = True
            
            if should_del: 
                self.deleted_players.append(player)
            else:
                player.name = new_name
            
            if not redo:
                self.modifications.append([(f'changename {p_indx} {new_name}', player, new_name, old_name, should_del)])
                self.undos.clear()
            ret+=f"`{Utils.backtick_clean(old_name)}` name changed to `{Utils.backtick_clean(player.getName())}`{' (removed from table)' if should_del else ''}.\n"
        
        return ret

    def undo_change_name(self, player: Player, restore_name, was_deleted):
        if was_deleted:
            self.deleted_players.remove(player)
        else:
            player.name = restore_name

    def get_player_list(self, p_form = True, include_tag = None, team_command = False):
        if include_tag is None:
            include_tag = not p_form
        
        counter = 1
        string =''
        self.tags = dict(sorted(self.tags.items(), key=lambda item: Utils.sanitize_uni(item[0].upper())))
        if isFFA(self.format):
            for p in self.players:
                if p in self.deleted_players: continue
                
                string+=f"\n{f'`{counter}.` ' if p_form else f'{counter}. '}{Utils.disc_clean(p.get_full_name(len(self.races)))}"
                self.player_ids[str(counter)] = p
                counter+=1
        else:
            for t_indx, tag in enumerate(list(self.tags.keys())):
                string+=f'\n{f"`{t_indx+1}.` " if team_command else ""}**{"Tag: " if include_tag else ""}{Utils.disc_clean(tag)}**'
                for p in self.tags[tag]:
                    self.player_ids[str(counter)] = p
                    if p in self.deleted_players: continue
                   
                    string+=f"\n{' '*4 if include_tag else ' '*3}{f'`{counter}.` ' if p_form and not team_command else f'{counter}. '}{Utils.disc_clean(p.get_full_name(len(self.races)))}"
                    counter+=1

        return string

    def dc_to_str(self, dc: Dict[str, Any]) -> str:
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

    def dc_list_str(self): 
        ret = "DCs in the room:\n"

        if len(self.dc_list)==0:
            ret+="**No DCs.**"
            return ret

        dc_count = 1
        for race in list(self.dc_list.items()):
            ret+=f'**Race #{race[0]}: {self.races[int(race[0]-1)][1]}**\n'
            for dc in race[1]:
                ret+=f'\t`{dc_count}.` **{self.dc_to_str(dc)}\n'
                dc_count+=1
                
        return ret
        
    def dc_ids_append(self,player: Player, race: int):
        self.temp_dc_list.append([player, race])
        self.temp_dc_list = sorted(self.temp_dc_list, key=lambda l: (l[1], Utils.sanitize_uni(l[0].getName())))
        self.dc_list_ids = {}
        for dcID, dc in enumerate(self.temp_dc_list):
            self.dc_list_ids[dcID+1] = dc
        for race, dcs in self.dc_list.items(): #sort dc_list within races
            self.dc_list[race] = sorted(dcs, key = lambda l: Utils.sanitize_uni(l.get('player').getName()))
        self.dc_list = defaultdict(list, dict(sorted(self.dc_list.items(), key = lambda l: l[0])))

    def edit(self,l, redo=False): 
        ret= ''

        for elem in l:
            player = elem[0]
            gp = elem[1]
            score = elem[2]
            if not redo:    
                try:
                    p_indx = int(player)
                    player: Player = self.player_ids[player]
                except KeyError:
                    ret+=f"`{player}` was not a valid player index. The player number must be from 1-{len(self.players)}.\n"
                    continue
        
            try:
                assert(int(gp)-1 <=self.gp)
            except AssertionError:
                ret+=f"`{gp}` was not a valid gp (player number `{p_indx}`). The gp number must be from 1-{self.gp+1}.\n"
                continue
            orig_edited_scores = copy.deepcopy(player.edited_scores)
            
            if '-' in score or '+' in score:
                if int(gp) in player.edited_scores:
                    player.edited_scores[int(gp)] += int(score)                    
                else:
                    player.edited_scores[int(gp)] = player.scores[1][int(gp)-1] + int(score)
                
                if not redo:
                    self.modifications.append([(f'edit {p_indx} {gp} {score}', player, gp, score, orig_edited_scores)])
                    self.undos.clear()
                
                try:
                    self.manual_warnings[-1].remove(f"GP {gp} scores have been manually modified by the tabler.")
                except ValueError:
                    pass
                self.manual_warnings[-1].append(f"GP {gp} scores have been manually modified by the tabler.")
                    
                ret += f"`{Utils.backtick_clean(player.getName())}` GP `{gp}` score changed to `{player.edited_scores[int(gp)]}`."
            else:
                player.edited_scores[int(gp)] = int(score)
                
                if not redo:
                    self.modifications.append([(f'edit {p_indx} {gp} {score}', player, gp, score, orig_edited_scores)])
                    self.undos.clear()
                
                try:
                    self.manual_warnings[-1].remove(f"GP {gp} scores have been manually modified by the tabler.")
                except ValueError:
                    pass
                self.manual_warnings[-1].append(f"GP {gp} scores have been manually modified by the tabler.")
                        
                ret+=f"`{Utils.backtick_clean(player.getName())}` GP `{gp}` score changed to `{score}`.\n"
        return ret
    
    def undo_edit(self, player: Player, orig_edited_scores):
        player.edited_scores = orig_edited_scores
       
    def get_rxx(self) -> str:
        ret = ""
        if len(self.prev_rxxs)>0:
            ret+="*Past rooms:*\n"
            for n, r in enumerate(self.prev_rxxs):
                ret+="\t{}. {} | {}\n".format(n+1, r, self.ROOM_URL.format(r))
        ret+= f'{"**Current room:**" if len(self.prev_rxxs)>0 else "Current room:"} {self.rxx} | {self.ROOM_URL.format(self.rxx)}'
        return ret
        
    def get_pen_player_list(self, c_form=True, team_command = False) -> str:
        counter = 1
        string =''
        self.tags = dict(sorted(self.tags.items(), key=lambda item: Utils.sanitize_uni(item[0].upper())))
        if isFFA(self.format):
            for p in self.players:
                self.player_ids[str(counter)] = p
                if p in self.deleted_players: continue
                
                string+=f"\n{f'`{counter}`' if c_form else counter}. {Utils.disc_clean(p.get_full_name(len(self.races)))} {'' if p.getPens() == 0 else f'(-{p.getPens()})'}"
                counter+=1
        else:
            for t_indx, tag in enumerate(list(self.tags.keys())):
                string+=f'\n{f"`{t_indx+1}`. " if team_command else ""}**{Utils.disc_clean(tag)}**'
                if tag in self.team_pens.keys(): 
                    string+=f" **(-{self.team_pens.get(tag)})**"
                for p in self.tags[tag]:
                    self.player_ids[str(counter)] = p
                    if p in self.deleted_players: continue
                   
                    string+=f"\n\t{f'`{counter}`' if c_form and not team_command else counter}. {Utils.disc_clean(p.get_full_name(len(self.races)))} {'' if p.getPens()==0 else f'(-{p.getPens()})'}"
                    counter+=1
                    
        return string
    
    def penalty(self,player, pen: str, reundo=False):
        if not reundo:
            try:
                p_indx = player
                player: Player = self.player_ids[player]
            except KeyError:
                return f"Invalid player number `{player}`."

        if pen[0] == '=':
            pen = int(pen.lstrip('=').lstrip('-'))
            pen = int(pen.lstrip('=').lstrip('-'))
            player.pens = pen
            
            if not reundo:
                self.modifications.append([('pen {} {}'.format(p_indx, '='+str(pen)), player, '='+str(pen))])
                self.undos.clear()
                
            return f"`{Utils.backtick_clean(player.getName())}` penalty set to `{pen}`."
        
        else:
            pen = int(pen.lstrip('-'))
            player.pens+=pen
            
            if not reundo:
                self.modifications.append([(f'pen {p_indx} {pen}', player, pen)])
                self.undos.clear()

            return f"`-{pen}` penalty given to `{Utils.backtick_clean(player.getName())}`."
    
    def unpenalty(self, player, unpen: str, reundo=False):
        if unpen !=None:
            unpen = int(unpen.lstrip('='))
        if not reundo:
            try:
                p_indx = player
                player: Player = self.player_ids[player]
            except KeyError:
                return f"Invalid player number `{player}`."

        if player.pens==0:
            return f"`{Utils.backtick_clean(player.getName())}` doesn't have any penalties."

        if unpen is None:
            orig_pen = player.pens
            player.pens = 0
            if not reundo:
                self.modifications.append([(f'unpen {p_indx}', player, orig_pen)])
                self.undos.clear()
            return f"Penalties for `{Utils.backtick_clean(player.getName())}` have been removed."
        else:
            player.pens -= unpen
            
            if not reundo: 
                self.modifications.append([(f'unpen {p_indx} {unpen}', player, unpen)])
                self.undos.clear()
            return f"Penalty for `{Utils.backtick_clean(player.getName())}` reduced by `{unpen}`."
        
    def team_penalty(self, team: str, pen: str, reundo = False):
        if team.isnumeric():
            try:
                t_indx = int(team)-1
                team = list(self.tags.keys())[t_indx]
            except IndexError:
                return f"Invalid team number `{team}`."
        try:
            try:
                assert(team in self.tags.keys())
            except AssertionError:
                lowered_tags = list(map(lambda l: Utils.sanitize_uni(l.strip()).lower(), self.tags.keys()))
                sanitized_tag = Utils.sanitize_uni(team.strip()).lower()
                assert(sanitized_tag in lowered_tags)
                team = list(self.tags.keys())[lowered_tags.index(sanitized_tag)]
        except AssertionError:
            valid_teams = ", ".join(list(map(lambda l: f'`{l}`', self.tags.keys())))
            return f"Invalid team name `{Utils.backtick_clean(team)}`. Valid teams: {valid_teams}."
        
        if pen[0] == '=':
            pen = int(pen.lstrip('=').lstrip('-'))
            self.team_pens[team] = pen
            if self.team_pens[team] == 0: self.team_pens.pop(team)
            
            if not reundo:
                self.modifications.append([(f"teampen {team} {'='+str(pen)}", team, '='+str(pen))])
                self.undos.clear()
                
            return f"Team `{Utils.backtick_clean(team)}` penalty set to `-{pen}`."
        
        else:
            pen = int(pen.lstrip('-'))
            if team in self.team_pens:
                self.team_pens[team]+=pen
            else:
                self.team_pens[team] = pen
            if self.team_pens[team] == 0: self.team_pens.pop(team)
            
            if not reundo:
                self.modifications.append([(f'teampen {team} {pen}', team, pen)])
                self.undos.clear()
            return f"`-{pen}` penalty given to team `{Utils.backtick_clean(team)}`."
    
    def team_unpenalty(self, team: str, unpen: str, reundo=False):
        if unpen !=None:
            unpen = int(unpen.lstrip('='))
        if team.isnumeric():
            try:
                t_indx = int(team)-1
                team = list(self.tags.keys())[t_indx]
            except IndexError:
                return f"Invalid team number `{team}`."
        try:
            try:
                assert(team in self.tags.keys())
            except AssertionError:
                lowered_tags = list(map(lambda l: Utils.sanitize_uni(l.strip()).lower(), self.tags.keys()))
                sanitized_tag = Utils.sanitize_uni(team.strip()).lower()
                assert(sanitized_tag in lowered_tags)
                team = list(self.tags.keys())[lowered_tags.index(sanitized_tag)]
        except AssertionError:
            valid_teams = ", ".join(list(map(lambda l: f'`{l}`', self.tags.keys())))
            return f"Invalid team name `{Utils.backtick_clean(team)}`. Valid teams: {valid_teams}."

        if team not in self.team_pens:
            return f"Team `{Utils.backtick_clean(team)}` doesn't have any penalties."

        if unpen is None:
            orig_pen = self.team_pens[team]
            self.team_pens.pop(team)
            if not reundo:
                self.modifications.append([(f'teamunpen {team}', team, orig_pen)])
                self.undos.clear()
            return f"Penalties for team `{Utils.backtick_clean(team)}` have been removed."
        else:
            self.team_pens[team] -= unpen
            if self.team_pens[team] == 0: self.team_pens.pop(team)
            
            if not reundo: 
                self.modifications.append([(f'teamunpen {team} {unpen}', team, unpen)])
                self.undos.clear()
            return f"Penalty for team `{Utils.backtick_clean(team)}` reduced by `{unpen}`."

    def find_players(self,url, soup: BeautifulSoup): 
        elem = soup.select('tr[id*=r]')[-1]
        next_elem = elem.findNext('tr').findNext('tr')
        
        players = []
        
        while next_elem !=None:
            miiName = next_elem.find('td', class_='mii-font').text
            if miiName == "no name": miiName = "Player"
            fc = next_elem.select('span[title*=PID]')[0].text
            
            players.append((miiName, fc))
            next_elem = next_elem.findNext('tr') 

        player_names = [i[0] for i in players]
        self.dup_names = set([x for x in player_names if player_names.count(x) > 1])

        for miiName, fc in players:
            if miiName in self.dup_names:
                x = 1
                name = miiName+'-'+str(x)
                while name in self.names:
                    x+=1
                    name = miiName+'-'+str(x)
                miiName = name
            
            self.players.append(Player(fc=fc, name=miiName, scores=[0,[0]*self.gps, [0]*self.gps*4]))

            self.names.append(miiName)
            
        self.all_players = copy.copy(self.players)

        if isFFA(self.format): 
            print(self.players)
        
    def check_name(self, name) -> str:
        if name not in self.dup_names and name not in self.names:
            return name
        x = 1
        new = name
        while new in self.dup_names or name in self.names:
            new = name+'-'+str(x)
        return new
    
    def sort_AP(self, player: Player) -> Tuple[int, str, str]:
        found_tag = ""
        for tag, tag_players in self.tags.items():
            if player in tag_players:
                found_tag = tag
                break
        return (0 if found_tag!="" else 1, Utils.sanitize_uni(found_tag), Utils.sanitize_uni(player.getName()))

    def get_all_players(self) -> str: 
        ret = ''
        self.all_players = sorted(self.all_players, key = lambda l: self.sort_AP(l))

        for i, p in enumerate(self.all_players):
            ret+="\n{}. {}".format(i+1, Utils.disc_clean(p.getName()))
            if p in self.deleted_players:
                ret+=' (removed by tabler)'
        return ret

    async def add_sub_player(self, player: Player) -> str:
        # player = Player(fc=fc, name=name, scores = [0,[0]*self.gps, [0]*self.gps*4])
        if player in self.all_players: return 'failed'
        self.all_players.append(player)
        self.players.append(player)
        
        if len(self.players)-1<self.num_players: #TEST: test if new missing players DC filling working (for multiple GPS: 1 + 2)
            warn_replaced = False
            for gp in range(0, self.gp):
                for warn_item in enumerate(self.warnings[gp*4+1]):
                    if warn_item[1].get('type') == "missing":
                        #print(ind,i)
                        self.dc_list[gp*4+1].append({'type': 'dc_before', 'race':1, 'player': player, 'gp': gp+1})
                        self.warnings[gp*4+1].append({'type': 'dc_before','race': 1, 'player': player, 'gp': gp+1})
                        self.dc_ids_append(player, gp*4+1)
                        if gp not in self.gp_dcs: self.gp_dcs[gp] = []
                        self.gp_dcs[gp].append(player)
                        if len(self.players)==self.num_players:
                            self.warnings[gp*4+1].pop(warn_item[0])
                        warn_replaced = True

            if warn_replaced:           
                if not isFFA(self.format): self.find_tag(player)
                return 'not sub'
        
        if not isFFA(self.format):
            if "SUBS" not in self.tags or len(self.tags['SUBS'])==0:
                self.tags['SUBS'] = []
            self.tags["SUBS"].append(player)

        return 'success'
    
    def find_tag(self, player: Player):
        name = player.getName()
        per_team = int(self.format[0])

        #only one spot left to be filled
        if len(self.players)==self.num_players:
            for tag in self.tags.items():
                if len(tag[1])<per_team:
                    self.tags[tag[0]].append(player)
                    return

        #prefix tag matching
        match = ["", 0]
        for tag in self.tags.keys():
            if Utils.sanitize_uni(name.strip()).lower().find(Utils.sanitize_uni(tag).lower())==0 and len(self.tags[tag]<per_team):
                if len(tag)>match[1]:
                    match = [tag, len(tag)]
        if match[1]>0:
            self.tags[match[0]].append(player)
            return

        #suffix tag matching
        match = ["", 0]
        for tag in self.tags.keys():
            if Utils.sanitize_uni(name[::-1].strip()).lower().find(Utils.sanitize_uni(tag[::-1]).lower())==0 and len(self.tags[tag]<per_team):
                if len(tag)>match[1]:
                    match = [tag, len(tag)]
        if match[1]>0:
            self.tags[match[0]].append(player)
            return
        
        #common substring matching if 2v2
        if per_team==2:
            match = ["", 0]
            for tag in self.tags.keys():
                lcs = Utils.LCS(Utils.sanitize_uni(name.strip()).lower(), Utils.sanitize_uni(tag).lower())
                if len(lcs)>1 and lcs==tag and len(self.tags[tag]<per_team):
                    if len(lcs)>match[1]:
                        match = [lcs, len(lcs)]
            if match[0]!="":   
                self.tags[match[0]].append(player)
                return
        
        #no tags matched, so randomly fill
        for i in self.tags.items():
            if len(i[1])<per_team:
                self.tags[i[0]].append(player)
                return

        #all tags were full, so create new tag
        new_tag = self.check_tags(Utils.sanitize_uni(name)[0])
        self.tags[new_tag] = [player]

    def get_subs(self) -> str:
        ret = 'Room subs:\n'
        if len(self.subs)==0:
            ret+=" **No subs.**"
        for sub in self.subs:
            ret+=f" - **{Utils.disc_clean(sub.get('in_player').getName())}** subbed in for **{Utils.disc_clean(sub.get('out_player').getName())}** (after {sub.get('out_races')} races played).\n"
        return ret

    def sub_in(self, _in, out, out_races, reundo=False): 
        in_player, out_player = _in, out
        out_races = int(out_races)
        if not reundo:
            try:
                in_player: Player = self.player_ids[_in]
            except KeyError:
                return f"`{_in}` was not a valid player number. The player number must be from 1-{len(self.player_ids)}."
            try:
                out_player: Player = self.player_ids[out]
            except KeyError:
                return f"`{out}` was not a valid player number. The player number must be from 1-{len(self.player_ids)}."
        
        # for sub in self.subs: #checking whether this player has already subbed in for someone
        #     if in_player == sub.get('in_player'):
        #         return f"`{Utils.backtick_clean(in_player.getName())}` has already subbed in for `{Utils.backtick_clean(sub.get('out_player'))}`."
        if len(in_player.getSubs())>0:
            return f"`{Utils.backtick_clean(in_player.getName())}` has already subbed in for `{Utils.backtick_clean(in_player.getSubs()[-1][0].getName())}`."

        self.subs.append({'in_player': in_player, 'out_player': out_player, "out_races": out_races})

        in_player.add_sub(out_player, out_races)
        self.players.remove(out_player)

        tag = ''
        in_tag = ""
        if not isFFA(self.format):
            for t in self.tags.items():
                if out_player in t[1]:
                    tag = t[0]
                    self.tags[tag].pop(t[1].index(out_player))
                    break

            for t in self.tags.items():
                try:
                    t[1].remove(in_player)
                    in_tag = t[0]
                    break
                except ValueError:
                    pass
                
            if tag!="" and in_player not in self.tags[tag]:
                self.tags[tag].append(in_player)
       
            self.tags = {k:v for k,v in self.tags.items() if len(v)!=0}
        
        done = False
        edited_warning = None
        for i, r in self.warnings.items():
            for w in r:
                if w.get('type') == 'sub' and w.get('player') == in_player:
                    w['is_edited'] = True
                    w['sub_out'] = out_player
                    edited_warning = w
                    done = True
                    break
            if done:
                break

        if not reundo: 
            restore = {'out_tag': tag,  'in_tag': in_tag, 'warning': edited_warning, 'in_edited_scores': copy.deepcopy(in_player.edited_scores)}
            self.modifications.append([(f'sub {out} {out_races} {_in}', in_player, out_player, out_races, restore)])
            self.undos.clear()
        return f"Subbed in `{Utils.backtick_clean(in_player.getName())}` for `{Utils.backtick_clean(out_player.getName())}` (played `{out_races}` races)."
    
    def undo_sub(self, in_player: Player, out_player: Player, restore: Dict[str, Any]): 
        self.subs.pop(-1) # pop last sub (always last because undos can only go linearly one by one)
        self.players.append(out_player)

        if restore['warning']:
            restore['warning']['is_edited'] = False
            restore['warning'].pop('sub_out')

        if restore['in_edited_scores'] is not None and len(restore['in_edited_scores']) >0:
            in_player.edited_scores = restore['in_edited_scores'] 

        if not isFFA(self.format):
            for tag in self.tags.items():
                try:
                    tag[1].remove(in_player)
                    try:
                        self.tags[restore['in_tag']].append(in_player)
                    except KeyError:
                        self.tags[restore['in_tag']] = [in_player]

                    break
                except ValueError:
                    pass

            try:
                self.tags[restore['out_tag']].append(out_player)
            except KeyError:
                self.tags[restore['out_tag']] = [out_player]

        in_player.remove_last_sub(out_player)
        
        
    def edit_sub_races(self, indx, races, is_in, out_index = 1, reundo=False):
        player = indx
        if not reundo:    
            try:
                player: Player = self.player_ids[str(indx)]
            except KeyError:
                return f"Player number `{indx}` was invalid. The player number must be from 1-{len(self.player_ids)}."
        try:
            assert(len(player.getSubs())>0)
        except AssertionError:
            return f"`{Utils.backtick_clean(player.getName())}` is not a subbed-in player."

        if is_in:
            orig_races = player.races_played
            player.races_played = races
        else:
            try:
                orig_races = player.subs[out_index-1][1]
                player.subs[out_index-1][1] = races
            except IndexError:
                return f"Sub out index `{out_index}` was invalid. It must be from 1-{len(player.getSubs())}."
            
        if not reundo: 
            self.modifications.append([(f"editsub {indx} {races} {'in' if is_in else 'out'} {out_index if not is_in else ''}", player, races, orig_races, is_in, out_index)])
            self.undos.clear()

        return f"Changed `{Utils.backtick_clean(player.getName())}` sub {'in' if is_in else 'out'}{'' if is_in else f' (`{Utils.backtick_clean(player.subs[out_index-1][0].getName())}`)'} races to {races}."
         
    def edit_dc_status(self,L, reundo=False): 
        ret=''
        for i in L:
            try:
                dc_num = i[0]
                player: Player = self.dc_list_ids[int(i[0])][0]
                raceNum = self.dc_list_ids[int(i[0])][1]
            except KeyError:
                if len(self.dc_list_ids)==0:
                    ret+=f"DC number `{i[0]}` was invalid. There are no DCs to edit.\n"
                else: 
                    ret+=f"DC number `{i[0]}` was invalid. DC numbers must be from 1-{len(self.dc_list_ids)}.\n"
                continue
            
            status = i[1]
            players = [i[0] for i in self.races[raceNum-1][2]]
            if status == "on" or status == "during": #CHANGE TO 'ON'
                orig_status = 'on'
                if player not in players:
                    orig_status = "before"
                    self.change_room_size([[raceNum, len(self.races[raceNum-1][2])+1]], self_call=True)
                    self.races[raceNum-1][2].append((player, 'DC', "", ""))
                    gp = int((raceNum-1)/4)

                    if raceNum %4 != 1:
                        player.scores[1][gp] -=3
                        player.scores[2][raceNum-1] = 0
                        
                        for indx,i in enumerate(player.dc_pts):
                            if i[0]==raceNum:
                                player.dc_pts[indx][1].pop(0)
                                break
                            
                        for indx,i in enumerate(self.warnings[raceNum]):
                            if i.get('player') == player and "before" in i.get('type'):
                                if (4-(raceNum%4))%4 == 0:
                                    self.warnings[raceNum][indx] = {'type': 'dc_on', 'race': -1, 'player': player, 'is_edited':True, 'gp': gp+1}
                                else: 
                                    self.warnings[raceNum][indx] = {'type':"dc_on", 'race': raceNum, 'player': player, 'gp': gp+1, 'pts': i.get('pts')-3, 'rem_races':(4-(raceNum%4))%4, 'is_edited':True}
                        
                        for indx, i in enumerate(self.dc_list[raceNum]):
                            if i.get('player') == player and "before" in i.get('type'):
                                if (4-(raceNum%4))%4 == 0:
                                    self.dc_list[raceNum][indx] = {'type': 'dc_on', 'race': -1, 'player': player, 'gp':gp+1, 'is_edited':True}
                                else:    
                                    self.dc_list[raceNum][indx]= {'type': 'dc_on', 'race': raceNum, 'player':player, 'gp':gp+1, 'rem_races': (4-(raceNum%4))%4, 'pts': i.get('pts')-3, 'is_edited':True}
                    
                    else:
                        for indx,i in enumerate(self.warnings[raceNum]):
                            if i.get('player') == player and "before" in i.get('type'):
                                self.warnings[raceNum][indx] = {'type':"dc_on", 'race':1, 'gp':gp+1, 'player':player, 'is_edited':True}
                        for indx, i in enumerate(self.dc_list[raceNum]):
                            if i.get('player') == player and "before" in i.get('type'):
                                self.dc_list[raceNum][indx] = {'type': 'dc_on', 'race': 1, 'gp': gp+1, 'player': player, 'is_edited':True}                
            else: #CHANGE TO 'BEFORE'
                orig_status = 'before'
                if player in players:
                    orig_status = 'on'
                    self.change_room_size([[raceNum, len(self.races[raceNum-1][2])-1]], self_call=True, player=player)
                    gp = int((raceNum-1)/4)
                    
                    if raceNum %4 != 1:
                        player.scores[1][gp] +=3
                        player.scores[2][raceNum-1] = 3
                        
                        for indx,i in enumerate(player.dc_pts):
                            if i[0]==raceNum:
                                player.dc_pts[indx][1].insert(0, raceNum)
                            break
                        
                        for indx,i in enumerate(self.warnings[raceNum]):
                            if i.get('player') == player and "on" in i.get('type'):
                                self.warnings[raceNum][indx] = {'type': "dc_before", 'player':player, 'race':raceNum, 'rem_races':4-((raceNum-1)%4), 'pts':i.get('pts')+3, 'gp':gp+1, 'is_edited':True}
                        for indx, i in enumerate(self.dc_list[raceNum]):
                            if i.get('player') == player and "on" in i.get('type'):
                                self.dc_list[raceNum][indx] = {'type': 'dc_before', 'player': player, 'race':raceNum, 'rem_races':4-((raceNum-1)%4), 'pts': i.get('pts')+3, 'gp':gp+1, 'is_edited':True}
                                        
                    else:     
                        for indx,i in enumerate(self.warnings[raceNum]):
                            if i.get('player') == player and "on" in i.get('type'):
                                self.warnings[raceNum][indx] = {'type': "dc_before", 'player': player,'race':1, 'gp':gp+1, 'is_edited':True}
                        for indx, i in enumerate(self.dc_list[raceNum]):
                            if i.get('player') == player and "on" in i.get('type'):
                                self.dc_list[raceNum][indx] = {'type':'dc_before', 'player': player, 'race':1, 'gp':gp+1, 'is_edited':True}

            if not reundo:
                self.modifications.append([(f'dcs {dc_num} {status}', dc_num, orig_status, status)]) 
                self.undos.clear()   

            ret+= f"Changed `{Utils.backtick_clean(player.getName())}` DC status for race `{raceNum}` to `{status}`.\n"
       
        return ret
                
                 
    def change_room_size(self, l, self_call = False, player=None, reundo=False, undo=False): 
        ret = ''
        for i in l:
            try:
                raceNum = int(i[0])-1
                assert(raceNum>=0)
                orig_room_size = len(self.races[raceNum][2]) 
                if raceNum+1 in self.changed_room_sizes and len(self.changed_room_sizes[raceNum+1])>0:
                    orig_room_size = self.changed_room_sizes[raceNum+1][-1]
                    
                gp = int(raceNum/4)
            except AssertionError:
                ret+= f"Invalid race number `{raceNum+1}`. The race number must be from 1-{len(self.races)}.\n"
                continue
            try:
                cor_room_size = int(i[1])
                assert(cor_room_size>0 and cor_room_size<=len(self.players) and (cor_room_size <=orig_room_size or self_call))
                
            except AssertionError:
                if cor_room_size> orig_room_size and cor_room_size<=len(self.players):
                    ret+=f"**Note:** *If a race is missing player(s) due to DCs, it is advised to use `{self.prefix}dcs` instead.\nOnly use this command if no DCs were shown for the race in question.*\n\n"
                else:
                    ret+= f"Invalid <corrected room size> for race `{raceNum+1}`. The corrected room size must be a number from 1-{len(self.players)}.\n"
                    continue
            
            if cor_room_size == orig_room_size:
                ret+=f'Race `{raceNum+1}` room size is already `{cor_room_size}` - no change made.\n'
                continue
            
            orig_pts = {}
            for place, p in enumerate(self.races[raceNum][2]):
                player = p[0]
                try:
                    pts = PTS_MAP[orig_room_size][place]
                except KeyError:
                    pts = 0
                orig_pts[player] = pts
            
            fixed_pts = {}
            
            if self_call and player is not None:
                for pos, player in enumerate(self.races[raceNum][2]):
                    if player[0] == player:
                        self.races[raceNum].pop(pos)

            for place, p in enumerate(self.races[raceNum][2]):
                player = p[0]
                try:
                    pts = PTS_MAP[cor_room_size][place]
                except KeyError:
                    pts = 0
                fixed_pts[player] = pts
                
            for player, pts in fixed_pts.items():
                player.scores[1][gp] += (pts - orig_pts[player])
                player.scores[2][raceNum] = pts

            if not reundo and not self_call:
                restore = copy.deepcopy(self.races[raceNum])
                self.races[raceNum][2] = self.races[raceNum][2][:cor_room_size]
                
            if not self_call:
                done = False
                for indx,i in enumerate(self.manual_warnings[raceNum+1]):
                    if i.find("Room size changed to") == 0:
                        self.manual_warnings[raceNum+1][indx] = f"Room size changed to {cor_room_size} by the tabler for this race."
                        done = True
                        break
                if not done:
                    self.manual_warnings[raceNum+1].append(f"Room size changed to {cor_room_size} by the tabler for this race.")
                
                if not undo: self.changed_room_sizes[raceNum+1].append(cor_room_size)
        
            if not reundo and not self_call:
                self.modifications.append([(f"changeroomsize {raceNum+1} {cor_room_size}", raceNum+1, orig_room_size, cor_room_size, restore)])
                self.undos.clear()
            
            ret+=f'Changed race {raceNum+1} room size to {cor_room_size}.\n'


        return ret
            
    def undo_crs(self, raceNum, orig_size, restore): 
        raceNum -=1

        self.races[raceNum] =  restore
        self.change_room_size([[raceNum+1, orig_size]], undo=True,reundo=True)
        if raceNum+1 in self.changed_room_sizes:
            self.changed_room_sizes[raceNum+1].pop()
        

    def edit_race(self, l, reundo=False):
        ret = ''
        mods = []
        for num, elem in enumerate(l):
            raceNum = elem[0]
            player =p_indx= elem[1]
            if not reundo:
                try:
                    player: Player = self.player_ids[player]
                except KeyError:
                    return f"Player index `{player}` was invalid. The player number must be from 1-{len(self.players)}."
                
            correct_pos = int(elem[2])-1
            try:
                raceNum = int(raceNum)
                corresponding_rr = self.races[raceNum-1][2]
            except IndexError:
                return f"Race number `{raceNum}` was invalid. It must be a number from 1-{len(self.races)}"
            
            corresponding_rr = [i[0] for i in corresponding_rr]
            
            orig_pos = corresponding_rr.index(player)
            orig_pts = PTS_MAP[len(corresponding_rr)][orig_pos]
            try:   
                cor_pts = PTS_MAP[len(corresponding_rr)][int(correct_pos)]
            except KeyError:
                return f"Corrected position `{correct_pos+1}` was invalid. It must be a number from 1-{len(corresponding_rr)}."
            
            if orig_pos<correct_pos:
                aff = [self.races[raceNum-1][2][i][0] for i in range(orig_pos+1,correct_pos+1)]
            else:
                aff = [self.races[raceNum-1][2][i][0] for i in range(correct_pos,orig_pos)]
                
            aff_orig_pts = {}
            for a in aff:
                aff_orig_pts[a] = PTS_MAP[len(corresponding_rr)][corresponding_rr.index(a)]
            
            # correct_ft_order = list(self.finish_times[raceNum-1].keys())
            # correct_ft_order.insert(correct_pos, correct_ft_order.pop(orig_pos))
            # self.finish_times[raceNum-1] = {k : self.finish_times[raceNum-1][k] for k in correct_ft_order}
            
            self.races[raceNum-1][2].insert(correct_pos, self.races[raceNum-1][2].pop(orig_pos))

            aff_new_pts = {}
            corresponding_rr = self.races[raceNum-1][2]
            corresponding_rr = [i[0] for i in corresponding_rr]
            
            for a in aff:
                aff_new_pts[a] = PTS_MAP[len(corresponding_rr)][corresponding_rr.index(a)]
            
            gp = int((raceNum-1)/4)

            player.scores[0] += (cor_pts-orig_pts)
            player.scores[1][gp] += (cor_pts-orig_pts)
            player.scores[2][raceNum-1] = cor_pts

            for a in aff:
                a.scores[0]+= (aff_new_pts[a] - aff_orig_pts[a])
                a.scores[1][gp] += (aff_new_pts[a] - aff_orig_pts[a])
                a.scores[2][raceNum-1] = aff_new_pts[a]
                        
            try:
                self.manual_warnings[raceNum].remove("Placements for this race have been manually altered by the tabler.")
            except ValueError:
                pass
            self.manual_warnings[raceNum].append("Placements for this race have been manually altered by the tabler.")
            
            mods.append((f'editrace {raceNum} {p_indx} {correct_pos+1}', player, raceNum, orig_pos+1, correct_pos+1))

            ret+=f'`{Utils.backtick_clean(player.getName())}` race `{raceNum}` placement changed to `{correct_pos+1}`.'+("\n" if num==len(l)-1 else "")

     
        if not reundo and len(mods)>0:
            self.modifications.append(mods)
            self.undos.clear()
        return ret
    
    async def merge_room(self, arg, redo=False):
        is_rxx = len(arg)==1 and Utils.is_rxx(arg[0])
            
        if is_rxx:
            error, mes = await self.find_room_to_merge(rid = arg, redo=redo)
        else:
            error, mes= await self.find_room_to_merge(mii=arg, redo=redo)
        
        if redo:
            # self.races = self.restore_merged[-1][0]
            # self.tracks = self.restore_merged[-1][1]
            # self.finish_times = self.restore_merged[-1][2]
            # self.warnings = self.restore_merged[-1][3]
            # self.dc_list = self.restore_merged[-1][4]
            # self.dc_list_ids = self.restore_merged[-1][5]
            # self.players = self.restore_merged[-1][6]
            
            # self.manual_warnings = self.restore_merged[-1][7]
            # if not isFFA(self.format):
            #     self.all_players = self.restore_merged[-1][8]
            #     self.tags = self.restore_merged[-1][9]
            # self.restore_merged.pop(-1)

            if len(self.races)<4*self.gps and not self.check_mkwx_update.is_running():
                try:
                    self.check_mkwx_update.start()
                except RuntimeError:
                    pass
            elif not self.check_mkwx_update.is_running():
                await self.auto_send_pic()
            
        return error, mes

    async def un_merge_room(self, merge_num): #TEST: test if updated un_merge works properly
        # self.restore_merged.append((copy.deepcopy(self.races), copy.copy(self.tracks), 
        #     copy.deepcopy(self.finish_times), copy.deepcopy(self.warnings), copy.deepcopy(self.dc_list), 
        #     copy.deepcopy(self.dc_list_ids), copy.deepcopy(self.players), copy.deepcopy(self.manual_warnings),
        #     copy.deepcopy(self.all_players), copy.deepcopy(self.tags)))
        merge_indx = merge_num-1
        self.rxx = self.prev_rxxs[merge_indx]  
        self.races = self.races[:len(self.prev_elems[merge_indx])-len(self.removed_races)]
        self.current_elems = self.prev_elems[merge_indx]
        self.prev_elems = self.prev_elems[:merge_indx]
        self.prev_rxxs = self.prev_rxxs[:merge_indx]
        self.recorded_elems = self.prev_elems+self.current_elems
        self.current_url = self.ROOM_URL.format(self.rxx)
        
        self.warnings = defaultdict(list,{k:v for k,v in self.warnings.items() if k<=len(self.races)})
        self.manual_warnings = defaultdict(list,{k:v for k,v in self.manual_warnings.items() if k<=len(self.races)})
        self.dc_list = defaultdict(list, {k:v for k, v in self.dc_list.items() if k<=len(self.races)})
        
        self.dc_list_ids = {k:v for k, v in self.dc_list_ids.items() if v[1]<=len(self.races)}
        
        for p in list(self.players):
            p.scores = [0,[0]*self.gps, [0]*self.gps*4]
        
        recorded_players = []
        for raceNum,race in enumerate(self.races):
            cur_room_size= len(race)
            gp = self.gp = int(raceNum/4)
            
            for placement, player in enumerate(race):
                player: Player = player[0]

                for indx, j in enumerate(player.dc_pts):
                    if raceNum+1 in j[1]:
                        player.dc_pts.pop(indx)
                        break

                recorded_players.append(player)
                player.scores[1][gp] += PTS_MAP[cur_room_size][placement]
                player.scores[raceNum] += PTS_MAP[cur_room_size][placement]
                player.scores[0] += PTS_MAP[cur_room_size][placement]

                for j in player.dc_pts:
                    if raceNum+1 in j[1]:
                        player.dc_pts[0]+=3
                        player.dc_pts[1][gp]+=3
                        player.dc_pts[2][raceNum]=3
                        break 
        
        x = copy.deepcopy(self.players)
        for i in x:
            if i not in recorded_players:
                self.players.remove(i)
                try:
                    self.all_players.remove(i)
                except ValueError:
                    pass

                if not isFFA(self.format):
                    for tag in list(self.tags.items())[::-1]:
                        if i in tag[1]:
                            tag[1].remove(i)
                            if len(self.tags[tag[0]])==0:
                                self.tags.pop(tag[0])
 
        if len(self.races)<4*self.gps and not self.check_mkwx_update.is_running():
            try:
                self.check_mkwx_update.start()
            except RuntimeError:
                pass
        elif not self.check_mkwx_update.is_running():
            await self.auto_send_pic()
                
    async def remove_race(self, raceNum, redo=False): 
        if raceNum==-1: raceNum = len(self.races)
        try:
            assert(0<raceNum<=len(self.races))
        except AssertionError:
            return f"`{raceNum}` was not a valid race number. The race number must be from 1-{len(self.races)}."
        
        track = self.races[raceNum-1][1]
        self.removed_races[raceNum] = [self.races.pop(raceNum-1)]
       
        try:
            rem_warn = self.warnings.pop(raceNum)
        except KeyError:
            rem_warn = None
        try:
            rem_dc_list = self.dc_list.pop(raceNum)
        except KeyError:
            rem_dc_list = None
            
        self.removed_warn_dcs[raceNum] = {'warnings':rem_warn, 'dc_list':rem_dc_list, 'm_warnings': self.manual_warnings.pop(raceNum) if raceNum in self.manual_warnings else None}

        self.shift_warnings(start=raceNum, direction='left')
        await self.recalc_table(start=raceNum)
        
        if not redo: 
            self.modifications.append([(f'removerace {raceNum}', raceNum, track)])
            self.undos.clear()

        self.manual_warnings[-1].append(f"Race #{raceNum} (originally) - {track} has been removed by the tabler.")
            
        return f"Removed race {raceNum} - {track} from table."
    
    async def restore_removed_race(self, raceNum):
        restore_race = self.removed_races.pop(raceNum)
        self.races.insert(raceNum-1, restore_race)
        self.shift_warnings(start=raceNum, direction='right')
        restore_warn = self.removed_warn_dcs.pop(raceNum)
        if restore_warn.get('warnings') is not None:
            self.warnings[raceNum] = restore_warn.get('warnings')
        if restore_warn.get("m_warnings") is not None:
            self.manual_warnings[raceNum] = restore_warn.get('m_warnings')
        
        await self.recalc_table(start=raceNum)
       
    def shift_warnings(self, start, direction):
        direction = 1 if direction == 'right' else -1
        
        #shift manual warnings
        for race in list(self.manual_warnings.keys())[::-direction]:
            if race>=start:
                self.manual_warnings[race+direction] = self.manual_warnings.pop(race)
        #shift warnings
        for race in list(self.warnings.keys())[::-direction]:
            if race>=start:
                self.warnings[race+direction] = self.warnings.pop(race)
       
    
    async def recalc_table(self, start = 0): #TEST: need to more extensively test different scenarios to ensure this works
        self.gp = int((start-1)/4)

        for player in self.players:
            player.scores[1] = [score if gp<self.gp else 0 for (gp, score) in enumerate(player.scores[1])]
            player.scores[2] = [score if int(race/4)<self.gp else 0 for (race, score) in enumerate(player.scores[2])]
            player.scores[0] = sum([gp for gp in player.scores[1]])

        reference_warnings = copy.deepcopy(self.warnings)
        
        self.warnings = defaultdict(list,{k:v for k,v in self.warnings.items() if k<self.gp*4+1})
        self.dc_list = defaultdict(list, {k:v for k, v in self.dc_list.items() if k<self.gp*4+1})
        #self.manual_warnings = defaultdict(list, {k:v for k, v in self.dc_list.items() if k<self.gp*4+1})
                
        self.gp_dcs = {k:v for k,v in self.gp_dcs.items() if k<self.gp} 
        
        for player in self.players:
            player.dc_pts = [dc for dc in player.dc_pts if dc[0]<(self.gp+1)*4-3]
        
        self.dc_list_ids = {k:v for k,v in self.dc_list_ids.items() if v[1]<(self.gp+1)*4-3} 
        
        self.room_sizes_error_affected = [i for indx, i in enumerate(self.room_players) if indx<self.gp]
        self.room_error_index = [i for indx, i in enumerate(self.room_error_index) if indx<self.gp]
        self.room_players = [i for indx, i in enumerate(self.room_players) if indx<self.gp]
        self.room_sizes = [i for indx, i in enumerate(self.room_sizes) if indx<self.gp]
        
        await self.update_table(recalc=True, reference_warnings = reference_warnings)
        
    def change_gps(self,gps, reundo=False): 
        for player in self.players:
            player.scores[1]+=[0]*(gps-self.gps)
            player.scores[2]+=[0]*(gps-self.gps)*4
        orig_gps = self.gps
        self.gps = gps
        
        if not reundo:
            self.modifications.append([(f'gps {orig_gps}'), orig_gps, gps])
            self.undos.clear()

        if not self.check_mkwx_update.is_running():
            try:
                self.check_mkwx_update.start()
            except RuntimeError:
                pass
    
    def change_sui(self, setting, reundo=False):
        orig_sui = self.sui
        self.sui = setting

        if not reundo:
            self.modifications.append([(f"largetimes {setting}", orig_sui, setting)])
    
    def create_new_player(self, name, fc):
        return Player(fc=fc, name=name, scores=[0, [0]*self.gps, [0]*self.gps*4])
                  
    async def room_is_updated(self):
        if self.last_race_update is not None and datetime.datetime.now() - self.last_race_update < datetime.timedelta(seconds=45): return False
        soup = await self.fetch(self.current_url)
        #TODO: JSON fetch for /room after first /list check (less load on wiimmfi apparently)
        # cur_race = await self.fetch_mkwx_JSON(self.current_url.replace('/list/', '/room/'))
        # if isinstance(cur_race, str and "error") and 'error' in cur_race:
        #     print("Wiimmfi error.")
        #     return False
        # check race_phase here == 19(end) or == 13(begin - in case missed when phase == 19) 
        # *** (11 & 12 i think is in lobby (voting + waiting) - could use instead of 13, also maybe race_mode == 1 means waiting in room lobby? - between gps/globe)
        # + need to keep track if race_phase check already passed so won't update table multiple times for one update
        # so need to reset the rase_phase counter and continue the check

        if isinstance(soup, str) and 'error' in soup:
            print("Wiimmfi error.")
            return False
                    
        elems = soup.select('tr[id*=r]')
        prev_elems_len = sum(map(len, self.prev_elems))
        
        if len(elems)+prev_elems_len>len(self.recorded_elems) and len(self.races)<self.gps*4:
            if len(self.races)!=0:
                self.last_race_update = datetime.datetime.now()
            return True
        return False
    
    @tasks.loop(seconds=5)
    async def check_mkwx_update(self): 
        # cur_iter = self.check_mkwx_update.current_loop
        if not await self.room_is_updated(): return

        await self.auto_send_pic()
        
        if len(self.races)>=self.gps*4 or (self.last_race_update is not None and datetime.datetime.now()-self.last_race_update>datetime.timedelta(minutes=30)):
            self.check_mkwx_update.stop()

    async def auto_send_pic(self):
        self.bot.command_stats['picture_generated']+=1
        self.picture_running = True
        self.last_command_sent = datetime.datetime.now()
        detect_mes = await self.ctx.send("Detected race finish.")
        wait_mes = await self.ctx.send("Updating scores...")
        mes = await self.update_table(auto=True)
        await wait_mes.edit(content=mes)
        pic_mes = await self.ctx.send("Fetching table picture...")
        img = await self.get_table_img()
        if isinstance(img, str):
            await pic_mes.delete()
            await detect_mes.delete()
            self.picture_running=False
            return await self.ctx.send(img)
        
        f=discord.File(fp=img, filename='table.png')
        em = discord.Embed(title=self.title_str(), 
                        description="\n[Edit this table on gb.hlorenzi.com]("+self.table_link+")")
        
        em.set_image(url='attachment://table.png')
        is_overflow, error_footer, full_footer= self.get_warnings()
        em.set_footer(text = error_footer)
        
        self.picture_running=False 
        await self.ctx.send(embed=em, file=f)
        await pic_mes.delete()
        await detect_mes.delete()

        if is_overflow: #send file of errors
            path = "./error_footers/"
            filename = f'warnings_and_errors-{self.ctx.channel.id}.txt'
            e_file = Utils.create_temp_file(filename, full_footer, dir=path)
            Utils.delete_file(path+filename)
            
            await self.ctx.send(file = discord.File(fp=e_file, filename=filename))

         
    async def update_table(self, prnt=True, auto=False, recalc = False, reference_warnings = None):
        def find_if_edited(player, raceNum, ref):
            for i in ref[raceNum]:
                if "dc_" in i.get('type') and i.get('player') == player:
                    return i.get("is_edited", False)

        shift = len(self.races) if not recalc else 0
        reference_warnings = self.warnings if reference_warnings is None else reference_warnings
        rID = self.rxx

        if not recalc:
            soup = await self.fetch(self.current_url)
            if isinstance(soup, str) and 'error' in soup:
                if 'response' in soup:
                    return "Wiimmfi appears to be down. The table could not be updated. Try again later."
                else:
                    return "I am currently experiencing some issues with Wiimmfi. The table could not be updated. Try again later."
            
            new_races = []
            elems = soup.select('tr[id*=r]')
            new_elems = []
            for i in elems:
                elem = i
                raceID = elem.findAll('a')[0].text

                if raceID in self.recorded_elems:
                    # print("RACE ALREADY RECORDED")
                    break
                new_elems.append(raceID)
                    
                try:
                    track = elem.findAll('a')[-1].text
                    assert(elem.findAll('a')[2] == elem.findAll('a')[-1])
                    track = track[0:track.find('(')-1]
                except (AssertionError, IndexError):
                    track = "Unknown Track"
                    
                race = (raceID, track,[])
                next_elem = elem.findNext('tr').findNext('tr')
                
                while next_elem not in elems and next_elem !=None:
                    fin_time = next_elem.findAll('td', align='center')[-1].text
                    # col_indx, dec_indx = fin_time.find(":"), fin_time.find('.')
                    fin_time = 'DC' if fin_time == '—' else fin_time
                    miiName = next_elem.find('td', class_='mii-font').text
                    if miiName == "no name": miiName = "Player"
                    fc = next_elem.select('span[title*=PID]')[0].text
                    tr = next_elem.find_all('td',{"align" : "center"})[4].text
                    tr = False if tr=="✓" else True
                    try:
                        delta = next_elem.select('td[title*=delay]')[0].text
                    except IndexError:
                        delta = next_elem.find_all('td',{"align" : "center"})[5].text
                    
                    player_obj = None
                    for player in self.players:
                        if player.getFC()==fc:
                            player_obj = player
                            break
                    if player_obj is None: 
                        player_obj = self.create_new_player(self.check_name(miiName), fc)

                    race[2].append((player_obj, fin_time, tr, delta))
                    next_elem = next_elem.findNext('tr')
                    
                new_races.append(race)

            new_races.reverse()
            new_elems.reverse()
            
            #make sure table doesn't record unwanted races
            if len(self.races+new_races)>self.gps*4:
                if len(self.races)>=self.gps*4:
                    new_races = []
                else:
                    new_races = new_races[:self.gps*4-len(self.races)]
            
            self.recorded_elems+=new_elems
            self.current_elems+=new_elems
            
            if len(self.recorded_elems)>self.gps*4:
                self.recorded_elems=self.recorded_elems[:self.gps*4]
       
        iter_races = new_races if not recalc else self.races[self.gp*4:]
        init_shift = 0 if not recalc else self.gp*4
        sub_miis = []
        last_race_players = []
        for raceNum, race in enumerate(iter_races):
            raceNum+=init_shift
            
            if (shift+raceNum)%4 == 0: #new gp
                if (raceNum!=init_shift and recalc) or (not recalc and raceNum+shift+init_shift!=0):
                    self.gp+=1
                self.room_sizes.append(len(race[2]))
                self.room_players.append([i[0] for i in race[2]])
                self.room_sizes_error_affected.append([])
                self.room_error_index.append([-1,-1])
                if self.gp>=self.gps: 
                    for p in self.players:
                        p.scores[1].append(0)
                        p.scores[2].extend([0]*4)
                        
            cur_room_size = len(race[2])
            cur_race_players = [i[0] for i in race[2]]
            
            all_blank = False
            dc_count = 0
            for i, r in enumerate(race[2]):
                if r[1] == 'DC':
                    dc_count +=1
            if dc_count == cur_room_size:
                self.warnings[shift+raceNum+1].append({"type": "mkwx_bug_blank", 'gp':self.gp+1})
                all_blank = True
                #continue

            if not all_blank: #don't check these errors if the race's times are all blank
                #repeat times check
                check_repeat_times = Utils.check_repeat_times(race, self.races[:raceNum] if recalc else self.races+iter_races[:raceNum])
                if check_repeat_times[0]:
                    self.warnings[shift+raceNum+1].append({'type': 'mkwx_bug_repeat', 'race': check_repeat_times[1].get('race'),
                                                        'num_affected':check_repeat_times[1].get('num_aff'), 'gp': self.gp+1})

                #tr check
                tr_count = Counter([i[2] for i in race[2]])[True]
                if tr_count>0:
                    self.warnings[shift+raceNum+1].append({'type': "mkwx_bug_tr", 'aff_players': tr_count, 'gp': self.gp+1})
            
                #delay check
                delay_count = len([i[3] for i in race[2] if i[3]=="—" or (Utils.isfloat(i[3]) and (float(i[3])>7.0 or float(i[3])<-7.0))])
                if delay_count>0:
                    self.warnings[shift+raceNum+1].append({'type': "mkwx_bug_delta", 'aff_players':delay_count, 'gp': self.gp+1})

                #check for room size increases (mkwx bug)
                if cur_room_size < self.room_sizes[self.gp]:
                    self.room_sizes[self.gp] = cur_room_size
                if cur_room_size > self.room_sizes[self.gp]:
                    self.room_sizes_error_affected[self.gp].append(shift+raceNum+1)
                    
                    if self.room_error_index[self.gp][1]==-1:
                        self.warnings[shift+raceNum+1].append({'type': "mkwx_bug_increase", 'new_players':cur_room_size, 'orig_players':self.room_sizes[self.gp], 'races':self.room_sizes_error_affected[self.gp]})
                        self.room_error_index[self.gp][1] = len(self.warnings[shift+raceNum+1])-1
                        self.room_error_index[self.gp][0] = shift+raceNum+1
                    else:
                        self.warnings[self.room_error_index[self.gp][0]][self.room_error_index[self.gp][1]]['races'] = self.room_sizes_error_affected[self.gp]
                
                #check for changed players mid-GP (mkwx bug)
                elif not all(elem in self.room_players[self.gp] for elem in cur_race_players) and not all(elem in last_race_players for elem in cur_race_players):
                    self.warnings[shift+raceNum+1].append({'type': "mkwx_bug_change", 'race': shift+raceNum+1, 'gp':self.gp+1})

                last_race_players = cur_race_players   
            
            if cur_room_size<self.num_players and len(self.players)<self.num_players and (shift+raceNum)%4 == 0:
                self.warnings[shift+raceNum+1].append({'type': 'missing', 'cur_players': cur_room_size, 'sup_players': self.num_players, 'gp': self.gp+1})

            elif cur_room_size > self.num_players and (shift+raceNum)%4 == 0:
                self.warnings[shift+raceNum+1].append({'type': 'overflow', 'cur_players': cur_room_size, 'sup_players': self.num_players, 'gp': self.gp+1})
             
            elif cur_room_size<len(self.players):
                players = cur_race_players
                total_missing_players = []
                missing_players = []
                for i in self.players:
                    if i not in players:
                        total_missing_players.append(i)
                        if (i in self.room_players[self.gp] and (shift+raceNum+1)%4!=1) or (i in self.room_players[self.gp-1] and (shift+raceNum+1)%4==1): 
                            missing_players.append(i)
                        
                sub_outs = False
                if len(self.players)>self.num_players and len(total_missing_players)==len(self.players)-self.num_players:
                    sub_outs= True
                if len(self.players)>self.num_players and len(total_missing_players)>len(self.players)-self.num_players and (shift+raceNum+1)%4==1:
                    sub_outs = True
                    self.warnings[shift+raceNum+1].append({'type': 'missing_w_sub', 'missing_players': missing_players, 'num_missing': len(missing_players), 'gp': self.gp+1})

                if not sub_outs:
                    if (shift+raceNum)%4 == 0:
                        for mp in missing_players:
                            is_edited = find_if_edited(mp, shift+raceNum+1, reference_warnings)
                            if self.gp not in self.gp_dcs or mp not in self.gp_dcs[self.gp]:
                                self.warnings[shift+raceNum+1].append({'type': 'dc_before', 'race':1, 'gp': self.gp+1, 'player':mp, "is_edited":is_edited})
                                self.dc_list[shift+raceNum+1].append({'type': 'dc_before', 'race':1, 'gp': self.gp+1, 'player':mp, "is_edited":is_edited})
                                self.dc_ids_append(mp, shift+raceNum+1)
                                if self.gp not in self.gp_dcs: self.gp_dcs[self.gp] = []
                                self.gp_dcs[self.gp].append(mp)
                                
                    else:
                        for mp in missing_players:
                            is_edited = find_if_edited(mp, shift+raceNum+1, reference_warnings)
                            if self.gp not in self.gp_dcs or mp not in self.gp_dcs[self.gp]:
                                self.warnings[shift+raceNum+1].append({'type':'dc_before', 'race':shift+raceNum+1, 'rem_races':4-((shift+raceNum)%4), 'pts':0, 'gp':self.gp+1,'player':mp, "is_edited":is_edited})    
                                self.dc_list[shift+raceNum+1].append({'type':'dc_before', 'race':shift+raceNum+1, 'rem_races':4-((shift+raceNum)%4), 'pts':0, 'gp':self.gp+1,'player':mp, "is_edited":is_edited})    
                                
                                mp.dc_pts.append([shift+raceNum+1, [i for i in range(shift+raceNum+1, shift+raceNum+1+(4-((shift+raceNum)%4))%4)]])
                                        
                                self.dc_ids_append(mp, shift+raceNum+1)
                                if self.gp not in self.gp_dcs: self.gp_dcs[self.gp] = []
                                self.gp_dcs[self.gp].append(mp)
            
            
            last_finish_times = {}
            ties = {}
            
            for place, player in enumerate(race[2]):
                time = player[1]
                player_obj = player[0]
                is_edited = find_if_edited(player_obj, shift+raceNum+1, reference_warnings)

                for indx, j in enumerate(player_obj.dc_pts):
                    if shift+raceNum+1 in j[1]:
                        player_obj.dc_pts.pop(indx)
                
                #sub player
                if player_obj not in self.players and player_obj not in self.deleted_players:
                    status = await self.add_sub_player(player_obj)
                    if status!='failed':
                        sub_miis.append(player_obj)
                    if not isFFA(self.format) and status == 'success':
                        self.warnings[shift+raceNum+1].append({'type':'sub', 'player': player_obj})
                
                player_obj.scores[1][self.gp] += PTS_MAP[cur_room_size][place]
                player_obj.scores[2][shift+raceNum] = PTS_MAP[cur_room_size][place]
                player_obj.scores[0] += PTS_MAP[cur_room_size][place]
                
                #check for ties
                if time != 'DC' and time in list(last_finish_times.values()):
                    for index,t in enumerate(list(last_finish_times.values())):
                        if t == time:
                            if time in ties:
                                ties[time].append(list(last_finish_times.keys())[index])
                            else:
                                ties[time] = [list(last_finish_times.keys())[index]]
                    
                    ties[time].append(player_obj)
                
                colon_indx = time.find(":")
                if time!='DC' and colon_indx>-1 and int(time[:colon_indx])>=5:
                    self.warnings[shift+raceNum+1].append({'type': 'large_time', 'player':player_obj, 'time':time})
                   
                last_finish_times[player_obj] = time

                try:
                    assert(time!='DC' or all_blank)
                except AssertionError:
                    if self.gp not in self.gp_dcs or player_obj not in self.gp_dcs[self.gp]:
                        if (shift+raceNum)%4==0:
                            self.warnings[shift+raceNum+1].append({'type': 'dc_on', 'race':1, 'gp':self.gp+1, 'player':player_obj, "is_edited":is_edited})
                            self.dc_list[shift+raceNum+1].append({'type': 'dc_on', 'race':1, 'gp':self.gp+1, 'player':player_obj, "is_edited":is_edited})
                            
                        else: 
                            if (4-((shift+raceNum+1)%4))%4 == 0:
                                self.warnings[shift+raceNum+1].append({'type': "dc_on", 'race':-1, 'player':player_obj, 'gp':self.gp+1, "is_edited":is_edited})
                                self.dc_list[shift+raceNum+1].append({'type': "dc_on", 'race':-1, 'player':player_obj, 'gp':self.gp+1, "is_edited":is_edited})
                        
                            else:
                                self.warnings[shift+raceNum+1].append({'type': "dc_on", 'race':shift+raceNum+1, 'rem_races': (4-((shift+raceNum+1)%4))%4, 'pts':0, 'player':player_obj, 'gp':self.gp+1, "is_edited":is_edited})
                                self.dc_list[shift+raceNum+1].append({'type': "dc_on", 'race':shift+raceNum+1, 'rem_races': (4-((shift+raceNum+1)%4))%4, 'pts':0, 'player':player_obj, 'gp':self.gp+1, "is_edited":is_edited})
                            
                            player_obj.dc_pts.append([shift+raceNum+1, [i for i in range(shift+raceNum+2, shift+raceNum+2+(4-((shift+raceNum+1)%4))%4)]])
                             
                        self.dc_ids_append(player_obj, shift+raceNum+1)
                        if self.gp not in self.gp_dcs: self.gp_dcs[self.gp] = []
                        self.gp_dcs[self.gp].append(player_obj)
                    else:
                        self.warnings[shift+raceNum+1].append({'type': 'blank_time', 'player': player_obj})                            

            for player_ref in self.players:
                for j in player_ref.dc_pts:
                    if shift+raceNum+1 in j[1]:
                        player_ref.scores[1][self.gp]+=3
                        player_ref.scores[2][shift+raceNum+1]=3

                        for ind,w in enumerate(self.warnings[j[0]]):
                            if w.get('player') == player_ref:
                                self.warnings[j[0]][ind]['pts']+=3
                                break
                        for ind, d in enumerate(self.dc_list[j[0]]):
                            if d.get('player') == player_ref:
                                self.dc_list[j[0]][ind]['pts'] +=3
                                break
                        break

            if len(ties)>0:
                for tie in list(ties.items()):     
                    self.warnings[shift+raceNum+1].append({'type':'tie', "time":tie[0], 'players':tie[1]}) 
                        
            
        if not recalc: self.races+=new_races
        if len(sub_miis)>0: self.populate_table_flags(subs=sub_miis)
        self.table_str = self.create_string()
        # self.update_warn_file()

        if prnt:
            print()
            print(self.table_str)
            # print(sub_miis)

        if not recalc:   
            return "Table {}updated. Room {} has finished {} {}. Last race: {}.".format("auto-" if auto else "", rID, len(self.races), "race" if len(self.races)==1 else "races",self.races[-1][1])

    def update_warn_file(self):
        warn_content = self.get_warnings(override=True)
        if "No warnings or room errors." not in warn_content:
            Utils.create_temp_file(f"warnings_and_errors-{self.ctx.channel.id}.txt", warn_content, dir='./error_footers/', no_ret=True)
                       
    def create_string(self, by_race = False):
        self.tags = {k:v for k,v in self.tags.items() if len(v)>0}
        
        ret = "#title {} {}".format(len(self.races), "race" if len(self.races)==1 else 'races')
        if self.style:
            ret+="\n#style {}".format(self.style.get('table'))
        if self.graph:
            ret+="\n#graph {}".format(self.graph.get('table'))

        if isFFA(self.format):
            ret+='\nFFA'
            for player in self.players:
                if player in self.deleted_players: 
                    continue
                ret+="\n{} ".format(player.get_full_name(len(self.races)))
                #flag insertion by region
                flag_code = player.getFlag()
                ret+=f"[{flag_code if flag_code else ''}] "
                ret+= player.get_score_str(by_race)
                
        else:
            for tag in self.tags.keys():
                ret+='\n\n{}'.format(tag)
                for player in self.tags[tag]:
                    if player in self.deleted_players: 
                        continue
                    ret+="\n{} ".format(player.get_full_name(len(self.races)))
                    #flag insertion by region
                    flag_code = player.getFlag()
                    ret+=f"[{flag_code if flag_code else ''}] "
                    ret+= player.get_score_str(by_race)
                    
                if tag in self.team_pens.keys():
                    ret+='\nPenalty -{}'.format(self.team_pens[tag])
                            
        return ret

    def get_table_text(self):
        self.table_str = self.create_string()
        return Utils.disc_clean(self.table_str)
    
    async def get_table_img(self, by_race = False):
        if by_race:
            temp_string = self.create_string(by_race=by_race)
            png_link = "https://gb.hlorenzi.com/table.png?data={}".format(quote(temp_string))
            
        else:
            png_link = "https://gb.hlorenzi.com/table.png?data={}".format(quote(self.table_str))
            
        self.table_link = png_link.replace('.png', "")
       
        timeout = 10
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(png_link, timeout=timeout) as resp:
                    if resp.status!=200:
                        return "Error while fetching table picture: table picture rendering site is down."
                    return BytesIO(await resp.read())
            except:
                return "Error while fetching table picture: timed out."

        # with urlopen(png_link) as url:
        #     output = BytesIO(url.read())
        # return output
    
    def get_modifications(self):
        ret = ''
        if len(self.modifications)==0:
            ret+="No table modifications to undo."
        for i,m in enumerate(self.modifications):
            ret+=f'{i+1}. {self.prefix}{m[0][0]}\n'
        return ret
    
    def get_undos(self):
        ret = ''
        if len(self.undos)==0:
            ret+="No table modification undos to redo."
        
        for i,u in enumerate(self.undos):
            ret+=f"{i+1}. {self.prefix}{u[0][0]}\n"
        return ret
    
    def undo_warning(self,mod):
        mod_type = mod[0]
        
        if mod_type.find('edit ') == 0:
            gp = int(mod[2])
            count = 0
            for x in self.modifications:
                for j in x:
                    if 'edit ' in j[0] and int(j[2])==gp:
                        count+=1
            if count==1: self.manual_warnings[-1].remove(f"GP {gp} scores have been manually modified by the tabler.")
            
        elif 'editrace' in mod_type:
            raceNum = int(mod[2])
            count = 0
            for x in self.modifications:
                for j in x:
                    if 'editrace' in j[0] and int(j[2])==raceNum:
                        count+=1
            if count==1: 
                self.manual_warnings[raceNum].pop(self.manual_warnings[raceNum].index("Placements for this race have been manually altered by the tabler."))
                
        elif 'dcs' in mod_type:
            count = 0
            for x in self.modifications:
                for j in x:
                    if 'dcs' in j[0] and int(j[1])==int(mod[1]):
                        count+=1
            if count==1:
                raceNum = self.dc_list_ids[int(mod[1])][1]
                player = self.dc_list_ids[int(mod[1])][0]
                for indx, i in enumerate(self.dc_list[raceNum]):
                    if i.get('player') == player:
                        self.dc_list[raceNum][indx]['is_edited'] = False
                for indx,i in enumerate(self.warnings[raceNum]):
                    if i.get('player') == player:
                        self.warnings[raceNum][indx]['is_edited'] = False
        elif "removerace" in mod_type:
            raceNum= int(mod[1])
            track = mod[2]
            for indx,i in enumerate(self.manual_warnings[-1]):
                if 'Race #{}'.format(raceNum) in i and track in i and 'has been removed' in i:
                    self.manual_warnings[-1].pop(indx)
                    break
        
        else:
            raceNum = int(mod[1])
            count=0
            for x in self.modifications:
                for j in x:
                    if 'changeroomsize' in j[0] and int(j[1])==raceNum:
                        count+=1
            if count==1:
                for indx, i in enumerate(self.manual_warnings[raceNum]):
                    if i.find("Room size changed")==0:
                        self.manual_warnings[raceNum].pop(indx)
                        break
                    
        self.warnings = defaultdict(list,{k:v for k,v in self.warnings.items() if len(v)>0})
        self.manual_warnings = defaultdict(list,{k:v for k,v in self.manual_warnings.items() if len(v)>0})  
    
    async def undo(self, j: Tuple[str, Any]):
        if j[0].find('edit ') == 0:
            self.undo_edit(j[1], j[4])
            self.undo_warning(j)
                
        elif 'editrace' in j[0]: 
            self.edit_race([[j[2], j[1], j[3]]], reundo=True)
            self.undo_warning(j)
        
        elif j[0].find('pen') == 0:
            self.unpenalty(j[1], str(j[2]), reundo=True)
        
        elif j[0].find('unpen') == 0:
            self.penalty(j[1], str(j[2]), reundo=True)
        
        elif 'teampen' in j[0]:
            self.team_unpenalty(j[1], str(j[2]), reundo=True)
        
        elif 'teamunpen' in j[0]:
            self.team_penalty(j[1], str(j[2]), reundo=True)
        
        elif 'dcs'in j[0]: 
            self.edit_dc_status([[j[1], j[2]]], reundo=True)
            self.undo_warning(j)
            
        elif 'changeroomsize' in j[0]:
            self.undo_crs(j[1], j[2], j[4])
            self.undo_warning(j)
        
        elif 'removerace' in j[0]:
            await self.restore_removed_race(j[1])
            self.undo_warning(j)
            
        elif j[0].find('sub') == 0:
            self.undo_sub(j[1], j[2], j[4])
            
        elif 'editsub' in j[0]:
            self.edit_sub_races(j[1], j[3], j[4], out_index=j[5], reundo=True)
        
        elif 'mergeroom' in j[0]:
            await self.un_merge_room(j[1])
        
        elif 'edittag' in j[0]:
            self.edit_tag_name([[j[1], j[2]]], reundo=True)
        
        elif 'changetag' in j[0]:
            self.change_tag(j[1], j[3], restore_indx=j[4], reundo=True)

        elif 'tags ' in j[0]:
            self.undo_group_tags(j[1])
        
        elif 'changename ' in j[0]:
            self.undo_change_name(j[1], j[3],j[4])
        
        elif 'graph ' in j[0]:
            self.change_graph(j[1], reundo=True)
        
        elif 'style ' in j[0]:
            self.change_style(j[1], reundo=True)
        
        elif 'gps ' in j[0]:
            self.change_gps(j[1], reundo=True)
        
        elif 'largetimes' in j[0]:
            self.change_sui(j[1], reundo=True)
        
        else:
            print("UNKNOWN UNDO TYPE:",j[0])
            raise AssertionError
    
    async def redo(self, j):
        if j[0].find('edit ') == 0:
            if "+" in j[0] or '-' in j[0]:
                self.edit([[j[1], j[2], str(j[3])]], redo=True)
            else:
                self.edit([[j[1], j[2], str(j[3])]], redo=True)
                
        elif 'editrace' in j[0]:
            self.edit_race([[j[2], j[1], j[4]]], reundo=True)
        
        elif j[0].find('pen') == 0:
            self.penalty(j[1], str(j[2]), reundo=True)
        
        elif j[0].find('unpen') == 0:
            self.unpenalty(j[1], str(j[2]), reundo=True)
            
        elif 'teampen' in j[0]:
            self.team_penalty(j[1], str(j[2]), reundo=True)
        
        elif 'teamunpen' in j[0]:
            self.team_unpenalty(j[1], str(j[2]), reundo=True)
        
        elif 'dcs'in j[0]:
            self.edit_dc_status([[j[1], j[3]]], reundo=True)
        
        elif 'changeroomsize' in j[0]:
            self.change_room_size([[j[1], j[3]]], reundo=True)
        
        elif 'removerace'==j[0]:
            await self.remove_race(j[1], redo=True)
            
        elif j[0].find('sub') == 0:
            self.sub_in(j[1], j[2], j[3], reundo=True)
    
        elif 'editsub' in j[0]:
            self.edit_sub_races(j[1], j[2], j[4], out_index=j[5], reundo=True)   
            
        elif 'mergeroom' in j[0]:
            await self.merge_room([j[2]], redo=True)
        
        elif 'edittag' in j[0]:
            self.edit_tag_name([[j[2], j[1]]], reundo=True)
        
        elif 'changetag' in j[0]:
            self.change_tag(j[1], j[2], reundo=True)

        elif 'tags ' in j[0]:
            self.group_tags(j[2], redo=True)

        elif 'changename ' in j[0]:
            self.change_name([[j[1], j[2]]], redo=True)
        
        elif 'graph ' in j[0]:
            self.change_graph(j[2], reundo=True)
        
        elif 'style ' in j[0]:
            self.change_style(j[2], reundo=True)
        
        elif 'gps ' in j[0]:
            self.change_gps(j[2], reundo=True)
        
        elif 'largetimes' in j[0]:
            self.change_sui(j[2], reundo=True)
        
        else:
            print("UNKNOWN REDO TYPE:",j[0])
            raise AssertionError
            
    async def undo_commands(self, num): 
        if num == 0: #undo all
            if len(self.modifications)>0:
                for i in list(reversed(copy.deepcopy(self.modifications))):
                    for j in i:
                        await self.undo(j)
                        self.undos.append(self.modifications.pop(self.modifications.index(i)))
                
                return "All manual table modifications have been undone."
            return "No manual modifications to the table to undo."
        
        else: #undo last
            if len(self.modifications)>0:
                for i in self.modifications[-1]:
                    await self.undo(i)
                    
                mod = self.modifications[-1]
                self.undos.append(mod)
                del self.modifications[-1]
                return f"Last table modification ({Utils.disc_clean(self.prefix+mod[0][0])}) has been undone."
            return "No manual modifications to the table to undo."
        
    async def redo_commands(self, num):
        if num == 0: #redo all
            if len(self.undos)>0:
                for i in list(reversed(self.undos)):
                    for j in i:
                        await self.redo(j)
                
                self.modifications = list(reversed(self.undos))
                self.undos = []
                return "All manual table modifications have been redone."
            return "No table modifications to redo."
        
        else: #redo last undo
            if len(self.undos)>0:
                for i in self.undos[-1]:
                    await self.redo(i)
                    
                mod = self.undos[-1]
                self.modifications.append(mod)
                del self.undos[-1]
                return f"Last table modification undo ({Utils.disc_clean(self.prefix+mod[0][0])}) has been redone."
            return "No table modifications to redo."
        
        
    async def fetch(self, url, headers=None): 
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession() as session:
            if headers == None:
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

    async def fetch_mkwx_JSON(self, url, headers=None):
        url+="?m=json"
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession() as session:
            if headers == None:
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
        
    
if __name__ == "__main__":
    import urllib3
    http = urllib3.PoolManager()
    page = http.request('GET', "www.wiimmfi.de/stats/mkwx/list/{}")
    soup = BeautifulSoup(page.data, "html.parser")
    