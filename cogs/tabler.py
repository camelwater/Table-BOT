# -*- coding: utf-8 -*-
"""
Created on Tue May 18 15:05:35 2021

@author: ryanz
"""
from bs4 import BeautifulSoup
import urllib3
import copy
from PIL import Image
from io import BytesIO
from urllib.parse import quote
import base64
import io
import aiohttp
from requests_html import AsyncHTMLSession
from urllib.request import urlopen
import datetime
import discord
from discord.ext import tasks

class Table():
    def __init__(self):
        self.URL = "https://wiimmfi.de/stats/mkwx"
        self.ROOM_URL = "https://wiimmfi.de/stats/mkwx/list/{}"
        self.current_url = ""
        self.last_race_update = None
        
        self.modifications = [] #keep track of all user modifications to the table
        self.undos = [] #keep track of all user undos of modifications to the table
        
        self.recorded_elems = [] #don't record races that have already been recorded
        self.players = {} #dictionary of players: holds their total score and their gp scores
        self.finish_times = {} #finish times of each race (used for ?rr)
        self.races = [] #list (race) of lists (placements for each race) 
        self.pens = {} # mapping players to penalties
        self.fcs = {} #map fcs to mii name (so no conflicts with mii names - uniqueness)
        self.player_ids = {} #used to map player ids to players (player id from bot)
       
        self.warnings = {} #race: list of warnings
        self.dc_list = {} # race: list of player dcs (?dcs)
        self.tracks = [] #track list
        self.dup_players = [] #in case some players have same mii name. fc: edited mii name (ex. 'Player 1' instead of 'Player')
        self.ties = {} #tied race times
        self.gp_dcs = {} #gp: list of players who have dced in gp (to ensure dc warnings are simplified in embed)
        self.dc_pts = {} #player: number of races to award +3 DC points 
        self.dc_list_ids = {} #mapping dcs to an id (used for the command ?dcs)
        
        self.room_sizes = [] #list of room sizes for different gps (check if room size increases mid-gp, to send warning message - ?changeroomsize might be necessary)
        self.room_sizes_error_affected = [[]] #races affected by mkwx messing up room sizes
        self.room_error_index = [[-1,-1]] #to update room size warnings
                   
        self.tags = {} #list of team tags and their respective players
        self.table_str = "" #argument for data (to get pic from gb.hlorenzi.com)
        self.table_img = None
        self.image_loc = '' #image uri
        
        self.format = "" #format (FFA, 2v2, etc.)
        self.teams = 0 #number of teams
        self.gps = 3 #number of total gps
        self.rxx = '' #rxx that table is watching
        self.gp = 0 #current gp
        self.num_players = 0
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
        ##### Stuff for bot instances #####
        
    
    def convert_format(self,f):
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
    
    def find_room(self,rid = None, mii = None): #TODO: rewrite html parsing for mii name search
        """
        find mkwx room using either rxx or mii name search
        """
        ret_str = ""
        type_ask = "none"
        http = urllib3.PoolManager()
        page = http.request("GET", self.URL)
        soup = BeautifulSoup(page.data, 'html.parser')
        if rid == None: #mii names

            #mii = [m.replace("_", " ") for m in mii]
            #print(mii)
            strings = list(soup.stripped_strings)
            strings = [i.lower() for i in strings]
            not_found = ""
            for m in mii:
                if m not in strings:
                    not_found+="{}, ".format(m)
            if len(not_found)>0:
                not_found = not_found[:-2]
                w = "were" if len(not_found.split(","))>1 else "was"
                return True, type_ask, "{} {} not found in any rooms. Make sure all mii names are correct.".format(not_found, w)
            
            #print(soup.get_text(separator = "\n",strip = True).replace("Private Room", ""))
            room_list = soup.get_text(separator = "\n",strip = True).replace("Private Room", "").split("Room")[1:]
            room_list = [i.split("\n") for i in room_list]

            for room in room_list:
                try:
                    h_index = room.index('HOST')
                except ValueError:
                    return True, type_ask, "An error occurred while searching for the mii names: {}.\nThis was likely an error on wiimmfi's side, and retrying the search should work.\nIf it doesn't, use the rxx search instead.".format(mii)
                room[h_index-1] = room[h_index-1]+ room[h_index]
                del room[h_index]
            matches = []
            
            for i, room in enumerate(room_list):
                lower_room = [i.lower() for i in room]
                matches.append(0)
                for p in mii:
                    if p in lower_room:
                        matches[i] +=1
            max_num = max(matches)
            if matches.count(max_num) > 1:
                type_ask = "match"
                indices = [i for i, x in enumerate(matches) if x == max_num]
                for i, ind in enumerate(indices):
                    room = room_list[ind]
                    ret_str+="{}. Room: {}\n".format(i+1, room[1])
                    ret_str+="Players in room:\n"
                    
                    for x in room[36::11]:
                        ret_str+="\t-{}\n".format(x)
                    ret_str+="\n"
                    return False, type_ask, ret_str
            else:
                room_name = room_list[matches.index(max_num)][1]
                self.rxx = room_name.upper() if len(room_name)==4 else room_name

                room_url = "https://wiimmfi.de/stats/mkwx/list/{}".format(room_name)
                page = http.request('GET', room_url)
                soup = BeautifulSoup(page.data, 'html.parser')
                if "No match found!" in list(soup.stripped_strings):
                    return True, type_ask, "The room either doesn't exist or hasn't finished at least one race yet.\nRetry the ?search command when the room has finished one race."
                else:
                    self.find_players(room_url)
                    #if len(self.players) != self.convert_format(self.format)*self.teams:
                        #return True, 'reset', "Room {} was found.\nHowever, the number of players in the room ({} players) did not match the format and teams you provided in the ?start command.\nThe tabler has been reset, and you must redo the ?start command.".format(room_name, len(self.players))
                    self.split_teams(self.format, self.teams)
                    type_ask = "confirm"
                    self.current_url = room_url
                    string = ""
                
                    counter = 1
                    if self.format[0] == 'f':
                        string+='\nFFA'
                        for p in self.players.keys():
                            string+="\n{}. {}".format(counter,p)
                            self.player_ids[str(counter)] = p
                            counter+=1          
                    else:
                        for tag in self.tags.keys():
                            if tag == "":
                                 for p in self.tags[tag]:
                                     string+="\n**NO TEAM**\n\t{}. {} ".format(counter,p.replace("*", "\*"))
                                     self.player_ids[str(counter)] = p
                                     counter+=1
                            else:   
                                string+='\n**Tag: {}**'.format(tag.replace("*", "\*"))
                                for p in self.tags[tag]:
                                    string+="\n\t{}. {}".format(counter,p.replace("*", "\*"))
                                    self.player_ids[str(counter)] = p
                                    #print(self.player_ids)
                                    counter+=1
                    string = string.replace("no name", "Player")
                    self.player_list = string
                    return False, type_ask, "Room {} found.\n{}\n\n**Is this correct?** Enter ?yes or ?no or\n?changetag <player #> <correct team> or ?tags.".format(self.rxx, string)
        
        else: #room id
            rid = rid[0]
            self.rxx = rid
            if len(rid)==4: self.rxx = self.rxx.upper()
            
            room_url = "https://wiimmfi.de/stats/mkwx/list/{}".format(rid)
            page = http.request('GET', room_url)
            soup = BeautifulSoup(page.data, 'html.parser')
            stripped = list(soup.stripped_strings)
            history_check = False
            for i in stripped:
                if "Mario Kart Wii: Match history" in i:
                    history_check = True
                    break
            if "No match found!" in stripped or not history_check:
                return True, type_ask, "The room either doesn't exist or hasn't finished at least one race yet.\nRetry the ?search command when the room has finished one race and make sure the room id is in rxx or XX00 format."
            else:
                self.find_players(room_url)
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
                        string+="\n{}. {}".format(counter,p)
                        self.player_ids[str(counter)] = p
                        counter+=1          
                else:
                    for tag in self.tags.keys():
                        if tag == "":
                             for p in self.tags[tag]:
                                 string+="\n**NO TEAM**\n\t{}. {} ".format(counter,p.replace("*", "\*"))
                                 self.player_ids[str(counter)] = p
                                 counter+=1
                        else:   
                            string+='\n**Tag: {}**'.format(tag.replace("*", "\*"))
                            for p in self.tags[tag]:
                                string+="\n\t{}. {}".format(counter,p.replace("*", "\*"))
                                self.player_ids[str(counter)] = p
                                counter+=1
                string = string.replace("no name", "Player")
                self.player_list = string
                return False, type_ask, "Room {} found.\n{}\n\n**Is this room correct?** Enter ?yes or ?no\nor ?changetag <player #> <correct team> or ?tags.".format(self.rxx, string)
    
    
    def split_teams(self, f, num_teams): #TODO: add postfix checker as well for tags
        """
        split players into teams based on tags
        """
        f = f[0]
        if not f.isnumeric():
            return
        per_team = int(f)
        teams = {} #tag: list of players
        player_copy = list(self.players.keys())
        un_players = []
        i = 0
        while i< len(player_copy):
            
            tag = ''
            matches = 1
            indx = len(player_copy[i])+1
            
            while matches != per_team:
                indx-=1
                for j in range(len(player_copy)):
                    if i!=j and player_copy[i].lower().replace("[","").replace(']','')[0:indx] == player_copy[j].lower().replace("[","").replace(']','')[0:indx]:
                        matches+=1
                        if matches == per_team: break
                
                if indx == 0: break
            
            tag = player_copy[i].replace("[","").replace(']','')[0:indx]
            if len(tag)>0 and tag[-1]=="-": 
                tag = tag[:-1]
                indx-=1
            if len(tag)==1: tag = tag.upper()
            
            temp_tag = tag
            #if tag == '': temp_tag = player_copy[i][0]
            if tag == "": 
                un_players.append(player_copy[i])
                del player_copy[i]
                continue
            x = 1
            while temp_tag in teams:
                #print(temp_tag)
                temp_tag = tag +"-"+str(x)
                x+=1
            teams[temp_tag] = []
            ind = 0
            while ind<len(player_copy):
                if tag.lower().replace("[","").replace(']','') == player_copy[ind].lower().replace("[","").replace(']','')[0:indx]: 
                    if len(teams[temp_tag])<per_team:
                        teams[temp_tag].append(player_copy[ind])
                        #player_copy.remove(p)
                        del player_copy[ind]
                        ind = 0
                        continue
                ind+=1
                
            i = 0
        
        #substring tag for 2v2s
        if per_team==2:
            i = 0
            while i<len(un_players):
                tag = ''
                longest_match = 1
                match = 0
                
                for j in range(len(un_players)):
                    m = self.lcs(un_players[i].lower().replace("[","").replace(']',''), un_players[j].lower().replace("[","").replace(']',''))
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
            #print(teams)
            for item in teams.items():
                while len(item[1])<per_team:
                    item[1].append(un_players[0])
                    del un_players[0]
        else:
            split = list(self.chunks(un_players, per_team))
            #print(split)
            for i in split:
                teams[i[0][0]] = i  
            
            
        self.tags = teams
        self.tags = dict(sorted(self.tags.items(), key=lambda item: item[0]))
        self.tags = {k.strip(): v for (k, v) in self.tags.items()}
        print()
        print(self.tags)
        
        
    def chunks(self,l, n):
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
    
    def lcs(self,S,T):
        """
        find longest common substring (for finding non-prefix tags), only used for 2v2 format right now

        Parameters
        ----------
        S : 1st string
        T : 2nd string

        Returns
        -------
        lcs_str : least common string between S and T

        """
        m = len(S)
        n = len(T)
        counter = [[0]*(n+1) for x in range(m+1)]
        longest = 0
        lcs_str = ''
        for i in range(m):
            for j in range(n):
                if S[i] == T[j]:
                    c = counter[i][j] + 1
                    counter[i+1][j+1] = c
                    if c > longest:
                        lcs_str = ''
                        longest = c
                        lcs_str+=S[i-c+1:i+1]
                    elif c == longest:
                        lcs_str+=S[i-c+1:i+1]
    
        return lcs_str
    
    def get_warnings(self):
        
        if len(self.warnings)==0:
            return "Room had no warnings or DCs. This table should be accurate."
        ret = 'Room errors that could affect the table (?dcs to fix dcs):\n'
        self.warnings = dict(sorted(self.warnings.items(), key=lambda item: item[0]))
        for i in self.warnings.items():
            ret+="     Race #{}: {}\n".format(i[0], self.tracks[i[0]-1])
            for warn in i[1]:
                ret+="       \t- {}\n".format(warn)
        
        return ret
    
    def tag_str(self):
        ret = '{}{} '.format(self.full_format(self.format), "" if self.full_format(self.format)=="FFA" else ":")
        for index, i in enumerate(list(self.tags.keys())):
            if index==len(self.tags.keys())-1:
                ret+="'{}' ".format(i)
            else:
                ret+="'{}' vs ".format(i)
        ret+="({} {})".format(len(self.races), 'race' if len(self.races)==1 else 'races')
        return ret
    
    def edit_tag_name(self, l):  
        ret = ''
        for num,e in enumerate(l):
            orig = e[0]
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
                
        return ret
            
    def full_format(self,f):
        if not f[0].isnumeric():
            return 'FFA'
        return '{}v{}'.format(int(f[0]), int(f[0]))
    

    def tracklist(self):
        ret = ''
        for i, track in enumerate(self.tracks):
            ret+='Race #{}: {}\n'.format(i+1, track)
        return ret
    
    def race_results(self,race):
        ret = ''
        x = {}
        if race==-1:
            x = self.finish_times[len(self.races)-1]
            race = len(self.races)
        else: 
            if race-1 not in self.finish_times:
                return True, "Race {} doesn't exist. The race number should be from 1-{}.".format(race, len(self.races))
            x = self.finish_times[race-1]
        count = 1 
        ret+="Race {} - {} results:\n".format(race, self.tracks[race-1])
        for i in list(x.items()):
            ret+="   {}. {} - {}\n".format(count, i[0], i[1])
            count+=1
        return False,ret
    
    def change_tag(self,player, tag):
        try:
            player = self.player_ids[player]
        except:
            return "Player id: {} not valid. It must be from {}-{}".format(player, 0,len(self.players))
        old_tag = ""
        for i in self.tags.items():
            if player in i[1]:
                old_tag = i[0]
                i[1].remove(player)
        if tag not in self.tags:
            self.tags[tag] = [player]
        else:
            self.tags[tag].append(player)
        empty_keys = [k[0] for k in list(self.tags.items()) if len(k[1])==0]
        for k in empty_keys:
            del self.tags[k]

        ret = "{} tag changed from {} to {}".format(player, old_tag, tag)  

        return ret
        
    def group_tags(self,dic):
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
        
        per_team = self.convert_format(self.format)
        if len(leftovers)>0:
            for i in self.tags.items():
                while len(i[1])!=per_team:
                    i[1].append(leftovers[0])
                    del leftovers[0]
        removal = []
        for x in self.tags.items():
            if len(x[1])==0: removal.append(x[0])
        for i in removal:
            self.tags.pop(i)
        
        return "Tags updated."
                
    def get_player_list(self):
        counter = 1
        string =''
        self.tags = dict(sorted(self.tags.items(), key=lambda item: item[0].upper()))
        if self.format[0].lower() == 'f':
            for p in list(self.players.keys()):
                string+="\n{}. {}".format(counter,p.replace("*", "\*"))
                self.player_ids[str(counter)] = p
                counter+=1
        else:
            for tag in self.tags.keys():
                if tag == "":
                     for p in self.tags[tag]:
                         string+="\n**NO TEAM**\n\t{}. {} ".format(counter,p.replace("*", "\*"))
                         self.player_ids[str(counter)] = p
                         counter+=1
                else:   
                    string+='\n**Tag: {}**'.format(tag.replace("*", "\*"))
                    for p in self.tags[tag]:
                        string+="\n\t{}. {}".format(counter,p.replace("*", "\*"))
                        self.player_ids[str(counter)] = p
                        counter+=1
        string = string.replace("no name", "Player")
        self.player_list = string
        return self.player_list
        
    def dc_list_str(self): 
        ret = "DCs in the room (you can use ?edit to correct wrong scores):\n"
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
        self.dc_list_ids[i] = (player,race)
        
    def edit(self,player, gp, score, reundo=False):
        try:
            p_indx = player
            player = self.player_ids[player]
        except:
            return "{} was not a valid player index. The index must be between 1-{}".format(player, len(self.players))
      
        try:
            if '-' in score or '+' in score:
                self.players[player][1][int(gp)-1] += int(score)
                if not reundo:
                    self.modifications.append([('?edit add', p_indx, gp,score)])
                
                    try:
                        if self.warnings[int(gp)*4-3][0] != "Scores have been manually modified by the tabler for this GP ({}).".format(gp):
                            self.warnings[int(gp)*4-3].insert(0, "Scores have been manually modified by the tabler for this GP ({}).".format(gp))
                    except:
                        self.warnings[int(gp)*4-3] = ["Scores have been manually modified by the tabler for this GP ({}).".format(gp)]
                        
                return "{} GP {} score changed to {}".format(player, gp, self.players[player][1][int(gp)-1])
            else:
                orig_score = self.players[player][1][int(gp)-1]
                self.players[player][1][int(gp)-1] = int(score)
                if not reundo:
                    self.modifications.append([('?edit change', p_indx, gp, orig_score, score)])
                
                    try:
                        if self.warnings[int(gp)*4-3][0] != "Scores have been manually modified by the tabler for this GP ({}).".format(gp):
                            self.warnings[int(gp)*4-3].insert(0, "Scores have been manually modified by the tabler for this GP ({}).".format(gp))
                    except:
                        self.warnings[int(gp)*4-3] = ["Scores have been manually modified by the tabler for this GP ({}).".format(gp)]
                        
                return "{} GP {} score changed to {}".format(player, gp, score)
        except:
            return "{} was not a valid gp. The gp number must be between 1-{}".format(gp, self.gp+1)
    
    def get_pen_player_list(self):
        counter = 1
        string =''
        self.tags = dict(sorted(self.tags.items(), key=lambda item: item[0].upper()))
        if self.format[0].lower() == 'f':
            for p in list(self.players.keys()):
                string+="\n\t{}. {} (-{})".format(counter,p.replace("*", "\*"), '0' if self.pens.get(p)==None else self.pens.get(p))
                self.player_ids[str(counter)] = p
                counter+=1
        else:
            for tag in self.tags.keys():
                if tag == "":
                     for p in self.tags[tag]:
                         string+="\n**NO TEAM**\n\t{}. {} ".format(counter,p.replace("*", "\*"))
                         self.player_ids[str(counter)] = p
                         counter+=1
                else:   
                    string+='\n**Tag: {}**'.format(tag.replace("*", "\*"))
                    for p in self.tags[tag]:
                        string+="\n\t{}. {} (-{})".format(counter,p.replace("*", "\*"), '0' if self.pens.get(p)==None else self.pens.get(p))
                        self.player_ids[str(counter)] = p
                        counter+=1
        string = string.replace("no name", "Player")
        self.player_list = string
        return self.player_list
    
    def penalty(self,player, pen, reundo=False):
        
        try:
            p_indx = player
            player = self.player_ids[player]
        except:
            return "Invalid player number {}.".format(player)
        if pen[0] == '=':
            pen = int(pen.lstrip('=').lstrip('-'))
            self.pens[player] = pen
            if not reundo:
                self.modifications.append([('?pen overwrite', p_indx, '='+str(pen))])
                
            return "{} penalty set to -{}".format(player, pen)
        
        else:
            pen = int(pen.lstrip('-'))
            if player in self.pens:
                self.pens[player]+=pen
            else:
                self.pens[player] = pen
      
            if not reundo:
                self.modifications.append([('?pen', p_indx, pen)])
            return "-{} penalty given to {}".format(pen, player)
    
    def unpenalty(self, player, unpen, reundo=False):
       
        if unpen !=None:
            unpen = int(unpen.lstrip('='))
        try:
            p_indx = player
            player = self.player_ids[player]
        except:
            return "Invalid player number {}.".format(player)
        if player not in self.pens:
            return "{} doesn't have any penalties.".format(player)
        else:
            if unpen ==None:
                orig_pen = self.pens[player]
                self.pens.pop(player)
                if not reundo:
                    self.modifications.append([('?unpen total', p_indx, orig_pen)])
                return "Penalties for {} have been removed.".format(player)
            else:
                self.pens[player] -= unpen
                if self.pens[player] == 0: self.pens.pop(player)
                if not reundo: self.modifications.append([('?unpen', p_indx, unpen)])
                return "Penalty for {} reduced by {}".format(player, unpen)

    def find_players(self,url): 
        http = urllib3.PoolManager()
        page = http.request('GET', url)
        soup = BeautifulSoup(page.data, 'html.parser')
       
        elem = soup.select('tr[id*=r]')[-1]
        next_elem = elem.findNext('tr').findNext('tr')
        
        players = []
        
        while next_elem !=None:
            miiName = next_elem.find('td', class_='mii-font').text
            if miiName == "no name": miiName = "Player"
            fc = next_elem.select('span[title*=PID]')[0].text
            
            players.append((miiName, fc))
            next_elem = next_elem.findNext('tr')
                  
        for i, fc in players:
        
            if i not in self.players:
                self.players[i] = [0,[0]*self.gps]
                self.fcs[fc] = i
                #print(i)
            else:
                if i not in self.dup_players:
                    self.dup_players.append(i)
                x = 2
                name = i
                while name in self.players:
                    name = i+"-"+str(x)
                    x+=1
                    
                self.players[name] = [0,[0]*self.gps]
                self.fcs[fc]= name
                
        for i in self.dup_players:
            if i in self.players:
                indx = list(self.fcs.values()).index(i)
                self.fcs[list(self.fcs.items())[indx][0]] = i+'-1'
                del self.players[i]
                self.players[i+'-1'] = [0,[0]*self.gps]
        
        self.room_sizes.append(len(self.players))
        self.players = dict(sorted(self.players.items(), key=lambda item: item[0]))
        print(self.players.keys())
        #self.num_players = self.convert_format(self.format)*self.teams
        #print(self.fcs)
        
    def check_name(self,name):
        if name not in self.players:
            return name
        x = 1
        new = name
        while new in self.players:
            new = name+'-'+str(x)
        return new
    
    def add_sub_player(self,player, fc):
         if len(self.players)<self.num_players:
             for ind,i in enumerate(self.dc_list[1]):
                 if "should've started with" in i:
                     print(ind,i)
                     self.dc_list[1][ind] = "{}** missing from GP 1. 18 pts for GP (mogi) or 15 pts (war).".format(player)
                     self.warnings[1][ind] = "{} missing from GP 1. 18 pts for GP (mogi) or 15 pts (war).".format(player)
                     self.dc_ids_append(player, 1)
                     if self.gp not in self.gp_dcs: self.gp_dcs[self.gp] = []
                     self.gp_dcs[self.gp].append(player)
                     break
            
         self.players[player] = [0,[0]*self.gps]
         self.fcs[fc] = player
         if "SUBS" not in self.tags:
             self.tags['SUBS'] = []
         self.tags["SUBS"].append(player)
         #self.update_player_list()
         
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
             players = [i[0] for i in self.races[raceNum-1]]
             if status == "on" or status == "during":
                 orig_status = 'on'
                 if player not in players:
                     orig_status = "before"
                     mes = self.change_room_size([[raceNum, len(self.races[raceNum-1])+1]], self_call=True)
                     print(mes)
                     self.races[raceNum-1].append((player, '—', list(self.fcs.keys())[list(self.fcs.values()).index(player)]))
                     self.finish_times[raceNum-1][player] = '—'
                     
                     if raceNum %4 != 1:
                         gp = int((raceNum-1)/4)
                         self.players[player][1][gp] -=3
                         for indx,i in enumerate(self.warnings[raceNum]):
                             if i.find(player) == 0 and ("before" in i or "missing" in i):
                                 if (4-(raceNum%4))%4 == 0:
                                     self.warnings[raceNum][indx] = "{} DCed during the race (on results). No DC points for GP {} - determined by tabler.".format(player, self.gp+1)
                                 else: 
                                     self.warnings[raceNum][indx] = "{} DCed during the race (on results). Awarding 3 DC points per race for the next {} races in GP {} ({} pts total) - determined by tabler.".format(player, (4-(raceNum%4))%4, self.gp+1, 3*(4-(raceNum%4))%4)
                         
                         for indx, i in enumerate(self.dc_list[raceNum]):
                             if i.find(player) == 0 and ("before" in i or "missing" in i):
                                 if (4-(raceNum%4))%4 == 0:
                                     self.dc_list[raceNum][indx] = "{}**  -  DCed during the race (on results). No DC points for GP {} - determined by tabler.".format(player, self.gp+1)
                                 else:    
                                     self.dc_list[raceNum][indx] = "{}**  -  DCed during the race (on results). Giving 3 DC points per race for remaining {} races in GP {} ({} pts total) - determined by tabler.".format(player, (4-(raceNum%4))%4, self.gp+1, 3*(4-(raceNum%4))%4)
                     
                     else:
                         for indx,i in enumerate(self.warnings[raceNum]):
                             if i.find(player) == 0 and ("before" in i or "missing" in i):
                                 self.warnings[raceNum][indx]="{} DCed on the first race of GP {} (blank race time). 15 DC points for GP {} - determined by tabler.".format(player, self.gp+1, self.gp+1)
                         for indx, i in enumerate(self.dc_list[raceNum]):
                             if i.find(player) == 0 and ("before" in i or "missing" in i):
                                 self.dc_list[raceNum][indx] = "{}**  -  DCed on the first race of GP {}. 15 DC points for GP {} - determined by tabler.".format(player, self.gp+1, self.gp+1)
             else:
                 orig_status = 'before'
                 if player in players:
                     orig_status = 'on'
                     mes = self.change_room_size([[raceNum, len(self.races[raceNum-1])-1]], self_call=True)
                     print(mes)
                     
                     if raceNum %4 != 1:
                         gp = int((raceNum-1)/4)
                         self.players[player][1][gp] +=3
                         
                         for indx,i in enumerate(self.warnings[raceNum]):
                             if i.find(player) == 0 and ("during" in i or "on" in i):
                                 self.warnings[raceNum][indx] = "{} DCed before race. 3 DC points per race for the next {} races in GP {} ({} pts total) - determined by tabler.".format(player, 4-(raceNum%4), self.gp+1, 3*(4-(raceNum%4)))
                         for indx, i in enumerate(self.dc_list[raceNum]):
                             if i.find(player) == 0 and ("during" in i or "on" in i):
                                 self.dc_list[raceNum][indx] = "{}**  -  DCed before race {} (missing from results). 3 pts per race for remaining races in GP {} ({} pts total) - determined by tabler.".format(player, raceNum, self.gp+1, 3*(4-(raceNum%4)))
                                            
                     else:     
                         for indx,i in enumerate(self.warnings[raceNum]):
                             if i.find(player) == 0 and ("during" in i or "on" in i):
                                 self.warnings[raceNum][indx] = "{} is missing from GP {}. 18 DC points for GP {} (mogi), 15 DC points for GP {} (war) - determined by tabler.".format(player,self.gp+1, self.gp+1, self.gp+1)                   
                         for indx, i in enumerate(self.dc_list[raceNum]):
                             if i.find(player) == 0 and ("during" in i or "on" in i):
                                 self.dc_list[raceNum][indx]="{}**  -  DCed before race {} (missing from GP {}). 18 pts for GP {} (mogi), 15 pts for GP {} (war) - determined by tabler.".format(player, raceNum,self.gp+1,self.gp+1, self.gp+1)

             mods.append(('?dcs', dc_num, orig_status, status))         
             ret+= "Changed {} DC status for race {} to '{}'.\n".format(player, raceNum, status)
         
         if not reundo and len(mods)>0: self.modifications.append(mods)
         return ret
                
                 
    def change_room_size(self, l, self_call = False, reundo=False): #TODO (unfinished) - temporarily resolved (?undo should completely resolve this)
        ret = ''
        mods = []
        for i in l:
            try:
                raceNum = int(i[0])-1
                assert(raceNum>=0)
                orig_room_size = len(self.races[raceNum]) #find way to keep track of room size that has changed (orig size should change if command previously used)
                gp = int(raceNum/4)
            except:
                ret+= "Invalid <race number>. Race number must be between 1-{}.\n".format(len(self.races))
                continue
            try:
                cor_room_size = int(i[1])
                assert(cor_room_size>0 and cor_room_size<=len(self.players) and (cor_room_size <=orig_room_size or self_call))
                
            except:
                
                if cor_room_size> orig_room_size and cor_room_size<=len(self.players):
                    ret+="Invalid <corrected room size> for race {}. The corrected room size command cannot be used to add players.\n**If a race is missing player(s) due to DCs, use the ?dcs command instead.**".format(raceNum+1)
                else:
                    ret+= "Invalid <corrected room size> for race {}. The corrected room size must be between 1-{}.\n".format(raceNum+1, len(self.players))
                continue
            
            if cor_room_size == orig_room_size:
                ret+='Changed race {} room size to {}.\n'.format(raceNum+1, cor_room_size)
                continue
            
            orig_pts = {}
            for place, p in enumerate(self.races[raceNum]):
                player = self.fcs[p[2]]
                pts = self.pts[orig_room_size][place]
                orig_pts[player] = pts
                
            
            fixed_pts = {}
            self.races[raceNum] = self.races[raceNum][:cor_room_size]
            removal = list(self.finish_times[raceNum].keys())[:cor_room_size]
            self.finish_times[raceNum] = {k : self.finish_times[raceNum][k] for k in removal}
            
            for place, p in enumerate(self.races[raceNum]):
                player = self.fcs[p[2]]
                pts = self.pts[cor_room_size][place]
                fixed_pts[player] = pts
                
            for player in list(fixed_pts.items()):
                self.players[player[0]][1][gp] += player[1] - orig_pts[player[0]]
                
            if not self_call:
                done = False
                for indx,i in enumerate(self.warnings[raceNum+1]):
                    if i.find("Room size changed to") == 0:
                        self.warnings[raceNum+1][indx] = "Room size changed to {} by the tabler for this race.".format(cor_room_size)
                        done = True
                        break
                if not done:
                    self.warnings[raceNum+1].append("Room size changed to {} by the tabler for this race.".format(cor_room_size))
        
            ret+='Changed race {} room size to {}.\n'.format(raceNum+1, cor_room_size)
            mods.append(("?changeroomsize", raceNum+1, orig_room_size, cor_room_size))
     
        if not reundo and not self_call and len(mods)>0: self.modifications.append(mods)
        return ret
            
    
    def edit_race(self, l, reundo=False):
        ret = ''
        mods = []
        for num, elem in enumerate(l):
            raceNum = elem[0]
            player =p_indx= elem[1]
            try:
                player = self.player_ids[player]
            except:
                return "The player index {} was invalid. The player id must be between 1-{}".format(player,len(self.players))
                
            correct_pos = int(elem[2])-1
            try:
                raceNum = int(raceNum)
                corresponding_rr = self.races[raceNum-1]
            except:
                return "The race number {} was invalid. It must be between 1-{}".format(raceNum, len(self.races))
            
            corresponding_rr = [self.fcs[i[2]] for i in corresponding_rr]
            #corresponding_rr = [self.fcs[i] for i in corresponding_rr]
            orig_pos = corresponding_rr.index(player)
            orig_pts = self.pts[len(corresponding_rr)][orig_pos]
            try:   
                cor_pts = self.pts[len(corresponding_rr)][int(correct_pos)]
            except:
                return "The corrected position {} was invalid. It must be a number between 1-{}".format(correct_pos, len(corresponding_rr))
            
            if orig_pos<correct_pos:
                aff = [self.fcs[self.races[raceNum-1][i][2]] for i in range(orig_pos+1,correct_pos+1)]
            else:
                aff = [self.fcs[self.races[raceNum-1][i][2]] for i in range(correct_pos,orig_pos)]
                
            aff_orig_pts = {}
            for a in aff:
                aff_orig_pts[a] = self.pts[len(corresponding_rr)][corresponding_rr.index(a)]
            
            correct_ft_order = list(self.finish_times[raceNum-1].keys())
            correct_ft_order.insert(correct_pos, correct_ft_order.pop(orig_pos))
            #correct_ft_order[correct_pos], correct_ft_order[orig_pos]= correct_ft_order[orig_pos], correct_ft_order[correct_pos]
            self.finish_times[raceNum-1] = {k : self.finish_times[raceNum-1][k] for k in correct_ft_order}
            
            #self.races[raceNum-1][correct_pos], self.races[raceNum-1][orig_pos] = self.races[raceNum-1][orig_pos], self.races[raceNum-1][correct_pos]
            self.races[raceNum-1].insert(correct_pos, self.races[raceNum-1].pop(orig_pos))

            aff_new_pts = {}
            corresponding_rr = self.races[raceNum-1]
            corresponding_rr = [self.fcs[i[2]] for i in corresponding_rr]
            
            for a in aff:
                aff_new_pts[a] = self.pts[len(corresponding_rr)][corresponding_rr.index(a)]
            
            gp = int((raceNum-1)/4)

            self.players[player][0] += (cor_pts-orig_pts)
            self.players[player][1][gp] += (cor_pts-orig_pts)

            for a in aff:
                print(a)
                print((aff_new_pts[a] - aff_orig_pts[a]))
                self.players[a][0]+= (aff_new_pts[a] - aff_orig_pts[a])
                self.players[a][1][gp] += (aff_new_pts[a] - aff_orig_pts[a])
            
            ret+='{} race {} placement changed to {}.{}'.format(player, raceNum, correct_pos+1, '\n' if num==len(l)-1 else "")
            try:
                if "Placements for this race have been manually altered by the tabler." not in self.warnings[raceNum]:
                    self.warnings[raceNum].append("Placements for this race have been manually altered by the tabler.")
            except KeyError:
                self.warnings[raceNum] = ["Placements for this race have been manually altered by the tabler."]
                
            mods.append(('?editrace', p_indx, raceNum, orig_pos+1, correct_pos+1))
     
        if not reundo and len(mods)>0: self.modifications.append(mods)
        return ret
        
    def check_updated(self):
        if self.last_race_update !=None and datetime.datetime.now() - self.last_race_update < datetime.timedelta(seconds=45): return False
        http = urllib3.PoolManager()
        page = http.request("GET", self.current_url)
        soup = BeautifulSoup(page.data, 'html.parser')
        elems = soup.select('tr[id*=r]')
        
        if len(elems)>len(self.races) and len(self.races)<self.gps*4:
            if len(self.races)!=0:
                self.last_race_update = datetime.datetime.now()
            return True
        return False
    
    @tasks.loop(seconds=5)
    async def check_mkwx_update(self):
        if self.check_updated():
            self.picture_running = True
            await self.ctx.send("Detected race finish.")
            wait_mes = await self.ctx.send("Updating scores...")
            mes = self.update_table()
            await wait_mes.edit(content="Fetching table picture. Please wait...")
            img = await self.get_table_img()
            await wait_mes.edit(content=mes)
            
            f=discord.File(fp=img, filename='table.png')
            em = discord.Embed(title=self.tag_str(), color=0x00ff6f)
            
            value_field = "[Edit this table on gb.hlorenzi.com]("+self.table_link+")"
            em.add_field(name='\u200b', value= value_field, inline=False)
            em.set_image(url='attachment://table.png')
            em.set_footer(text = self.get_warnings())
            await self.ctx.send(embed=em, file=f)
            
        if len(self.races)>=self.gps*4:
            self.check_mkwx_update.stop()
            
        self.picture_running=False
        
    def update_table(self, prnt=True):
        rID = self.rxx
        
        http = urllib3.PoolManager()
        page = http.request('GET', self.current_url)
        soup = BeautifulSoup(page.data, 'html.parser')
        
        new_races = []
        new_tracks = []
        elems = soup.select('tr[id*=r]')
        for i in elems:
            race = []
            elem = i
            if elem in self.recorded_elems:
                break
            self.recorded_elems.append(elem)
                
            try:
                track = elem.findAll('a')[-1].text
                assert(elem.findAll('a')[2] == elem.findAll('a')[-1])
                track = track[0:track.find('(')-1]
            except:
                track = "Unknown Track"
            
            new_tracks.insert(0, track)
            next_elem = elem.findNext('tr').findNext('tr')
            
            while next_elem not in elems and next_elem !=None:
                #print(next_elem)
                time = next_elem.findAll('td', align='center')[-1].text
                miiName = next_elem.find('td', class_='mii-font').text
                if miiName == "no name": miiName = "Player"
                fc = next_elem.select('span[title*=PID]')[0].text
                
                race.append((miiName, time, fc))
                next_elem = next_elem.findNext('tr')
                
            new_races.append(race)

        new_races.reverse()
        
        #make sure table doesn't record unwanted races
        if len(self.races+new_races)>self.gps*4:
            if len(self.races)>=self.gps*4:
                new_races = []
            else:
                new_races = new_races[:self.gps*4-len(self.races)]
        
        self.tracks+=new_tracks
        if len(self.tracks)>self.gps*4:
            self.tracks = self.tracks[:self.gps*4]
        
        start_room_size = len(self.players)
        
        #increment gp
        for raceNum, race in enumerate(new_races):
            if (len(self.races)+raceNum)%4 == 0 and len(self.races)+raceNum!=0: 
                self.gp+=1
                self.room_sizes.append(len(race))
                self.room_sizes_error_affected.append([])
                self.room_error_index.append([-1,-1])
                if self.gp>=self.gps: 
                    for i in self.players.values():
                        i[1].append(0)
                        
            cur_room_size = len(race)
            
            if cur_room_size < self.room_sizes[self.gp]:
                self.room_sizes[self.gp] = cur_room_size
            if cur_room_size > self.room_sizes[self.gp]:
                self.room_sizes_error_affected[self.gp].append(len(self.races)+raceNum+1)
                
                if len(self.races)+raceNum+1 not in self.warnings and self.room_error_index[self.gp][1]==-1:
                    self.warnings[len(self.races)+raceNum+1] = ["Room size increased mid-GP (race {}) from {} to {}. This is impossible unless if there was a reset, and likely an mkwx bug. Affected races: {}. Run ?changeroomsize to fix this.".format(len(self.races)+raceNum+1, self.room_sizes[self.gp], cur_room_size, self.room_sizes_error_affected[self.gp])]
                    self.room_error_index[self.gp][1] = len(self.warnings[len(self.races)+raceNum+1])-1
                    self.room_error_index[self.gp][0] = len(self.races)+raceNum+1
                else:
                    self.warnings[self.room_error_index[self.gp][0]][self.room_error_index[self.gp][1]] = ("Room size increased mid-GP (race {}) from {} to {}. This is impossible unless if there was a reset, and likely an mkwx bug. Affected races: {}. Run ?changeroomsize to fix this.".format(self.room_sizes_error_affected[self.gp][0],self.room_sizes[self.gp], cur_room_size, self.room_sizes_error_affected[self.gp])) 
                
            
            last_finish_times = {}
            
            if cur_room_size<self.num_players and len(self.races)+raceNum == 0:
                if len(self.races)+raceNum+1 not in self.warnings:
                    self.warnings[len(self.races)+raceNum+1] = []
                if len(self.races)+raceNum+1 not in self.dc_list:   
                    self.dc_list[len(self.races)+raceNum+1] = []
                    
                self.warnings[len(self.races)+raceNum+1].append("GP {} is missing player(s). GP started with {} players, but should've started with {} players.".format(self.gp+1, cur_room_size,self.num_players))
                self.dc_list[len(self.races)+raceNum+1].append("GP {} is missing player(s). GP started with {} players, but should've started with {} players.".format(self.gp+1, cur_room_size,self.num_players))
                           
            elif cur_room_size<len(self.players):
                f_codes = [i[2] for i in race]
                missing_players = []
                for i in self.fcs:
                    if i not in f_codes: missing_players.append(self.fcs[i])
                
                sub_outs = False
                if len(self.players)>self.num_players and len(missing_players)==len(self.players)-self.num_players:
                    sub_outs= True
                    
                if not sub_outs:
                    if (len(self.races)+raceNum)%4 == 0:
                        for mp in missing_players:
                            if self.gp not in self.gp_dcs or mp not in self.gp_dcs[self.gp]:
                                if len(self.races)+raceNum+1 not in self.warnings:
                                    self.warnings[len(self.races)+raceNum+1] = []
                                if len(self.races)+raceNum+1 not in self.dc_list:   
                                    self.dc_list[len(self.races)+raceNum+1] = []
                                    
                                self.warnings[len(self.races)+raceNum+1].append("{} is missing from GP {}. 18 DC points for GP {} (mogi), 15 DC points for GP {} (war).".format(mp,self.gp+1, self.gp+1, self.gp+1))
                                self.dc_list[len(self.races)+raceNum+1].append("{}**  -  DCed before race {} (missing from GP {}). 18 pts for GP {} (mogi), 15 pts for GP {} (war).".format(mp, len(self.races)+raceNum+1,self.gp+1,self.gp+1, self.gp+1))
                                self.dc_ids_append(mp, len(self.races)+raceNum+1)
                                if self.gp not in self.gp_dcs: self.gp_dcs[self.gp] = []
                                self.gp_dcs[self.gp].append(mp)
                                
                    else:
                        for mp in missing_players:
                            if self.gp not in self.gp_dcs or mp not in self.gp_dcs[self.gp]:
                                if len(self.races)+raceNum+1 not in self.warnings:
                                    self.warnings[len(self.races)+raceNum+1] = []
                                if len(self.races)+raceNum+1 not in self.dc_list:   
                                    self.dc_list[len(self.races)+raceNum+1] = []
                                    
                                self.warnings[len(self.races)+raceNum+1].append("{} DCed before race. 3 DC points per race for the next {} races in GP {} ({} pts total).".format(mp, 4-((len(self.races)+raceNum)%4), self.gp+1, 3*(4-((len(self.races)+raceNum)%4))))
                                self.dc_list[len(self.races)+raceNum+1].append("{}**  -  DCed before race {} (missing from results). 3 pts per race for remaining races in GP {} ({} pts total).".format(mp, len(self.races)+raceNum+1, self.gp+1, 3*(4-((len(self.races)+raceNum)%4))))
                                
                                self.dc_pts[mp] = 4-((len(self.races)+raceNum)%4)
                                #print("DC points:",self.dc_pts[mp])
                                self.dc_ids_append(mp, len(self.races)+raceNum+1)
                                if self.gp not in self.gp_dcs: self.gp_dcs[self.gp] = []
                                self.gp_dcs[self.gp].append(mp)
                            
            for dc in list(self.dc_pts.items()):
                    self.players[dc[0]][1][self.gp] +=3
                    self.dc_pts[dc[0]] -=1
                    if self.dc_pts[dc[0]] ==0: del self.dc_pts[dc[0]]
        
            for place,player in enumerate(race):
                time = player[1]
                fc = player[2]
                
                if fc not in self.fcs: #sub player
                    self.add_sub_player(self.check_name(player[0]), fc)
                    
                    try:
                        self.warnings[len(self.races)+raceNum+1].append("{}  -  Potential sub detected. If this player is a sub, ?changetag to correct the tag.".format(player[0]))
                    except:
                        self.warnings[len(self.races)+raceNum+1] = ["{}  -  Potential sub detected. If this player is a sub, ?changetag to correct the tag.".format(player[0])]

                miiName = self.fcs[fc]
        
                try:
                    self.players[miiName][1][self.gp] += self.pts[cur_room_size][place]
                    self.players[miiName][0] += self.pts[cur_room_size][place]
                    
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
                        
                        self.ties[len(self.races)+raceNum+1][time].append(miiName)
                    
                    if ":" in time and int(time[0:time.find(':')])>=5:
                        try:
                            self.warnings[len(self.races)+raceNum+1].append("{} had an unusually large finish time - {}.".format(miiName, time))
                        except KeyError:
                            self.warnings[len(self.races)+raceNum+1] = ["{} had an unusually large finish time - {}.".format(miiName, time)]
                    
                    last_finish_times[miiName] = time
                    assert(time!='—')
                    
                except:
                    if self.gp not in self.gp_dcs or miiName not in self.gp_dcs[self.gp]:
                        if len(self.races)+raceNum+1 not in self.warnings:
                            self.warnings[len(self.races)+raceNum+1] = []
                        if len(self.races)+raceNum+1 not in self.dc_list:   
                            self.dc_list[len(self.races)+raceNum+1] = []
                        
                        if (len(self.races)+raceNum)%4==0:
                            self.warnings[len(self.races)+raceNum+1].append("{} DCed on the first race of GP {} (on results). 15 DC points for GP {}.".format(miiName, self.gp+1, self.gp+1))
                            self.dc_list[len(self.races)+raceNum+1].append("{}**  -  DCed on the first race of GP {} (on results). 15 DC points for GP {}.".format(miiName, self.gp+1, self.gp+1))
                            
                        else: 
                            if (4-((len(self.races)+raceNum+1)%4))%4 == 0:
                                self.warnings[len(self.races)+raceNum+1].append("{} DCed during the race (on results). No DC points for GP {}.".format(miiName, self.gp+1))
                                self.dc_list[len(self.races)+raceNum+1].append("{}**  -  DCed during the race (on results). No DC points for GP {}.".format(miiName, self.gp+1))
                        
                            else:
                                self.warnings[len(self.races)+raceNum+1].append("{} DCed during the race (on results). Awarding 3 DC points per race for next {} races in GP {} ({} pts total).".format(miiName,(4-((len(self.races)+raceNum+1)%4))%4 , self.gp+1, 3*((4-((len(self.races)+raceNum+1)%4))%4)))
                                self.dc_list[len(self.races)+raceNum+1].append("{}**  -  DCed during the race (on results). Giving 3 DC points per race for remaining {} races in GP {} ({} pts total).".format( miiName, (4-((len(self.races)+raceNum+1)%4))%4, self.gp+1,3*((4-((len(self.races)+raceNum+1)%4))%4)))
                        
                            self.dc_pts[miiName] = 4-((len(self.races)+raceNum+1)%4)
                        
                        self.dc_ids_append(miiName, len(self.races)+raceNum+1)
                        if self.gp not in self.gp_dcs: self.gp_dcs[self.gp] = []
                        self.gp_dcs[self.gp].append(miiName)
                    else:
                        if len(self.races)+raceNum+1 not in self.warnings:
                            self.warnings[len(self.races)+raceNum+1] = []
                        #if len(self.races)+raceNum+1 not in self.dc_list:   
                            #self.dc_list[len(self.races)+raceNum+1] = []
                        
                        self.warnings[len(self.races)+raceNum+1].append("{} had a blank race time and was on results. If this wasn't a DC, this is an mkwx bug. Run ?changeroomsize to fix this.".format(miiName))
                        #self.dc_list[len(self.races)+raceNum+1].append("{}**  -  DCed on the first race of GP {} (on results). 15 DC points for GP {}.".format(miiName, self.gp+1, self.gp+1))
                            
                      
                        
            if len(self.races)+raceNum+1 in self.ties:
                for tie in list(self.ties[len(self.races)+raceNum+1].items()):     
                    if len(self.races)+raceNum+1 not in self.warnings:
                        self.warnings[len(self.races)+raceNum+1] = []
                    
                    self.warnings[len(self.races)+raceNum+1].append("{} had tied race times ({}). Correct any errors with ?editrace.".format(tie[1], tie[0])) 
            
            self.finish_times[len(self.races)+raceNum] = last_finish_times
            
            
        #self.players = dict(sorted(self.players.items(), key=lambda item: item[1], reverse=True))
        self.races+=new_races
        
        if prnt:
            self.table_str = self.create_string()
            print()
            print(self.table_str)
            #last_table_img = table_img
            
        return "Table updated. Room {} has finished {} {}. Last race: {}".format(rID, len(self.races), "race" if len(self.races)==1 else "races",self.tracks[len(self.races)-1])
                

    def create_string(self):
        ret = "#title {} {}".format(len(self.races), "race" if len(self.races)==1 else 'races')
        if self.format[0] == 'f':
            ret+='\nFFA'
            for p in self.players.keys():
                ret+="\n{} ".format(p)
                for num,gp in enumerate(self.players[p][1]):
                    ret+="{}".format(gp)
                    if num+1!=len(self.players[p][1]):
                        ret+='|'
                if p in self.pens:
                    ret+='-{}'.format(self.pens[p])
                
        else:
            for tag in self.tags.keys():
                if tag == "":
                    for p in self.tags[tag]:
                        ret+="\n\nNO TEAM\n{} ".format(p)
                        for num,gp in enumerate(self.players[p][1]):
                            ret+="{}".format(gp)
                            if num+1!=len(self.players[p][1]):
                                ret+='|'
                        if p in self.pens:
                            ret+='-{}'.format(self.pens[p])
                else:   
                    ret+='\n\n{}'.format(tag)
                    for p in self.tags[tag]:
                        ret+="\n{} ".format(p)
                        for num,gp in enumerate(self.players[p][1]):
                            ret+="{}".format(gp)
                            if num+1!=len(self.players[p][1]):
                                ret+='|'
                        if p in self.pens:
                            ret+='-{}'.format(self.pens[p])
                            
        ret = ret.replace("no name", "Player")
        return ret
    
    
    async def get_table_img(self):
        self.table_link = "https://gb.hlorenzi.com/table.png?data={}".format(quote(self.table_str))
        with urlopen(self.table_link) as url:
            output = BytesIO(url.read())
        
        return output
    
    def get_modifications(self):
        ret = ''
        if len(self.modifications)==0:
            ret+="No table modifications to undo."
        for i,m in enumerate(self.modifications):
            ret+='{}. {}\n'.format(i+1, m)
        return ret
    
    def get_undos(self):
        ret = ''
        if len(self.undos)==0:
            ret+="No table modification undos to redo."
        for i,u in enumerate(self.undos):
            ret+="{}. {}\n".format(i+1, u)
        return ret
    
    def undo(self, j):
        if '?edit change' == j[0] or '?edit add'==j[0]:
            if "add" in j[0]:
                self.edit(j[1], j[2], str(int(j[3])-2*int(j[3])), reundo=True)
            else:
                self.edit(j[1], j[2], str(j[3]), reundo=True)
                
        elif 'editrace' in j[0]:
            self.edit_race([[j[2], j[1], j[3]]], reundo=True)
        
        elif '?pen overwrite' == j[0] or '?pen' ==j[0]:
            self.unpenalty(j[1], str(j[2]), reundo=True)
        
        elif '?unpen' in j[0]:
            self.penalty(j[1], str(j[2]), reundo=True)
        
        elif 'dcs'in j[0]:
            self.edit_dc_status([[j[1], j[2]]], reundo=True)
        
        elif 'changeroomsize' in j[0]:
            self.change_room_size([[j[1], j[2]]], reundo=True)
        
        else:
            print("undo error:",j[0])
    
    def redo(self, j):
        if '?edit change' == j[0] or "?edit add" == j[0]:
            if "add" in j[0]:
                self.edit(j[1], j[2], str(j[3]), reundo=True)
            else:
                self.edit(j[1], j[2], str(j[4]), reundo=True)
                
        elif 'editrace' in j[0]:
            self.edit_race([[j[2], j[1], j[4]]], reundo=True)
        
        elif '?pen overwrite' == j[0] or '?pen' ==j[0]:
            self.penalty(j[1], str(j[2]), reundo=True)
        
        elif '?unpen' in j[0]:
            self.unpenalty(j[1], str(j[2]), reundo=True)
        
        elif 'dcs'in j[0]:
            self.edit_dc_status([[j[1], j[3]]], reundo=True)
        
        elif 'changeroomsize' in j[0]:
            self.change_room_size([[j[1], j[3]]], reundo=True)
        
        else:
            print("redo error:",j[0])
            
    def undo_commands(self, num): #TODO: try to clear "manually edited" warnings
        if num == 0: #undo all
            if len(self.modifications)>0:
                for i in list(reversed(self.modifications)):
                    for j in i:
                        self.undo(j)
                
                self.undos = list(reversed(self.modifications))
                self.modifications = []
                return "All manual table modifications have been undone."
            return "No manual modifications have been made to the table."
        
        elif num == -1: #undo last
            if len(self.modifications)>0:
                for i in self.modifications[-1]:
                    self.undo(i)
                    
                mod = self.modifications[-1]
                self.undos.append(mod)
                del self.modifications[-1]
                return "Last table modification ({}) has been undone.".format(mod)
            return "No manual modifications to the table have been made."
        
        else:
            if len(self.modifications)>0 and num<=len(self.modifications):
                for i in self.modifications[num-1]:
                    self.undo(i)
                    
                n = num%10
                if num%100>10 and num%100<20:
                    e_str = 'th'
                elif n == 1: e_str = "st"
                elif n==2: e_str = "nd"
                elif n==3: e_str = 'rd'
                else: e_str = 'th'
                    
                mod = self.modifications[num-1]
                self.undos.append(mod)
                del self.modifications[num-1]
                return "{}{} table modification ({}) has been undone.".format(num, e_str, mod)
            
            if len(self.modifications)<num:
                return "No such table modification number '{}'. The modification number must be between 1-{}".format(num, len(self.modifications))    
            return "No manual modifications to the table have been made."
    
    def redo_commands(self, num):
        if num == 0: #redo all
            if len(self.undos)>0:
                for i in list(reversed(self.undos)):
                    for j in i:
                        self.redo(j)
                
                self.modifications = list(reversed(self.undos))
                self.undos = []
                return "All manual table modifications undos have been redone."
            return "No manual modifications to the table have been undone."
        
        elif num == -1: #redo last undo
            if len(self.undos)>0:
                for i in self.undos[-1]:
                    self.redo(i)
                    
                mod = self.undos[-1]
                self.modifications.append(mod)
                del self.undos[-1]
                return "Last table modification undo ({}) has been redone.".format(mod)
            return "No manual modifications to the table have been undone."
        
        else: #redo specific undo
            if len(self.undos)>0 and num<=len(self.undos):
                for i in self.undos[num-1]:
                    self.redo(i)
                    
                n = num%10
                if num%100>10 and num%100<20:
                    e_str = 'th'
                elif n == 1: e_str = "st"
                elif n==2: e_str = "nd"
                elif n==3: e_str = 'rd'
                else: e_str = 'th'
                    
                mod = self.undos[num-1]
                self.modifications.append(mod)
                del self.undos[num-1]
                return "{}{} table modification undo ({}) has been redone.".format(num, e_str, mod)
            
            if len(self.undos)<num:
                return "No such table modification undo number '{}'. The modification undo number must be between 1-{}".format(num, len(self.undos))    
            return "No manual modifications to the table have been undone."

    async def lorenzi_fetch(self):
        async with aiohttp.ClientSession() as session:
            headers = {"Content-Type" : "text/plain"}
            async with session.post(self.LORENZI_WEBSITE_DATA_API, headers=headers, data=self.PAYLOAD) as resp:
                data = await resp.json()
                return data
    
if __name__ == "__main__":
    #ask()
    print()
    
    #table = Table()
    #table.format = '2'
    #table.teams = 5
    #table.find_players('https://wiimmfi.de/stats/mkwx/list/r2884087')

    #import scrapy
    #from scrapy_splash import SplashRequests
    
    

    