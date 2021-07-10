import Utils
from os.path import commonprefix
from collections import defaultdict
import copy
import random as rand

def find_substring_tags(un_players, teams): #unused right now (maybe should bring it back)
    i = 0
    while i<len(un_players):
        tag = ''
        longest_match = 1
        match = 0
        
        for j in range(len(un_players)):
            m = Utils.LCS(Utils.sanitize_uni(un_players[i].strip().lower()), Utils.sanitize_uni(un_players[j].strip().lower()))
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

def count_pre_tags(tag, players):
    count= 0
    for p in players:
        if Utils.sanitize_uni(p.strip()).lower().startswith(Utils.sanitize_uni(tag.strip()).lower()):
            count+=1
    return count

def sort_tags(tag, players, per_team):
    if isinstance(tag, tuple):
        tag = tag[0]

    pre_count = count_pre_tags(tag, players)
    post_count = len(players)-pre_count
    if pre_count==per_team:
        return per_team+1

    if post_count==per_team:
        return per_team

    return pre_count

def clean_overlaps(all_tags):
    to_remove = []
    for tag, players in all_tags.items():
            for tag2, players2 in all_tags.items():
                    if tag!=tag2 and players2.issubset(players) and len(tag2)<len(tag) and \
                    (tag.lower().strip().startswith(tag2.lower().strip()) or tag.lower().strip().endswith(tag2.lower().strip())):
                        if tag2 not in to_remove:
                            to_remove.append(tag2)
    
    for r in to_remove:
        all_tags.pop(r)

    
def check_other_overlaps(players, tag, all_tags, per_team):
    def more_prefix(players, tag):
        return count_pre_tags(tag, players) >= int(len(players)/2)
    def more_suffix(players, tag):
        return count_pre_tags(tag, players) < int(len(players)/2)
    
    def overlaps(p):
        num_overlaps = 0
        for x, x_players in all_tags.items():
            if x==tag: continue
            if p in x_players and len(x_players)==per_team:
                num_overlaps+=1
        return num_overlaps

    if len(players)<=per_team: return

    non_overlapped = [i for i in players if overlaps(i)==0]
    if len(non_overlapped)==per_team:
        for i in copy.copy(players):
            if i not in non_overlapped:
                all_tags[tag].discard(i)

    for comp_tag, tag_p in all_tags.items():
        if comp_tag == tag:
            continue
        if isinstance(comp_tag, tuple): 
            comp_tag = comp_tag[0]
        iter = sorted(list(players), key=lambda l: (0 if overlaps(l)==1 else 1, 1 if Utils.sanitize_uni(l.strip()).lower().startswith(Utils.sanitize_uni(tag.strip()).lower()) else 0))
        for p in iter:
            if p in tag_p and len(tag_p) == per_team:
                if Utils.sanitize_uni(p.strip()).lower().startswith(Utils.sanitize_uni(comp_tag.strip()).lower()) \
                    and not Utils.sanitize_uni(p.strip()).lower().startswith(Utils.sanitize_uni(tag.strip()).lower()) \
                        and more_prefix(all_tags[comp_tag], comp_tag) and not more_suffix(all_tags[tag], tag):
                    if overlaps(p)==1:
                        all_tags[tag].discard(p)
                    else:
                        all_tags[tag].discard(p)
                        if len(all_tags[tag])<=per_team:
                            return

                elif Utils.sanitize_uni(p.strip()).lower().endswith(Utils.sanitize_uni(comp_tag.strip()).lower()) \
                    and not Utils.sanitize_uni(p.strip()).lower().endswith(Utils.sanitize_uni(tag.strip()).lower()) \
                        and more_suffix(all_tags[comp_tag], comp_tag) and not more_prefix(all_tags[tag], tag):
                    if overlaps(p)==1:
                        all_tags[tag].discard(p)
                    else:
                        all_tags[tag].discard(p)
                        if len(all_tags[tag])<=per_team:
                            return

    # for comp_tag, tag_p in all_tags.items():
    #     if comp_tag == tag:
    #         continue
    #     for p in copy.copy(players):
    #         if p in tag_p and len(tag_p) == per_team:
    #             all_tags[tag].discard(p)

    #             if len(all_tags[tag])<=per_team:
    #                 return

def try_split_by_actual(players, tag, per_team, all_tags):
    diff_actual_players = []
    for p in players:
        if not (p.strip().lower().startswith(tag.lower()) or p.strip().lower().endswith(tag.lower())):
            diff_actual_players.append(p)
    if len(diff_actual_players)>=per_team:
        diff_actual_players = diff_actual_players[:per_team]
        for i in diff_actual_players:
            all_tags[tag].discard(i)
            #players.discard(i)

        all_tags[Utils.sanitize_tag_uni(commonprefix(diff_actual_players))] = set(diff_actual_players)
    
        
def try_split_chunks(players, tag, per_team, all_tags):
    def post_id(p):
        if Utils.sanitize_uni(p.strip()).lower().startswith(Utils.sanitize_uni(tag.strip()).lower()):
            return 0
        return 1
    pre = []
    post = []
    mash = []
    if len(players)<=per_team:
        return
    indx = (int(len(players)/per_team)-1)*per_team
    players = sorted(list(players), key=lambda l: post_id(l), reverse=True)
    if indx == 0: indx = 1
    for p in (players)[indx:]:
        if Utils.sanitize_uni(p.strip()).lower().startswith(tag.lower()):
            pre.append(p)
        else:
            post.append(p)
    
    all_tags[tag] = set(players[:indx])
    while len(pre)%per_team!=0:
        mash.append(pre.pop(-1))
    while len(post)%per_team!=0:
        mash.append(post.pop(-1))
    pre_chunks = list(Utils.chunks(pre, per_team))
    post_chunks = list(Utils.chunks(post, per_team))

    for g in pre_chunks+post_chunks+[mash]:
        if len(g)==0: continue
        a = 1
        temp = tag
        while temp in all_tags:
            temp = (tag, a) #tuple for duplicate tags (a bit annoying)
            a+=1
        all_tags[temp] = g


def try_find_most_pre(players, tag, per_team, all_tags):
    prefix_players = []
    non_pre_players = []
    if len(players)<=per_team:
        return
    for p in players:
        if Utils.sanitize_uni(p.strip()).lower().startswith(Utils.sanitize_uni(tag.strip()).lower()):
            prefix_players.append(p)
        else:
            non_pre_players.append(p)

    if set(non_pre_players) == players:
        return

    if len(non_pre_players)>=per_team and len(players)-len(non_pre_players)>=per_team:
        all_tags[Utils.sanitize_tag_uni(commonprefix(map(lambda o: o[::-1],list(non_pre_players))))] = non_pre_players
    elif 0 < len(non_pre_players) < per_team:
        while len(all_tags[tag])>per_team and len(non_pre_players)>0:
            all_tags[tag].discard(non_pre_players.pop(0))

def handle_undetermined(teams, un_players, per_team):

    #substring tag for 2v2s check
    # if len(un_players)>0 and per_team==2:
    #     find_substring_tags(un_players, teams)

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

    #randomly tag the rest (tag could not be determined)
    if len(un_players)>0:
        is_all_filled = True
        for item in teams.items():
                if len(item[1])<per_team:
                    is_all_filled = False
                    break
        
        if not is_all_filled:
            for item in teams.items():
                while len(item[1])<per_team and len(un_players)>0:
                    item[1].append(un_players.pop(0))
            if len(un_players)>0:
                split()
        else:
            split()   

def assert_correct(teams, un_players, per_team, num_teams, num_teams_supposed):
    found_num_teams = len(teams)
    corrupt_tags = []
    
    for tag, players in teams.items():
        if len(players)>per_team:
            corrupt_tags.append(tag)

    if ((found_num_teams==num_teams or found_num_teams == num_teams_supposed) or 
        ((found_num_teams<num_teams and len(un_players)>=(per_team*num_teams)) 
        or (found_num_teams<num_teams_supposed and len(un_players)>=(per_team*num_teams_supposed))))\
        and len(corrupt_tags)==0:
        return
    if num_teams!=num_teams_supposed and len(corrupt_tags)==0:
        return

    while len(teams)>num_teams:
        for i in teams.items():
            print(teams)
            if len(i[1])!=per_team:
                popped = teams.pop(i[0])
                try:
                    un_players.extend(popped)
                except:
                    pass
                break
    
    for tag in corrupt_tags:
        tag_players = teams[tag]
        while len(tag_players)>per_team:
            del_player = rand.choice(tag_players)
            if del_player not in un_players:
                un_players.append(del_player)
            teams[tag].remove(del_player)


def select_tops(all_tags, per_team, num_teams, num_teams_supposed, teams, players):
    for tag, tag_players in copy.deepcopy(all_tags).items():
        tag_players = all_tags[tag]
        if len(tag_players)>per_team:
            try_split_by_actual(tag_players, tag, per_team, all_tags)
            check_other_overlaps(tag_players, tag, all_tags, per_team) 
            #try_find_most_pre(tag_players, tag, per_team, all_tags)
            try_split_chunks(tag_players, tag, per_team, all_tags)
        if len(tag_players)>per_team:   
            while len(tag_players)>per_team: #just randomly get rid of someone - either the format is wrong or the players tags are bad (and impossible to get completely correct)
                tag_players.discard(rand.choice(list(tag_players)))
    
    for _ in range(num_teams_supposed):
        for x in copy.deepcopy(all_tags).items():
            for player in x[1]:
                if player not in players:
                    all_tags[x[0]].remove(player)
            if len(all_tags[x[0]]) == 0:
                all_tags.pop(x[0])
        if len(all_tags)==0:
            break
        all_tags = dict(sorted(all_tags.items(), key=lambda item: (len(item[1]), sort_tags(item[0],item[1], per_team)), reverse=True))
        teams[list(all_tags.keys())[0]] = list(all_tags[list(all_tags.keys())[0]])
        for p in all_tags[list(all_tags.keys())[0]]:
            try:
                players.remove(p)
            except:
                pass
        all_tags.pop(list(all_tags.keys())[0])

def clean_tags(teams):
    def check_tag(t, add_self=False):
        count = 0
        for i in list(teams.keys()):
            if isinstance(i, tuple): 
                i = i[0]+'-'+str(i[1])
            if i.strip().lower() == t.strip().lower(): count+=1
        if add_self:count+=1 
        return count>1

    new_tags = []
    for ind, tag in enumerate(list(teams.keys())):
        if not isinstance(tag, tuple) and check_tag(tag):
            temp = tag
            a = 1
            while temp in teams:
                temp = f'{tag}-{a}'
                a+=1
            new_tags.append((temp, ind))
        else:
            if isinstance(tag, tuple):
                if not check_tag(tag[0], add_self=True):
                    
                    new_tags.append((tag[0], ind))
                else:
                    n_tag = tag[0]+'-'+str(tag[1])
                    new_tags.append((n_tag, ind))
    teams_copy = copy.deepcopy(teams)
    for nt, ind in new_tags:
        teams[nt] = teams.pop(list(teams_copy.keys())[ind])

def find_possible_tags(players):
    all_tag_matches= defaultdict(list)

    for i in range(len(players)):
        tag_matches = defaultdict(set)
        temp_indx = len(players[i])+1
        orig_i = players[i].strip()
        i_tag = Utils.sanitize_uni(orig_i).lower()
        while temp_indx>1:
            temp_indx-=1
            
            for j in range(len(players)):
                if i==j: continue

                j_tag = Utils.sanitize_uni(players[j].strip()).lower()
                
                if i!=j and (i_tag[:temp_indx] == j_tag[:temp_indx]
                                or i_tag[:temp_indx] == j_tag[::-1][:temp_indx][::-1]):
                    
                    #print(temp_indx, players[i], players[j])
                    #m_tag = Utils.sanitize_tag_uni(orig_i)[:temp_indx]
                    m_tag = Utils.sanitize_uni(orig_i.strip()[:temp_indx])
                    if len(m_tag) == 1: 
                        m_tag = m_tag.upper()
                    if m_tag[-1] == '-':
                        m_tag = m_tag[:-1]
                    
                    tag_matches[m_tag].add(players[i])
                    tag_matches[m_tag].add(players[j])
                
                    
                elif i!=j and (i_tag[::-1][:temp_indx][::-1] == j_tag[::-1][:temp_indx][::-1]
                                or i_tag[::-1][:temp_indx][::-1] == j_tag[:temp_indx]):
                    
                    #print(temp_indx, players[i], players[j])
                    #m_tag = Utils.sanitize_tag_uni(orig_i)[::-1][:temp_indx][::-1]
                    m_tag = Utils.sanitize_uni(orig_i.strip()[::-1][:temp_indx][::-1])

                    if len(m_tag) == 1: 
                        m_tag = m_tag.upper()
                    if m_tag[-1] == '-':
                        m_tag = m_tag[:-1]
                  
                    tag_matches[m_tag].add(players[i])
                    tag_matches[m_tag].add(players[j])
                    
            
        for tag, tagged_players in tag_matches.items():
            if not any(tagged_players.issubset(e) for e in all_tag_matches[tag]):
                all_tag_matches[tag].append(tagged_players) #adding possible permutation for this tag (has to be new)
    return all_tag_matches

def tag_algo(players, per_team, num_teams):
    teams = {}

    all_tag_matches = find_possible_tags(players)

    for tag, perms in all_tag_matches.items():
        to_remove = []
        for p1 in range(len(perms)):
            for p2 in range(len(perms)):
                if p1!=p2 and perms[p2].issubset(perms[p1]):
                    to_remove.append(p2)
        for tr in to_remove:
            all_tag_matches[tag].pop(tr)
    for i in all_tag_matches.items():
        all_tag_matches[i[0]] = i[1][0]

    supposed_teams = int(len(players)/per_team)
    clean_overlaps(all_tag_matches) #get rid of tags that have overlapping players (such as shorter tags with subset of players)
    select_tops(all_tag_matches, per_team, num_teams, supposed_teams, teams, players) #select best tags that meet requirements (sort by number with prefixes, and actual tags for ones with too many)
    
    assert_correct(teams, players, per_team, num_teams, supposed_teams) #contingency in case of rare errors
    clean_tags(teams)

    if len(players)>0:  
        un_players = players
        handle_undetermined(teams, un_players, per_team)
    
    return teams

if __name__ == "__main__":
    import time
    #players = list({'x#1':0, 'xxx':0, 'Ryan@X':0, '¢unt':0, 'coolio': 0, 'cool kid cool': 0, "GG EZ": 0, 'gas mob':0, "gassed up":0, "kaya yanar":0, "yaya kanar":0, "yaka ranar":0}.keys())
    # players = ['hello', 'he123', 'borrowed time', 'WAX', 'barrel', 
    #             'A-1', 'what?', "WWW.PH.COM", "λxe", 'A-2', 'λp fraud', 'WOW!!']
    players = ['λρ Tom', 'A*', 'v¢ sauzule', 'saharave', 'MKW 4Beans', 'cadavreMK', 'coci loko', 'C', 'So[LLLLLL]', 'Zjazca', 'Z- stavros']
   
    tick = time.time()
    print(tag_algo(players, per_team=2, num_teams=6))
    print("done: ", time.time()-tick)