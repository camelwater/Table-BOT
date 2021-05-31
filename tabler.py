# -*- coding: utf-8 -*-
"""
Created on Tue May 18 15:05:35 2021

@author: ryanz
"""
from urllib.request import urlopen
from bs4 import BeautifulSoup
import urllib3
import copy
from selenium import webdriver
from PIL import Image
from io import BytesIO
from urllib.parse import quote
import base64
import io
import aiohttp
from requests_html import AsyncHTMLSession
#TODO: need to find out how to get table picture faster (currently using requests-html : around 5 secs for picture)

class Table():
    def __init__(self):
        self.URL = "https://wiimmfi.de/stats/mkwx"
        self.ROOM_URL = "https://wiimmfi.de/stats/mkwx/list/{}"
        self.current_url = ""
        
        self.recorded_elems = [] #don't record races that have already been recorded
        self.players = {} #dictionary of players: holds total score and their gp scores
        self.finish_times = {} #finish times of each race (used for ?rr)
        self.races = []
        self.pens = {}
        self.fcs = {} #map fcs to mii name (used so no conflicts with mii names)
        self.player_ids = {} #used to map player ids to players (player id from bot)
       
        self.warnings = {} #race: list of warnings
        self.dc_list = {} # race: list of player dcs (?dcs)
        self.dc_players = {} 
        self.tracks = [] #track list
        self.dup_players = [] #in case some players have same mii name fc: edited mii name (ex. 'Player 1' instead of 'Player')
        self.ties = {} #tied race times
        self.gp_dcs = {} #gp: list of players who have dced in gp (to ensure dc warnings are simplified in embed)
        self.dc_pts = {} #player: number of races to award +3 DC points 
        self.dc_list_ids = {}
        
        self.room_sizes = [] #list of room sizes for different gps (check if room size increases mid-gp, to send warning message - ?changeroomsize might be necessary)
        self.room_sizes_error_affected = [[]] #races affected by mkwx messing up room sizes
        self.room_error_index = [(-1,-1)] #to update room size warnings
                   
        self.tags = {} #list of team tags and their respective players
        self.table_str = "" #argument for data (to get pic from gb.hlorenzi.com)
        self.table_img = None
        self.image_loc = '' #image uri
        
        self.format = ""
        self.teams = 0
        self.gps = 3
        self.rxx = ''
        self.gp = 0
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
        
    
    def convert_format(self,f):
        f = f[0]
        if not f.isnumeric():
            return 1
        return int(f)
    
    def find_room(self,rid = None, mii = None): #TODO: rewrite html parsing for mii name search
        global current_url
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
                self.rxx = room_name

                room_url = "https://wiimmfi.de/stats/mkwx/list/{}".format(room_name)
                page = http.request('GET', room_url)
                soup = BeautifulSoup(page.data, 'html.parser')
                if "No match found!" in list(soup.stripped_strings):
                    return True, type_ask, "The room either doesn't exist or hasn't finished at least one race yet.\nRetry the ?search command when the room has finished one race."
                else:
                    #begin_table(room_url)
                    self.find_players(room_url)
                    #print(self.convert_format(self.format)*self.teams)
                    #if len(self.players) != self.convert_format(self.format)*self.teams:
                        #return True, 'reset', "Room {} was found.\nHowever, the number of players in the room ({} players) did not match the format and teams you provided in the ?start command.\nThe tabler has been reset, and you must redo the ?start command.".format(room_name, len(self.players))
                    self.split_teams(self.format, self.teams)
                    type_ask = "confirm"
                    self.current_url = room_url
                    #print("Table initiated. Watching {}".format(rID))
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
                    return False, type_ask, "Room {} found.\n{}\n\n**Is this correct?** Enter ?yes or ?no or\n?changetag <player #> <correct team> or ?tags.".format(room_name, string)
        
        else: #room id
            rid = rid[0]
            self.rxx = rid
            if len(rid)==4: rid = rid.upper()
            print(rid)
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
                return False, type_ask, "Room {} found.\n{}\n\n**Is this room correct?** Enter ?yes or ?no\nor ?changetag <player #> <correct team> or ?tags.".format(rid, string)
    
    
    def split_teams(self, f, num_teams):
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
            if len(tag)==1: tag = tag.upper()
            if tag=="Player-": 
                tag = 'Player'
                indx-=1
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
        print()
        print(self.tags)
        
        
    def chunks(self,l, n):
        for i in range(0, len(l), n):
            yield l[i:i+n]
    
    #find longest common substring (for finding non-prefix tags), only used for 2v2 format right now
    def lcs(self,S,T):
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
        #print(self.warnings)
        if len(self.warnings)==0:
            return "Room had no warnings or DCs. This table should be accurate."
        ret = 'Room errors that could affect the table (?dcs to fix dcs):\n'
        for i in self.warnings.items():
            ret+="     Race #{}: {}\n".format(i[0], self.tracks[i[0]-1])
            for warn in i[1]:
                ret+="       \t- {}\n".format(warn)
        
        return ret
    
    def tag_str(self):
        ret = '{}: '.format(self.full_format(self.format))
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
                    orig = list(self.tags.keys())[int(orig)]
                except:
                    return "'{}' out of range. Number must be between 1-{}".format(orig, len(self.tags))
                data = self.tags.pop(orig)
                self.tags[new]= data
                self.update_player_list()
                ret+= "Edited tag '{}' to '{}'.{}".format(orig, new, '\n' if len(l)>1 and num <len(l)-1 else "")
            
            else:
                try:
                    data = self.tags.pop(orig)
                except:
                    string = "Tag '{}' not a valid tag. Tags are case-sensitive.\n The original tag must be one of the following:\n"
                    for i in list(self.tags.keys()):
                        string+='{}\n'.format(i)
                    return string
                self.tags[new] = data
                self.update_player_list()
                ret+= "Edited tag '{}' to '{}'.{}".format(orig, new, '\n' if len(l)>1 and num <len(l)-1 else "")
        
        return ret
            
    def full_format(self,f):
        if not f[0].isnumeric():
            return 'FFA'
        return '{}v{}'.format(int(f[0]), int(f[0]))
    

    def tracklist(self):
        ret = 'Tracks played:\n'
        for i, track in enumerate(self.tracks):
            ret+='Race {}: {}\n'.format(i+1, track)
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
        for i in self.tags.items():
            if player in i[1]:
                i[1].remove(player)
        if tag not in self.tags:
            self.tags[tag] = [player]
        else:
            self.tags[tag].append(player)
        empty_keys = [k[0] for k in list(self.tags.items()) if len(k[1])==0]
        for k in empty_keys:
            del self.tags[k]
        self.update_player_list()   
        return "{} tag changed to {}".format(player, tag)  
        
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
        self.update_player_list()
        
        return "Tags updated."
                
    def update_player_list(self):
        counter = 1
        string =''
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
        
    def edit(self,player, gp, score):
        try:
            player = self.player_ids[player]
        except:
            return "{} was not a valid player index. The index must be between 1-{}".format(player, len(self.players))
      
        try:
            if '-' or '+' in score:
                self.players[player][1][int(gp)-1] += int(score)
                return "{} GP {} score changed to {}".format(player, gp, self.players[player][1][int(gp)-1])
            else:
                self.players[player][1][int(gp)-1] = int(score)
                return "{} GP {} score changed to {}".format(player, gp, score)
        except:
            return "{} was not a valid gp. The gp number must be between 1-{}".format(gp, self.gp+1)
    
    def penalty(self,player, pen):
        pen = int(pen.lstrip('-'))
        player = self.player_ids[player]
        if player in self.pens:
            self.pens[player]+=pen
        else:
            self.pens[player] = pen
        
        return "-{} penalty given to {}".format(pen, player)
    
    def unpenalty(self, player, unpen):
        if unpen !=None:
            unpen = int(unpen)
        player = self.player_ids[player]
        if player not in self.pens:
            return "{} doesn't have any penalties.".format(player)
        else:
            if unpen ==None:
                self.pens.pop(player)
                return "Penalties for {} have been removed.".format(player)
            else:
                self.pens[player] -= unpen
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
        print(self.players.keys())
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
         self.players[player] = [0,[0]*self.gps]
         self.fcs[fc] = player
         if "SUBS" not in self.tags:
             self.tags['SUBS'] = []
         self.tags["SUBS"].append(player)
         self.update_player_list()
         
    def edit_dc_status(self,L): #TODO: change the dc_list and warnings accordingly based on what user corrects
         ret=''
         for i in L:
             try:
                 player = self.dc_list_ids[int(i[0])][0]
                 raceNum = self.dc_list_ids[int(i[0])][1]
             except:
                 if len(self.dc_list_ids)==0:
                     ret+="DC number {} was invalid. There are no DCs to edit.\n"
                 else: 
                     ret+="DC number {} was invalid. DC numbers must be between 1-{}.\n".format(i[0], len(self.dc_list_ids))
                 continue
             
             status = i[1]
             players = [i[0] for i in self.races[raceNum-1]]
             if status == "on" or status == "during":
                 if player not in players:
                     mes = self.change_room_size([[raceNum, len(self.races[raceNum-1])+1]], self_call=True)
                     print(mes)
                     self.races[raceNum-1].append((player, '—', list(self.fcs.keys())[list(self.fcs.values()).index(player)]))
                     self.finish_times[raceNum-1][player] = '—'
                     
                     if raceNum %4 != 1:
                         gp = int((raceNum-1)/4)
                         self.players[player][1][gp] -=3
                         for indx,i in enumerate(self.warnings[raceNum]):
                             if i.find(player) == 0 and ("before" in i or "missing" in i):
                                 self.warnings[raceNum][indx] = "{} DCed during the race (on results). Awarding 3 DC points per race for the next {} races in GP {} ({} pts total) - determined by tabler.".format(player, 4-(raceNum%4), self.gp+1, 3*(4-(raceNum%4)))
                         for indx, i in enumerate(self.dc_list[raceNum]):
                             if i.find(player) == 0 and ("before" in i or "missing" in i):
                                 self.dc_list[raceNum][indx] = "{}**  -  DCed during the race (on results). Giving 3 DC points per race for remaining {} races in GP {} ({} pts total) - determined by tabler.".format(player, 4-(raceNum%4), self.gp+1, 3*(4-(raceNum%4)))
                     
                     else:
                         for indx,i in enumerate(self.warnings[raceNum]):
                             if i.find(player) == 0 and ("before" in i or "missing" in i):
                                 self.warnings[raceNum][indx]="{} DCed on the first race of GP {} (blank race time). 15 DC points for GP {} - determined by tabler.".format(player, self.gp+1, self.gp+1)
                         for indx, i in enumerate(self.dc_list[raceNum]):
                             if i.find(player) == 0 and ("before" in i or "missing" in i):
                                 self.dc_list[raceNum][indx] = "{}**  -  DCed on the first race of GP {}. 15 DC points for GP {} - determined by tabler.".format(player, self.gp+1, self.gp+1)
             else:
                 if player in players:
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

                        
             ret+= "Changed {} DC status for race {} to '{}'.\n".format(player, raceNum, status)
         return ret
                
                 
    def change_room_size(self, l, self_call = False): #TODO (unfinished)
        ret = ''
        #print(l)
        for i in l:
            #print(i)
            try:
                raceNum = int(i[0])-1
                assert(raceNum>=0)
                #race_room = self.races[raceNum]
                orig_room_size = len(self.races[raceNum]) #find way to keep track of room size that has changed (orig size should change if command previously used)
                gp = int(raceNum/4)
            except:
                ret+= "Invalid <race number>. Race number must be between 1-{}.\n".format(len(self.races))
                continue
            try:
                cor_room_size = int(i[1])
                assert(cor_room_size>0 and cor_room_size<=len(self.players) and cor_room_size <=orig_room_size)
                
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
            #print(self.races[raceNum])
            for place, p in enumerate(self.races[raceNum]):
                player = self.fcs[p[2]]
                pts = self.pts[orig_room_size][place]
                orig_pts[player] = pts
                
            
            fixed_pts = {}
            self.races[raceNum] = self.races[raceNum][:cor_room_size]
            removal = list(self.finish_times[raceNum].keys())[:cor_room_size]
            self.finish_times[raceNum] = {k : self.finish_times[raceNum-1][k] for k in removal}
            #print(len(self.finish_times[raceNum]))
            
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
        return ret
            
    
    def edit_race(self, l):
        ret = ''
        for num, elem in enumerate(l):
            raceNum = elem[0]
            player = elem[1]
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
            
            corresponding_rr = [i[2] for i in corresponding_rr]
            corresponding_rr = [self.fcs[i] for i in corresponding_rr]
            orig_pos = corresponding_rr.index(player)
            orig_pts = self.pts[len(corresponding_rr)][orig_pos]
            try:   
                cor_pts = self.pts[len(corresponding_rr)][int(correct_pos)]
            except:
                return "The corrected position {} was invalid. It must be a number between 1-{}".format(correct_pos, len(corresponding_rr))
            
            correct_ft_order = list(self.finish_times[raceNum-1].keys())
            correct_ft_order[correct_pos], correct_ft_order[orig_pos]= correct_ft_order[orig_pos], correct_ft_order[correct_pos]
            self.finish_times[raceNum-1] = {k : self.finish_times[raceNum-1][k] for k in correct_ft_order}
            
            self.races[raceNum-1][correct_pos], self.races[raceNum-1][orig_pos] = self.races[raceNum-1][orig_pos], self.races[raceNum-1][correct_pos]
            
            gp = int((raceNum-1)/4)
            #print(cor_pts-orig_pts)
            
            self.players[player][0] += (cor_pts-orig_pts)
            self.players[player][1][gp] += (cor_pts-orig_pts)

            aff = self.fcs[self.races[raceNum-1][orig_pos][2]]
            self.players[aff][0] += (orig_pts-cor_pts)
            self.players[aff][1][gp] += (orig_pts-cor_pts)
            
            
            ret+='{} race {} placement changed to {}{}'.format(player, raceNum, correct_pos+1, '\n' if num==len(l)-1 else "")
            
        return ret
        
    def update_table(self):
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
        
        #self.races.reverse()
        #self.tracks.reverse()
        self.tracks+=new_tracks
        if len(self.tracks)>self.gps*4:
            self.tracks = self.tracks[:self.gps*4]
        
        real_room_size = len(self.players)
        
        #increment gp
        for raceNum, race in enumerate(new_races):
            if (len(self.races)+raceNum)%4 == 0 and len(self.races)+raceNum!=0: 
                self.gp+=1
                self.room_sizes.append(len(self.players))
                self.room_sizes_error_affected.append([])
                self.room_error_index.append((-1,-1))
                if self.gp>=self.gps: 
                    for i in self.players.values():
                        i[1].append(0)
                        
            cur_room_size = len(race)
            
            
            if cur_room_size < self.room_sizes[self.gp]:
                self.room_sizes[self.gp] = cur_room_size
            if cur_room_size > self.room_sizes[self.gp]:
                self.room_sizes_error_affected[self.gp].append(len(self.races)+raceNum+1)
                
                if len(self.races)+raceNum+1 not in self.warnings and self.room_error_index[self.gp][1]!= -1:
                    self.warnings[len(self.races)+raceNum+1] = ["Room size increased mid-GP (race {}) from {} to {}. This is impossible unless if there was a reset, and likely an mkwx bug. Affected races: {}. Run ?changeroomsize to fix this.".format(len(self.races)+raceNum+1, self.room_size[self.gp], cur_room_size, self.room_sizes_error_affected[self.gp])]
                    self.room_error_index[self.gp][1] = len(self.warnings[len(self.races)+raceNum+1])
                    self.room_error_index[self.gp][0] = len(self.races)+raceNum+1
                else:
                    self.warnings[self.room_error_index[self.gp][0]][self.room_error_index[self.gp][1]] = ("Room size increased mid-GP (race {}) from {} to {}. This is impossible unless if there was a reset, and likely an mkwx bug. Affected races: {}. Run ?changeroomsize to fix this.".format(len(self.races)+raceNum+1,self.room_size[self.gp], cur_room_size, self.room_sizes_error_affected[self.gp])) 
                
            
            last_finish_times = {}
            
            if cur_room_size<real_room_size:
                f_codes = [i[2] for i in race]
                missing_players = []
                for i in self.fcs:
                    if i not in f_codes: missing_players.append(self.fcs[i])
                
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
                            self.dc_ids_append(mp, len(self.races)+raceNum+1)
                            if self.gp not in self.gp_dcs: self.gp_dcs[self.gp] = []
                            self.gp_dcs[self.gp].append(mp)
        
            for place,player in enumerate(race):
                time = player[1]
                fc = player[2]
                
                if fc not in self.fcs: #sub
                    self.add_sub_player(self.check_name(player[0]), fc)
                    
                    try:
                        self.warnings[len(self.races)+raceNum+1].append("{}  -  Potential sub detected. If this player is a sub, ?changetag to correct the tag.".format(player[0]))
                    except:
                        self.warnings[len(self.races)+raceNum+1] = ["{}  -  Potential sub detected. If this player is a sub, ?changetag to correct the tag.".format(player[0])]

                
                miiName = self.fcs[fc]
                
                for dc in list(self.dc_pts.items()):
                    self.players[dc[0]][1][self.gp] +=3
                    self.dc_pts[dc[0]] -=1
                    if self.dc_pts[dc[0]] ==0: del self.dc_pts[dc[0]]
                
                
        
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
                            self.warnings[len(self.races)+raceNum+1].append("{} DCed during the race (on results). Giving 3 DC points per race for next {} races in GP {} ({} pts total).".format(miiName,4-((len(self.races)+raceNum+1)%4) , self.gp+1, 3*(4-((len(self.races)+raceNum+1)%4))))
                            self.dc_list[len(self.races)+raceNum+1].append("{}**  -  DCed during the race (on results). Giving 3 DC points per race for remaining {} races in GP {} ({} pts total).".format( miiName, 4-((len(self.races)+raceNum+1)%4), self.gp+1, 3*(4-((len(self.races)+raceNum+1)%4))))
                        
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
                    
                    self.warnings[len(self.races)+raceNum+1].append("{} had tied race times ({}). Check GP picture to correct any errors with ?editrace.".format(tie[1], tie[0])) 
            
            self.finish_times[len(self.races)+raceNum] = last_finish_times
            
            
        self.players = dict(sorted(self.players.items(), key=lambda item: item[1], reverse=True))
        self.races+=new_races
        
        self.table_str = self.create_string()
        print()
        #print(self.warnings)
        #print()
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
        import time
        '''
        f_options = webdriver.FirefoxOptions()
        f_options.set_headless()
        driver = webdriver.Firefox(firefox_options=f_options,executable_path='./geckodriver.exe')
        driver.get("https://gb.hlorenzi.com/table?data={}".format(quote(data)))
        '''
        self.table_link = "https://gb.hlorenzi.com/table?data={}".format(quote(self.table_str))
        asession = AsyncHTMLSession()
        
        r = await asession.get(self.table_link)
        
        tick = time.time()
        await r.html.arender(timeout=15)
        print("JS render time:", time.time()-tick)
        image = r.html.find('img')[7]
        #print(images)
        data = image.attrs['src']
        #print(data)
        
        #html = driver.page_source
        #soup = BeautifulSoup(html, features='lxml')
        #images = soup.findAll('img')
        #data = images[7]['src']
        self.image_loc = data
        #driver.close()
        
        im = Image.open(io.BytesIO(base64.b64decode(data.split(',')[1])))
        output = BytesIO()
        im.save(output, format="png")
        output.seek(0)
        self.table_img = output
        return output
    
    def get_quick_table(self):
        im = Image.open(io.BytesIO(base64.b64decode(self.image_loc.split(',')[1])))
        output = BytesIO()
        im.save(output, format="png")
        output.seek(0)
        self.table_img = output
        return output
    
    async def fetch(self,url, headers=None):
        async with aiohttp.ClientSession() as session:
            if headers == None:
                async with session.get(url) as response:
                    return await response.text()
            else:
                async with session.get(url, headers=headers) as response:
                    return await response.text()

if __name__ == "__main__":
    #ask()
    print()
    
    #table = Table()
    #table.format = '2'
    #table.teams = 5
    #table.find_players('https://wiimmfi.de/stats/mkwx/list/r2884087')
    
    #from requests_html import HTMLSession
    #asession = HTMLSession()
    #r= asession.get("https://gb.hlorenzi.com/table")
    #r.html.render()
    import scrapy
    from scrapy_splash import SplashRequests
    
    
    
    #payload = {'data':"%23title%2012%20races%0AFFA%0ARushW%20%5Bus%5D%2036%7C15%7C29%0AWolf%2029%7C7%7C40%0AEdison%20%5Bus%5D%2022%7C44%7C14%0AHenryUS%20%5Btk%5D%2018%7C34%7C27%0Ashamron%2038%7C36%7C25%0AFM72%2017%7C20%7C13%0AZn%20%5Bbr%5D%2015%7C15%7C25%0ACamelot%2027%7C32%7C18%0ASchwoz%20%5Bau%5D%2026%7C15%7C35%0AzachUK%20%5Bgb%5D%2016%7C22%7C19%0ASword%2017%7C33%7C33%0AUkemu%2031%7C13%7C14%0A"}
    #r = requests.get('https://gb.hlorenzi.com/table', params=payload)
    #print(r.text)
    
    
    ###  x =  475.4, y = 75.233
    
    
    
    
'''
    def update_table(self):
        #global players, last_finish_times, races, table_img, table_str, last_table_img
        #indx = len(self.current_url) - 1 - self.current_url[::-1].index('/')
        #rID = self.current_url[indx+1:]
        rID = self.rxx
        
        http = urllib3.PoolManager()
        page = http.request('GET', self.current_url)
        soup = BeautifulSoup(page.data, 'html.parser')
        new_races = soup.get_text(separator = "\n",strip = True).split("UTC ★")[1:]
        new_races.reverse()
        new_races = new_races[len(self.races):]
        new_races = [i.split("\n") for i in new_races]
        #print(new_races)
        for race in new_races:
            #print(race)
            h_index = race.index('HOST')
            race[h_index-1] = race[h_index-1]+ race[h_index]
            del race[h_index]
            
        
        #self.gp = (len(self.races)+1)/4
        
        if(len(new_races)==0 and self.image_loc!=''):
            print('same table')
            
            print(self.table_str)
            #same_table = self.get_table_img(self.table_str)
            table_pic = self.get_quick_table()
            race_str = "race" if len(self.races)==1 else "races"
            return "Table updated. Room {} has finished {} {}. Last race: {}".format(rID, len(self.races), race_str,self.tracks[len(self.races)-1]), table_pic
        
        gp = self.gp
        for num,race in enumerate(new_races):
            last_finish_times = {}
            #player_pos = race[35::10]
            try:
                delta_index = race.index('Δ')+13
                player_pos = race[delta_index::10]
                f_codes = race[delta_index-9::10]
                
            except:
                mii_index = race.index('Mii name')+10
                player_pos = race[mii_index::10]
                f_codes = race[mii_index-9::10]
            #print(player_pos)
            player_pos = ['Player' if i == 'no name' else i for i in player_pos]
            #f_codes = race[26::10]
            
            try:
                track_ind = race.index("Track:")+1
                par_ind = race[track_ind].find('(')
                self.tracks.append(race[track_ind][:par_ind].strip())
            except:
                self.tracks.append('Unknown Track')
            
            room_size = len(self.players)
            current_room_size = len(player_pos)
             add warnings (large finish times, ties, etc.)
            #add dcs (blank finish times, and missing players)
            #players who dc in gp added to dc_players dict so it doesn't repeat the error message
            #add mergeroom and removerace commands 
            if len(player_pos)<len(self.players):
                missing_players = []
                for i in self.players:
                    if i not in player_pos: missing_players.append(i)
                if num%4 == 0:
                    for mp in missing_players:
                        if len(self.races)+num+1 not in self.warnings:
                            self.warnings[len(self.races)+num+1] = []
                        self.warnings[len(self.races)+num+1].append("{} missing from GP. 15 DC points for GP {}".format(mp,gp))
                else:
                    for mp in missing_players:
                        add = False
                         add check to ensure that DC warnings on same player doesn't repeat in same GP (only show warning on the race that the DC occurred)
                        if len(self.races)+num+1 not in self.warnings:
                            self.warnings[len(self.races)+num+1] = []
                        self.warnings[len(self.races)+num+1].append("{} DCed before race. 3 DC points for the next {} races in GP {}.".format(mp, 4-(num%4), gp+1))
            if (len(self.races)+num)%4==0 and (len(self.races))!=0: #new gp
                    gp+=1
                    self.gp+=1
                    if self.gp>=self.gps:
                        for i in self.players.values():
                            i[1].append(0)
            indx = -1
            for player, fc in zip(player_pos, f_codes):
                indx+=1
                if player in self.dup_players:
                    #print(self.fcs)
                    cor_name = self.fcs[fc]
                    try:
                        self.players[cor_name][1][gp] += self.pts[current_room_size][f_codes.index(fc)]
                        self.players[cor_name][0] += self.pts[current_room_size][f_codes.index(fc)]
                        
                        last_finish_times[cor_name] = race[race.index(fc)+8]
                        
                    except:
                        if len(self.races)+num+1 not in self.warnings:
                            self.warnings[len(self.races)+num+1] = []
                        #print("AOSIDJ")
                        self.warnings[len(self.races)+num+1].append("{} had a blank race time. No DC points for this race.".format(cor_name))
                        
                else:
                    if player not in self.players:
                        
                        player = self.check_name(player)
                        self.sub_players.append(player)
                        self.add_sub_player(player)
                        try:
                            self.players[player][1][gp] += self.pts[current_room_size][f_codes.index(fc)]
                            self.players[player][0] += self.pts[current_room_size][f_codes.index(fc)]
                            last_finish_times[player] = race[race.index(fc)+8]
                            self.warnings[len(self.races)+num+1].append("Potential sub detected: {}. If this player is a sub, run ?sub to fix the table.".format(player))
                        except:
                            if len(self.races)+num+1 not in self.warnings:
                                self.warnings[len(self.races)+num+1] = []
                            #print("AOSIDJ 2222")
                            self.warnings[len(self.races)+num+1].append("{} had a blank race time. No DC points for this race.".format(player))
                    else:   
                        try:
                            self.players[player][1][gp] += self.pts[current_room_size][player_pos.index(player)]
                            self.players[player][0] += self.pts[current_room_size][player_pos.index(player)]
                            #if player == 'Player': print("aksjdhalsdkj")
                            last_finish_times[player] = race[race.index(fc)+8]
                        except:
                            if len(self.races)+num+1 not in self.warnings:
                                self.warnings[len(self.races)+num+1] = []

                            self.warnings[len(self.races)+num+1].append("{} had a blank race time. No DC points for this race.".format(player))
                
            self.players = dict(sorted(self.players.items(), key=lambda item: item[1], reverse=True))
            #for ft in list(self.finish_times.items()):
                #self.finish_times[ft[0]] = dict(sorted(self.finish_times[ft[0]].items(), key=lambda item: item[1]))
            #last_finish_times = dict(sorted(self.last_finish_times.items(), key = lambda item: item[1]))
            self.finish_times[len(self.races)+num]= last_finish_times
            
            #print("Race: %d"%(num+1))
            #print("Player dict:", players)
        if len(new_races)>0:
            self.races+=new_races    
        self.table_str = self.create_string()
        print()
        print(self.warnings)
        print()
        print(self.table_str)
        self.table_img = self.get_table_img(self.table_str)
        #last_table_img = table_img
        #print(last_table_img)
        return "Table updated. Room {} has finished {} {}. Last race: {}".format(rID, len(self.races), "race" if len(self.races)==1 else "races",self.tracks[len(self.races)-1]), self.table_img
'''
    
'''
def ask():
    http = urllib3.PoolManager()
    page = http.request('GET', URL)
    soup = BeautifulSoup(page.data, 'html.parser')
    print("-rid rxxxxxx\t-mii NAME, NAME2")
    search = ""
    done = False
    while not done:
        identify = input("Enter one or mutiple player mii names (separate by comma), or room id: ").lower().strip()
        indx = identify.find(" ")
        if identify == 'q':
            done = True
            return
        elif identify[1:indx] == "rid":
            search = "room"
            identify = identify[indx+1:]
            if identify[0] !='r':
                print("invalid room id. room id's begin with an 'r'")
            else: 
                done = True
        elif identify[1:indx] == "mii":
            search = "player"
            if ',' in identify[indx+1:]:
                identify = identify.split(',')
                identify = [i.strip() for i in identify]
            done = True
        else:
            print("That is an unrecognized command. Use '-rid' or '-mii' or 'q' to break.")
            
    
    
    #print(len(room_list))
    if search == 'room':
        room_url = "https://wiimmfi.de/stats/mkwx/list/{}".format(identify)
        page = http.request('GET', room_url)
        soup = BeautifulSoup(page.data, 'html.parser')
        #print(list(soup.stripped_strings))
        if "No match found!" not in list(soup.stripped_strings):
            begin_table(room_url)
        else:
            print("There is no room with that room id. Make sure the id is correct and that the room has finished at least one race.")
    else:
        room_list = soup.get_text(separator = "\n",strip = True).split("Room")[1:]
        room_list = [i.split("\n") for i in room_list]
        for room in room_list:
            h_index = room.index('HOST')
            room[h_index-1] = room[h_index-1]+ room[h_index]
            del room[h_index]
        matches = []
        for i, room in enumerate(room_list):
            matches.append(0)
            for p in identify:
                if p in room:
                    matches[i] +=1
        max_num = max(matches)
        if matches.count(max_num) > 1:
            
            doneInput = False
            while not doneInput:
                print("Your player mii name argument(s) yielded {} matching rooms. Choose the correct room.".format(matches.count(max_num)))
                indices = [i for i, x in enumerate(matches) if x == max_num]
                for i, ind in enumerate(indices):
                    room = room_list[ind]
                    print("{}. Room:{}".format(i+1, room[1]))
                    print("Players in room: ", end = "")
                    
                    for x in room[36::11]:
                        print(x, sep=", ")
                    print("\n")
                    
                _input = input("Enter the room number: ").strip().lower()
                if not _input.isnumeric():
                    print("Please enter a number")
                elif int(_input) not in indices:
                    print("enter a number that is shown in the list.")
                else:
                    doneInput = True
                    into_link(room_list[int(_input)][1])
        else:
            into_link(room_list[matches.index(max_num)][1])
'''
    