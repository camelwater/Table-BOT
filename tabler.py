# -*- coding: utf-8 -*-
"""
Created on Tue May 18 15:05:35 2021

@author: ryanz
"""
from bs4 import BeautifulSoup
import copy
#from PIL import Image
from io import BytesIO
from urllib.parse import quote
import aiohttp
from urllib.request import urlopen
import datetime
import discord
from discord.ext import tasks
import time as timer
from unidecode import unidecode
from collections import defaultdict, Counter
import Utils
from Utils import isFFA, warning_map, dc_map, style_map, pts_map
from Utils import graph_map as gm
graph_map = copy.deepcopy(gm)


class Table():
    def __init__(self, ctx = None, bot = None, graph = None, style = None, testing = False):
        self.TESTING = testing
        self.IGNORE_FCS = False
        if self.TESTING:
            self.init_testing()
        
        self.URL = "https://wiimmfi.de/stats/mkwx"
        self.ROOM_URL = "https://wiimmfi.de/stats/mkwx/list/{}"
        self.current_url = ""
        self.last_race_update = None
        
        self.modifications = [] #keep track of all user modifications to the table
        self.undos = [] #keep track of all user undos of modifications to the table
        
        self.recorded_elems = [] #don't record races that have already been recorded
        self.players = {} #dictionary of players: holds their total score, gp scores, and race scores
        self.finish_times = {} #finish times of each race (used for ?rr)
        self.races = [] #list (race) of lists (placements for each race) 
        self.pens = {} # mapping players to penalties
        self.team_pens = {} #mapping penalties to teams
        self.fcs = {} #map fcs to mii name (so no conflicts with mii names - uniqueness)
        self.display_names = {}
        self.player_ids = {} #used to map player ids to players (player id from bot)
        self.all_players = [] #list of every player who has been in the room
        self.sub_names = {}
        self.deleted_players = [] #players who have been removed from table through ?changename
       
        self.warnings = defaultdict(list) #race: list of warnings
        self.manual_warnings = defaultdict(list)

        self.dc_list = defaultdict(list) # race: list of player dcs (?dcs)
        self.tracks = [] #track list
        self.dup_names = [] #in case some players have same mii name. fc: edited mii name (ex. 'Player-1' instead of 'Player') for clarity purposes on table
        self.ties = {} #tied race times
        self.gp_dcs = {} #gp: list of players who have dced in gp (to ensure dc warnings are simplified in embed)
        self.dc_pts = {} #player: number of races to award +3 DC points 
        self.dc_list_ids = {} #mapping dcs to an id (used for the command ?dcs)
        
        self.removed_races = {}
        self.removed_warn_dcs = {}
        
        self.room_sizes = [] #list of room sizes for different gps (check if room size increases mid-gp, to send warning message - ?changeroomsize might be necessary)
        self.room_players = [] #list of list of players at beginning of GP (check if room changes mid-gp, send warning)
        self.room_sizes_error_affected = [] #races affected by mkwx messing up room sizes
        self.room_error_index = [] #to update room size warnings
        
        self.changed_room_sizes = defaultdict(list) #races that have edited room sizes (?changeroomsize)
        self.edited_scores = defaultdict(lambda: defaultdict(int)) #players with edited gp scores
                   
        self.tags = {} #list of team tags and their respective players
        self.table_str = "" #argument for data (to get pic from gb.hlorenzi.com)
        self.graph = graph
        self.style = style
        self.table_img = None
        self.table_link = '' #image png link
        self.sui = False 
        
        self.prev_rxxs = [] # for rooms that have been merged
        self.prev_elems = []
        self.current_elems = []
        
        self.format = "" #format (FFA, 2v2, etc.)
        self.teams = 0 #number of teams
        self.gps = 3 #number of total gps
        self.rxx = '' #rxx that table is watching
        self.gp = 0 #current gp
        self.num_players = 0 #number of players room is supposed to have (based on format and teams)
        self.player_list = '' #string for bot printout of players and their ids
        

        ##### Stuff for bot instances #####
        self.choose_message = ""
        self.searching_room = False
        self.choose_room = False
        self.confirm_room = False
        self.confirm_reset = False
        self.reset_args = None
        self.undo_empty = False
        self.redo_empty = False
        self.table_running = False
        self.picture_running = False
        self.ctx = ctx
        self.bot = bot
        self.last_command_sent = None
        ##### Stuff for bot instances #####
        
    def init_testing(self):
        # self.players = {'pringle@MV':0,'5headMV':0,'hello LTA':0,'LTAX':0,
        #     'jaja LTA':0,'stupid@LTA':0,'poop MV':0,'MVMVMVMV':0,'LTA Valpo':0,"mom's mv":0}
        self.players = {'x#1':0, 'xxx':0, 'Z':0, '¢unt':0, 'ZZZ': 0, 'cool kid': 0, "i am": 0, "IS U DUMB": 0, 'gas mob':0, "gassed up":0}
        self.IGNORE_FCS = True
        self.split_teams('2', 1)

    async def find_room(self, rid = None, mii = None, merge=False, redo=False) -> tuple:
        """
        find mkwx room using either rxx or mii name search
        """
        if merge:
            
            if rid == None:
                rxxs = {}
                data= await self.fetch(self.URL)
                if isinstance(data, str) and 'error' in data:
                    if 'response' in data:
                        return True, "Wiimmfi appears to be down. Try again later."
                    else:
                        return True, "I am currently experiencing some issues with Wiimmfi. Try again later."
                    
                miis = data.find_all('span', {'class': 'mii-font'})
                for m in mii:
                    for comp in miis:
                        if comp.text.lower()==m.lower():
                            rxx = comp.findPrevious('tr', {'id':True})['id']
                            try:
                                rxxs[rxx]+=1
                            except:
                                rxxs[rxx] = 1
                if len(rxxs)==0:
                    return True, "{} {} not found in any rooms.\nMake sure all mii names are correct.".format(mii, "were" if len(mii)>1 else "was")
                if len(rxxs)>1:
                    if len(mii)==1:
                        return True, "{} was found in multiple rooms: {}.\nTry again with a more refined search.".format(mii[0], list(rxxs.keys()))
                    rxx = [keys for keys,values in rxxs.items() if values == max(rxxs.values())]
                    if len(rxx)>1:
                        return True, "{} {} found in multiple rooms: {}.\nTry again with a more refined search.".format(mii, "were" if len(mii)>1 else "was", rxx)
               
                rxx = max(rxxs, key=rxxs.get) 
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
                    return True, "The room ({}) hasn't finished a race yet.\nRetry `?mergeroom` when the room has finished one race.".format(rxx)
                
                self.current_url = room_url
                self.prev_rxxs.append(self.rxx)
                self.prev_elems.append(self.current_elems)
                self.current_elems=[]
                self.rxx = rxx
                self.last_race_update = None
                if not redo:
                    self.modifications.append([("?mergeroom {}".format(mii), len(self.prev_elems), rxx)])
                    self.undos.clear()
                
                new_elems = soup.select('tr[id*=r]')
                return False, "Rooms have successfully merged. Now watching room {}. {} races played.".format(self.rxx, len(self.races)+len(new_elems))
            
            else:
                rid = rid[0]
                if rid==self.rxx or rid in self.prev_rxxs:
                    return True, "This room is already part of this table. Merge cancelled."
                room_url = "https://wiimmfi.de/stats/mkwx/list/{}".format(rid)
                
                soup = await self.fetch(room_url)
                if isinstance(soup, str) and 'error' in soup:
                    if 'response' in soup:
                        return True, "Wiimmfi appears to be down. Try again later."
                    else:
                        return True, "I am currently experiencing some issues with Wiimmfi. Try again later."
                
                stripped = list(soup.stripped_strings)
                if "No match found!" in stripped:
                    return True, "The room ({}) hasn't finished at least one race yet.\nRetry `?mergeroom` when the room has finished at least one race.".format(rid)
                
                self.current_url = room_url
                self.prev_rxxs.append(self.rxx)
                self.prev_elems.append(self.current_elems)
                self.current_elems=[]
                self.rxx = rid
                if len(rid)==4: self.rxx = self.rxx.upper()
                self.last_race_update = None
                if not redo:
                    self.modifications.append([("?mergeroom {}".format(rid), len(self.prev_elems), rid)])
                    self.undos.clear()
                
                new_elems = soup.select('tr[id*=r]')
                return False, "Rooms have successfully merged. Now watching room {}. {} races played.".format(self.rxx,len(self.races)+len(new_elems))
        else:
            type_ask = "none"
            if rid == None: #mii names search
                rxxs = {}
                data = await self.fetch(self.URL)
                if isinstance(data, str) and 'error' in data:
                    if 'response' in data:
                        return True, type_ask,"Wiimmfi appears to be down. Try again later."
                    else:
                        return True, type_ask,"I am currently experiencing some issues with Wiimmfi. Try again later."
                
                miis = data.find_all('span',{"class" : "mii-font"})
                for m in mii:
                    for comp in miis:
                        if comp.text.lower()==m.lower():
                            rxx = comp.findPrevious('tr', {"id":True})['id']
                            try:
                                rxxs[rxx]+=1
                            except:
                                rxxs[rxx] = 1
               
                if len(rxxs)==0:
                    return True, type_ask, "{} {} not found in any rooms.\nMake sure all mii names are correct.".format(', '.join(map(str, mii)), "were" if len(mii)>1 else "was")
                if len(rxxs)>1:
                    if len(mii)==1:
                        return True, type_ask, "{} was found in multiple rooms: {}.\nTry again with a more refined search.".format(mii[0], list(rxxs.keys()))
                    rxx = [keys for keys,values in rxxs.items() if values == max(rxxs.values())]
                    if len(rxx)>1:
                        return True, type_ask, "{} {} found in multiple rooms: {}.\nTry again with a more refined search.".format(', '.join(map(str, mii)), "were" if len(mii)>1 else "was", ', '.join(map(str,rxx)))
               
                rxx = max(rxxs, key=rxxs.get) 
                self.rxx = rxx
    
                room_url = "https://wiimmfi.de/stats/mkwx/list/{}".format(self.rxx)
                soup = await self.fetch(room_url)
                if isinstance(soup, str) and 'error' in soup:
                    if 'response' in soup:
                        return True, type_ask, "Wiimmfi appears to be down. Try again later."
                    else:
                        return True,type_ask, "I am currently experiencing some issues with Wiimmfi. Try again later."

                if "No match found!" in list(soup.stripped_strings):
                    return True, type_ask, "The room hasn't finished at a race yet.\nRetry `?search` when the room has finished one race."
                else:
                    self.find_players(room_url, soup)
                    self.split_teams(self.format, self.teams)
                    type_ask = "confirm"
                    self.current_url = room_url
                    string = ""
                
                    counter = 1
                    if isFFA(self.format):
                        string+='\n__FFA__'
                        for p in self.players.keys():
                            string+="\n{}. {}".format(counter,self.display_names[p])
                            self.player_ids[str(counter)] = p
                            counter+=1          
                    else:
                        self.tags = dict(sorted(self.tags.items(), key=lambda item: unidecode(item[0].upper())))
                        for tag in self.tags.keys():
                            if tag == "":
                                 for p in self.tags[tag]:
                                     string+="\n**NO TEAM**\n\t{}. {} ".format(counter,Utils.dis_clean(self.display_names[p]))
                                     self.player_ids[str(counter)] = p
                                     counter+=1
                            else:   
                                string+='\n**Tag: {}**'.format(Utils.dis_clean(tag))
                                for p in self.tags[tag]:
                                    string+="\n\t{}. {}".format(counter,Utils.dis_clean(self.display_names[p]))
                                    self.player_ids[str(counter)] = p
                                    counter+=1
                                    
                    self.player_list = string
                    return False, type_ask, "Room {} found.\n{}\n\n**Is this correct?** (`?yes` / `?no`)".format(self.rxx, string)     
                
            else: #room id search
                rid = rid[0]
                self.rxx = rid
                if len(rid)==4: self.rxx = self.rxx.upper()
                
                room_url = "https://wiimmfi.de/stats/mkwx/list/{}".format(rid)
                
                soup = await self.fetch(room_url)

                if isinstance(soup, str) and 'error' in soup:
                    if 'response' in soup:
                        return True, type_ask, "Wiimmfi appears to be down. Try again later."
                    else:
                        return True,type_ask, "I am currently experiencing some issues with Wiimmfi. Try again later."
                
                stripped = list(soup.stripped_strings)
                if "No match found!" in stripped:
                    return True, type_ask, "The room either doesn't exist or hasn't finished a race yet.\nRetry `?search` when the room has finished one race and make sure the room id is in rxx or XX00 format."
                else:
                    self.find_players(room_url, soup)
                    self.split_teams(self.format, self.teams)
                    type_ask = "confirm"
                    self.current_url = room_url
                    string = ""
                    
                    counter = 1
                    if isFFA(self.format):
                        string+='\n_FFA_'
                        for p in self.players.keys():
                            string+="\n{}. {}".format(counter,self.display_names[p])
                            self.player_ids[str(counter)] = p
                            counter+=1          
                    else:
                        self.tags = dict(sorted(self.tags.items(), key=lambda item: unidecode(item[0].upper())))
                        for tag in self.tags.keys():
                            if tag == "":
                                 for p in self.tags[tag]:
                                     string+="\n**NO TEAM**\n\t{}. {} ".format(counter,Utils.dis_clean(self.display_names[p]))
                                     self.player_ids[str(counter)] = p
                                     counter+=1
                            else:   
                                string+='\n**Tag: {}**'.format(Utils.dis_clean(tag))
                                for p in self.tags[tag]:
                                    string+="\n\t{}. {}".format(counter,Utils.dis_clean(self.display_names[p]))
                                    self.player_ids[str(counter)] = p
                                    counter+=1
                    #string = string.replace("no name", "Player")
                    self.player_list = string
                    return False, type_ask, "Room {} found.\n{}\n\n**Is this room correct?** (`?yes` / `?no`)".format(self.rxx, string)
    
    
    def split_teams(self, f, num_teams):
        """
        split players into teams based on tags
        """
        tick=timer.perf_counter_ns()
        f = f[0]
        if not f.isnumeric():
            return
        per_team = int(f)
        teams = {} #tag: list of players
        player_copy = list(self.display_names.values()) if not self.IGNORE_FCS else list(copy.deepcopy(self.players).keys())
        #print(player_copy)
        post_players = []
        
        i = 0
        while i< len(player_copy):
            tag = ''
            matches = 1
            indx = len(player_copy[i])+1

            while matches < per_team and indx>0:
                indx-=1
                matches = 1
                for j in range(len(player_copy)):                    
                    if i!=j and indx>0 and unidecode(Utils.sanitize_uni(player_copy[i].strip().lower().replace("[","").replace(']','')))[:indx] == unidecode(Utils.sanitize_uni(player_copy[j].strip().lower().replace("[","").replace(']','')))[:indx]:
                        matches+=1
                        #print(unidecode(Utils.sanitize_uni(player_copy[i].strip().lower().replace("[","").replace(']','')))[:indx], unidecode(Utils.sanitize_uni(player_copy[j].strip().lower().replace("[","").replace(']','')))[:indx])
                        if matches == per_team: break 
                
            tag = Utils.sanitize_uni_tag(player_copy[i].replace("[","").replace(']',''))[:indx]
            if len(tag)>0 and tag[-1]=="-": 
                tag = tag[:-1]
                indx-=1
            if len(tag)==1: tag = Utils.sanitize_uni(tag).upper()
            
            temp_tag = tag
            if tag == "": 
                post_players.append(player_copy.pop(i))
                continue
            x = 1
            while temp_tag in teams:
                temp_tag = tag.rstrip() +"-"+str(x)
                x+=1
            teams[temp_tag] = []
            ind = 0
            while ind<len(player_copy):
                if unidecode(Utils.sanitize_uni(tag.lower().replace("[","").replace(']',''))) == unidecode(Utils.sanitize_uni(player_copy[ind].strip().lower().replace("[","").replace(']','')))[:indx]: 
                    if len(teams[temp_tag])<per_team:
                        teams[temp_tag].append(player_copy.pop(ind))
                        ind = 0
                        continue
                ind+=1
                
            i = 0 

        #find suffix tags
        i = 0
        all_tag_matches= {}
        while i < len(post_players):
            tag = ''
            matches = 1
            indx = len(post_players[i])+1
            
            postfix_fill = False
            for team in teams.items():
                if len(team[1])<per_team:
                    postfix_fill = True
                    break
            if postfix_fill:
                cont=False
                while indx>0:
                    indx-=1
                    for tag, _list in teams.items():
                        if len(_list)<per_team and unidecode(Utils.sanitize_uni(post_players[i].strip().lower().replace("[","").replace(']','')))[::-1][:indx][::-1] == unidecode(Utils.sanitize_uni(tag.lower().strip().replace("[","").replace(']',''))):
                            teams[tag].append(post_players.pop(i))
                            i = 0
                            cont = True
                            break
                if cont:
                    continue


            #suffix and prefix (together) check
            temp_tag = ''
            tag_matches = defaultdict(list)
            temp_indx = len(post_players[i])+1
            while temp_indx>0:
                cont=False
                temp_indx-=1
               
                for j in range(len(post_players)):
                    i_tag = unidecode(Utils.sanitize_uni(post_players[i].strip().lower().replace("[","").replace(']','')))
                    j_tag = unidecode(Utils.sanitize_uni(post_players[j].strip().lower().replace("[","").replace(']','')))
                    
                    if i!=j and temp_indx>0 and (i_tag[:temp_indx] == j_tag[::-1][:temp_indx][::-1]
                                                 or i_tag[:temp_indx] == j_tag[:temp_indx]):
                        
                        #print(temp_indx, post_players[i], post_players[j])
                        m_tag = Utils.sanitize_uni_tag(post_players[i].strip().replace("[","").replace(']',''))[:temp_indx]
                        if len(m_tag) == 1: 
                            m_tag = Utils.sanitize_uni(m_tag).upper()
                        temp = m_tag
                        d = 1
                        while m_tag.lower().strip() in map(lambda o: o.lower().strip(), list(teams)):
                            m_tag = f"{temp}-{d}"
                            d+=1

                        if len(tag_matches[m_tag])==0:
                            tag_matches[m_tag].append(post_players[i])
                        tag_matches[m_tag].append(post_players[j])
                        if len(tag_matches[m_tag])==per_team:
                            teams[m_tag] = tag_matches.pop(m_tag)
                            for p in teams[m_tag]:
                                try:
                                    post_players.remove(p)
                                except:
                                    pass
                                for x in all_tag_matches.items():
                                    try:
                                        all_tag_matches[1].remove(p)
                                    except:
                                        pass
                                i = -1
                            cont=True
                            break
                        
                    elif i!=j and temp_indx>0 and (i_tag[::-1][:temp_indx][::-1] == j_tag[::-1][:temp_indx][::-1]
                                   or i_tag[::-1][:temp_indx][::-1] == j_tag[:temp_indx]):
                        
                        #print(temp_indx, post_players[i], post_players[j])
                        m_tag = Utils.sanitize_uni_tag(post_players[i].strip().replace("[","").replace(']',''))[::-1][:temp_indx][::-1]
                        if len(m_tag) == 1: 
                            m_tag = Utils.sanitize_uni(m_tag).upper()
                        temp = m_tag
                        d = 1
                        while m_tag.lower().strip() in map(lambda o: o.lower().strip(), list(teams)):
                            m_tag = f"{temp}-{d}"
                            d+=1

                        if len(tag_matches[m_tag])==0:
                            tag_matches[m_tag].append(post_players[i])
                        tag_matches[m_tag].append(post_players[j])
                        if len(tag_matches[m_tag])==per_team:
                            teams[m_tag] = tag_matches.pop(m_tag)
                            for p in teams[m_tag]:
                                try:
                                    post_players.remove(p)
                                except:
                                    pass
                                for x in all_tag_matches.items():
                                    try:
                                        all_tag_matches[1].remove(p)
                                    except:
                                        pass
                                i = -1
                            cont=True  
                            break
                                
                if cont:
                    break
               
            i+=1
            for item in tag_matches.items():
                if item[0] in all_tag_matches:
                    if len(item[1]) > len(all_tag_matches[item[0]]):
                        all_tag_matches[item[0]] = item[1]
                    # if len(item[1]) > len(all_tag_matches[item[0]]) and len(all_tag_matches[item[0]])!=per_team:
                    #     all_tag_matches[item[0]] = item[1]
                    # else:
                    #     temp = check = item[0]
                    #     d = 1
                    #     while check in all_tag_matches:
                    #         check = f"{temp}-{d}"
                    #         d+=1
                    #     all_tag_matches[check] = item[1]
                else:
                    all_tag_matches[item[0]] = item[1]

        #print(post_players)
        teams_needed = num_teams-len(teams.keys())
        #print("teams needed:",teams_needed)
        if(len(all_tag_matches)>=teams_needed):
            for t in range(teams_needed):
                for x in copy.deepcopy(all_tag_matches).items():
                    for player in x[1]:
                        if player not in post_players:
                            all_tag_matches[x[0]].remove(player)
                    if len(all_tag_matches[x[0]]) == 0:
                        all_tag_matches.pop(x[0])
                if len(all_tag_matches) == 0:
                    continue
                all_tag_matches = dict(sorted(all_tag_matches.items(), key=lambda item: len(item[1]), reverse=True))
                teams[list(all_tag_matches.keys())[0]] = all_tag_matches[list(all_tag_matches.keys())[0]]
                for p in all_tag_matches[list(all_tag_matches.keys())[0]]:
                    try:
                        post_players.remove(p)
                    except:
                        pass
                all_tag_matches.pop(list(all_tag_matches.keys())[0])
                
                        
        un_players = copy.deepcopy(post_players)
        post_players.clear()
      
        #substring (unconventional) tag for 2v2s
        if per_team==2:
            i = 0
            while i<len(un_players):
                tag = ''
                longest_match = 1
                match = 0
                
                for j in range(len(un_players)):
                    m = Utils.LCS(unidecode(Utils.sanitize_uni(un_players[i].strip().lower().replace("[","").replace(']','').replace(" ", ""))), unidecode(Utils.sanitize_uni(un_players[j].strip().lower().replace("[","").replace(']','').replace(" ",""))))
                    if i!=j and len(m)>longest_match:
                        longest_match = len(m)
                        match= un_players[i], un_players[j]
                        tag = m

                if match == 0 or tag == '':
                    i+=1
                else:
                    temp_tag = tag
                    x = 1
                    while temp_tag in teams:
                        temp_tag = tag+"-"+str(x)
                        x+=1
                    teams[temp_tag] = list(match)
                    for p in match:
                        un_players.remove(p)

        #randomly tag the rest (tag could not be determined)
        if len(un_players)>0:
            is_all_filled = True
            for item in teams.items():
                    if len(item[1])<per_team:
                        is_all_filled = False
                        break
            def split():
                split = list(Utils.chunks(un_players, per_team))
                for i in split:
                    for ind,j in enumerate(i):
                        try:
                            temp = check = Utils.replace_brackets(j)[0]
                            d = 1
                            while check.lower() in map(lambda o: o.lower(), list(teams)):
                                check = f"{temp}-{d}"
                                d+=1
                            teams[check] = i
                            break
                        
                        except:
                            if ind+1==len(i):
                                teams[j[0][0]] = i
                            else:
                                continue
                    
            if len(teams)==num_teams and not is_all_filled:
                for item in teams.items():
                    while len(item[1])<per_team and len(un_players)>0:
                        item[1].append(un_players.pop(0))
                if len(un_players)>0:
                    split()
            else:
                split()
        
        if not self.IGNORE_FCS:
            print(teams)
            for i in teams.items():
                teams[i[0]] = [self.fcs[j] for j in i[1]]  
        self.tags = teams
        self.all_players = copy.deepcopy(self.tags)
        self.tags = dict(sorted(self.tags.items(), key=lambda item: unidecode(item[0].lower())))
        self.tags = {k.strip(): v for (k, v) in self.tags.items()}

        print()
        print(self.tags)
        print("tag algo time:",timer.perf_counter_ns()-tick)

    def warn_to_str(self, warning):                
        warning_type = warning.get('type')

        if "dc_" in warning_type:
            ret = ''
            is_edited = warning.get('is_edited', False)

            if "on" in warning_type:
                warning_type = warning_type+"_confirmed" if is_edited else warning_type
                race = warning.get('race')
                if race == 1:
                    ret = warning_map.get((warning_type, race)).format(self.display_names[warning.get('player')], warning.get('gp'), warning.get('gp')) 
                elif race == -1:
                    ret = warning_map.get((warning_type, race)).format(self.display_names[warning.get('player')], warning.get('gp'))
                else:
                    ret = warning_map.get(warning_type).format(self.display_names[warning.get('player')], warning.get('gp'), warning.get('pts'))
            
            else:
                race = warning.get('race')
                if race == 1:
                    ret = warning_map.get((warning_type,race)).format(self.display_names[warning.get('player')], warning.get('gp'), warning.get('gp'), warning.get('gp'))
                else:
                    ret = warning_map.get(warning_type).format(self.display_names[warning.get('player')], warning.get('gp'), warning.get('pts'))
        
            return ret + '{}'.format(" - determined by tabler" if is_edited else "")

        elif "mkwx_bug" in warning_type:
            if "_increase" in warning_type:
                return warning_map.get(warning_type).format(warning.get('orig_players'), warning.get('new_players'), ', '.join(map(str, warning.get('races'))))

            elif "_change" in warning_type:
                return warning_map.get(warning_type).format(warning.get('race'), warning.get('gp'))
            
            elif "_tr" in warning_type:
                return warning_map.get(warning_type).format(warning.get("aff_players"), warning.get("gp"))

            elif "_delta" in warning_type:
                return warning_map.get(warning_type).format(warning.get("aff_players"), warning.get('gp'))
            
            elif "_repeat" in warning_type:
                return warning_map.get(warning_type).format(warning.get("num_affected"), warning.get('gp'))

            else:
                return warning_map.get(warning_type).format(warning.get('gp'))

        elif warning_type == "missing":
            return warning_map.get(warning_type).format(warning.get('gp'), warning.get('cur_players'), warning.get('sup_players'))
        
        elif warning_type == "overflow":
            return warning_map.get(warning_type).format(warning.get('gp'), warning.get('cur_players'), warning.get('sup_players'))
        
        elif warning_type == "blank_time":
            return warning_map.get(warning_type).format(self.display_names[warning.get('player')])

        elif warning_type == "tie":
            return warning_map.get(warning_type).format([self.display_names[i] for i in warning.get('players')], warning.get('time'))

        elif warning_type == "sub":
            return warning_map.get(warning_type).format(self.display_names[warning.get('player')])

        elif warning_type == "large_time":
            return warning_map.get(warning_type).format(self.display_names[warning.get('player')], warning.get('time'))

        else:
            print("WARNING TYPE NOT FOUND:", warning_type)
            raise AssertionError

    def get_warnings(self):
        warnings = defaultdict(list)
        #merging self.warnings with self.manual_warnings
        for race, warn_list in self.manual_warnings.items():
            warnings[race] += warn_list

        for race, warn_list in self.warnings.items():
            if race ==-1:
                warnings[race] = warn_list + warnings[race]
            else:
                warnings[race]+=warn_list

        actual_warn_len = sum([len(i[1]) for i in warnings.items()])
        if actual_warn_len==0:
            return "No warnings or room errors. Table should be accurate."
        warnings = defaultdict(list,dict(sorted(warnings.items(), key=lambda item: item[0])))
        ret = 'Room warnings/errors that could affect the table{}:\n'.format(" (?dcs to fix dcs)" if len(self.dc_list)>0 else "")
        
        for indx,i in enumerate(warnings[-1]):
            if "scores have been manually modified" in i:
                warnings[-1].append(warnings[-1].pop(indx))

        for i in warnings.items():
            if len(i[1])==0:
                continue
            if i[0]==-1:
                for warning in i[1]:
                    ret+='     - {}\n'.format(warning)
                continue
            ret+="     Race #{}: {}\n".format(i[0], self.tracks[i[0]-1])
            for warning in i[1]:
                ret+="       \t- {}\n".format(self.warn_to_str(warning) if isinstance(warning, dict) else warning)
                
        if len(ret)>2048: #potentially look to implement system for overflowing warnings (either page or separate message/command)
            return ret[:2048]
        
        return ret
    
    def set_teams(self, teams):
        self.teams = teams
        if self.teams!=2 and 3 in graph_map:
            graph_map.pop(3)
            if self.graph and self.graph.get('table') == 'diff':
                self.graph = None

    def style_options(self):
        ret = 'Table style options:'
        for num,style in style_map.items():
            ret+="\n   {} {}".format("**{}.**".format(num) if self.style and self.style.get('type') == style.get('type') else "`{}.`".format(num), style.get('type'))
        return ret
    
    def graph_options(self):
        ret = 'Table graph options:'
        for num,graph in graph_map.items():
            ret+="\n   {} {}".format("**{}.**".format(num) if self.graph and self.graph.get('type') == graph.get('type') else "`{}.`".format(num), graph.get('type'))
        return ret

    def change_style(self, choice, reundo=False):
        if choice is None:
            self.style=choice
            return

        if choice.lstrip('+').lstrip('-').isnumeric():
            c_indx = int(choice)
            choice = style_map.get(c_indx, None)
            if not choice:
                return "`{}` is not a valid style number. The style number must be from 1-{}. Look at `?style` for reference.".format(c_indx, len(style_map))
            
            if not reundo:
                self.modifications.append([("?style {}".format(c_indx), self.style.get('type') if self.style is not None else None, choice.get('type'))])
                self.undos.clear()
            
            self.style = choice
            return "Table style set to `{}`.".format(choice.get('type'))

        else:
            o_choice = choice
            not_in = True
            for i in list(style_map.values()):
                if choice.lower() in map(lambda l: l.lower(), i.values()):
                    not_in=False
                    break
            if not_in:
                options = ''
                for i in list(style_map.values()):
                    options+='   - {}\n'.format(" | ".join(map(lambda orig: "`{}`".format(orig), i.values())))
                    
                return "`{}` is not a valid style. The following are the only available style options:\n".format(o_choice)+options
            
            for i in list(style_map.values()):
                if choice.lower() in map(lambda l: l.lower(), i.values()):
                    choice = i
                    break
            
            if not reundo:
                self.modifications.append([("?style {}".format(o_choice), self.style.get('type') if self.style is not None else None, choice.get('type'))])
                self.undos.clear()
            
            self.style = choice
            return "Table style set to `{}`.".format(choice.get('type'))

    def change_graph(self, choice, reundo=False):
        if choice is None:
            self.graph = choice
            return
     
        if choice.lstrip('+').lstrip('-').isnumeric():
            c_indx = int(choice)
            choice = graph_map.get(c_indx, None)
            if not choice:
                return "`{}` is not a valid graph number. The graph number must be from 1-{}. Look at `?graph` for reference.".format(c_indx, len(graph_map))
            
            if self.teams != 2 and choice.get('table') == 'diff':
                return "The graph type `{}` can only be used when there are two teams.".format('Difference')

            if not reundo:
                self.modifications.append([("?graph {}".format(c_indx), self.graph.get('type') if self.graph is not None else None, choice.get('type'))])
                self.undos.clear()
            
            self.graph = choice
            return "Table graph set to `{}`.".format(choice.get('type'))

        else:
            o_choice = choice
            not_in = True
            for i in list(graph_map.values()):
                if choice.lower() in map(lambda l: l.lower(), i.values()):
                    not_in=False
                    break
            if not_in:
                options = ''
                for i in list(graph_map.values()):
                    options+='   - {}\n'.format(" | ".join(map(lambda orig: "`{}`".format(orig), i.values())))
                    
                return "`{}` is not a valid graph. The following are the only available graph options:\n".format(o_choice)+options
            
            for i in list(graph_map.values()):
                if choice.lower() in map(lambda l: l.lower(), i.values()):
                    choice = i
                    break
            
            if self.teams != 2 and choice.get('table') == 'diff':
                return "The graph type `{}` can only be used when there are two teams.".format('Difference')
            
            if not reundo:
                self.modifications.append([("?graph {}".format(o_choice), self.graph.get('type') if self.graph is not None else None, choice.get('type'))])
                self.undos.clear()
            
            self.graph= choice
            return "Table graph set to `{}`.".format(choice.get('type'))

    def tag_str(self):
        ret = '{}{} '.format(Utils.full_format(self.format), "" if Utils.full_format(self.format)=="FFA" else ":")
        tags_copy = list(self.tags.keys())
        try:
            tags_copy.remove("SUBS")
        except:
            pass
        try:
            tags_copy.remove("")
        except:
            pass
        for index, i in enumerate(tags_copy):
                if index==len(tags_copy)-1:
                    ret+="'{}' ".format(i)
                else:
                    ret+="'{}' vs ".format(i)
        ret+="({} {})".format(len(self.races), 'race' if len(self.races)==1 else 'races')
        return ret
    
    def check_tags(self, tag):
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
                except:
                    return "Tag index `{}` is out of range. The tag number must be from 1-{}".format(orig, len(self.tags))
                data = self.tags.pop(orig)
                new = self.check_tags(new)
                self.tags[new]= data
                self.all_players[new] = self.all_players.pop(orig)
                ret+= "Edited tag `{}` to `{}`.{}".format(orig, new, '\n' if len(l)>1 and num <len(l)-1 else "")
                
            else:
                comp = orig.upper()
                try:
                    data = None
                    for i in self.tags.keys():
                        if comp == i.upper():
                            data = self.tags.pop(i)
                            break
                    assert(data is not None)
                except:
                    string = "Tag `{}` is not a valid tag. The tag to edit must be one of the following:\n".format(orig)
                    for i in list(self.tags.keys()):
                        string+='   - `{}`\n'.format(i)
                    return string
                new = self.check_tags(new)
                self.tags[new] = data
                self.all_players[new] = self.all_players.pop(orig)
                ret+= "Edited tag `{}` to `{}`.{}".format(orig, new, '\n' if len(l)>1 and num <len(l)-1 else "")
                
            if not reundo and self.table_running:
                self.modifications.append([('?edittag {} {}'.format(t_orig, new), new, orig)])
                self.undos.clear()

        return ret
    
    def tracklist(self):
        ret = ''
        for i, track in enumerate(self.tracks):
            ret+='Race #{}: {}\n'.format(i+1, track)
        return ret
    
    def race_results(self,race):
        ret = ''
        x = {}
        tag_places = defaultdict(list)
        if race==-1:
            x = self.finish_times[len(self.races)-1]
            race = len(self.races)
        else: 
            if race-1 not in self.finish_times:
                return True, "Race `{}` doesn't exist. The race number should be from 1-{}.".format(race, len(self.races))
            x = self.finish_times[race-1]
       
        count = 0
        ret+="Race #{} - {}:\n".format(race, self.tracks[race-1])
        for i in list(x.items()):
            count+=1
            ret+="   {}. {} - {}\n".format(count, Utils.dis_clean(self.display_names[i[0]]), i[1])
            if not isFFA(self.format):
                for t in self.tags.items():
                    if i[0] in t[1]:
                        tag_places[t[0]].append(count)
            
        tag_places = dict(sorted(tag_places.items(), key=lambda item: sum([pts_map[count][i-1] for i in item[1]]), reverse=True))

        if not isFFA(self.format):
            ret+="\n"
            for tag, placements in tag_places.items():
                ret+="{} -".format(tag)
                for p in placements:
                    ret+=' {}{}'.format(p, '' if p==placements[-1] else ',')
                ret+=" ({} pts)".format(sum([pts_map[count][i-1] for i in placements]))
                ret+="{}".format("" if tag==list(tag_places.items())[-1][0] else "   |   ")
        return False,ret
    
    def change_tag(self,player, tag, restore_indx = None,reundo=False):
        if not reundo:
            p_indx=player
            try:
                player = self.player_ids[player]
            except:
                return "Player number `{}` is not valid. It must be from {}-{}".format(player, 0,len(self.players))
        old_tag = ""
        for i in self.tags.items():
            if player in i[1]:
                old_tag = i[0]
                old_indx = i[1].index(player)
                i[1].remove(player)
                self.all_players[i[0]].remove(player)
        if tag not in self.tags:
            self.tags[tag] = [player]
            self.all_players[tag] = [player]
        else:
            if reundo and restore_indx is not None:
                self.tags[tag].insert(restore_indx, player)
                self.all_players[tag].insert(restore_indx, player)
            else:
                self.tags[tag].append(player)
                self.all_players[tag].append(player)

        empty_keys = [k[0] for k in list(self.tags.items()) if len(k[1])==0]
        for k in empty_keys:
            del self.tags[k]

        ret = "{} tag changed from {} to {}".format(self.display_names[player], old_tag, tag)  
        if not reundo and self.table_running:
            self.modifications.append([("?changetag {} {}".format(p_indx, tag), player, tag, old_tag, old_indx)])

        return ret
       
    def group_tags(self,dic, redo=False):
        if not redo:
            orig_tags = self.tags
            dic_str = ''
            for i in dic.items():
                dic_str+="{} ".format(i[0])
                for j in i[1]:
                    dic_str+='{} '.format(j)
        affected_players = []
        for i in dic.items():
            for j in range(len(i[1])):
                try:
                    affected_players.append(self.player_ids[i[1][j]])
                    i[1][j] = self.player_ids[i[1][j]]
                except:
                    del i[1][j]
        for i in self.tags.items():
            for j in affected_players:
                if j in i[1]:
                    i[1].remove(j)
                    self.all_players[i[0]].remove(j)
        leftovers = []
        for i in dic.items():
            if i[0] not in self.tags:
                self.tags[i[0]] = i[1]
                self.all_players[i[0]] = i[1]
            else:
                for j in self.tags[i[0]]:
                    if j not in i[1] and j not in affected_players:
                        leftovers.append(j)
                self.tags[i[0]] = i[1]
                self.all_players[i[0]] = i[1]
        
        per_team = Utils.convert_format(self.format)
        if len(leftovers)>0:
            for i in self.tags.items():
                while len(i[1])!=per_team:
                    try:
                        i[1].append(leftovers[0])
                        self.all_players[i[0]].append(leftovers[0])
                        del leftovers[0]
                    except:
                        break
        removal = []
        for x in self.tags.items():
            if len(x[1])==0: removal.append(x[0])
        for i in removal:
            self.tags.pop(i)
        
        if not redo and self.table_running:
            self.modifications.append([("?tags {}".format(dic_str), orig_tags, dic)])

        return "Tags updated."
    
    def undo_group_tags(self, restore_tags):
        self.tags = restore_tags

    def change_name(self, l, redo=False): 
        ret = ''
        for j in l:
            player = p_indx = j[0]
            if not redo:
                player = self.player_ids[player]
            old_name = self.display_names[player] 
            if len(j)<2:
                new_name='#'
            else:
                new_name = j[1]
            new_name = self.check_name(new_name)

            should_del = False
            if new_name[0] in ['#','-']:
                should_del = True
            
            if should_del: 
                self.deleted_players.append(player)
            else:
                self.display_names[player] = new_name
            
            if not redo:
                self.modifications.append([('?changename {} {}'.format(p_indx, new_name), player, new_name, old_name, should_del)])
                self.undos.clear()
            ret+="`{}` name changed to `{}`{}.\n".format(old_name, new_name, " (removed from table)" if should_del else "")
        
        return ret

    def undo_change_name(self, player, restore_name, was_deleted):
        if was_deleted:
            self.deleted_players.remove(player)
        else:
            self.display_names[player] = restore_name
        return

    def get_player_list(self, p_form = True):
        counter = 1
        string =''
        self.tags = dict(sorted(self.tags.items(), key=lambda item: unidecode(item[0].upper())))
        if isFFA(self.format):
            for p in list(self.players.keys()):
                p2 = p
                if p in self.deleted_players: continue
                if p in self.sub_names: 
                    p2 = ''
                    for x,r in zip(self.sub_names[p]['sub_out'], self.sub_names[p]['out_races']):
                        p2 += '{}({})/'.format(x, r)
                    p2+='{}({})'.format(self.display_names[p], self.sub_names[p]['in_races'])
                else:
                    p2 = self.display_names[p2]
                string+="\n{}{}".format('`{}.` '.format(counter) if p_form else '{}. '.format(counter),Utils.dis_clean(p2))
                self.player_ids[str(counter)] = p
                counter+=1
        else:
            for tag in self.tags.keys():
                if tag == "":
                     for p in self.tags[tag]:
                         self.player_ids[str(counter)] = p
                         p2 = p
                         if p in self.deleted_players: continue
                         if p in self.sub_names: 
                            p2 = ''
                            for x,r in zip(self.sub_names[p]['sub_out'], self.sub_names[p]['out_races']):
                                p2 += '{}({})/'.format(x, r)
                            p2+='{}({})'.format(self.display_names[p], self.sub_names[p]['in_races'])
                         else:
                             p2 = self.display_names[p2]
                         string+="\n**NO TEAM**\n\t{}{}".format('`{}.` '.format(counter) if p_form else '{}. '.format(counter),Utils.dis_clean(p2))
                         
                         counter+=1
                else:   
                    string+='\n**Tag: {}**'.format(Utils.dis_clean(tag))
                    for p in self.tags[tag]:
                        self.player_ids[str(counter)] = p
                        p2 = p
                        if p in self.deleted_players: continue
                        if p in self.sub_names: 
                            p2 = ''
                            for x,r in zip(self.sub_names[p]['sub_out'], self.sub_names[p]['out_races']):
                                p2 += '{}({})/'.format(x, r)
                            p2+='{}({})'.format(self.display_names[p], self.sub_names[p]['in_races'])
                        else:
                            p2 = self.display_names[p2]
                        string+="\n\t{}{}".format('`{}.` '.format(counter) if p_form else '{}. '.format(counter),Utils.dis_clean(p2))
                        
                        counter+=1

        self.player_list = string
        return self.player_list

    def dc_to_str(self, dc):
        dc_type = dc.get('type')
        is_edited = dc.get('is_edited', False)
        race = dc.get('race', 0)
        ret = ""

        if '_on' in dc_type:
            dc_type = dc_type+'_confirmed' if is_edited else dc_type
            if race == 1:
                ret = dc_map.get((dc_type, 1)).format(self.display_names[dc.get('player')], dc.get('gp'), dc.get('gp'))
            elif race == -1:
                ret = dc_map.get((dc_type, -1)).format(self.display_names[dc.get('player')], dc.get('gp'))
            else:
                ret = dc_map.get(dc_type).format(self.display_names[dc.get('player')], dc.get('gp'), dc.get('pts'))
        else:
            if race == 1:
                ret = dc_map.get((dc_type, 1)).format(self.display_names[dc.get('player')], dc.get('gp'), dc.get('gp'), dc.get('gp'))
            else:
                ret = dc_map.get(dc_type).format(self.display_names[dc.get('player')],  dc.get('gp'), dc.get('pts'))
        return ret + '{}'.format(' - edited by tabler' if is_edited else "")

    def dc_list_str(self): 
        ret = "DCs in the room:\n"
        dc_count = 1
        for race in list(self.dc_list.items()):
            ret+='**Race #{}: {}**\n'.format(race[0], self.tracks[int(race[0]-1)])
            for dc in race[1]:
                ret+='\t`{}.` **{}\n'.format(dc_count, self.dc_to_str(dc))
                dc_count+=1
                
        if len(self.dc_list)==0:
            ret+="**No DCs.**"
        return ret
        
    def dc_ids_append(self,player, race):
        i = 1
        while i in self.dc_list_ids:
            i+=1
        self.dc_list_ids[i] = [player,race]
        
    def edit(self,l, redo=False): 
        ret= ''

        for elem in l:
            player = elem[0]
            gp = elem[1]
            score = elem[2]
            if not redo:    
                try:
                    p_indx = int(player)
                    player = self.player_ids[player]
                except:
                    ret+="`{}` was not a valid player index. The player number must be from 1-{}.\n".format(player, len(self.players))
                    continue
        
            try:
                assert(int(gp)-1 <=self.gp)
            except:
                ret+="`{}` was not a valid gp (player number `{}`). The gp number must be from 1-{}.\n".format(gp, p_indx, self.gp+1)
                continue
            
            if '-' in score or '+' in score:
                if int(gp) in self.edited_scores[player]:
                    self.edited_scores[player][int(gp)] += int(score)                    
                else:
                    self.edited_scores[player][int(gp)] = self.players[player][1][int(gp)-1] + int(score)
                    
                
                if not redo:
                    self.modifications.append([('?edit {} {} {}'.format(p_indx, gp, score), player, gp, score)])
                    self.undos.clear()
                
                try:
                    self.manual_warnings[-1].remove("GP {} scores have been manually modified by the tabler.".format(gp))
                except:
                    pass
                self.manual_warnings[-1].append("GP {} scores have been manually modified by the tabler.".format(gp))
                    
                return "`{}` GP {} score changed to {}.".format(self.display_names[player], gp, self.edited_scores[player][int(gp)])
            else:
                self.edited_scores[player][int(gp)] = int(score)
                
                if not redo:
                    self.modifications.append([('?edit {} {} {}'.format(p_indx, gp, score), player, gp, score)])
                    self.undos.clear()
                
                try:
                    self.manual_warnings[-1].remove("GP {} scores have been manually modified by the tabler.".format(gp))
                except:
                    pass
                self.manual_warnings[-1].append("GP {} scores have been manually modified by the tabler.".format(gp))
                        
                ret+="`{}` GP {} score changed to {}.\n".format(self.display_names[player], gp, score)
        return ret
    
    def undo_edit(self, player, gp):
        self.edited_scores[player].pop(int(gp))
       
    def get_rxx(self):
        ret = ""
        if len(self.prev_rxxs)>0:
            ret+="Past rooms:\n"
            for n, r in enumerate(self.prev_rxxs):
                ret+="\t{}. {} | {}\n".format(n+1, r, self.ROOM_URL.format(r))
        ret+= 'Current room: {} | {}'.format(self.rxx, self.ROOM_URL.format(self.rxx))
        return ret
        
    def get_pen_player_list(self, c_form=True):
        counter = 1
        string =''
        self.tags = dict(sorted(self.tags.items(), key=lambda item: item[0].upper()))
        if isFFA(self.format):
            for p in list(self.players.keys()):
                self.player_ids[str(counter)] = p
                p2 = p
                if p in self.deleted_players: continue
                if p in self.sub_names: 
                    p2 = ''
                    for x,r in zip(self.sub_names[p]['sub_out'], self.sub_names[p]['out_races']):
                        p2 += '{}({})/'.format(x, r)
                    p2+='{}({})'.format(self.display_names[p], self.sub_names[p]['in_races'])
                else:
                    p2 = self.display_names[p2]
                string+="\n{}. {} {}".format('`{}`'.format(counter) if c_form else counter,Utils.dis_clean(p2), '' if self.pens.get(p)==None else '(-{})'.format(self.pens.get(p)))
                
                counter+=1
        else:
            for tag in self.tags.keys():
                if tag == "":
                     for p in self.tags[tag]:
                         self.player_ids[str(counter)] = p
                         string+="\n**NO TEAM**\n\t{}. {} {}".format('`{}`'.format(counter) if c_form else counter,Utils.dis_clean(self.display_names[p]), '' if self.pens.get(p)==None else '(-{})'.format(self.pens.get(p)))
                         
                         counter+=1
                else:   
                    string+='\n**Tag: {}**'.format(Utils.dis_clean(tag))
                    if tag in self.team_pens.keys(): 
                        string+=" **(-{})**".format(self.team_pens.get(tag))
                    for p in self.tags[tag]:
                        self.player_ids[str(counter)] = p
                        p2 = p
                        if p in self.deleted_players: continue
                        if p in self.sub_names: 
                            p2 = ''
                            for x,r in zip(self.sub_names[p]['sub_out'], self.sub_names[p]['out_races']):
                                p2 += '{}({})/'.format(x, r)
                            p2+='{}({})'.format(self.display_names[p], self.sub_names[p]['in_races'])
                        else:
                            p2 = self.display_names[p2]
                        string+="\n\t{}. {} {}".format('`{}`'.format(counter) if c_form else counter,Utils.dis_clean(p2), '' if self.pens.get(p)==None else '(-{})'.format(self.pens.get(p)))
                        
                        counter+=1
                    
        self.player_list = string
        return self.player_list
    
    def penalty(self,player, pen, reundo=False):
        if not reundo:
            try:
                p_indx = player
                player = self.player_ids[player]
            except:
                return "Invalid player number `{}`.".format(player)
        if pen[0] == '=':
            pen = int(pen.lstrip('=').lstrip('-'))
            self.pens[player] = pen
            if self.pens[player] == 0: self.pens.pop(player)
            
            if not reundo:
                self.modifications.append([('?pen {} {}'.format(p_indx, '='+str(pen)), player, '='+str(pen))])
                self.undos.clear()
                
            return "{} penalty set to -{}".format(self.display_names[player], pen)
        
        else:
            pen = int(pen.lstrip('-'))
            if player in self.pens:
                self.pens[player]+=pen
            else:
                self.pens[player] = pen
            if self.pens[player] == 0: self.pens.pop(player)
            
            if not reundo:
                self.modifications.append([('?pen {} {}'.format(p_indx, pen), player, pen)])
                self.undos.clear()
            return "-{} penalty given to {}".format(pen, self.display_names[player])
    
    def unpenalty(self, player, unpen, reundo=False):
        if unpen !=None:
            unpen = int(unpen.lstrip('='))
        if not reundo:
            try:
                p_indx = player
                player = self.player_ids[player]
            except:
                return "Invalid player number `{}`.".format(player)
        if player not in self.pens:
            return "`{}` doesn't have any penalties.".format(self.display_names[player])
        else:
            if unpen ==None:
                orig_pen = self.pens[player]
                self.pens.pop(player)
                if not reundo:
                    self.modifications.append([('?unpen {}'.format(p_indx), player, orig_pen)])
                    self.undos.clear()
                return "Penalties for `{}` have been removed.".format(self.display_names[player])
            else:
                self.pens[player] -= unpen
                if self.pens[player] == 0: self.pens.pop(player)
                
                if not reundo: 
                    self.modifications.append([('?unpen {} {}'.format(p_indx, unpen), player, unpen)])
                    self.undos.clear()
                return "Penalty for `{}` reduced by {}".format(self.display_names[player], unpen)
            
    def team_penalty(self, team, pen, reundo = False):
        if team.isnumeric():
            try:
                t_indx = int(team)-1
                team = list(self.tags.keys())[t_indx]
            except:
                return "Invalid team number `{}`.".format(team)
        try:
            assert(team in self.tags.keys())
        except:
            return "Invalid team name `{}`. Team names are case-sensitive.".format(team)
        if pen[0] == '=':
            pen = int(pen.lstrip('=').lstrip('-'))
            self.team_pens[team] = pen
            if self.team_pens[team] == 0: self.team_pens.pop(team)
            
            if not reundo:
                self.modifications.append([('?teampen {} {}'.format(team, '='+str(pen)), team, '='+str(pen))])
                self.undos.clear()
                
            return "Team `{}` penalty set to -{}.".format(team, pen)
        
        else:
            pen = int(pen.lstrip('-'))
            if team in self.team_pens:
                self.team_pens[team]+=pen
            else:
                self.team_pens[team] = pen
            if self.team_pens[team] == 0: self.team_pens.pop(team)
            
            if not reundo:
                self.modifications.append([('?teampen {} {}'.format(team, pen), team, pen)])
                self.undos.clear()
            return "-{} penalty given to team {}.".format(pen, team)
    
    def team_unpenalty(self, team, unpen, reundo=False):
        if unpen !=None:
            unpen = int(unpen.lstrip('='))
        if team.isnumeric():
            try:
                t_indx = int(team)-1
                team = list(self.tags.keys())[t_indx]
            except:
                return "Invalid team number `{}`.".format(team)
        try:
            assert(team in self.tags.keys())
        except:
            return "Invalid team name `{}`. Team names are case-sensitive.".format(team)
        if team not in self.team_pens:
            return "Team `{}` doesn't have any penalties.".format(team)
        else:
            if unpen ==None:
                orig_pen = self.team_pens[team]
                self.team_pens.pop(team)
                if not reundo:
                    self.modifications.append([('?teamunpen {}'.format(team), team, orig_pen)])
                    self.undos.clear()
                return "Penalties for team `{}` have been removed.".format(team)
            else:
                self.team_pens[team] -= unpen
                if self.team_pens[team] == 0: self.team_pens.pop(team)
                
                if not reundo: 
                    self.modifications.append([('?teamunpen {} {}'.format(team, unpen), team, unpen)])
                    self.undos.clear()
                return "Penalty for team {} reduced by {}.".format(team, unpen)

    def find_players(self,url, soup): 
       
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
            self.players[fc] = [0,[0]*self.gps, [0]*self.gps*4]
            if miiName in self.dup_names:
                x = 1
                name = miiName+'-'+str(x)
                while name in self.fcs:
                    x+=1
                    name = miiName+'-'+str(x)
                
                self.fcs[name] = fc
                self.display_names[fc] = name
            
            else:
                self.fcs[miiName] = fc
                self.display_names[fc] = miiName
        
        self.players = dict(sorted(self.players.items(), key=lambda item: item[0]))
        if isFFA(self.format): 
            self.all_players = list(copy.deepcopy(self.players).keys())
            print(self.players.keys())
        
    def check_name(self,name):
        if name not in self.display_names.values():
            return name
        x = 1
        new = name
        while new in self.display_names.values():
            new = name+'-'+str(x)
        return new
    
    def get_all_players(self): 
        ret = ''
        if isFFA(self.format):
            for i, p in enumerate(self.all_players):
                ret+="\n{}. {}".format(i+1, Utils.dis_clean(self.display_names[p]))
                if p in self.deleted_players:
                    ret+=' (removed by tabler)'
            return ret

        for tag, players in self.tags.items():
            if tag not in self.all_players:
                for t1 in self.all_players.items():
                    for p in players:
                        if p in t1[1]:
                            self.all_players[t1[0]].remove(p)
                self.all_players[tag] = players
                continue
            
            for p in players: 
                if p not in self.all_players[tag]:
                    self.all_players[tag].append(p)

        self.all_players = dict(sorted(self.all_players.items(), key=lambda item: unidecode(item[0].upper())))

        count = 0
        for tag in self.all_players.items():
            for p in tag[1]:
                count+=1
                ret+="\n{}. {}".format(count, Utils.dis_clean(self.display_names[p]))
                if p in self.deleted_players:
                    ret+=' (removed by tabler)'
        
        return ret
            
    def add_sub_player(self,player, fc):
        if fc in self.all_players: return 'failed'
        if isFFA(self.format): self.all_players.append(fc)
        self.players[fc] = [0,[0]*self.gps, [0]*self.gps*4]
        self.fcs[player] = fc
        self.display_names[fc] = player
        print(self.num_players)
        if len(self.players)-1<self.num_players:
            print("asd")
            for warn_item in enumerate(self.warnings[1]):
                if warn_item[1].get('type') == "missing":
                    #print(ind,i)
                    self.dc_list[1].append({'type': 'dc_before', 'race':1, 'player': fc, 'gp': 1})
                    self.warnings[1].append({'type': 'dc_before','race': 1, 'player': fc, 'gp': 1})
                    self.dc_ids_append(fc, 1)
                    if self.gp not in self.gp_dcs: self.gp_dcs[self.gp] = []
                    self.gp_dcs[self.gp].append(fc)
                    if len(self.players)==self.num_players:
                        self.warnings[1].pop(warn_item[0])
                    
                    if not isFFA(self.format): self.find_tag(player, fc)
                    return 'not sub'
        
        if not isFFA(self.format):
            if "SUBS" not in self.tags:
                self.tags['SUBS'] = []
            self.tags["SUBS"].append(fc)
        return 'success'
    
    def find_tag(self, player, fc):
        per_team = int(self.format[0])

        #if only one spot left to be filled
        if len(self.players)==self.num_players:
            for tag in self.tags.items():
                if len(tag[1])<per_team:
                    self.tags[tag[0]].append(fc)
                    self.all_players[tag[0]].append(fc)
                    return

        #prefix matching
        match = ["", 0]
        for tag in self.tags.keys():
            if player.find(tag)==0 and len(self.tags[tag]<per_team):
                if len(tag)>match[1]:
                    match = [tag, len(tag)]
        if match[1]>0:
            self.tags[match[0]].append(fc)
            self.all_players[match[0]].append(fc)
            return

        #suffix matching
        match = ["", 0]
        for tag in self.tags.keys():
            if player[::-1].find(tag[::-1])==0 and len(self.tags[tag]<per_team):
                if len(tag)>match[1]:
                    match = [tag, len(tag)]
        if match[1]>0:
            self.tags[match[0]].append(fc)
            self.all_players[match[0]].append(fc)
            return
        
        #common substring matching if 2v2
        if per_team==2:
            match = ["", 0]
            for tag in self.tags.keys():
                lcs = Utils.LCS(player, tag)
                if len(lcs)>1 and lcs==tag and len(self.tags[tag]<per_team):
                    if len(lcs)>match[1]:
                        match = [lcs, len(lcs)]
            if match[0]!="":   
                self.tags[match[0]].append(fc)
                self.all_players[match[0]].append(fc)
                return
        
        #no tags matched, so randomly fill
        for i in self.tags.items():
            if len(i[1])<per_team:
                self.tags[i[0]].append(fc)
                self.all_players[i[0]].append(fc)
                return

        #all tags were full, so create new tag
        self.tags[player[0]] = [fc]
        self.all_players[player[0]] = [fc]

    def sub_in(self, _in, out, out_races, reundo=False): 
        in_player, out_player = _in, out
        out_races = int(out_races)
        if not reundo:
            try:
                in_player = self.player_ids[_in]
            except:
                return "`{}` was not a valid player number. The player number must be from 1-{}.".format(_in, len(self.player_ids))
            try:
                out_player = self.player_ids[out]
            except:
                return "`{}` was not a valid player number. The player number must be from 1-{}.".format(out, len(self.player_ids))
        
        if out_player in self.sub_names:
            self.sub_names[in_player] = {'sub_out': self.sub_names[out_player]['sub_out']+[self.display_names[out_player]], 
                                         'in_races': self.gps*4-sum(self.sub_names[out_player]['out_races']+[out_races]), 
                                         "out_races": self.sub_names[out_player]['out_races']+[out_races]}
        else:
            self.sub_names[in_player] = {'sub_out': [self.display_names[out_player]], 'in_races': self.gps*4-out_races, "out_races": [out_races]}
            
        self.players[in_player][1] = [a+b for a, b in zip(self.players[in_player][1], self.players[out_player][1])]
        self.players[in_player][2] = [a+b for a, b in zip(self.players[in_player][2], self.players[out_player][2])]
        self.players[in_player][0] = self.players[out_player][0]+self.players[in_player][0]

        out_edited_scores = self.edited_scores.pop(out_player, None)
        in_edited_scores = self.edited_scores.get(in_player, None)
        for i in out_edited_scores.items():
            if i[0] in self.edited_scores[in_player]:
                self.edited_scores[in_player][i[0]] += i[1]
            else:
                self.edited_scores[in_player][i[0]] = i[1]
        

        out_pens = None
        if out_player in self.pens:
            self.pens[in_player] = out_pens = self.pens.pop(out_player) 
        
        pts=self.players.pop(out_player)
        out_player_name=self.display_names[out_player]
        self.fcs.pop(self.display_names[out_player])
        try:
            pid = self.player_ids.pop(list(self.player_ids.keys())[list(self.player_ids.values()).index(out_player)])
        except:
            pid = None
        tag = ""
        in_tag = ''
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
                except:
                    pass
                
            if tag!="" and in_player not in self.tags[tag]:
                self.tags[tag].append(in_player)
                self.all_players[tag].append(in_player)
       
            self.tags = {k:v for k,v in self.tags.items() if len(v)!=0}
            
        if not reundo: 
            restore = {'pts':pts, 'name': self.display_names.get(out_player), 'out_tag':tag, 'id':pid, 'in_tag': in_tag, 'out_edited_scores': out_edited_scores, 'in_edited_scores': in_edited_scores}
            if out_pens!=None:
                restore['pens'] = out_pens
            self.modifications.append([('?sub {} {} {}'.format(out, out_races, _in), in_player, out_player, out_races, restore)])
            self.undos.clear()
        return "Subbed in {} for {} (played {} races).".format(self.display_names[in_player], out_player_name, out_races)
    
    def undo_sub(self, in_player, out_player, restore):
        self.sub_names.pop(in_player)
        self.players[out_player] = restore['pts']
        self.fcs[restore['name']] = out_player
        self.display_names[out_player] = restore['name']

        if restore['in_edited_scores'] is not None and len(restore['in_edited_scores']) >0:
            self.edited_scores[in_player] = restore['in_edited_scores'] 
        else:
            try:
                self.edited_scores.pop(in_player)
            except:
                pass
        if restore['out_edited_scores'] is not None and len(restore['out_edited_scores']) >0:
            self.edited_scores[out_player] = restore['out_edited_scores'] 
        else:
            try:
                self.edited_scores.pop(out_player)
            except:
                pass

        if not isFFA(self.format):
            for tag in self.tags.items():
                try:
                    tag[1].remove(in_player)
                    self.all_players[tag[0]].remove(in_player)
                    try:
                        self.tags[restore['in_tag']].append(in_player)
                        self.all_players[restore['in_tag']].append(in_player)
                    except KeyError:
                        self.tags[restore['in_tag']] = [in_player]
                        self.all_players[restore['in_tag']] = [in_player]

                    break
                except:
                    pass
            try:
                self.tags[restore['out_tag']].append(out_player)
                self.all_players[restore['out_tag']].append(out_player)
            except KeyError:
                self.tags[restore['out_tag']] = [out_player]
                self.all_players[restore['out_tag']] = [out_player]
        
        
        self.players[in_player][1] = [a-b for a, b in zip(self.players[in_player][1], self.players[out_player][1])]
        self.players[in_player][2] = [a-b for a, b in zip(self.players[in_player][2], self.players[out_player][2])]
        self.players[in_player][0] = self.players[in_player][0] - self.players[out_player][0]

        if 'pens' in restore:
            self.pens[out_player] = restore['pens']
            self.pens[in_player] = self.pens[in_player]-restore['pens']
            if self.pens[in_player]==0:
                self.pens.pop(in_player)
        
        
    def edit_sub_races(self, indx, races, is_in, out_index = 1, reundo=False):
        player = indx
        if not reundo:    
            try:
                player = self.player_ids[str(indx)]
            except:
                return "Player number `{}` was invalid. The player number must be from 1-{}.".format(indx, len(self.player_ids))
        try:
            assert(player in self.sub_names)
        except:
            return "`{}` is not a subbed in player.".format(self.display_names[player])
        if is_in:
            orig_races = self.sub_names[player]['in_races']
            self.sub_names[player]['in_races'] = races
        else:
            try:
                orig_races = self.sub_names[player]['out_races'][out_index-1]
                self.sub_names[player]['out_races'][out_index-1] = races
            except:
                return "Sub out index `{}` was invalid. It must be from 1-{}.".format(out_index, len(self.sub_names[player]['out_races']))
            
        if not reundo: 
            self.modifications.append([("?editsub {} {} {} {}".format(indx, races, 'in' if is_in else 'out', out_index if not is_in else ""), player, races, orig_races, is_in, out_index)])
            self.undos.clear()

        return "Changed `{}` sub {}{} races to {}.".format(self.display_names[player], 'in' if is_in else 'out', '' if is_in else ' (`{}`)'.format(self.sub_names[player]['sub_out'][out_index-1]), races)
         
    def edit_dc_status(self,L, reundo=False): 
        ret=''
        for i in L:
            try:
                dc_num = i[0]
                player = self.dc_list_ids[int(i[0])][0]
                raceNum = self.dc_list_ids[int(i[0])][1]
            except:
                if len(self.dc_list_ids)==0:
                    ret+="DC number `{}` was invalid. There are no DCs to edit.\n".format(i[0])
                else: 
                    ret+="DC number `{}` was invalid. DC numbers must be from 1-{}.\n".format(i[0], len(self.dc_list_ids))
                continue
            
            status = i[1]
            players = [i[2] for i in self.races[raceNum-1]]
            if status == "on" or status == "during": #CHANGE TO 'ON'
                orig_status = 'on'
                if player not in players:
                    orig_status = "before"
                    self.change_room_size([[raceNum, len(self.races[raceNum-1])+1]], self_call=True)
                    self.races[raceNum-1].append((self.display_names[player], 'DC', player))
                    self.finish_times[raceNum-1][player] = 'DC'
                    gp = int((raceNum-1)/4)

                    if raceNum %4 != 1:
                        self.players[player][1][gp] -=3
                        self.players[player][2][raceNum-1] = 0
                        
                        for indx,i in enumerate(self.dc_pts[player]):
                            if i[0]==raceNum:
                                self.dc_pts[player][indx][1].pop(0)
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
                    self.change_room_size([[raceNum, len(self.races[raceNum-1])-1]], self_call=True)
                    #print(mes)
                    gp = int((raceNum-1)/4)
                    
                    if raceNum %4 != 1:
                        self.players[player][1][gp] +=3
                        self.players[player][2][raceNum-1] = 3
                        
                        for indx,i in enumerate(self.dc_pts[player]):
                            if i[0]==raceNum:
                                self.dc_pts[player][indx][1].insert(0, raceNum)
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
                                self.warnings[raceNum][indx] = {'type': "dc_before", 'race':1, 'gp':gp+1, 'is_edited':True}
                        for indx, i in enumerate(self.dc_list[raceNum]):
                            if i.get('player') == player and "on" in i.get('type'):
                                self.dc_list[raceNum][indx] = {'type':'dc_before', 'race':1, 'gp':gp+1, 'is_edited':True}

            if not reundo:
                self.modifications.append([('?dcs {} {}'.format(dc_num, status), dc_num, orig_status, status)]) 
                self.undos.clear()   

            ret+= "Changed {} DC status for race {} to '{}'.\n".format(Utils.dis_clean(self.display_names[player]), raceNum, status)
       
        return ret
                
                 
    def change_room_size(self, l, self_call = False, reundo=False, undo=False): 
        ret = ''
        for i in l:
            try:
                raceNum = int(i[0])-1
                assert(raceNum>=0)
                orig_room_size = len(self.races[raceNum]) 
                if raceNum+1 in self.changed_room_sizes and len(self.changed_room_sizes[raceNum+1])>0:
                    orig_room_size = self.changed_room_sizes[raceNum+1][-1]
                    
                gp = int(raceNum/4)
            except:
                ret+= "Invalid <race number>. The race number must be from 1-{}.\n".format(len(self.races))
                continue
            try:
                cor_room_size = int(i[1])
                assert(cor_room_size>0 and cor_room_size<=len(self.players) and (cor_room_size <=orig_room_size or self_call))
                
            except:
                
                if cor_room_size> orig_room_size and cor_room_size<=len(self.players):
                    ret+="**Note:** *If a race is missing player(s) due to DCs, it is advised to use `?dcs` instead.\nOnly use this command if no DCs were shown for the race in question.*\n\n"
                else:
                    ret+= "Invalid <corrected room size> for race `{}`. The corrected room size must be a number from 1-{}.\n".format(raceNum+1, len(self.players))
                    continue
            
            if cor_room_size == orig_room_size:
                ret+='Race {} room size is already {} - no change made.\n'.format(raceNum+1, cor_room_size)
                continue
            
            orig_pts = {}
            for place, p in enumerate(self.races[raceNum]):
                player = p[2]
                try:
                    pts = pts_map[orig_room_size][place]
                except KeyError:
                    pts = 0
                orig_pts[player] = pts
            
            fixed_pts = {}
            
            for place, p in enumerate(self.races[raceNum]):
                player = p[2]
                try:
                    pts = pts_map[cor_room_size][place]
                except KeyError:
                    pts = 0
                fixed_pts[player] = pts
                
            for player in list(fixed_pts.items()):
                self.players[player[0]][1][gp] += (player[1] - orig_pts[player[0]])
                self.players[player[0]][2][raceNum] = player[1]

            if not reundo:
                restore = (self.races[raceNum], self.finish_times[raceNum])
                self.races[raceNum] = self.races[raceNum][:cor_room_size]
                removal = list(self.finish_times[raceNum].keys())[:cor_room_size]
                self.finish_times[raceNum] = {k : self.finish_times[raceNum][k] for k in removal}
                
            if not self_call:
                done = False
                for indx,i in enumerate(self.manual_warnings[raceNum+1]):
                    if i.find("Room size changed to") == 0:
                        self.manual_warnings[raceNum+1][indx] = "Room size changed to {} by the tabler for this race.".format(cor_room_size)
                        done = True
                        break
                if not done:
                    self.manual_warnings[raceNum+1].append("Room size changed to {} by the tabler for this race.".format(cor_room_size))
                
        
            ret+='Changed race {} room size to {}.\n'.format(raceNum+1, cor_room_size)
            
            if not self_call and not undo:
                self.changed_room_sizes[raceNum+1].append(cor_room_size)
            if not reundo and not self_call:
                self.modifications.append([("?changeroomsize {} {}".format(raceNum+1, cor_room_size), raceNum+1, orig_room_size, cor_room_size, restore)])
                self.undos.clear()

        return ret
            
    def undo_crs(self, raceNum, orig_size, restore): 
        raceNum -=1

        self.races[raceNum] =  restore[0]
        self.finish_times[raceNum] = restore[1]
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
                    player = self.player_ids[player]
                except:
                    return "Player index `{}` was invalid. The player number must be from 1-{}.".format(player,len(self.players))
                
            correct_pos = int(elem[2])-1
            try:
                raceNum = int(raceNum)
                corresponding_rr = self.races[raceNum-1]
            except:
                return "Race number `{}` was invalid. It must be a number from 1-{}".format(raceNum, len(self.races))
            
            corresponding_rr = [i[2] for i in corresponding_rr]
            
            orig_pos = corresponding_rr.index(player)
            orig_pts = pts_map[len(corresponding_rr)][orig_pos]
            try:   
                cor_pts = pts_map[len(corresponding_rr)][int(correct_pos)]
            except:
                return "Corrected position `{}` was invalid. It must be a number from 1-{}.".format(correct_pos+1, len(corresponding_rr))
            
            if orig_pos<correct_pos:
                aff = [self.races[raceNum-1][i][2] for i in range(orig_pos+1,correct_pos+1)]
            else:
                aff = [self.races[raceNum-1][i][2] for i in range(correct_pos,orig_pos)]
                
            aff_orig_pts = {}
            for a in aff:
                aff_orig_pts[a] = pts_map[len(corresponding_rr)][corresponding_rr.index(a)]
            
            correct_ft_order = list(self.finish_times[raceNum-1].keys())
            correct_ft_order.insert(correct_pos, correct_ft_order.pop(orig_pos))
            self.finish_times[raceNum-1] = {k : self.finish_times[raceNum-1][k] for k in correct_ft_order}
            
            self.races[raceNum-1].insert(correct_pos, self.races[raceNum-1].pop(orig_pos))

            aff_new_pts = {}
            corresponding_rr = self.races[raceNum-1]
            corresponding_rr = [i[2] for i in corresponding_rr]
            
            for a in aff:
                aff_new_pts[a] = pts_map[len(corresponding_rr)][corresponding_rr.index(a)]
            
            gp = int((raceNum-1)/4)

            self.players[player][0] += (cor_pts-orig_pts)
            self.players[player][1][gp] += (cor_pts-orig_pts)
            self.players[player][2][raceNum-1] = cor_pts

            for a in aff:
                self.players[a][0]+= (aff_new_pts[a] - aff_orig_pts[a])
                self.players[a][1][gp] += (aff_new_pts[a] - aff_orig_pts[a])
                self.players[a][2][raceNum-1] = aff_new_pts[a]
            
            ret+='`{}` race {} placement changed to {}.{}'.format(Utils.dis_clean(self.display_names[player]), raceNum, correct_pos+1, '\n' if num==len(l)-1 else "")
            
            try:
                self.manual_warnings[raceNum].remove("Placements for this race have been manually altered by the tabler.")
            except:
                pass
            self.manual_warnings[raceNum].append("Placements for this race have been manually altered by the tabler.")
            
            mods.append(('?editrace {} {} {}'.format(raceNum, p_indx, correct_pos+1), player, raceNum, orig_pos+1, correct_pos+1))
     
        if not reundo and len(mods)>0:
            self.modifications.append(mods)
            self.undos.clear()
        return ret
    
    async def merge_room(self, arg, redo=False):
        is_rxx = False
        check = arg[0]
        if len(arg)==1 and (len(check)==8 and check[1:].isnumeric() and check[0]=='r') or (len(check)==4 and check[2:].isnumeric()):
            is_rxx = True
            
        if is_rxx:
            error, mes = await self.find_room(rid = arg, merge=True, redo=redo)
        else:
            error, mes= await self.find_room(mii=arg, merge=True, redo=redo)
        
        if redo:
            self.races = self.restore_merged[0]
            self.tracks = self.restore_merged[1]
            self.finish_times = self.restore_merged[2]
            self.warnings = self.restore_merged[3]
            self.dc_list = self.restore_merged[4]
            self.dc_list_ids = self.restore_merged[5]
            self.players = self.restore_merged[6]
            self.manual_warnings = self.restore_merged[7]
            self.restore_merged = None
        
        return error, mes

    def un_merge_room(self, merge_num): #TODO: update pts recalculation (maybe use update_table?)
        self.restore_merged = (self.races, self.tracks, self.finish_times, copy.deepcopy(self.warnings), copy.deepcopy(self.dc_list), self.dc_list_ids, copy.deepcopy(self.players), copy.deepcopy(self.manual_warnings))
        merge_indx = merge_num-1
        self.rxx = self.prev_rxxs[merge_indx]  
        self.races = self.races[:len(self.prev_elems[merge_indx])-len(self.removed_races)]
        self.tracks = self.tracks[:len(self.races)]
        self.current_elems = self.prev_elems[merge_indx]
        self.prev_elems = self.prev_elems[:merge_indx]
        self.prev_rxxs = self.prev_rxxs[:merge_indx]
        self.recorded_elems = self.prev_elems+self.current_elems
        self.current_url = self.ROOM_URL.format(self.rxx)
        
        self.finish_times = {k:v for k,v in self.finish_times.items() if k<len(self.races)}
        self.warnings = defaultdict(list,{k:v for k,v in self.warnings.items() if k<=len(self.races)})
        self.manual_warnings = defaultdict(list,{k:v for k,v in self.manual_warnings.items() if k<=len(self.races)})
        self.dc_list = defaultdict(list, {k:v for k, v in self.dc_list.items() if k<=len(self.races)})
        
        self.dc_list_ids = {k:v for k, v in self.dc_list_ids.items() if v[1]<=len(self.races)}
        
        for p in list(self.players.keys()):
            self.players[p] = [0,[0]*self.gps, [0]*self.gps*4]
        
        recorded_players = []
        for raceNum,race in enumerate(self.races):
            cur_room_size= len(race)
            gp = int(raceNum/4)
            for dc in list(self.dc_pts.items()):
                for j in dc[1]:
                    if raceNum+1 in j[1]:
                        self.players[dc[0]][1][self.gp]+=3
                        self.players[dc[0]][2][raceNum]=3
                        break
            for placement, player in enumerate(race):
                player = player[2]
                recorded_players.append(player)
                self.players[player][1][gp] += pts_map[cur_room_size][placement]
                self.players[player][2][raceNum] += pts_map[cur_room_size][placement]
                self.players[player][0] += pts_map[cur_room_size][placement]
        
        x = copy.deepcopy(self.players)
        for i in x.keys():
            if i not in recorded_players:
                self.players.pop(i)
                self.fcs.pop(self.display_names[i])
                self.display_names.pop(i)
                for tag in self.tags.items():
                    if i in tag[1]:
                        tag[1].remove(i)
                
    
    async def remove_race(self, raceNum, redo=False): 
        if raceNum==-1: raceNum = len(self.races)
        try:
            assert(raceNum<=len(self.races) and raceNum>0)
        except:
            return "`{}` was not a valid race number. The race number must be from 1-{}.".format(raceNum,len(self.races))
        
        track = self.tracks.pop(raceNum-1)
        self.removed_races[raceNum] = [self.races.pop(raceNum-1), track]
       
        try:
            rem_warn = self.warnings.pop(raceNum)
        except:
            rem_warn = None
        try:
            rem_dc_list = self.dc_list.pop(raceNum)
        except:
            rem_dc_list = None
            
        #self.removed_warn_dcs[raceNum] = {'warnings':rem_warn, 'dc_list':rem_dc_list, 'dc_list_ids': removed_dc_list_ids, 'dc_pts':removed_dc_pts}
        self.removed_warn_dcs[raceNum] = {'warnings':rem_warn, 'dc_list':rem_dc_list, 'm_warnings': self.manual_warnings.pop(raceNum) if raceNum in self.manual_warnings else None}

        self.shift_warnings(start=raceNum, direction='left')
        await self.recalc_table(start=raceNum)
        
        if not redo: 
            self.modifications.append([('?removerace {}'.format(raceNum), raceNum, track)])
            self.undos.clear()

        self.manual_warnings[-1].append("Race #{} (originally) - {} has been removed by the tabler.".format(raceNum, track))
            
        return "Removed race {} - {} from table.".format(raceNum, track)
    
    async def restore_removed_race(self, raceNum):
        restore_race, restore_track = self.removed_races.pop(raceNum)
        self.races.insert(raceNum-1, restore_race)
        self.tracks.insert(raceNum-1, restore_track)
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
        for player in self.players.items():
            for num,gp in enumerate(player[1][1]):
                if num>=self.gp:
                    self.players[player[0]][1][num] = 0
            for num, race in enumerate(player[1][2]):
                if int(num/4)>=self.gp:
                    self.players[player[0]][2][num] = 0
            pts = sum([race for race in self.players[player[0]][1]])
            self.players[player[0]][0] = pts

        reference_warnings = copy.deepcopy(self.warnings)
        
        self.warnings = defaultdict(list,{k:v for k,v in self.warnings.items() if k<self.gp*4+1})
        self.dc_list = defaultdict(list, {k:v for k, v in self.dc_list.items() if k<self.gp*4+1})
        #self.manual_warnings = defaultdict(list, {k:v for k, v in self.dc_list.items() if k<self.gp*4+1})
                
        self.finish_times = {k:v for k,v in self.finish_times.items() if k+1<(self.gp+1)*4-3}
        self.ties = {k:v for k,v in self.ties.items() if k<(self.gp+1)*4-3} 
        self.gp_dcs = {k:v for k,v in self.gp_dcs.items() if k<self.gp} 
        
        for player, dcs in self.dc_pts.items():
            for indx, dc in enumerate(dcs):
                if dc[0]>=(self.gp+1)*4-3:
                    self.dc_pts[player].pop(indx)
        self.dc_pts = {k:v for k, v in self.dc_pts.items() if len(v)>0}
        
        self.dc_list_ids = {k:v for k,v in self.dc_list_ids.items() if v[1]<(self.gp+1)*4-3} 
        
        self.room_sizes_error_affected = [i for indx, i in enumerate(self.room_players) if indx<self.gp]
        self.room_error_index = [i for indx, i in enumerate(self.room_error_index) if indx<self.gp]
        self.room_players = [i for indx, i in enumerate(self.room_players) if indx<self.gp]
        self.room_sizes = [i for indx, i in enumerate(self.room_sizes) if indx<self.gp]
        
        await self.update_table(recalc=True, reference_warnings = reference_warnings)
        
    
    def change_gps(self,gps): 
        for player in list(self.players.keys()):
            self.players[player][1]+=[0]*(gps-self.gps)
            self.players[player][2]+=[0]*(gps-self.gps)*4
        self.gps = gps
        if not self.check_mkwx_update.is_running():
            try:
                self.check_mkwx_update.start()
            except:
                pass
          
        
    async def check_updated(self):
        if self.last_race_update !=None and datetime.datetime.now() - self.last_race_update < datetime.timedelta(seconds=45): return False
        soup = await self.fetch(self.current_url)
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
        cur_iter = self.check_mkwx_update.current_loop
        if cur_iter!=0 and cur_iter%50==0:
            print("Mkwx check {}.".format(cur_iter))
            
        if await self.check_updated():
            self.bot.command_stats['picture_generated']+=1
            self.picture_running = True
            detect_mes = await self.ctx.send("Detected race finish.")
            wait_mes = await self.ctx.send("Updating scores...")
            mes = await self.update_table(auto=True)
            await wait_mes.edit(content=mes)
            pic_mes = await self.ctx.send("Fetching table picture...")
            img = await self.get_table_img()
            
            f=discord.File(fp=img, filename='table.png')
            em = discord.Embed(title=self.tag_str(), color=0x00ff6f)
            
            value_field = "[Edit this table on gb.hlorenzi.com]("+self.table_link+")"
            em.add_field(name='\u200b', value= value_field, inline=False)
            em.set_image(url='attachment://table.png')
            em.set_footer(text = self.get_warnings())
            
            await pic_mes.delete()
            await self.ctx.send(embed=em, file=f)
            await detect_mes.delete()

            self.picture_running=False
            
        if len(self.races)>=self.gps*4 or (self.last_race_update!=None and datetime.datetime.now()-self.last_race_update>datetime.timedelta(minutes=30)):
            self.check_mkwx_update.stop()
            

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
            new_tracks = []
            elems = soup.select('tr[id*=r]')
            new_elems = []
            for i in elems:
                race = []
                elem = i
                if elem in self.recorded_elems:
                    break
                new_elems.append(elem)
                    
                try:
                    track = elem.findAll('a')[-1].text
                    assert(elem.findAll('a')[2] == elem.findAll('a')[-1])
                    track = track[0:track.find('(')-1]
                except:
                    track = "Unknown Track"
                
                new_tracks.insert(0, track)
                next_elem = elem.findNext('tr').findNext('tr')
                
                while next_elem not in elems and next_elem !=None:
                    fin_time = next_elem.findAll('td', align='center')[-1].text
                    miiName = next_elem.find('td', class_='mii-font').text
                    if miiName == "no name": miiName = "Player"
                    fc = next_elem.select('span[title*=PID]')[0].text
                    tr = next_elem.find_all('td',{"align" : "center"})[4].text
                    tr = False if tr=="✓" else True
                    delta = next_elem.select('td[title*=delay]')[0].text
                    
                    race.append((miiName, fin_time, fc, tr, delta))
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
            
            self.tracks+=new_tracks
            if len(self.tracks)>self.gps*4:
                self.tracks = self.tracks[:self.gps*4]
            
            self.recorded_elems+=new_elems
            self.current_elems+=new_elems
            
            if len(self.recorded_elems)>self.gps*4:
                self.recorded_elems=self.recorded_elems[:self.gps*4]
       
        iter_races = new_races if not recalc else self.races[self.gp*4:]
        init_shift = 0 if not recalc else self.gp*4
        last_race_players = []
        for raceNum, race in enumerate(iter_races):
            raceNum+=init_shift
            
            if (shift+raceNum)%4 == 0: #new gp
                if (raceNum!=init_shift and recalc) or (not recalc and raceNum+shift+init_shift!=0):
                    self.gp+=1
                self.room_sizes.append(len(race))
                self.room_players.append([i[2] for i in race])
                self.room_sizes_error_affected.append([])
                self.room_error_index.append([-1,-1])
                if self.gp>=self.gps: 
                    for i in self.players.values():
                        i[1].append(0)
                        
            cur_room_size = len(race)
            cur_race_players = [i[2] for i in race]

            #repeat times check
            #t = timer.perf_counter()
            check_repeat_times = Utils.check_repeat_times(race, self.races+iter_races[:raceNum])
            #print("repeat time check:", timer.perf_counter()-t)
            if check_repeat_times[0]:
                self.warnings[shift+raceNum+1].append({'type': 'mkwx_bug_repeat', 'num_affected':check_repeat_times[1], 'gp': self.gp+1})

            #tr check
            tr_count = Counter([i[3] for i in race])[True]
            if tr_count>0:
                self.warnings[shift+raceNum+1].append({'type': "mkwx_bug_tr", 'aff_players': tr_count, 'gp': self.gp+1})
            
            #delay check
            delay_count = len([i[4] for i in race if i[4].replace('.','').isnumeric() and (float(i[4])>6.0 or float(i[4])<-1.0)])
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
                #TEST: test if player missing race one and comes back later gp
                self.warnings[shift+raceNum+1].append({'type': 'missing', 'cur_players': cur_room_size, 'sup_players': self.num_players, 'gp': self.gp+1})

            elif cur_room_size > self.num_players and (shift+raceNum)%4 == 0:
                self.warnings[shift+raceNum+1].append({'type': 'overflow', 'cur_players': cur_room_size, 'sup_players': self.num_players, 'gp': self.gp+1})
             
            elif cur_room_size<len(self.players):
                f_codes = [i[2] for i in race]
                total_missing_players = []
                missing_players = []
                for i in self.players:
                    total_missing_players.append(i)
                    if i not in f_codes and ((i in self.room_players[self.gp] and (shift+raceNum+1)%4!=1) or (i in self.room_players[self.gp-1] and (shift+raceNum+1)%4==1)): 
                        missing_players.append(i)
                        
                sub_outs = False
                if len(self.players)>self.num_players and len(total_missing_players)==len(self.players)-self.num_players:
                    sub_outs= True
                    
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
                                
                                try:
                                    self.dc_pts[mp].append([shift+raceNum+1, [i for i in range(shift+raceNum+1, shift+raceNum+1+(4-((shift+raceNum)%4))%4)]])
                                
                                except:
                                    self.dc_pts[mp] = [[shift+raceNum+1, [i for i in range(shift+raceNum+1, shift+raceNum+1+(4-((shift+raceNum)%4))%4)]]]
                                    
                                self.dc_ids_append(mp, shift+raceNum+1)
                                if self.gp not in self.gp_dcs: self.gp_dcs[self.gp] = []
                                self.gp_dcs[self.gp].append(mp)
            
            dc_count = 0
            for i, r in enumerate(race):
                if r[1] == '—':
                    dc_count +=1
                    race[i] = (r[0], 'DC', r[2])
            if dc_count == cur_room_size:
                self.warnings[shift+raceNum+1].append({"type": "mkwx_bug_blank", 'gp':self.gp+1})
                fin_times = {}
                for i in race:
                    fin_times[i[0]] = i[1]
                self.finish_times[shift+raceNum] = fin_times
                continue
            
            last_finish_times = {}
            
            for place,player in enumerate(race):
                time = player[1]
                fc = player[2]
                is_edited = find_if_edited(fc, shift+raceNum+1, reference_warnings)

                for dc in list(self.dc_pts.items()):    
                    for indx,j in enumerate(dc[1]):
                        if shift+raceNum+1 in j[1] and dc[0] == fc:
                            self.dc_pts[dc[0]].pop(indx)
                            continue
                
                #sub player
                if fc not in self.players and fc not in self.deleted_players:
                    status = self.add_sub_player(self.check_name(player[0]), fc)
                    if not isFFA(self.format) and status == 'success':
                        self.warnings[shift+raceNum+1].append({'type':'sub', 'player': fc})

                miiName = self.display_names[fc]
                
                self.players[fc][1][self.gp] += pts_map[cur_room_size][place]
                self.players[fc][2][shift+raceNum] = pts_map[cur_room_size][place]
                self.players[fc][0] += pts_map[cur_room_size][place]
                
                #check for ties
                if time != 'DC' and time in list(last_finish_times.values()):
                    for index,t in enumerate(list(last_finish_times.values())):
                        if t == time:
                            if shift+raceNum+1 not in self.ties:
                                self.ties[shift+raceNum+1] = {}
                            if time in self.ties[shift+raceNum+1]:
                                self.ties[shift+raceNum+1][time].append(list(last_finish_times.keys())[index])
                            else:
                                self.ties[shift+raceNum+1][time] = [list(last_finish_times.keys())[index]]
                    
                    self.ties[shift+raceNum+1][time].append(fc)
                
                if ":" in time and int(time[0:time.find(':')])>=5:
                    if self.sui:
                        if "Large finish times occurred, but are being ignored. Table could be inaccurate." not in self.warnings[-1]:
                            self.warnings[-1].append("Large finish times occurred, but are being ignored. Table could be inaccurate.")

                    else:
                        self.warnings[shift+raceNum+1].append({'type': 'large_time', 'player':fc, 'time':time})

                last_finish_times[fc] = time

                try:
                    assert(time!='DC')
                except AssertionError:
                    if self.gp not in self.gp_dcs or fc not in self.gp_dcs[self.gp]:
                        if (shift+raceNum)%4==0:
                            self.warnings[shift+raceNum+1].append({'type': 'dc_on', 'race':1, 'gp':self.gp+1, 'player':fc, "is_edited":is_edited})
                            self.dc_list[shift+raceNum+1].append({'type': 'dc_on', 'race':1, 'gp':self.gp+1, 'player':fc, "is_edited":is_edited})
                            
                        else: 
                            if (4-((shift+raceNum+1)%4))%4 == 0:
                                self.warnings[shift+raceNum+1].append({'type': "dc_on", 'race':-1, 'player':fc, 'gp':self.gp+1, "is_edited":is_edited})
                                self.dc_list[shift+raceNum+1].append({'type': "dc_on_unsure", 'race':-1, 'player':fc, 'gp':self.gp+1, "is_edited":is_edited})
                        
                            else:
                                self.warnings[shift+raceNum+1].append({'type': "dc_on", 'race':shift+raceNum+1, 'rem_races': (4-((shift+raceNum+1)%4))%4, 'pts':0, 'player':fc, 'gp':self.gp+1, "is_edited":is_edited})
                                self.dc_list[shift+raceNum+1].append({'type': "dc_on", 'race':shift+raceNum+1, 'rem_races': (4-((shift+raceNum+1)%4))%4, 'pts':0, 'player':fc, 'gp':self.gp+1, "is_edited":is_edited})
                            
                            try:
                                self.dc_pts[fc].append([shift+raceNum+1, [i for i in range(shift+raceNum+2, shift+raceNum+2+(4-((shift+raceNum+1)%4))%4)]])
                                
                            except:
                                self.dc_pts[fc] = [[shift+raceNum+1, [i for i in range(shift+raceNum+2, shift+raceNum+2+(4-((shift+raceNum+1)%4))%4)]]]
                        
                        self.dc_ids_append(fc, shift+raceNum+1)
                        if self.gp not in self.gp_dcs: self.gp_dcs[self.gp] = []
                        self.gp_dcs[self.gp].append(fc)
                    else:
                        self.warnings[shift+raceNum+1].append({'type': 'blank_time', 'player': fc})                            
                      
            for dc in list(self.dc_pts.items()):
                for j in dc[1]:
                    if shift+raceNum+1 in j[1]:
                        self.players[dc[0]][1][self.gp]+=3
                        for ind,w in enumerate(self.warnings[j[0]]):
                            if w.get('player') == dc[0]:
                                self.warnings[j[0]][ind]['pts']+=3
                                break
                        for ind, d in enumerate(self.dc_list[j[0]]):
                            if d.get('player') == dc[0]:
                                self.dc_list[j[0]][ind]['pts'] +=3
                                break
                            
                        self.players[dc[0]][2][raceNum]=3
                        break

            if shift+raceNum+1 in self.ties:
                for tie in list(self.ties[shift+raceNum+1].items()):     
                    self.warnings[shift+raceNum+1].append({'type':'tie', "time":tie[0], 'players':tie[1]}) 
            
            self.finish_times[shift+raceNum] = last_finish_times
            
            
        if not recalc: self.races+=new_races
        self.table_str = self.create_string()

        if prnt:
            print()
            print(self.table_str)

        if not recalc:   
            return "Table {}updated. Room {} has finished {} {}. Last race: {}.".format("auto-" if auto else "",rID, len(self.races), "race" if len(self.races)==1 else "races",self.tracks[len(self.races)-1])
                

    def create_string(self, by_race = False):
        self.tags = {k:v for k,v in self.tags.items() if len(v)>0}
        
        ret = "#title {} {}".format(len(self.races), "race" if len(self.races)==1 else 'races')
        if self.style:
            ret+="\n#style {}".format(self.style.get('table'))
        if self.graph:
            ret+="\n#graph {}".format(self.graph.get('table'))

        if isFFA(self.format):
            ret+='\nFFA'
            for p in self.players.keys():
                p2 = p
                if p in self.deleted_players: continue
                if p in self.sub_names: 
                    p2 = ''
                    for x,r in zip(self.sub_names[p]['sub_out'], self.sub_names[p]['out_races']):
                        p2 += '{}({})/'.format(x, r)
                    p2+='{}({})'.format(self.display_names[p], self.sub_names[p]['in_races'])
                else:
                    p2 = self.display_names[p2]
                ret+="\n{} ".format(p2)
                if by_race: 
                    scores = self.players[p][2]
                else:
                    scores = self.players[p][1]
                for num,gp in enumerate(scores):
                    if by_race:
                        if int(num/4)+1 in self.edited_scores[p]:
                            if num/4 +1 in self.edited_scores[p]:
                                ret+="{}".format(self.edited_scores[p][int(num/4)+1])
                            else:
                                ret+='0'
                            if num+1!=len(scores):
                                ret+='|'
                            continue
                    else:
                        if num+1 in self.edited_scores[p]:
                            ret+='{}'.format(self.edited_scores[p][num+1])
                            if num+1!=len(scores):
                                ret+='|'
                            continue

                    ret+="{}".format(gp)
                    if num+1!=len(scores):
                        ret+='|'
                if p in self.pens:
                    ret+='-{}'.format(self.pens[p])
                
        else:
            for tag in self.tags.keys():
                if tag == "":
                    for p in self.tags[tag]:
                        p2 = p
                        if p in self.deleted_players: continue
                        if p in self.sub_names: 
                            p2 = ''
                            for x,r in zip(self.sub_names[p]['sub_out'], self.sub_names[p]['out_races']):
                                p2 += '{}({})/'.format(x, r)
                            p2+='{}({})'.format(self.display_names[p], self.sub_names[p]['in_races'])
                        else:
                            p2 = self.display_names[p2]
                        ret+="\n\nNO TEAM\n{} ".format(p2)
                        if by_race: 
                            scores = self.players[p][2]
                        else:
                            scores = self.players[p][1]
                        for num,gp in enumerate(scores):
                            if by_race:
                                if int(num/4)+1 in self.edited_scores[p]:
                                    if num/4 +1 in self.edited_scores[p]:
                                        ret+="{}".format(self.edited_scores[p][int(num/4)+1])
                                    else:
                                        ret+='0'
                                    if num+1!=len(scores):
                                        ret+='|'
                                    continue        
                            else:
                                if num+1 in self.edited_scores[p]:
                                    ret+='{}'.format(self.edited_scores[p][num+1])
                                    if num+1!=len(scores):
                                        ret+='|'
                                    continue
                            
                            ret+="{}".format(gp)
                            if num+1!=len(scores):
                                ret+='|'
                        if p in self.pens:
                            ret+='-{}'.format(self.pens[p])
                    
                else:   
                    ret+='\n\n{}'.format(tag)
                    for p in self.tags[tag]:
                        p2 = p
                        if p in self.deleted_players: continue
                        if p in self.sub_names: 
                            p2 = ''
                            for x,r in zip(self.sub_names[p]['sub_out'], self.sub_names[p]['out_races']):
                                p2 += '{}({})/'.format(x, r)
                            p2+='{}({})'.format(self.display_names[p], self.sub_names[p]['in_races'])
                        else:
                            p2 = self.display_names[p2]
                        ret+="\n{} ".format(p2)
                        if by_race: 
                            scores = self.players[p][2]
                        else:
                            scores = self.players[p][1]
                        for num,gp in enumerate(scores):
                            if by_race:
                                if int(num/4)+1 in self.edited_scores[p]:
                                    if num/4 +1 in self.edited_scores[p]:
                                        ret+="{}".format(self.edited_scores[p][int(num/4)+1])
                                    else:
                                        ret+='0'
                                    if num+1!=len(scores):
                                        ret+='|'
                                    continue      
                            else:
                                if num+1 in self.edited_scores[p]:
                                    ret+='{}'.format(self.edited_scores[p][num+1])
                                    if num+1!=len(scores):
                                        ret+='|'
                                    continue
                                
                            ret+="{}".format(gp)
                            if num+1!=len(scores):
                                ret+='|'
                        if p in self.pens:
                            ret+='-{}'.format(self.pens[p])
                if tag in self.team_pens.keys():
                    ret+='\nPenalty -{}'.format(self.team_pens[tag])
                            
        return ret
    
    def get_table_text(self):
        self.table_str = self.create_string()
        return Utils.dis_clean(self.table_str)
    
    async def get_table_img(self, by_race = False):
        if by_race:
            temp_string = self.create_string(by_race=by_race)
            png_link = "https://gb.hlorenzi.com/table.png?data={}".format(quote(temp_string))
            
        else:
            png_link = "https://gb.hlorenzi.com/table.png?data={}".format(quote(self.table_str))
            
        self.table_link = png_link.replace('.png', "")
        with urlopen(png_link) as url:
            output = BytesIO(url.read())
        
        return output
    
    def get_modifications(self):
        ret = ''
        if len(self.modifications)==0:
            ret+="No table modifications to undo."
        for i,m in enumerate(self.modifications):
            ret+='{}. {}\n'.format(i+1, m[0][0])
        return ret
    
    def get_undos(self):
        ret = ''
        if len(self.undos)==0:
            ret+="No table modification undos to redo."
        
        for i,u in enumerate(self.undos):
            ret+="{}. {}\n".format(i+1, u[0][0])
        return ret
    
    def undo_warning(self,mod):
        mod_type = mod[0]
        
        if '?edit ' in mod_type:
            gp = int(mod[2])
            count = 0
            for x in self.modifications:
                for j in x:
                    if '?edit ' in j[0] and int(j[2])==gp:
                        count+=1
            if count==1: self.manual_warnings[-1].remove("GP {} scores have been manually modified by the tabler.".format(gp))
            
        elif '?editrace' in mod_type:
            raceNum = int(mod[2])
            count = 0
            for x in self.modifications:
                for j in x:
                    if '?editrace' in j[0] and int(j[2])==raceNum:
                        count+=1
            if count==1: 
                self.manual_warnings[raceNum].pop(self.manual_warnings[raceNum].index("Placements for this race have been manually altered by the tabler."))
                
        elif '?dcs' in mod_type:
            count = 0
            for x in self.modifications:
                for j in x:
                    if '?dcs' in j[0] and int(j[1])==int(mod[1]):
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
        elif "?removerace" in mod_type:
            raceNum= int(mod[1])
            track = mod[2]
            for indx,i in enumerate(self.manual_warnings[-1]):
                if 'Race #{}'.format(raceNum) in i and track in i and 'has been removed' in i:
                    self.manual_warnings[-1].pop(indx)
                    break
        
        else:
            raceNum= int(mod[1])
            count=0
            for x in self.modifications:
                for j in x:
                    if '?changeroomsize' in j[0] and int(j[1])==raceNum:
                        count+=1
            if count==1:
                for indx, i in enumerate(self.manual_warnings[raceNum]):
                    if i.find("Room size changed")==0:
                        self.manual_warnings[raceNum].pop(indx)
                        break
                    
        self.warnings = defaultdict(list,{k:v for k,v in self.warnings.items() if len(v)>0})
        self.manual_warnings = defaultdict(list,{k:v for k,v in self.manual_warnings.items() if len(v)>0})  
    
    async def undo(self, j):
        if '?edit ' in j[0]:
            self.undo_edit(j[1], j[2])
            self.undo_warning(j)
                
        elif '?editrace' in j[0]: 
            self.edit_race([[j[2], j[1], j[3]]], reundo=True)
            self.undo_warning(j)
        
        elif '?pen' in j[0]:
            self.unpenalty(j[1], str(j[2]), reundo=True)
        
        elif '?unpen' in j[0]:
            self.penalty(j[1], str(j[2]), reundo=True)
        
        elif '?teampen' in j[0]:
            self.team_unpenalty(j[1], str(j[2]), reundo=True)
        
        elif '?teamunpen' in j[0]:
            self.team_penalty(j[1], str(j[2]), reundo=True)
        
        elif '?dcs'in j[0]: 
            self.edit_dc_status([[j[1], j[2]]], reundo=True)
            self.undo_warning(j)
            
        elif '?changeroomsize' in j[0]:
            self.undo_crs(j[1], j[2], j[4])
            self.undo_warning(j)
        
        elif '?removerace' in j[0]:
            await self.restore_removed_race(j[1])
            self.undo_warning(j)
            
        elif '?sub' in j[0]:
            self.undo_sub(j[1], j[2], j[4])
            
        elif '?editsub' in j[0]:
            self.edit_sub_races(j[1], j[3], j[4], out_index=j[5], reundo=True)
        
        elif '?mergeroom' in j[0]:
            self.un_merge_room(j[1])
        
        elif '?edittag' in j[0]:
            self.edit_tag_name([[j[1], j[2]]], reundo=True)
        
        elif '?changetag' in j[0]:
            self.change_tag(j[1], j[3], restore_indx=j[4], reundo=True)

        elif '?tags ' in j[0]:
            self.undo_group_tags(j[1])
        
        elif '?changename ' in j[0]:
            self.undo_change_name(j[1], j[3],j[4])
        
        elif '?graph ' in j[0]:
            self.change_graph(j[1], reundo=True)
        
        elif '?style ' in j[0]:
            self.change_style(j[1], reundo=True)
        
        else:
            print("UNKNOWN UNDO TYPE:",j[0])
            raise AssertionError
    
    async def redo(self, j):
        if '?edit ' in j[0]:
            if "+" in j[0] or '-' in j[0]:
                self.edit(j[1], j[2], str(j[3]), redo=True)
            else:
                self.edit(j[1], j[2], str(j[4]), redo=True)
                
        elif 'editrace' in j[0]:
            self.edit_race([[j[2], j[1], j[4]]], reundo=True)
        
        elif '?pen' in j[0]:
            self.penalty(j[1], str(j[2]), reundo=True)
        
        elif '?unpen' in j[0]:
            self.unpenalty(j[1], str(j[2]), reundo=True)
            
        elif '?teampen' in j[0]:
            self.team_penalty(j[1], str(j[2]), reundo=True)
        
        elif '?teamunpen' in j[0]:
            self.team_unpenalty(j[1], str(j[2]), reundo=True)
        
        elif '?dcs'in j[0]:
            self.edit_dc_status([[j[1], j[3]]], reundo=True)
        
        elif '?changeroomsize' in j[0]:
            self.change_room_size([[j[1], j[3]]], reundo=True)
        
        elif '?removerace'==j[0]:
            await self.remove_race(j[1], redo=True)
            
        elif '?sub' in j[0]:
            self.sub_in(j[1], j[2], j[3], reundo=True)
    
        elif '?editsub' in j[0]:
            self.edit_sub_races(j[1], j[2], j[4], out_index=j[5], reundo=True)   
            
        elif '?mergeroom' in j[0]:
            await self.merge_room(j[2], redo=True)
        
        elif '?edittag' in j[0]:
            self.edit_tag_name([[j[2], j[1]]], reundo=True)
        
        elif '?changetag' in j[0]:
            self.change_tag(j[1], j[2], reundo=True)

        elif '?tags ' in j[0]:
            self.group_tags(j[2], redo=True)

        elif '?changename ' in j[0]:
            self.change_name([[j[1], j[2]]], redo=True)
        
        elif '?graph ' in j[0]:
            self.change_graph(j[2], reundo=True)
        
        elif '?style ' in j[0]:
            self.change_style(j[2], reundo=True)
        
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
                return "Last table modification ({}) has been undone.".format(mod[0][0])
            return "No manual modifications to the table to undo."
        
    async def redo_commands(self, num):
        if num == 0: #redo all
            if len(self.undos)>0:
                for i in list(reversed(self.undos)):
                    for j in i:
                        await self.redo(j)
                
                self.modifications = list(reversed(self.undos))
                self.undos = []
                return "All manual table modifications undos have been redone."
            return "No table modification undos to redo."
        
        else: #redo last undo
            if len(self.undos)>0:
                for i in self.undos[-1]:
                    await self.redo(i)
                    
                mod = self.undos[-1]
                self.modifications.append(mod)
                del self.undos[-1]
                return "Last table modification undo ({}) has been redone.".format(mod[0][0])
            return "No table modification undos to redo."
        
        
    async def fetch(self, url, headers=None): 
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession() as session:
            if headers == None:
                try:
                    async with session.get(url, timeout=timeout) as response:
                        if response.status!=200:
                            return 'response error'
                        resp = await response.text()
                        soup = BeautifulSoup(resp, 'html.parser')
                        return soup
                except:
                    return 'timeout error'

            else:
                async with session.get(url, headers=headers) as response:
                    return await response.text()
        
    
if __name__ == "__main__":
    import urllib3
    http = urllib3.PoolManager()
    page = http.request('GET', "www.wiimmfi.de/stats/mkwx/list/r3120806")
    soup = BeautifulSoup(page.data, "html.parser")
    
