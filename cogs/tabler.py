# -*- coding: utf-8 -*-
"""
Created on Tue May 18 15:05:35 2021

@author: ryanz
"""
from re import X
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
import time
from unidecode import unidecode
from collections import defaultdict
import Utils

#TODO: add graph and style options, and fix dc_list the way warnings has been updated
class Table():
    def __init__(self):
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

        self.dc_list = {} # race: list of player dcs (?dcs)
        self.tracks = [] #track list
        self.dup_players = [] #in case some players have same mii name. fc: edited mii name (ex. 'Player-1' instead of 'Player') for clarity purposes on table
        self.ties = {} #tied race times
        self.gp_dcs = {} #gp: list of players who have dced in gp (to ensure dc warnings are simplified in embed)
        self.dc_pts = {} #player: number of races to award +3 DC points 
        self.dc_list_ids = {} #mapping dcs to an id (used for the command ?dcs)
        
        self.removed_races = {}
        self.removed_warn_dcs = {}
        
        self.room_sizes = [] #list of room sizes for different gps (check if room size increases mid-gp, to send warning message - ?changeroomsize might be necessary)
        self.room_players = [] #list of list of players at beginning of GP (check if room changes mid-gp, send warning)
        self.room_sizes_error_affected = [[]] #races affected by mkwx messing up room sizes
        self.room_error_index = [[-1,-1]] #to update room size warnings
        
        self.changed_room_sizes = defaultdict(list) #races that have edited room sizes (?changeroomsize)
        self.edited_scores = defaultdict(lambda: defaultdict(int)) #players with edited gp scores
                   
        self.tags = {} #list of team tags and their respective players
        self.table_str = "" #argument for data (to get pic from gb.hlorenzi.com)
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
        
        self.pts= {12:{0:15, 1:12, 2:10, 3:8, 4:7, 5:6, 6:5, 7:4, 8:3, 9:2, 10:1, 11:0},
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
        self.ctx = None
        self.bot = None
        ##### Stuff for bot instances #####
        
    
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
                    return True, "The room ({}) hasn't finished at least one race yet.\nRetry the ?mergeroom command when the room has finished one race.".format(rxx)
                
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
                    return True, "The room ({}) hasn't finished at least one race yet.\nRetry the ?mergeroom command when the room has finished at least one race.".format(rid)
                
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
                #tick = time.time()
                data = await self.fetch(self.URL)
                if isinstance(data, str) and 'error' in data:
                    if 'response' in data:
                        return True, type_ask,"Wiimmfi appears to be down. Try again later."
                    else:
                        return True, type_ask,"I am currently experiencing some issues with Wiimmfi. Try again later."
                #print(time.time()-tick)
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
                    return True, type_ask, "{} {} not found in any rooms.\nMake sure all mii names are correct.".format(mii, "were" if len(mii)>1 else "was")
                if len(rxxs)>1:
                    if len(mii)==1:
                        return True, type_ask, "{} was found in multiple rooms: {}.\nTry again with a more refined search.".format(mii[0], list(rxxs.keys()))
                    rxx = [keys for keys,values in rxxs.items() if values == max(rxxs.values())]
                    if len(rxx)>1:
                        return True, type_ask, "{} {} found in multiple rooms: {}.\nTry again with a more refined search.".format(mii, "were" if len(mii)>1 else "was", rxx)
               
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
                    return True, type_ask, "The room hasn't finished at least one race yet.\nRetry the ?search command when the room has finished one race."
                else:
                    self.find_players(room_url, soup)
                    self.split_teams(self.format, self.teams)
                    type_ask = "confirm"
                    self.current_url = room_url
                    string = ""
                
                    counter = 1
                    if self.format[0] == 'f':
                        string+='\nFFA'
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
                    return False, type_ask, "Room {} found.\n{}\n\n**Is this correct?**\nEnter ?yes or ?no or ?changetag or ?tags.".format(self.rxx, string)     
                
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
                    return True, type_ask, "The room either doesn't exist or hasn't finished at least one race yet.\nRetry the ?search command when the room has finished one race and make sure the room id is in rxx or XX00 format."
                else:
                    self.find_players(room_url, soup)
                    #if len(self.players) != self.convert_format(self.format)*self.teams:
                            #return True, 'reset', "Room {} was found.\nHowever, the number of players in the room ({}) did not match the format and teams you provided in the ?start command.\nThe tabler has been reset, and you must redo the ?start command.".format(rid, len(self.players))
                    self.split_teams(self.format, self.teams)
                    type_ask = "confirm"
                    self.current_url = room_url
                    string = ""
                    
                    counter = 1
                    if self.format[0] == 'f':
                        #string+='\n-'
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
                    string = string.replace("no name", "Player")
                    self.player_list = string
                    return False, type_ask, "Room {} found.\n{}\n\n**Is this room correct?**\nEnter ?yes or ?no or ?changetag or ?tags.".format(self.rxx, string)
    
    
    def split_teams(self, f, num_teams): #TODO: unidecode doesn't work fully, need to find another method
        """
        split players into teams based on tags
        """
        tick=time.time()
        f = f[0]
        if not f.isnumeric():
            return
        per_team = int(f)
        teams = {} #tag: list of players
        player_copy = list(self.display_names.values())
        post_players = []
        un_players = []
        
        i = 0
        while i< len(player_copy):
            
            tag = ''
            matches = 1
            #most_matches = [1, '']
            indx = len(player_copy[i])+1

            while matches < per_team and indx>0:
                indx-=1
                matches = 1
                for j in range(len(player_copy)):
                    if i!=j and indx>0 and unidecode(Utils.strip_CJK(player_copy[i].strip().lower().replace("[","").replace(']','')))[:indx] == unidecode(Utils.strip_CJK(player_copy[j].strip().lower().replace("[","").replace(']','')))[:indx]:
                        matches+=1
                            
                        if matches == per_team: break 
                
            
            tag = player_copy[i].replace("[","").replace(']','')[:indx]
            if len(tag)>0 and tag[-1]=="-": 
                tag = tag[:-1]
                indx-=1
            if len(tag)==1: tag = tag.upper()
            
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
                if unidecode(tag.lower().replace("[","").replace(']','')) == unidecode(player_copy[ind].strip().lower().replace("[","").replace(']',''))[:indx]: 
                    if len(teams[temp_tag])<per_team:
                        teams[temp_tag].append(player_copy.pop(ind))
                        ind = 0
                        continue
                ind+=1
                
            i = 0
            
            
        #find postfix tags
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
                        if len(_list)<per_team and unidecode(Utils.strip_CJK(post_players[i].strip().lower().replace("[","").replace(']','')))[::-1][:indx][::-1] == unidecode(tag.lower().strip().replace("[","").replace(']','')):
                            teams[tag].append(post_players.pop(i))
                            i = 0
                            cont = True
                            break
                if cont:
                    continue


            #postfix and prefix (together) check
            temp_tag = ''
            tag_matches = defaultdict(list)
            temp_indx = len(post_players[i])+1
            
            while temp_indx>0:
                cont=False
                temp_indx-=1
               
                for j in range(len(post_players)):
                    i_tag = unidecode(Utils.strip_CJK(post_players[i].strip().replace("[","").replace(']','')))
                    j_tag = unidecode(Utils.strip_CJK(post_players[j].strip().replace("[","").replace(']','')))
                    
                    if i!=j and temp_indx>0 and (i_tag[:temp_indx] == j_tag[::-1][:temp_indx][::-1]
                                                 or i_tag[:temp_indx] == j_tag[:temp_indx]):
                        
                        #print(temp_indx, post_players[i], post_players[j])
                        if len(tag_matches[i_tag[:temp_indx]])==0:
                            tag_matches[i_tag[:temp_indx]].append(post_players[i])
                        tag_matches[i_tag[:temp_indx]].append(post_players[j])
                        if len(tag_matches[i_tag[:temp_indx]])==per_team:
                            teams[i_tag[:temp_indx]] = tag_matches.pop(i_tag[:temp_indx])
                            for p in teams[i_tag[:temp_indx]]:
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
                        if len(tag_matches[i_tag[::-1][:temp_indx][::-1]])==0:
                            tag_matches[i_tag[::-1][:temp_indx][::-1]].append(post_players[i])
                        tag_matches[i_tag[::-1][:temp_indx][::-1]].append(post_players[j])
                        if len(tag_matches[i_tag[::-1][:temp_indx][::-1]])==per_team:
                            teams[i_tag[::-1][:temp_indx][::-1]] = tag_matches.pop(i_tag[::-1][:temp_indx][::-1])
                            for p in teams[i_tag[::-1][:temp_indx][::-1]]:
                                try:
                                    post_players.remove(p)
                                except:
                                    pass
                                for x in all_tag_matches.items():
                                    try:
                                        all_tag_matches[1].remove(p)
                                    except:
                                        pass
                                i = 1
                            cont=True
                                
                            break
                                
                if cont:
                    break
               
            i+=1
            for item in tag_matches.items():
                if item[0] in all_tag_matches:
                    if len(item[1]) > len(all_tag_matches[item[0]]):
                        all_tag_matches[item[0]] = item[1]
                else:
                    all_tag_matches[item[0]] = item[1]
        
        teams_needed = num_teams-len(teams.keys())
        if(len(all_tag_matches)>=teams_needed):
            for t in range(teams_needed):
                all_tag_matches = dict(sorted(all_tag_matches.items(), key=lambda item: len(item[1]), reverse=True))
                teams[list(all_tag_matches.keys())[0]] = all_tag_matches[list(all_tag_matches.keys())[0]]
                for p in all_tag_matches[list(all_tag_matches.keys())[0]]:
                    post_players.remove(p)
                    for x in tag_matches.items():
                        try:
                            x[1].remove(p)
                        except:
                            pass
                        
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
                    m = Utils.LCS(unidecode(un_players[i].strip().lower().replace("[","").replace(']','')), unidecode(un_players[j].strip().lower().replace("[","").replace(']','')))
                    if un_players[i]!=un_players[j] and len(m)>longest_match:
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
                
        #randomly tag the rest
        if len(un_players)>0 and len(un_players) <per_team and len(teams)==num_teams:
            for item in teams.items():
                while len(item[1])<per_team and len(un_players)>0:
                    item[1].append(un_players.pop(0))
        else:
            split = list(Utils.chunks(un_players, per_team))
            for i in split:
                for ind,j in enumerate(i):
                    try:
                        teams[Utils.replace_brackets(j)[0]] = i
                        break
                    
                    except:
                        if ind+1==len(i):
                            teams[j[0][0]] = i
                        else:
                            continue
        
        print(teams)
        for i in teams.items():
            teams[i[0]] = [self.fcs[j] for j in i[1]]  
        self.tags = teams
        self.tags = dict(sorted(self.tags.items(), key=lambda item: unidecode(item[0].lower())))
        self.tags = {k.strip(): v for (k, v) in self.tags.items()}
        print()
        print(self.tags)
        print("tag algo time:",time.time()-tick)

    def warn_to_str(self, warning):                
        warning_map = {
            "dc_on": "{} DCed during the race (on results). Awarding 3 DC points per race for next {} races in GP {} ({} pts total).",
            ("dc_on", 1): "{} DCed during the first race of GP {} (on results). 15 DC points for GP {}.",
            ("dc_on", -1): "{} DCed during the race (on results). No DC points for GP {}.", 

            "dc_before": "{} DCed before race. 3 DC points per race for the next {} races in GP {} ({} pts total).", 
            ("dc_before", 1): "{} is missing from GP {}. 18 DC points for GP {} (mogi), 15 DC points for GP {} (war).", 

            "missing": "GP {} is missing player(s). GP started with {} players, but should've started with {} players.",

            "blank_time": "{} had a blank race time and was on results. If this wasn't a DC, this is an MKWX BUG. Run ?changeroomsize to fix this.",

            "tie": "{} had tied race times ({}). Check ?rr for errors.", 

            "mkwx_bug_increase": "Room size increased mid-GP from {} to {}. This is impossible unless if there was a reset or mid-GP sub(s), and likely an MKWX BUG. Affected races: {}. Run ?changeroomsize to fix this.", 
            "mkwx_bug_change": "Players in the room changed mid-GP (race {}). Unless if there were mid-GP sub(s) this race or a reset, this is an MKWX BUG. Table could be inaccurate for this GP ({}).", 
            "mkwx_bug_blank": "All players in the race had blank race times. This is an MKWX BUG if there was no room reset. Table is inaccurate for this GP ({}).", 

            "sub": "{}  -  Potential sub detected. If this player is a sub, use ?sub.", 

            "large_time": "{} had a large finish time - {}. Check ?rr for errors."
        }
        warning_type = warning.get('type')

        if "dc_" in warning_type:
            ret = ''
            is_edited = warning.get('is_edited', False)

            if "on" in warning_type:
                race = warning.get('race')
                if race == 1:
                    ret = warning_map.get((warning_type, race)).format(self.display_names[warning.get('player')], warning.get('gp'), warning.get('gp')) 
                elif race == -1:
                    ret = warning_map.get((warning_type, race)).format(self.display_names[warning.get('player')], warning.get('gp'))
                else:
                    ret = warning_map.get(warning_type).format(self.display_names[warning.get('player')], warning.get('rem_races'), warning.get('gp'), warning.get('pts'))
            
            else:
                race = warning.get('race')
                if race == 1:
                    ret = warning_map.get((warning_type,race)).format(self.display_names[warning.get('player')], warning.get('gp'), warning.get('gp'))
                else:
                    ret = warning_map.get(warning_type).format(self.display_names[warning.get('player')], warning.get('rem_races'), warning.get('gp'), warning.get('pts'))
        
            return ret + '{}'.format(" - determined by tabler" if is_edited else "")

        elif "mkwx_bug" in warning_type:
            if "_increase" in warning_type:
                return warning_map.get(warning_type).format(warning.get('orig_players'), warning.get('new_players'), warning.get('races'))

            elif "_change" in warning_type:
                return warning_map.get(warning_type).format(warning.get('race'), warning.get('gp'))

            else:
                return warning_map.get(warning_type).format(warning.get('gp'))

        elif warning_type == "missing":
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


    #TODO: rewrite with new warnings update
    def get_warnings(self):
        #merge self.warnings with self.manual_warnings
        warnings = self.warnings | dict(self.manual_warnings)

        if len(warnings)==0:
            return "No warnings or room errors. Table should be accurate."
        warnings = dict(sorted(warnings.items(), key=lambda item: item[0]))

        ret = 'Room warnings/errors that could affect the table{}:\n'.format(" (?dcs to fix dcs)" if len(self.dc_list)>0 else "")
        
        for i in warnings.items():
            if i[0]==-1:
                for warning in i[1]:
                    ret+='     - {}\n'.format(warning)
                continue
            ret+="     Race #{}: {}\n".format(i[0], self.tracks[i[0]-1])
            for warning in i[1]:
                ret+="       \t- {}\n".format(self.warn_to_str(warning) if isinstance(warning, dict) else warning)
                
        if len(ret)>2048: #potentially look to implement system for overflowing warnings (either page or separate message/command)
            ret = ret[:2048]
        
        return ret
    
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
    #TEST: test if undoing and redoing tag modifications works
    def edit_tag_name(self, l, reundo=False):  
        ret = ''
        for num,e in enumerate(l):
            orig = t_orig = e[0]
            new = e[1]
            if orig.isnumeric():
                try:
                    orig = list(self.tags.keys())[int(orig)-1]
                except:
                    return "'{}' out of range. Number must be between 1-{}".format(orig, len(self.tags))
                data = self.tags.pop(orig)
                self.tags[new]= data
                ret+= "Edited tag '{}' to '{}'.{}".format(orig, new, '\n' if len(l)>1 and num <len(l)-1 else "")
                
            else:
                try:
                    data = self.tags.pop(orig)
                except:
                    string = "Tag '{}' not a valid tag. Tags are case-sensitive.\nThe original tag must be one of the following:\n".format(orig)
                    for i in list(self.tags.keys()):
                        string+='**   - {}**\n'.format(i)
                    return string
                self.tags[new] = data
                ret+= "Edited tag '{}' to '{}'.{}".format(orig, new, '\n' if len(l)>1 and num <len(l)-1 else "")
                
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
                return True, "Race {} doesn't exist. The race number should be from 1-{}.".format(race, len(self.races))
            x = self.finish_times[race-1]
       
        count = 0
        ret+="Race #{} - {} results:\n".format(race, self.tracks[race-1])
        for i in list(x.items()):
            count+=1
            ret+="   {}. {} - {}\n".format(count, Utils.dis_clean(self.display_names[i[0]]), i[1])
            if self.format[0]!='f':
                for t in self.tags.items():
                    if i[0] in t[1]:
                        tag_places[t[0]].append(count)
            
        tag_places = dict(sorted(tag_places.items(), key=lambda item: sum([self.pts[count][i-1] for i in item[1]]), reverse=True))

        if self.format[0]!='f':
            ret+="\n"
            for tag, placements in tag_places.items():
                ret+="{} -".format(tag)
                for p in placements:
                    ret+=' {}{}'.format(p, '' if p==placements[-1] else ',')
                ret+=" ({} pts)".format(sum([self.pts[count][i-1] for i in placements]))
                ret+="{}".format("" if tag==list(tag_places.items())[-1][0] else "   |   ")
        return False,ret
    
    def change_tag(self,player, tag, restore_indx = None,reundo=False):
        if not reundo:
            p_indx=player
            try:
                player = self.player_ids[player]
            except:
                return "Player id: {} not valid. It must be from {}-{}".format(player, 0,len(self.players))
        old_tag = ""
        for i in self.tags.items():
            if player in i[1]:
                old_tag = i[0]
                old_indx = i[1].index(player)
                i[1].remove(player)
        if tag not in self.tags:
            self.tags[tag] = [player]
        else:
            if reundo and restore_indx is not None:
                self.tags[tag].insert(restore_indx, player)
            else:
                self.tags[tag].append(player)
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
                        i[1].append(leftovers[0])
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
            ret+="{} name changed to {}{}.\n".format(old_name, new_name, " (removed from table)" if should_del else "")
        
        return ret

    def undo_change_name(self, player, restore_name, was_deleted):
        if was_deleted:
            self.deleted_players.remove(player)
        else:
            self.display_names[player] = restore_name
        return

    def get_player_list(self):
        counter = 1
        string =''
        self.tags = dict(sorted(self.tags.items(), key=lambda item: unidecode(item[0].upper())))
        if self.format[0].lower() == 'f':
            for p in list(self.players.keys()):
                string+="\n{}. {}".format(counter,Utils.dis_clean(self.display_names[p]))
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
                         string+="\n**NO TEAM**\n\t{}. {} ".format(counter,Utils.dis_clean(p2))
                         
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
                        string+="\n\t{}. {}".format(counter,Utils.dis_clean(p2))
                        
                        counter+=1
        #string = string.replace("no name", "Player")
        self.player_list = string
        return self.player_list
        
    def dc_list_str(self): 
        ret = "DCs in the room:\n"
        dc_count = 1
        for race in list(self.dc_list.items()):
            ret+='Race #{}: {}\n'.format(race[0], self.tracks[int(race[0]-1)])
            for mes in race[1]:
                ret+='\t- **{}. {}\n'.format(dc_count,mes)
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
                    ret+="{} was not a valid player index. The index must be between 1-{}.\n".format(player, len(self.players))
                    continue
        
            try:
                assert(int(gp)-1 <=self.gp)
            except:
                ret+="{} was not a valid gp (player number {}). The gp number must be between 1-{}.\n".format(p_indx,gp, self.gp+1)
                continue
            
        
            if '-' in score or '+' in score:
                self.edited_scores[int(gp)][player] = self.players[player][1][int(gp)-1] + int(score)
                
                if not redo:
                    self.modifications.append([('?edit {} {} {}'.format(p_indx, gp, score), player, gp, score)])
                    self.undos.clear()
                
                
                if "Scores have been manually modified by the tabler for this GP ({}).".format(gp) not in self.manual_warnings[int(gp)*4-3]:
                    self.manual_warnings[int(gp)*4-3].insert(0, "Scores have been manually modified by the tabler for this GP ({}).".format(gp))
                    
                return "{} GP {} score changed to {}".format(self.display_names[player], gp, self.players[player][1][int(gp)-1])
            else:
                #orig_score = self.players[player][1][int(gp)-1]
                self.edited_scores[int(gp)][player] = int(score)
                
                if not redo:
                    self.modifications.append([('?edit {} {} {}'.format(p_indx, gp, score), player, gp, score)])
                    self.undos.clear()
                
                if "Scores have been manually modified by the tabler for this GP ({}).".format(gp) not in self.manual_warnings[int(gp)*4-3]:
                    self.manual_warnings[int(gp)*4-3].insert(0, "Scores have been manually modified by the tabler for this GP ({}).".format(gp))
                        
                ret+="{} GP {} score changed to {}.\n".format(self.display_names[player], gp, score)
        return ret
    
    def undo_edit(self, player, gp):
        self.edited_scores[int(gp)].pop(player)
       
    def get_rxx(self):
        ret = ""
        if len(self.prev_rxxs)>0:
            ret+="Past rooms:\n"
            for n, r in enumerate(self.prev_rxxs):
                ret+="\t{}. {} - {}\n".format(n+1, r, self.ROOM_URL.format(r))
        ret+= 'Current room: {} - {}'.format(self.rxx, self.ROOM_URL.format(self.rxx))
        return ret
        
    def get_pen_player_list(self):
        counter = 1
        string =''
        self.tags = dict(sorted(self.tags.items(), key=lambda item: item[0].upper()))
        if self.format[0].lower() == 'f':
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
                string+="\n{}. {} {}".format(counter,Utils.dis_clean(p2), '' if self.pens.get(p)==None else '(-{})'.format(self.pens.get(p)))
                
                counter+=1
        else:
            for tag in self.tags.keys():
                if tag == "":
                     for p in self.tags[tag]:
                         self.player_ids[str(counter)] = p
                         string+="\n**NO TEAM**\n\t{}. {} {}".format(counter,Utils.dis_clean(self.display_names[p]), '' if self.pens.get(p)==None else '(-{})'.format(self.pens.get(p)))
                         
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
                        string+="\n\t{}. {} {}".format(counter,Utils.dis_clean(p2), '' if self.pens.get(p)==None else '(-{})'.format(self.pens.get(p)))
                        
                        counter+=1
                    
        #string = string.replace("no name", "Player")
        self.player_list = string
        return self.player_list
    
    def penalty(self,player, pen, reundo=False):
        if not reundo:
            try:
                p_indx = player
                player = self.player_ids[player]
            except:
                return "Invalid player number {}.".format(player)
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
                return "Invalid player number {}.".format(player)
        if player not in self.pens:
            return "{} doesn't have any penalties.".format(self.display_names[player])
        else:
            if unpen ==None:
                orig_pen = self.pens[player]
                self.pens.pop(player)
                if not reundo:
                    self.modifications.append([('?unpen {}'.format(p_indx), player, orig_pen)])
                    self.undos.clear()
                return "Penalties for {} have been removed.".format(self.display_names[player])
            else:
                self.pens[player] -= unpen
                if self.pens[player] == 0: self.pens.pop(player)
                
                if not reundo: 
                    self.modifications.append([('?unpen {} {}'.format(p_indx, unpen), player, unpen)])
                    self.undos.clear()
                return "Penalty for {} reduced by {}".format(self.display_names[player], unpen)
            
    def team_penalty(self, team, pen, reundo = False):
        if team.isnumeric():
            try:
                t_indx = int(team)-1
                team = list(self.tags.keys())[t_indx]
            except:
                return "Invalid team number {}.".format(team)
        try:
            assert(team in self.tags.keys())
        except:
            return "Invalid team name '{}'. Team names are case-sensitive.".format(team)
        if pen[0] == '=':
            pen = int(pen.lstrip('=').lstrip('-'))
            self.team_pens[team] = pen
            if self.team_pens[team] == 0: self.team_pens.pop(team)
            
            if not reundo:
                self.modifications.append([('?teampen {} {}'.format(team, '='+str(pen)), team, '='+str(pen))])
                self.undos.clear()
                
            return "Team {} penalty set to -{}.".format(team, pen)
        
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
                return "Invalid team number {}.".format(team)
        try:
            assert(team in self.tags.keys())
        except:
            return "Invalid team name '{}'. Team names are case-sensitive.".format(team)
        if team not in self.team_pens:
            return "Team {} doesn't have any penalties.".format(team)
        else:
            if unpen ==None:
                orig_pen = self.team_pens[team]
                self.team_pens.pop(team)
                if not reundo:
                    self.modifications.append([('?teamunpen {}'.format(team), team, orig_pen)])
                    self.undos.clear()
                return "Penalties for team {} have been removed.".format(team)
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
        
        self.room_sizes.append(len(self.players))
        self.room_players.append(list(self.players.keys()))
        self.all_players = list(self.players.keys())
        self.players = dict(sorted(self.players.items(), key=lambda item: item[0]))
        if self.format[0].lower() == 'f': print(self.players.keys())
        
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
        
        self.all_players.sort(key=lambda x: unidecode(self.display_names[x].lower()))
        for i,p in enumerate(self.all_players):
            ret+="\n{}. {}".format(i+1, Utils.dis_clean(self.display_names[p]))
            if p in self.deleted_players:
                ret+=' (removed by tabler)'
        
        return ret
            
    def add_sub_player(self,player, fc):
        if fc in self.all_players: return 'failed'
        self.all_players.append(fc)
        self.players[fc] = [0,[0]*self.gps, [0]*self.gps*4]
        self.fcs[player] = fc
        self.display_names[fc] = player

        if len(self.players)-1<self.num_players:
            for dc_item, warn_item in zip(enumerate(self.dc_list[1]), enumerate(self.warnings[1])):
                if "should've started with" in dc_item[1]:
                    #print(ind,i)
                    self.dc_list[1].append("{}** missing from GP 1. 18 DC pts for GP (mogi) or 15 pts (war).".format(Utils.dis_clean(self.display_names[fc])))
                    self.warnings[1].append({'type': 'dc_before','race': 1, 'player': fc})
                    self.dc_ids_append(fc, 1)
                    if self.gp not in self.gp_dcs: self.gp_dcs[self.gp] = []
                    self.gp_dcs[self.gp].append(fc)
                    if len(self.players)==self.num_players:
                        self.dc_list[1].pop(dc_item[0])
                        self.warnings[1].pop(warn_item[0])
                    
                    self.find_tag(player, fc)
                    return 'success'
        
        if self.format[0].lower()!='f':
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
                    return

        #prefix matching
        match = ["", 0]
        for tag in self.tags.keys():
            if player.find(tag)==0 and len(self.tags[tag]<per_team):
                if len(tag)>match[1]:
                    match = [tag, len(tag)]
        if match[1]>0:
            self.tags[match[0]].append(fc)
            return

        #suffix matching
        match = ["", 0]
        for tag in self.tags.keys():
            if player[::-1].find(tag[::-1])==0 and len(self.tags[tag]<per_team):
                if len(tag)>match[1]:
                    match = [tag, len(tag)]
        if match[1]>0:
            self.tags[match[0]].append(fc)
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
                return
        
        #no tags matched, so randomly fill
        for i in self.tags.items():
            if len(i[1])<per_team:
                self.tags[i[0]].append(fc)
                return

        #all tags were full, so create new tag
        self.tags[player[0]] = [fc]

    def sub_in(self, _in, out, out_races, reundo=False): 
        in_player, out_player = _in, out
        out_races = int(out_races)
        if not reundo:
            try:
                in_player = self.player_ids[_in]
            except:
                return "{} was not a valid player number. The player number must be between 1-{}.".format(_in, len(self.player_ids))
            try:
                out_player = self.player_ids[out]
            except:
                return "{} was not a valid player number. The player number must be between 1-{}.".format(out, len(self.player_ids))
        
        if out_player in self.sub_names:
            self.sub_names[in_player] = {'sub_out': self.sub_names[out_player]['sub_out']+[self.display_names[out_player]], 
                                         'in_races': self.gps*4-sum(self.sub_names[out_player]['out_races']+[out_races]), 
                                         "out_races": self.sub_names[out_player]['out_races']+[out_races]}
        else:
            self.sub_names[in_player] = {'sub_out': [self.display_names[out_player]], 'in_races': self.gps*4-out_races, "out_races": [out_races]}
            
        self.players[in_player][1] = [a+b for a, b in zip(self.players[in_player][1], self.players[out_player][1])]
        self.players[in_player][2] = [a+b for a, b in zip(self.players[in_player][2], self.players[out_player][2])]
        self.players[in_player][0] = self.players[out_player][0]+self.players[in_player][0]
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
            
        if in_player not in self.tags[tag]:
            self.tags[tag].append(in_player)
       
        self.tags = {k:v for k,v in self.tags.items() if len(v)!=0}
            
        if not reundo: 
            restore = {'pts':pts, 'name': self.display_names.pop(out_player), 'out_tag':tag, 'id':pid, 'in_tag': in_tag}
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
        for tag in self.tags.items():
            try:
                tag[1].remove(in_player)
                try:
                    self.tags[restore['in_tag']].append(in_player)
                except KeyError:
                    self.tags[restore['in_tag']] = [in_player]
                break
            except:
                pass
        try:
            self.tags[restore['out_tag']].append(out_player)
        except KeyError:
            self.tags[restore['out_tag']] = [out_player]
        
        
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
                return "Player number {} was invalid. The player number must be between 1-{}.".format(indx, len(self.player_ids))
        try:
            assert(player in self.sub_names)
        except:
            return "{} is not a subbed in player.".format(self.display_names[player])
        if is_in:
            orig_races = self.sub_names[player]['in_races']
            self.sub_names[player]['in_races'] = races
        else:
            try:
                orig_races = self.sub_names[player]['out_races'][out_index-1]
                self.sub_names[player]['out_races'][out_index-1] = races
            except:
                return "Sub out index {} was invalid. It must be between 1-{}.".format(out_index, len(self.sub_names[player]['out_races']))
            
        if not reundo: 
            self.modifications.append([("?editsub {} {} {} {}".format(indx, races, 'in' if is_in else 'out', out_index if not is_in else ""), player, races, orig_races, is_in, out_index)])
            self.undos.clear()
        return "Changed {} sub {}{} races to {}.".format(self.display_names[player], 'in' if is_in else 'out', '' if is_in else ' ({})'.format(self.sub_names[player]['sub_out'][out_index-1]), races)
         
    def edit_dc_status(self,L, reundo=False): 
        mods = []
        ret=''
        for i in L:
            try:
                dc_num = i[0]
                player = self.dc_list_ids[int(i[0])][0]
                raceNum = self.dc_list_ids[int(i[0])][1]
            except:
                if len(self.dc_list_ids)==0:
                    ret+="DC number {} was invalid. There are no DCs to edit.\n".format(i[0])
                else: 
                    ret+="DC number {} was invalid. DC numbers must be between 1-{}.\n".format(i[0], len(self.dc_list_ids))
                continue
            
            status = i[1]
            players = [i[2] for i in self.races[raceNum-1]]
            if status == "on" or status == "during":
                orig_status = 'on'
                if player not in players:
                    orig_status = "before"
                    self.change_room_size([[raceNum, len(self.races[raceNum-1])+1]], self_call=True)
                    self.races[raceNum-1].append((self.display_names[player], 'DC', player))
                    self.finish_times[raceNum-1][player] = 'DC'
                    
                    if raceNum %4 != 1:
                        gp = int((raceNum-1)/4)
                        self.players[player][1][gp] -=3
                        self.players[player][2][raceNum-1] = 0
                        
                        for indx,i in enumerate(self.dc_pts[player]):
                            if i[0]==raceNum:
                                self.dc_pts[player][indx][1].pop(0)
                                break
                            
                        for indx,i in enumerate(self.warnings[raceNum]):
                            if i.get('player') == player and "before" in i.get('type'):
                                if (4-(raceNum%4))%4 == 0:
                                    self.warnings[raceNum][indx] = {'type': 'dc_on', 'race': -1, 'player': player, 'is_edited':True}
                                else: 
                                    self.warnings[raceNum][indx] = {'type':"dc_on", 'race': raceNum, 'player': player, 'gp': self.gp+1, 'pts':3*(4-(raceNum%4))%4, 'rem_races':(4-(raceNum%4))%4, 'is_edited':True}
                        
                        for indx, i in enumerate(self.dc_list[raceNum]):
                            if i.find(self.display_names[player]) == 0 and ("before" in i or "missing" in i):
                                if (4-(raceNum%4))%4 == 0:
                                    self.dc_list[raceNum][indx] = "{}**  -  DCed during the race (on results). No DC points for GP {} - determined by tabler.".format(Utils.dis_clean(self.display_names[player]), self.gp+1)
                                else:    
                                    self.dc_list[raceNum][indx] = "{}**  -  DCed during the race (on results). Giving 3 DC points per race for remaining {} races in GP {} ({} pts total) - determined by tabler.".format(Utils.dis_clean(self.display_names[player]), (4-(raceNum%4))%4, self.gp+1, 3*(4-(raceNum%4))%4)
                    
                    else:
                        for indx,i in enumerate(self.warnings[raceNum]):
                            if i.get('player') == player and "before" in i.get('type'):
                                self.warnings[raceNum][indx] = {'type':"dc_on", 'race':1, 'gp':self.gp+1, 'player':player, 'is_edited':True}
                        for indx, i in enumerate(self.dc_list[raceNum]):
                            if i.find(self.display_names[player]) == 0 and ("before" in i or "missing" in i):
                                self.dc_list[raceNum][indx] = "{}**  -  DCed on the first race of GP {}. 15 DC points for GP {} - determined by tabler.".format(Utils.dis_clean(self.display_names[player]), self.gp+1, self.gp+1)
            else:
                orig_status = 'before'
                if player in players:
                    orig_status = 'on'
                    self.change_room_size([[raceNum, len(self.races[raceNum-1])-1]], self_call=True)
                    #print(mes)
                    
                    if raceNum %4 != 1:
                        gp = int((raceNum-1)/4)
                        self.players[player][1][gp] +=3
                        self.players[player][2][raceNum-1] = 3

                        for indx,i in enumerate(self.dc_pts[player]):
                            if i[0]==raceNum:
                                self.dc_pts[player][indx][1].insert(0, raceNum)
                                break
                        
                        for indx,i in enumerate(self.warnings[raceNum]):
                            if i.get('player') == player and "on" in i.get('type'):
                                self.warnings[raceNum][indx] = {'type': "dc_before", 'player':player, 'race':raceNum, 'rem_races':4-((raceNum-1)%4), 'pts':3*(4-((raceNum-1)%4)), 'gp':self.gp+1, 'is_edited':True}
                        for indx, i in enumerate(self.dc_list[raceNum]):
                            if i.find(self.display_names[player]) == 0 and ("during" in i or "on" in i):
                                self.dc_list[raceNum][indx] = "{}**  -  DCed before race {} (missing from results). 3 pts per race for remaining races in GP {} ({} pts total) - determined by tabler.".format(Utils.dis_clean(self.display_names[player]), raceNum, self.gp+1, 3*(4-(raceNum%4)))
                                        
                    else:     
                        for indx,i in enumerate(self.warnings[raceNum]):
                            if i.get('player') == player and "on" in i.get('type'):
                                self.warnings[raceNum][indx] = {'type': "dc_before", 'race':1, 'gp':self.gp+1, 'is_edited':True}
                        for indx, i in enumerate(self.dc_list[raceNum]):
                            if i.find(self.display_names[player]) == 0 and ("during" in i or "on" in i):
                                self.dc_list[raceNum][indx]="{}**  -  DCed before race {} (missing from GP {}). 18 pts for GP {} (mogi), 15 pts for GP {} (war) - determined by tabler.".format(Utils.dis_clean(self.display_names[player]), raceNum,self.gp+1,self.gp+1, self.gp+1)

            mods.append(('?dcs {} {}'.format(dc_num, status), dc_num, orig_status, status))         
            ret+= "Changed {} DC status for race {} to '{}'.\n".format(Utils.dis_clean(self.display_names[player]), raceNum, status)
        
        if not reundo and len(mods)>0: 
            self.modifications.append(mods)
            self.undos.clear()
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
                # print("ROOM SIZES:",self.changed_room_sizes[raceNum+1])
                # print("ORIG ROOM SIZE:", orig_room_size)
                    
                gp = int(raceNum/4)
            except:
                ret+= "Invalid <race number>. Race number must be between 1-{}.\n".format(len(self.races))
                continue
            try:
                cor_room_size = int(i[1])
                assert(cor_room_size>0 and cor_room_size<=len(self.players) and (cor_room_size <=orig_room_size or self_call))
                
            except:
                
                if cor_room_size> orig_room_size and cor_room_size<=len(self.players):
                    ret+="**Note: If a race is missing player(s) due to DCs, it is advised to use the ?dcs command instead.\nOnly use this command if no DCs were shown for the race in question.\n\n**"
                else:
                    ret+= "Invalid <corrected room size> for race {}. The corrected room size must be between 1-{}.\n".format(raceNum+1, len(self.players))
                    continue
            
            if cor_room_size == orig_room_size:
                ret+='Race {} room size is already {} - no change made.\n'.format(raceNum+1, cor_room_size)
                continue
            
            orig_pts = {}
            for place, p in enumerate(self.races[raceNum]):
                player = p[2]
                try:
                    pts = self.pts[orig_room_size][place]
                except KeyError:
                    pts = 0
                orig_pts[player] = pts
            
            fixed_pts = {}
            
            for place, p in enumerate(self.races[raceNum]):
                player = p[2]
                try:
                    pts = self.pts[cor_room_size][place]
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
                    return "The player index {} was invalid. The player id must be between 1-{}".format(player,len(self.players))
                
            correct_pos = int(elem[2])-1
            try:
                raceNum = int(raceNum)
                corresponding_rr = self.races[raceNum-1]
            except:
                return "The race number {} was invalid. It must be a number from 1-{}".format(raceNum, len(self.races))
            
            corresponding_rr = [i[2] for i in corresponding_rr]
            
            orig_pos = corresponding_rr.index(player)
            orig_pts = self.pts[len(corresponding_rr)][orig_pos]
            try:   
                cor_pts = self.pts[len(corresponding_rr)][int(correct_pos)]
            except:
                return "The corrected position {} was invalid. It must be a number from 1-{}.".format(correct_pos, len(corresponding_rr))
            
            if orig_pos<correct_pos:
                aff = [self.races[raceNum-1][i][2] for i in range(orig_pos+1,correct_pos+1)]
            else:
                aff = [self.races[raceNum-1][i][2] for i in range(correct_pos,orig_pos)]
                
            aff_orig_pts = {}
            for a in aff:
                aff_orig_pts[a] = self.pts[len(corresponding_rr)][corresponding_rr.index(a)]
            
            correct_ft_order = list(self.finish_times[raceNum-1].keys())
            correct_ft_order.insert(correct_pos, correct_ft_order.pop(orig_pos))
            self.finish_times[raceNum-1] = {k : self.finish_times[raceNum-1][k] for k in correct_ft_order}
            
            self.races[raceNum-1].insert(correct_pos, self.races[raceNum-1].pop(orig_pos))

            aff_new_pts = {}
            corresponding_rr = self.races[raceNum-1]
            corresponding_rr = [i[2] for i in corresponding_rr]
            
            for a in aff:
                aff_new_pts[a] = self.pts[len(corresponding_rr)][corresponding_rr.index(a)]
            
            gp = int((raceNum-1)/4)

            self.players[player][0] += (cor_pts-orig_pts)
            self.players[player][1][gp] += (cor_pts-orig_pts)
            self.players[player][2][raceNum-1] = cor_pts

            for a in aff:
                self.players[a][0]+= (aff_new_pts[a] - aff_orig_pts[a])
                self.players[a][1][gp] += (aff_new_pts[a] - aff_orig_pts[a])
                self.players[a][2][raceNum-1] = aff_new_pts[a]
            
            ret+='{} race {} placement changed to {}.{}'.format(Utils.dis_clean(self.display_names[player]), raceNum, correct_pos+1, '\n' if num==len(l)-1 else "")
            
            if "Placements for this race have been manually altered by the tabler." not in self.manual_warnings[raceNum]:
                self.manual_warnings[raceNum].append("Placements for this race have been manually altered by the tabler.")
            
            mods.append(('?editrace {} {} {}'.format(raceNum, p_indx, correct_pos+1), player, raceNum, orig_pos+1, correct_pos+1))
     
        if not reundo and len(mods)>0:
            self.modifications.append(mods)
            self.undos.clear()
        return ret
    
    async def merge_room(self, arg):
        is_rxx = False
        check = arg[0]
        if len(arg)==1 and (len(check)==8 and check[1:].isnumeric() and check[0]=='r') or (len(check)==4 and check[2:].isnumeric()):
            is_rxx = True
            
        if is_rxx:
            error, mes = await self.find_room(rid = arg, merge=True)
        else:
            error, mes= await self.find_room(mii=arg, merge=True)
        
        return error, mes

    def un_merge_room(self, merge_num): #TEST: need testing
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
        self.warnings = {k:v for k,v in self.warnings.items() if k<=len(self.races)}
        self.dc_list = {k:v for k, v in self.dc_list.items() if k<=len(self.races)}
        
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
                self.players[player][1][gp] += self.pts[cur_room_size][placement]
                self.players[player][2][raceNum] += self.pts[cur_room_size][placement]
                self.players[player][0] += self.pts[cur_room_size][placement]
        
        x = copy.deepcopy(self.players)
        for i in x.keys():
            if i not in recorded_players:
                self.players.pop(i)
                self.fcs.pop(self.display_names[i])
                self.display_names.pop(i)
                for tag in self.tags.items():
                    if i in tag[1]:
                        tag[1].remove(i)
                
    
    def remove_race(self, raceNum, redo=False): #TEST: needs testing (also need to figure out how to keep manual warnings and manual edits to the table)
        if raceNum==-1: raceNum = len(self.races)
        try:
            assert(raceNum<=len(self.races))
        except:
            return "{} was not a valid race number. The race number must be between 1-{}.".format(raceNum,len(self.races))
        
        track = self.tracks.pop(raceNum-1)
        self.removed_races[raceNum] = [self.races.pop(raceNum-1), track]
        
        #don't know if I need to keep the removed warnings and dcs for the removed race (since the dc_pts and warnings might need to be recalculated)
        removed_dc_pts = defaultdict(list)
        for player in copy.deepcopy(self.dc_pts).items():
            for num, dc in enumerate(player[1]):
                if dc[0] == raceNum:
                    removed_dc_pts[player[0]].append(player[1].pop(num))
        self.dc_pts = {k:v for k,v in self.dc_pts.items() if len(v)>0}
        
        removed_dc_list_ids = {}
        for _id, dc in copy.deepcopy(self.dc_list_ids).items():
            if dc[1]==raceNum:
                removed_dc_list_ids[_id] = self.dc_list_ids.pop(_id)
        try:
            rem_warn = self.warnings.pop(raceNum)
        except:
            rem_warn = None
        try:
            rem_dc_list = self.dc_list.pop(raceNum)
        except:
            rem_dc_list = None
            
        self.removed_warn_dcs[raceNum] = {'warnings':rem_warn, 'dc_list':rem_dc_list, 'dc_list_ids': removed_dc_list_ids, 'dc_pts':removed_dc_pts}
        #self.shift_warnings(start=raceNum, direction='left')
        self.recalc_table(start=raceNum)
        
        if not redo: 
            self.modifications.append([('?removerace {}'.format(raceNum), raceNum, track)])
            self.undos.clear()

        self.warnings[-1].append("Race #{} (originally) - {} has been removed by the tabler.".format(raceNum, track))
            
        return "Removed race {} - {} from table.".format(raceNum, track)
    
    def restore_removed_race(self, raceNum):
       restore_race, restore_track = self.removed_races.pop(raceNum)
       self.races.insert(raceNum-1, restore_race)
       self.tracks.insert(raceNum-1, restore_track)
       
       #self.shift_warnings(start=raceNum+1, direction='right')
       self.recalc_table(start=raceNum)
       
    def shift_warnings(self, start, direction):
        direction = 1 if direction == 'right' else -1
        
        #shift warnings
        for race in list(self.warnings.keys()):
            if race>=start:
                self.warnings[race+direction] = self.warnings.pop(race)
        
        #shift dc_list
        for race in list(self.dc_list.keys()):
            if race>=start:
                self.dc_list[race+direction] = self.warnings.pop(race)
        
        #shift dc_list_ids
        for num, dc in self.dc_list_ids.items():
            if dc[1] >=start:
                dc[1] = dc[1]+direction
        
    
    def recalc_table(self, start = 0): #TODO: figure out how to shift warnings to keep manual warnings
                                        
        self.gp = int((start-1)/4)
        for player in self.players.items():
            for num,gp in enumerate(player[1][1]):
                if num>=self.gp:
                    self.players[player[0]][1][num] = 0
            for num, race in enumerate(player[1][2]):
                if int(num/4)>=self.gp:
                    self.players[player[0]][2][num] = 0
        
        self.warnings = {k:v for k,v in self.warnings.items() if k<self.gp*4+1}
        self.dc_list = {k:v for k, v in self.dc_list.items() if k<self.gp*4+1}
                
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
        
       
        last_race_players = []
        begin = self.gp*4
        for raceNum, race in enumerate(self.races[self.gp*4:]):
            raceNum+=begin
            if raceNum%4 == 0:
                if raceNum-begin!=0:
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
            
            if cur_room_size < self.room_sizes[self.gp]:
                self.room_sizes[self.gp] = cur_room_size
                
            #check for mid_GP room size increases (mkwx bug)
            if cur_room_size > self.room_sizes[self.gp]:
                self.room_sizes_error_affected[self.gp].append(raceNum+1)
                
                if self.room_error_index[self.gp][1]==-1:
                    self.warnings[raceNum+1].append({'type': "mkwx_bug_increase", 'new_players':cur_room_size, 'orig_players':self.room_sizes[self.gp], 'races':self.room_sizes_error_affected[self.gp]})
                    self.room_error_index[self.gp][1] = len(self.warnings[raceNum+1])-1
                    self.room_error_index[self.gp][0] = raceNum+1
                else:
                    self.warnings[self.room_error_index[self.gp][0]][self.room_error_index[self.gp][1]]['races'] = self.room_sizes_error_affected[self.gp]
            #check for changed players mid-GP (mkwx bug)
            elif not all(elem in self.room_players[self.gp] for elem in cur_race_players) and not all(elem in last_race_players for elem in cur_race_players):
                self.warnings[raceNum+1].append({'type': "mkwx_bug_change", 'race': raceNum+1, 'gp':self.gp+1})
            last_race_players = cur_race_players     
            
            
            if cur_room_size<self.num_players and len(self.players)<self.num_players and (len(self.races)+raceNum)%4 == 0:
                if raceNum+1 not in self.dc_list:   
                    self.dc_list[raceNum+1] = []
                    
                self.warnings[raceNum+1].append({'type': 'missing', 'cur_players': cur_room_size, 'sup_players': self.num_players, 'gp': self.gp+1})
                self.dc_list[raceNum+1].append("GP {} is missing player(s). GP started with {} players, but should've started with {} players.".format(self.gp+1, cur_room_size,self.num_players))
                           
            elif cur_room_size<len(self.players):
                f_codes = [i[2] for i in race]
                missing_players = []
                for i in self.players:
                    if i not in f_codes: missing_players.append(i)
                
                sub_outs = False
                if len(self.players)>self.num_players and len(missing_players)==len(self.players)-self.num_players:
                    sub_outs= True
                    
                if not sub_outs:
                    if (raceNum)%4 == 0:
                        for mp in missing_players:
                            if self.gp not in self.gp_dcs or mp not in self.gp_dcs[self.gp]:
                                if raceNum+1 not in self.dc_list:   
                                    self.dc_list[raceNum+1] = []
                                    
                                self.warnings[raceNum+1].append({'type': 'dc_before', 'race':1, 'gp': self.gp+1, 'player':mp})
                                self.dc_list[raceNum+1].append("{}**  -  DCed before race {} (missing from GP {}). 18 pts for GP {} (mogi), 15 pts for GP {} (war).".format(Utils.dis_clean(self.display_names[mp]), raceNum+1,self.gp+1,self.gp+1, self.gp+1))
                                self.dc_ids_append(mp, raceNum+1)
                                if self.gp not in self.gp_dcs: self.gp_dcs[self.gp] = []
                                self.gp_dcs[self.gp].append(mp)
                                
                    else:
                        for mp in missing_players:
                            if self.gp not in self.gp_dcs or mp not in self.gp_dcs[self.gp]:
                                if raceNum+1 not in self.dc_list:   
                                    self.dc_list[raceNum+1] = []

                                self.warnings[raceNum+1].append({'type':'dc_before', 'race':raceNum+1, 'rem_races':4-((raceNum)%4), 'pts':3*(4-((raceNum)%4)), 'gp':self.gp+1,'player':mp})    
                                self.dc_list[raceNum+1].append("{}**  -  DCed before race {} (missing from results). 3 pts per race for remaining races in GP {} ({} pts total).".format(Utils.dis_clean(self.display_names[mp]), raceNum+1, self.gp+1, 3*(4-((raceNum)%4))))
                                
                                try:
                                    self.dc_pts[mp].append([raceNum+1, [i for i in range(raceNum+1, raceNum+1+(4-((raceNum)%4))%4)]])
                                    
                                except: 
                                    self.dc_pts[mp] = [[raceNum+1, [i for i in range(raceNum+1, raceNum+1+(4-((raceNum)%4))%4)]]]
                            
                                self.dc_ids_append(mp, raceNum+1)
                                if self.gp not in self.gp_dcs: self.gp_dcs[self.gp] = []
                                self.gp_dcs[self.gp].append(mp)
                            
            for dc in list(self.dc_pts.items()):
                for j in dc[1]:
                    if raceNum+1 in j[1]:
                        self.players[dc[0]][1][self.gp]+=3
                        self.players[dc[0]][2][raceNum]=3
                        break

            dc_count = 0
            for i, r in enumerate(race):
                if r[1] == '—':
                    dc_count +=1
                    race[i] = (r[0], 'DC', r[2])
            if dc_count == cur_room_size:
                self.warnings[raceNum+1].append({'type': "mkwx_bug_blank", 'gp':self.gp+1})

                fin_times = {}
                for i in race:
                    fin_times[i[0]] = i[1]
                self.finish_times[raceNum] = fin_times
                
                continue

            last_finish_times = {}
            
            for place,player in enumerate(race):
                time = player[1]
                fc = player[2]
                
                if fc not in self.players and fc not in self.deleted_players: #sub player
                    status = self.add_sub_player(self.check_name(player[0]), fc)
                    if self.format[0].lower()!='f' and status !='failed':
                        self.warnings[raceNum+1].append({'type':'sub', 'player': fc})
                        
                miiName = self.display_names[fc]
        
                try:
                    self.players[fc][1][self.gp] += self.pts[cur_room_size][place]
                    self.players[fc][2][raceNum] = self.pts[cur_room_size][place]
                    self.players[fc][0] += self.pts[cur_room_size][place]
                    
                    #check for ties
                    if time in list(last_finish_times.values()):
                        
                        for index,t in enumerate(list(last_finish_times.values())):
                            if t == time:
                                if raceNum+1 not in self.ties:
                                    self.ties[raceNum+1] = {}
                                if time in self.ties[raceNum+1]:
                                    self.ties[raceNum+1][time].append(list(last_finish_times.keys())[index])
                                else:
                                    self.ties[raceNum+1][time] = [list(last_finish_times.keys())[index]]
                        
                        self.ties[raceNum+1][time].append(fc)
                    
                    if ":" in time and int(time[0:time.find(':')])>=5:
                        if self.sui:    
                            if "Large finish times occurred, but are being ignored. Table could be inaccurate." not in self.warnings[-1]:
                                self.warnings[-1].append("Large finish times occurred, but are being ignored. Table could be inaccurate.")

                        else:
                            self.warnings[raceNum+1].append({'type': 'large_time', 'player':fc, 'time':time})
                           
                    
                    last_finish_times[fc] = time
                    assert(time!='DC')
                    
                except:
                    if self.gp not in self.gp_dcs or fc not in self.gp_dcs[self.gp]:
                        if raceNum+1 not in self.dc_list:   
                            self.dc_list[raceNum+1] = []
                        
                        if (raceNum)%4==0:
                            self.warnings[raceNum+1].append({'type': 'dc_on', 'race':1, 'gp':self.gp+1, 'player':fc})
                            self.dc_list[raceNum+1].append("{}**  -  DCed on the first race of GP {} (on results). 15 DC points for GP {}.".format(Utils.dis_clean(miiName), self.gp+1, self.gp+1))
                            
                        else: 
                            if (4-((raceNum+1)%4))%4 == 0:
                                self.warnings[raceNum+1].append({'type': "dc_on", 'race':-1, 'player':fc, 'gp':self.gp+1})
                                self.dc_list[raceNum+1].append("{}**  -  DCed during the race (on results). No DC points for GP {}.".format(Utils.dis_clean(miiName), self.gp+1))
                        
                            else:
                                self.warnings[raceNum+1].append({'type': "dc_on", 'race':raceNum+1, 'rem_races': (4-((raceNum+1)%4))%4, 'pts':3*((4-((raceNum+1)%4))%4), 'player':fc, 'gp':self.gp+1})
                                self.dc_list[raceNum+1].append("{}**  -  DCed during the race (on results). Giving 3 DC points per race for remaining {} races in GP {} ({} pts total).".format(Utils.dis_clean(miiName), (4-((raceNum+1)%4))%4, self.gp+1,3*((4-((raceNum+1)%4))%4)))
                            
                            if (4-((raceNum+1)%4))%4!=0:
                                try:
                                    self.dc_pts[fc].append([raceNum+1, [i for i in range(raceNum+2, raceNum+2+(4-((raceNum+1)%4))%4)]])
                                    
                                except:
                                    self.dc_pts[fc]= [[raceNum+1, [i for i in range(raceNum+2, raceNum+2+(4-((raceNum+1)%4))%4)]]]
                        
                        self.dc_ids_append(fc, raceNum+1)
                        if self.gp not in self.gp_dcs: self.gp_dcs[self.gp] = []
                        self.gp_dcs[self.gp].append(fc)
                    else:
                        self.warnings[raceNum+1].append({'type': 'blank_time', 'player': fc})
                            
                              
            if raceNum+1 in self.ties:
                for tie in list(self.ties[raceNum+1].items()):     
                    self.warnings[raceNum+1].append({'type':'tie', "time":tie[0], 'players':tie[1]})
            
            self.finish_times[raceNum] = last_finish_times
        
        self.table_str = self.create_string()
    
    
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
            

    async def update_table(self, prnt=True, auto=False):
        rID = self.rxx
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
                
                race.append((miiName, fin_time, fc))
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
       
        #start_room_size = len(self.players)
        last_race_players = []
        for raceNum, race in enumerate(new_races):
            #increment gp
            if (len(self.races)+raceNum)%4 == 0 and len(self.races)+raceNum!=0: 
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
            
            #check for room size increases (mkwx bug)
            if cur_room_size < self.room_sizes[self.gp]:
                self.room_sizes[self.gp] = cur_room_size
            if cur_room_size > self.room_sizes[self.gp]:
                self.room_sizes_error_affected[self.gp].append(len(self.races)+raceNum+1)
                
                if self.room_error_index[self.gp][1]==-1:
                    self.warnings[len(self.races)+raceNum+1].append({'type': "mkwx_bug_increase", 'new_players':cur_room_size, 'orig_players':self.room_sizes[self.gp], 'races':self.room_sizes_error_affected[self.gp]})
                    self.room_error_index[self.gp][1] = len(self.warnings[len(self.races)+raceNum+1])-1
                    self.room_error_index[self.gp][0] = len(self.races)+raceNum+1
                else:
                    self.warnings[self.room_error_index[self.gp][0]][self.room_error_index[self.gp][1]]['races'] = self.room_sizes_error_affected[self.gp]
            
            #check for changed players mid-GP (mkwx bug)
            elif not all(elem in self.room_players[self.gp] for elem in cur_race_players) and not all(elem in last_race_players for elem in cur_race_players):
                self.warnings[len(self.races)+raceNum+1].append({'type': "mkwx_bug_change", 'race': len(self.races)+raceNum+1, 'gp':self.gp+1})

            last_race_players = cur_race_players   
            
            if cur_room_size<self.num_players and len(self.players)<self.num_players and (len(self.races)+raceNum)%4 == 0:
                if len(self.races)+raceNum+1 not in self.dc_list:   
                    self.dc_list[len(self.races)+raceNum+1] = []
                #TEST:  
                self.warnings[len(self.races)+raceNum+1].append({'type': 'missing', 'cur_players': cur_room_size, 'sup_players': self.num_players, 'gp': self.gp+1})
                self.dc_list[len(self.races)+raceNum+1].append("GP {} is missing player(s). GP started with {} players, but should've started with {} players.".format(self.gp+1, cur_room_size,self.num_players))
                           
            elif cur_room_size<len(self.players):
                f_codes = [i[2] for i in race]
                missing_players = []
                for i in self.players:
                    if i not in f_codes: missing_players.append(i)
                
                sub_outs = False
                if len(self.players)>self.num_players and len(missing_players)==len(self.players)-self.num_players:
                    sub_outs= True
                    
                if not sub_outs:
                    if (len(self.races)+raceNum)%4 == 0:
                        for mp in missing_players:
                            if self.gp not in self.gp_dcs or mp not in self.gp_dcs[self.gp]:
                                if len(self.races)+raceNum+1 not in self.dc_list:   
                                    self.dc_list[len(self.races)+raceNum+1] = []
                                    
                                self.warnings[len(self.races)+raceNum+1].append({'type': 'dc_before', 'race':1, 'gp': self.gp+1, 'player':mp})
                                self.dc_list[len(self.races)+raceNum+1].append("{}**  -  DCed before race {} (missing from GP {}). 18 pts for GP {} (mogi), 15 pts for GP {} (war).".format(Utils.dis_clean(self.display_names[mp]), len(self.races)+raceNum+1,self.gp+1,self.gp+1, self.gp+1))
                                self.dc_ids_append(mp, len(self.races)+raceNum+1)
                                if self.gp not in self.gp_dcs: self.gp_dcs[self.gp] = []
                                self.gp_dcs[self.gp].append(mp)
                                
                    else:
                        for mp in missing_players:
                            if self.gp not in self.gp_dcs or mp not in self.gp_dcs[self.gp]:
                                if len(self.races)+raceNum+1 not in self.dc_list:   
                                    self.dc_list[len(self.races)+raceNum+1] = []
                                    
                                self.warnings[len(self.races)+raceNum+1].append({'type':'dc_before', 'race':len(self.races)+raceNum+1, 'rem_races':4-((len(self.races)+raceNum)%4), 'pts':3*(4-((len(self.races)+raceNum)%4)), 'gp':self.gp+1,'player':mp})    
                                self.dc_list[len(self.races)+raceNum+1].append("{}**  -  DCed before race {} (missing from results). 3 pts per race for remaining races in GP {} ({} pts total).".format(Utils.dis_clean(self.display_names[mp]), len(self.races)+raceNum+1, self.gp+1, 3*(4-((len(self.races)+raceNum)%4))))
                                
                                try:
                                    self.dc_pts[mp].append([len(self.races)+raceNum+1, [i for i in range(len(self.races)+raceNum+1, len(self.races)+raceNum+1+(4-((len(self.races)+raceNum)%4))%4)]])
                                
                                except:
                                    self.dc_pts[mp] = [[len(self.races)+raceNum+1, [i for i in range(len(self.races)+raceNum+1, len(self.races)+raceNum+1+(4-((len(self.races)+raceNum)%4))%4)]]]
                                    
                            
                                self.dc_ids_append(mp, len(self.races)+raceNum+1)
                                if self.gp not in self.gp_dcs: self.gp_dcs[self.gp] = []
                                self.gp_dcs[self.gp].append(mp)
                            
            for dc in list(self.dc_pts.items()):
                for j in dc[1]:
                    if len(self.races)+raceNum+1 in j[1]:
                        self.players[dc[0]][1][self.gp]+=3
                        self.players[dc[0]][2][raceNum]=3
                        break
            
            dc_count = 0
            for i, r in enumerate(race):
                if r[1] == '—':
                    dc_count +=1
                    race[i] = (r[0], 'DC', r[2])
            if dc_count == cur_room_size:
                self.warnings[len(self.races)+raceNum+1].append({"type": "mkwx_bug_blank", 'gp':self.gp+1})
                
                fin_times = {}
                for i in race:
                    fin_times[i[0]] = i[1]
                self.finish_times[len(self.races)+raceNum] = fin_times
                
                continue
            
            last_finish_times = {}
            
            for place,player in enumerate(race):
                time = player[1]
                fc = player[2]
                
                if fc not in self.players and fc not in self.deleted_players: #sub player
                    status = self.add_sub_player(self.check_name(player[0]), fc)
                    if self.format[0].lower()!='f' and status !='failed':
                        self.warnings[len(self.races)+raceNum+1].append({'type':'sub', 'player': fc})

                miiName = self.display_names[fc]
        
                try:
                    self.players[fc][1][self.gp] += self.pts[cur_room_size][place]
                    self.players[fc][2][len(self.races)+raceNum] = self.pts[cur_room_size][place]
                    self.players[fc][0] += self.pts[cur_room_size][place]
                    
                    #check for ties
                    if time in list(last_finish_times.values()):
                        for index,t in enumerate(list(last_finish_times.values())):
                            if t == time:
                                if len(self.races)+raceNum+1 not in self.ties:
                                    self.ties[len(self.races)+raceNum+1] = {}
                                if time in self.ties[len(self.races)+raceNum+1]:
                                    self.ties[len(self.races)+raceNum+1][time].append(list(last_finish_times.keys())[index])
                                else:
                                    self.ties[len(self.races)+raceNum+1][time] = [list(last_finish_times.keys())[index]]
                        
                        self.ties[len(self.races)+raceNum+1][time].append(fc)
                    
                    if ":" in time and int(time[0:time.find(':')])>=5:
                        if self.sui:
                            if "Large finish times occurred, but are being ignored. Table could be inaccurate." not in self.warnings[-1]:
                                self.warnings[-1].append("Large finish times occurred, but are being ignored. Table could be inaccurate.")

                        else:
                            self.warnings[len(self.races)+raceNum+1].append({'type': 'large_time', 'player':fc, 'time':time})
 
                    last_finish_times[fc] = time
                    assert(time!='DC')
                    
                except:
                    if self.gp not in self.gp_dcs or fc not in self.gp_dcs[self.gp]:
                        if len(self.races)+raceNum+1 not in self.dc_list:   
                            self.dc_list[len(self.races)+raceNum+1] = []
                        
                        if (len(self.races)+raceNum)%4==0:
                            self.warnings[len(self.races)+raceNum+1].append({'type': 'dc_on', 'race':1, 'gp':self.gp+1, 'player':fc})
                            self.dc_list[len(self.races)+raceNum+1].append("{}**  -  DCed on the first race of GP {} (on results). 15 DC points for GP {}.".format(Utils.dis_clean(miiName), self.gp+1, self.gp+1))
                            
                        else: 
                            if (4-((len(self.races)+raceNum+1)%4))%4 == 0:
                                self.warnings[len(self.races)+raceNum+1].append({'type': "dc_on", 'race':-1, 'player':fc, 'gp':self.gp+1})
                                self.dc_list[len(self.races)+raceNum+1].append("{}**  -  DCed during the race (on results). No DC points for GP {}.".format(Utils.dis_clean(miiName), self.gp+1))
                        
                            else:
                                self.warnings[len(self.races)+raceNum+1].append({'type': "dc_on", 'race':len(self.races)+raceNum+1, 'rem_races': (4-((len(self.races)+raceNum+1)%4))%4, 'pts':3*((4-((len(self.races)+raceNum+1)%4))%4), 'player':fc, 'gp':self.gp+1})
                                self.dc_list[len(self.races)+raceNum+1].append("{}**  -  DCed during the race (on results). Giving 3 DC points per race for remaining {} races in GP {} ({} pts total).".format(Utils.dis_clean(miiName), (4-((len(self.races)+raceNum+1)%4))%4, self.gp+1,3*((4-((len(self.races)+raceNum+1)%4))%4)))
                            
                            if (4-((len(self.races)+raceNum+1)%4))%4!=0:
                                try:
                                    self.dc_pts[fc].append([len(self.races)+raceNum+1, [i for i in range(len(self.races)+raceNum+2, len(self.races)+raceNum+2+(4-((len(self.races)+raceNum+1)%4))%4)]])
                                    
                                except:
                                    self.dc_pts[fc]= [[len(self.races)+raceNum+1, [i for i in range(len(self.races)+raceNum+2, len(self.races)+raceNum+2+(4-((len(self.races)+raceNum+1)%4))%4)]]]
                        
                        self.dc_ids_append(fc, len(self.races)+raceNum+1)
                        if self.gp not in self.gp_dcs: self.gp_dcs[self.gp] = []
                        self.gp_dcs[self.gp].append(fc)
                    else:
                        self.warnings[len(self.races)+raceNum+1].append({'type': 'blank_time', 'player': fc})
                        #self.dc_list[len(self.races)+raceNum+1].append("{}**  -  DCed on the first race of GP {} (on results). 15 DC points for GP {}.".format(miiName, self.gp+1, self.gp+1))
                            
                      
                        
            if len(self.races)+raceNum+1 in self.ties:
                for tie in list(self.ties[len(self.races)+raceNum+1].items()):     
                    self.warnings[len(self.races)+raceNum+1].append({'type':'tie', "time":tie[0], 'players':tie[1]}) 
            
            self.finish_times[len(self.races)+raceNum] = last_finish_times
            
            
        #self.players = dict(sorted(self.players.items(), key=lambda item: item[1], reverse=True))
        self.races+=new_races
        self.table_str = self.create_string()

        if prnt:
            print()
            print(self.table_str)
            #last_table_img = table_img
            
        return "Table {}updated. Room {} has finished {} {}. Last race: {}.".format("auto-" if auto else "",rID, len(self.races), "race" if len(self.races)==1 else "races",self.tracks[len(self.races)-1])
                

    def create_string(self, by_race = False):
        self.tags = {k:v for k,v in self.tags.items() if len(v)>0}
        
                
        ret = "#title {} {}".format(len(self.races), "race" if len(self.races)==1 else 'races')
        if self.format[0] == 'f':
            ret+='\nFFA'
            for p in self.players.keys():
                ret+="\n{} ".format(self.display_names[p])
                if by_race: 
                    scores = self.players[p][2]
                else:
                    scores = self.players[p][1]
                for num,gp in enumerate(scores):
                    if by_race:
                        if int(num/4)+1 in self.edited_scores and p in self.edited_scores[int(num/4)+1]:
                            if num/4 +1 in self.edited_scores:
                                ret+="{}".format(self.edited_scores[int(num/4)+1][p])
                            else:
                                ret+='0'
                            if num+1!=len(scores):
                                ret+='|'
                            continue
                    else:
                        if num+1 in self.edited_scores and p in self.edited_scores[num+1]:
                            ret+='{}'.format(self.edited_scores[num+1][p])
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
                                if int(num/4)+1 in self.edited_scores and p in self.edited_scores[int(num/4)+1]:
                                    if num/4 +1 in self.edited_scores:
                                        ret+="{}".format(self.edited_scores[int(num/4)+1][p])
                                    else:
                                        ret+='0'
                                    if num+1!=len(scores):
                                        ret+='|'
                                    continue        
                            else:
                                if num+1 in self.edited_scores and p in self.edited_scores[num+1]:
                                    ret+='{}'.format(self.edited_scores[num+1][p])
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
                                if int(num/4)+1 in self.edited_scores and p in self.edited_scores[int(num/4)+1]:
                                    if num/4 +1 in self.edited_scores:
                                        ret+="{}".format(self.edited_scores[int(num/4)+1][p])
                                    else:
                                        ret+='0'
                                    if num+1!=len(scores):
                                        ret+='|'
                                    continue      
                            else:
                                if num+1 in self.edited_scores and p in self.edited_scores[num+1]:
                                    ret+='{}'.format(self.edited_scores[num+1][p])
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
                            
        ret = ret.replace("no name", "Player")
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
            raceNum =  gp*4-3
            count = 0
            for x in self.modifications:
                for j in x:
                    if '?edit ' in j[0] and int(j[2])==gp:
                        count+=1
            if count==1: self.manual_warnings[raceNum].pop(0)
            
        elif '?editrace' in mod_type:
            raceNum = int(mod[2])
            count = 0
            for x in self.modifications:
                for j in x:
                    if '?editrace' in j[0] and int(j[2])==raceNum:
                        count+=1
            if count==1: 
                #print("ASD")
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
                    if i.find(player) == 0:
                        self.dc_list[raceNum][indx] = self.dc_list[raceNum][indx].replace(' - determined by tabler', '')
                for indx,i in enumerate(self.warnings[raceNum]):
                    if i.get('player') == player:
                        self.warnings[raceNum][indx]['is_edited'] = False
        elif "?removerace" in mod_type:
            raceNum= int(mod[1])
            track = mod[2]
            for indx,i in enumerate(self.warnings[-1]):
                if 'Race #{}'.format(raceNum) in i and track in i and 'has been removed' in i:
                    self.warnings[-1].pop(indx)
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
                    
        self.warnings = {k:v for k,v in self.warnings.items() if len(v)>0}
        self.manual_warnings = {k:v for k,v in self.manual_warnings.items() if len(v)>0}    
    
    def undo(self, j):
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
            self.restore_removed_race(j[1])
            self.undo_warning(j)
            
        elif '?sub' in j[0]:
            self.undo_sub(j[1], j[2], j[4])
            
        elif '?editsub' in j[0]:
            self.edit_sub_races(j[1], j[3], j[4], out_index=j[5], reundo=True)
        
        elif '?mergeroom' in j[0]:
            self.un_merge_room(j[1])
        
        elif '?edittag' in j[0]:
            self.edit_tag_name([[j[2], j[1]]], reundo=True)
        
        elif '?changetag' in j[0]:
            self.change_tag(j[1], j[3], restore_indx=j[4], reundo=True)

        elif '?tags ' in j[0]:
            self.undo_group_tags(j[1])
        
        elif '?changename ' in j[0]:
            self.undo_change_name(j[1], j[3],j[4])

        else:
            print("undo error:",j[0])
    
    def redo(self, j):
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
            self.remove_race(j[1], redo=True)
            
        elif '?sub' in j[0]:
            self.sub_in(j[1], j[2], j[3], reundo=True)
    
        elif '?editsub' in j[0]:
            self.edit_sub_races(j[1], j[2], j[4], out_index=j[5], reundo=True)   
            
        elif '?mergeroom' in j[0]:
            self.merge_room(j[2])
        
        elif '?edittag' in j[0]:
            self.edit_tag_name([[j[1], j[2]]], reundo=True)
        
        elif '?changetag' in j[0]:
            self.change_tag(j[1], j[2], reundo=True)

        elif '?tags ' in j[0]:
            self.group_tags(j[2], redo=True)

        elif '?changename ' in j[0]:
            self.change_name([[j[1], j[2]]], redo=True)
        
        else:
            print("redo error:",j[0])
            
    def undo_commands(self, num): #TODO: clearing "manually edited" warnings needs further testing and additions for new commands
        if num == 0: #undo all
            if len(self.modifications)>0:
                for i in list(reversed(copy.deepcopy(self.modifications))):
                    for j in i:
                        self.undo(j)
                        self.undos.append(self.modifications.pop(self.modifications.index(i)))
                
                return "All manual table modifications have been undone."
            return "No manual modifications to the table to undo."
        
        else: #undo last
            if len(self.modifications)>0:
                for i in self.modifications[-1]:
                    self.undo(i)
                    
                mod = self.modifications[-1]
                self.undos.append(mod)
                del self.modifications[-1]
                return "Last table modification ({}) has been undone.".format(mod[0][0])
            return "No manual modifications to the table to undo."
        
    def redo_commands(self, num):
        if num == 0: #redo all
            if len(self.undos)>0:
                for i in list(reversed(self.undos)):
                    for j in i:
                        self.redo(j)
                
                self.modifications = list(reversed(self.undos))
                self.undos = []
                return "All manual table modifications undos have been redone."
            return "No manual modification undos to redo."
        
        else: #redo last undo
            if len(self.undos)>0:
                for i in self.undos[-1]:
                    self.redo(i)
                    
                mod = self.undos[-1]
                self.modifications.append(mod)
                del self.undos[-1]
                return "Last table modification undo ({}) has been redone.".format(mod[0][0])
            return "No manual modifications undos to redo."
        
        
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
    pass
   