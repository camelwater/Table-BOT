#old tag algorithm (testing new one right now)

import time as timer
import copy
import Utils
from os.path import commonprefix
from unidecode import unidecode
from collections import defaultdict

def split_teams(self, f, num_teams): 
        """
        split players into teams based on tags
        """
        tick=timer.time()
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
                    if i!=j and indx>0 and Utils.sanitize_uni(player_copy[i].strip().replace("[","").replace(']','')).lower()[:indx] == Utils.sanitize_uni(player_copy[j].strip().replace("[","").replace(']','')).lower()[:indx]:
                        matches+=1
                        #print(Utils.sanitize_uni(player_copy[i].strip().lower().replace("[","").replace(']',''))[:indx], Utils.sanitize_uni(player_copy[j].strip().lower().replace("[","").replace(']',''))[:indx])
                        if matches == per_team: break 
                
            tag = Utils.sanitize_tag_uni(player_copy[i].replace("[","").replace(']',''))[:indx]
            if len(tag)>0 and tag[-1]=="-": 
                tag = tag[:-1]
                indx-=1
            if len(tag)==1: tag = Utils.sanitize_uni(tag).upper()
            
            temp_tag = tag
            if tag == "": 
                post_players.append(player_copy.pop(i))
                continue
            x = 1
            #print(temp_tag, matches)
            while temp_tag in teams:
                temp_tag = tag.rstrip() +"-"+str(x)
                x+=1
            teams[temp_tag] = []
            ind = 0
            while ind<len(player_copy):
                if Utils.sanitize_uni(tag.replace("[","").replace(']','')).lower() == Utils.sanitize_uni(player_copy[ind].strip().replace("[","").replace(']','')).lower()[:indx]: 
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
                for tag, _list in teams.items():
                    if len(_list)<per_team and len(commonprefix([Utils.sanitize_uni(post_players[i].strip().lower().replace("[","").replace(']',''))[::-1], Utils.sanitize_uni(tag.lower().strip().replace("[","").replace(']',''))]))>0:
                        teams[tag].append(post_players.pop(i))
                        i = 0
                        cont = True
                        break
                # while indx>0:
                #     indx-=1
                #     for tag, _list in teams.items():
                #         if len(_list)<per_team and Utils.sanitize_uni(post_players[i].strip().lower().replace("[","").replace(']',''))[::-1][:indx][::-1] == Utils.sanitize_uni(tag.lower().strip().replace("[","").replace(']','')):
                #             teams[tag].append(post_players.pop(i))
                #             i = 0
                #             cont = True
                #             break
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
                    i_tag = Utils.sanitize_uni(post_players[i].strip().lower().replace("[","").replace(']',''))
                    j_tag = Utils.sanitize_uni(post_players[j].strip().lower().replace("[","").replace(']',''))
                    
                    if i!=j and temp_indx>0 and (i_tag[:temp_indx] == j_tag[::-1][:temp_indx][::-1]
                                                 or i_tag[:temp_indx] == j_tag[:temp_indx]):
                        
                        #print(temp_indx, post_players[i], post_players[j])
                        m_tag = Utils.sanitize_tag_uni(post_players[i].strip().replace("[","").replace(']',''))[:temp_indx]
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
                        m_tag = Utils.sanitize_tag_uni(post_players[i].strip().replace("[","").replace(']',''))[::-1][:temp_indx][::-1]
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
                    m = Utils.LCS(Utils.sanitize_uni(un_players[i].strip().lower().replace("[","").replace(']','').replace(" ", "")), Utils.sanitize_uni(un_players[j].strip().lower().replace("[","").replace(']','').replace(" ","")))
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
        
        if self.TESTING:
                L = []
                for i in teams.items():
                    L.append([i[0].lower(), list(map(lambda l: Utils.sanitize_uni(l.lower()), i[1]))])
                print(L)
                tagalgo = tagAlgo.TagAlgo(None, num_teams, per_team)
                print(tagalgo.fitness(L))

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
        print("tag algo time:",timer.time()-tick)