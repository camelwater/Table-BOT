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
import traceback


class Table():
    def __init__(self):
        self.URL = "https://wiimmfi.de/stats/mkwx"
        self.ROOM_URL = "https://wiimmfi.de/stats/mkwx/list/{}"
        self.left = 500#475.4
        self.top = 95#75.233
        self.right = self.left+900 #731
        self.bottom = self.top + 484#442
        self.current_url = ""
        
        self.players = {}
        self.pot_sub_players = {}
        self.finish_times = {}
        self.races = []
        self.warnings = {} #race: list of warnings
        self.dcs = {} # race: list of player dcs
        self.dc_players = {} #gp: list of players who have dced in gp
        self.tracks = []
        self.fcs = {}
       
        self.dup_players = [] #in case some players have same mii name fc: edited mii name (ex. 'Player 1' instead of 'Player')
        self.player_ids = {} 
        self.pens = {}
                            
        self.tags = {}
        self.table_str = ""
        self.table_img = None
        self.image_loc = ''
        
        self.format = ""
        self.teams = 0
        self.gps = 3
        self.rxx = ''
        self.gp = 0
        self.player_list = ''
        
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
    def find_room(self,rid = None, mii = None):
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
                    if len(self.players) != self.convert_format(self.format)*self.teams:
                        return True, 'reset', "Room {} was found.\nHowever, the number of players in the room ({} players) did not match the format and teams you provided in the ?start command.\nThe tabler has been reset, and you must redo the ?start command.".format(room_name, len(self.players))
                    self.split_teams(self.format, self.teams)
                    type_ask = "confirm"
                    self.current_url = room_url
                    #print("Table initiated. Watching {}".format(rID))
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
                                    #print(self.player_ids)
                                    counter+=1
                    string = string.replace("no name", "Player")
                    self.player_list = string
                    return False, type_ask, "Room {} found.\n{}\n\n**Is this correct?** Enter ?yes or ?no or\n?changetag <player #> <correct team> or ?tags.".format(room_name, string)
        
        else: #room id
            rid = rid[0]
            self.rxx = rid
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
                #print(self.convert_format(self.format)*self.teams)
                if len(self.players) != self.convert_format(self.format)*self.teams:
                        return True, 'reset', "Room {} was found.\nHowever, the number of players in the room ({}) did not match the format and teams you provided in the ?start command.\nThe tabler has been reset, and you must redo the ?start command.".format(rid, len(self.players))
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
                    if i!=j and player_copy[i].lower().replace("[","").replace(']','').replace(" ","")[0:indx] == player_copy[j].lower().replace("[","").replace(']','').replace(" ","")[0:indx]:
                        matches+=1
                        if matches == per_team: break
                
                if indx == 0: break
            tag = player_copy[i].replace("[","").replace(']','').replace(" ","")[0:indx]
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
                print(temp_tag)
                temp_tag = tag +"-"+str(x)
                x+=1
            teams[temp_tag] = []
            ind = 0
            while ind<len(player_copy):
                if tag.lower().replace("[","").replace(']','').replace(" ","") == player_copy[ind].lower().replace("[","").replace(']','').replace(" ","")[0:indx]: 
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
                    m = self.lcs(un_players[i].lower().replace("[","").replace(']','').replace(" ",""), un_players[j].lower().replace("[","").replace(']','').replace(" ",""))
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
        if len(un_players)>0 and len(un_players) <per_team:
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
        if len(self.warnings)==0:
            return "Room had no warnings or DCs. This table should be accurate."
        ret = 'Room errors that could affect the table:\n'
        for i in self.warnings.items():
            ret+="   Race #{}: {}".format(i[0], self.tracks[i[0]-1])
            for warn in i[1]:
                ret+="   \t-{}".format(warn)
    
        return ret
            
            
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
                return True, "Race {} doesn't exist. The race number should be from {}-{}.".format(race, 0, len(self.races))
            x = self.finish_times[race-1]
        count = 1 
        ret+="Race {} results:\n".format(race)
        for i in list(x.items()):
            ret+="{}. {} - {}\n".format(count, i[0], i[1])
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
                    pass
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
    
    def edit(player, gp, score): #TODO
        pass
    
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
        races = soup.get_text(separator = "\n",strip = True).split("UTC ★")[1:]
        races.reverse()
        races = [i.split("\n") for i in races]
        #print(races[0])
        for race in races:
            #print(race)
            h_index = race.index('HOST')
            race[h_index-1] = race[h_index-1]+ race[h_index]
            del race[h_index]
        #players = races[0][35::10]
        try:
            delta_index = races[0].index('Δ')+13
            players = races[0][delta_index::10]
            f_codes = races[0][delta_index-9::10]
            
        except:
            mii_index = races[0].index('Mii name')+10
            players= races[0][mii_index::10]
            f_codes = races[0][mii_index-9::10]
        
        players = ['Player' if i == 'no name' else i for i in players]
        for i, fc in zip(players, f_codes):
            
            if i == 'no name':
                i == "Player"
            
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
    
    def begin_table(self):
        #global players, last_finish_times, races
        #indx = len(self.current_url) - 1 - self.current_url[::-1].index('/')
        #rID = self.current_url[indx+1:]
        rID = self.rxx
        
        http = urllib3.PoolManager()
        page = http.request('GET', self.current_url)
        soup = BeautifulSoup(page.data, 'html.parser')
        self.races = soup.get_text(separator = "\n",strip = True).split("UTC ★")[1:]
        self.races.reverse()
        self.races = [i.split("\n") for i in self.races]
        #print(self.races)
        for race in self.races:
            #print(race)
            h_index = race.index('HOST')
            race[h_index-1] = race[h_index-1]+ race[h_index]
            del race[h_index]
        '''
        for i in races[0][35::10]:
            players[i] = [0,[0]]
        print()
        '''
        #print(self.players.keys())
        #print()
        gp = 0

        for num,race in enumerate(self.races):
            #print(race)
            #self.last_finish_times= copy.deepcopy(self.players)
            last_finish_times = {}
            
            try:
                delta_index = race.index('Δ')+13
                player_pos = race[delta_index::10]
                f_codes = race[delta_index-9::10]
                
            except:
                mii_index = race.index('Mii name')+10
                player_pos = race[mii_index::10]
                f_codes = race[mii_index-9::10]
            #f_codes = race[26::10]
            #player_pos = race[35::10]
            orig_player_pos = copy.deepcopy(player_pos)
            player_pos = ['Player' if i == 'no name' else i for i in player_pos]
            
            
            try:
                track_ind = race.index("Track:")+1
                par_ind = race[track_ind].find('(')
                self.tracks.append(race[track_ind][:par_ind].strip())
            except:
                self.tracks.append('Unknown Track')
            
            #TODO: add warnings (large finish times, ties, etc.)
            #add dcs (blank finish times, and missing players)
            #players who dc in gp added to dc_players dict so it doesn't repeat the error message
            current_room_size = len(player_pos)
            real_room_size = len(self.players)
            if current_room_size<len(self.players):
                missing_players = []
                for i in self.fcs:
                    if i not in f_codes: missing_players.append(self.fcs[i])
                if num%4 == 0:
                    for mp in missing_players:
                        if num+1 not in self.warnings:
                            self.warnings[num+1] = []
                        self.warnings[num+1].append("{} missing from GP. 15 DC points for GP {}".format(mp,gp))
                else:
                    for mp in missing_players:
                        if num+1 not in self.warnings:
                            self.warnings[num+1] = []
                        self.warnings[num+1].append("{} DCed before race. 3 DC points for the next {} races in GP {}.".format(mp, 4-(num%4), gp+1))
            if num%4==0 and num!=0: #new gp
                    gp+=1
                    self.gp = gp
                    if self.gp>=self.gps:
                        for i in self.players.values():
                            i[1].append(0)

            for player, fc in zip(player_pos, f_codes):

                if player in self.dup_players:
                    cor_name = self.fcs[fc]
                    try:
                        self.players[cor_name][1][gp] += self.pts[current_room_size][f_codes.index(fc)]
                        self.players[cor_name][0] += self.pts[current_room_size][f_codes.index(fc)]
                        last_finish_times[cor_name] = race[race.index(fc)+8]
                    except:
                        if num+1 not in self.warnings:
                            self.warnings[num+1] = []
                        self.warnings[num+1].append("{} had a blank race time. No DC points for this race.".format(cor_name))
                else:
                    if player not in self.players:
                        #print('poop')
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
                            last_finish_times[player] = race[race.index(fc)+8]
    
                        except:
                            if num+1 not in self.warnings:
                                self.warnings[num+1] = []

                            self.warnings[num+1].append("{} had a blank race time. No DC points for this race.".format(player))
                            
            self.players = dict(sorted(self.players.items(), key=lambda item: item[1], reverse=True))
            #print(self.players)
            #last_finish_times = dict(sorted(last_finish_times.items(), key =lambda item : item[1]))
            self.finish_times[num] = last_finish_times
            #for ft in list(self.finish_times.items()):
                #self.finish_times[ft[0]] = dict(sorted(self.finish_times[ft[0]].items(), key=lambda item: item[1]))
           

        #print("Race: %d"%(num+1))
        #print("Player dict:", players)
        #print("Finish times: ", last_finish_times)
        #print()
        self.table_str =  self.create_string()  
        #print("Player dict:",self.players)
        #print()
        #print("\nFinish times:",self.finish_times)
        #print()
        print(self.warnings)
        return "Table successfully started. Watching room {}.\n?pic to get table picture.".format(rID)
    
    
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
        #TODO: need to find out how to get table picture without selenium so it is much faster
        '''
        if(len(new_races)==0 and self.image_loc!=''):
            print('same table')
            
            print(self.table_str)
            #same_table = self.get_table_img(self.table_str)
            table_pic = self.get_quick_table()
            race_str = "race" if len(self.races)==1 else "races"
            return "Table updated. Room {} has finished {} {}. Last race: {}".format(rID, len(self.races), race_str,self.tracks[len(self.races)-1]), table_pic
        '''
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
            #TODO: add warnings (large finish times, ties, etc.)
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
                        #TODO: add check to ensure that DC warnings on same player doesn't repeat in same GP (only show warning on the race that the DC occurred)
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
     
   
    def create_string(self):
        ret = "#title {} races".format(len(self.races))
        if self.format[0] == 'f':
            ret+='\n-'
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
    
    
    def get_table_img(self,data):
        f_options = webdriver.FirefoxOptions()
        f_options.set_headless()
        driver = webdriver.Firefox(firefox_options=f_options,executable_path='./geckodriver.exe')
        driver.get("https://gb.hlorenzi.com/table?data={}".format(quote(data)))
        self.table_link = "https://gb.hlorenzi.com/table?data={}".format(quote(data))
        '''
        png = driver.get_screenshot_as_png()
        im = Image.open(BytesIO(png)) # uses PIL library to open image in memory
        driver.close()
        left = 500#475.4
        top = 95#75.233
        right = left+900 #731
        bottom = top + 484#442
    
        im = im.crop((left, top, right, bottom))
        #im.save('screenshot.png')
        '''
        html = driver.page_source
        soup = BeautifulSoup(html, features='lxml')
        images = soup.findAll('img')
        data = images[7]['src']
        self.image_loc = data
        #print(data)
        driver.close()
        
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


if __name__ == "__main__":
    #ask()
    
    
    #table = Table()
    #table.format = '2'
    #table.teams = 5
    #table.find_players('https://wiimmfi.de/stats/mkwx/list/r2884087')
    
    #from requests_html import HTMLSession
    #asession = HTMLSession()
    #r= asession.get("https://gb.hlorenzi.com/table")
    #r.html.render()
    
    
    
    http = urllib3.PoolManager()
    #page = http.request("GET", "https://gb.hlorenzi.com/table")
    page = http.request("GET", 'https://wiimmfi.de/stats/mkwx/list/r2896707')
    
    soup = BeautifulSoup(page.data, 'html.parser')
    #print(soup.prettify())
    
    races = []
    tracks = []
    elems = soup.select('tr[id*=r]')
    for i in elems:
        race = []
        elem = i
        
        try:
            track = elem.findAll('a')[2].text
            track = track[0:track.find('(')-1]
        except:
            track = "Unknown Track"
        
        tracks.append(track)
        next_elem = elem.findNext('tr').findNext('tr')
        
        #tr_parent = elems[0].parent
        
        #next_elem = tr_parent.findNext('tr').findNext('tr').findNext('tr')
        
        while next_elem not in elems and next_elem !=None:
            #print(next_elem)
            time = next_elem.findAll('td', align='center')[6].text
            miiName = next_elem.find('td', class_='mii-font').text
            if miiName == "no name": miiName = "Player"
            fc = next_elem.select('span[title*=PID]')[0].text
            race.append((miiName, time, fc))
            next_elem = next_elem.findNext('tr')
        races.append(race)
        #print(race[0])
        #print()
    races.reverse()
    tracks.reverse()
    #print(races[1])
    for i, track in zip(races, tracks):
        print(track)
        for place,j in enumerate(i):
            print("{}. {}\t|\t{}".format(place+1, j[0], j[1]))
        print()
    print()
    print(tracks)
    
    
    ###  x =  475.4, y = 75.233
    
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
    