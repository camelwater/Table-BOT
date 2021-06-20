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
    
