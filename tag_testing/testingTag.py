import copy
import numpy as np
import math
from collections import defaultdict

team_formats = {}
VALID_CHARS = "/\\*^+abcdefghijklmnopqrstuvwxyz\u03A9\u038F" + "abcdefghijklmnopqrstuvwxyz0123456789".upper()
UNICODE_MAPPINGS_TO_ALPHA = {"@":"A", "\u00A7":"S", "$":"S", "\u00A2":"c", "\u00A5":"Y", "\u20AC":"E", "\u00A3":"E", "\u00E0":"a", "\u00E1":"a", "\u00E2":"a", "\u00E4":"a", "\u00E5":"a", "\u00E6":"ae", "\u00E3":"a", "\u00E7":"c", "\u00E8":"e", "\u00E9":"e", "\u00EA":"e", "\u00EB":"e", "\u00EC":"i", "\u00ED":"i", "\u00EE":"i", "\u00EF":"i", "\u00F1":"n", "\u00F2":"o", "\u00F3":"o", "\u00F4":"o", "\u00F6":"o", "\u0153":"oe", "\u00F8":"o", "\u00F5":"o", "\u00DF":"B", "\u00F9":"u", "\u00FA":"u", "\u00FB":"u", "\u00FC":"u", "\u00FD":"y", "\u00FF":"y", "\u00C0":"A", "\u00C1":"A", "\u00C2":"A", "\u00C4":"A", "\u00C5":"A", "\u00C6":"AE", "\u00C3":"A", "\u00C7":"C", "\u00C8":"E", "\u00C9":"E", "\u00CA":"E", "\u00CB":"E", "\u00CC":"I", "\u00CD":"I", "\u00CE":"I", "\u00CF":"I", "\u00D1":"N", "\u00D2":"O", "\u00D3":"O", "\u00D4":"O", "\u00D6":"O", "\u0152":"OE", "\u00D8":"O", "\u00D5":"O", "\u00D9":"U", "\u00DA":"U", "\u00DB":"U", "\u00DC":"U", "\u00DD":"Y", "\u0178":"Y", "\u03B1":"a", "\u03B2":"B", "\u03B3":"y", "\u03B4":"o", "\u03B5":"e", "\u03B6":"Z", "\u03B7":"n", "\u03B8":"O", "\u03B9":"i", "\u03BA":"k", "\u03BB":"A", "\u03BC":"u", "\u03BD":"v", "\u03BE":"E", "\u03BF":"o", "\u03C0":"r", "\u03C1":"p", "\u03C3":"o", "\u03C4":"t", "\u03C5":"u", "\u03C6":"O", "\u03C7":"X", "\u03C8":"w", "\u03C9":"W", "\u0391":"A", "\u0392":"B", "\u0393":"r", "\u0394":"A", "\u0395":"E", "\u0396":"Z", "\u0397":"H", "\u0398":"O", "\u0399":"I", "\u039A":"K", "\u039B":"A", "\u039C":"M", "\u039D":"N", "\u039E":"E", "\u039F":"O", "\u03A0":"N", "\u03A1":"P", "\u03A3":"E", "\u03A4":"T", "\u03A5":"Y", "\u03A6":"O", "\u03A7":"X", "\u03A8":"w", "\u0386":"A", "\u0388":"E", "\u0389":"H", "\u038A":"I", "\u038C":"O", "\u038E":"Y", "\u0390":"i", "\u03AA":"I", "\u03AB":"Y", "\u03AC":"a", "\u03AD":"E", "\u03AE":"n", "\u03AF":"i", "\u03B0":"u", "\u03C2":"c", "\u03CA":"i", "\u03CB":"u", "\u03CC":"o", "\u03CD":"u", "\u03CE":"w", "\u2122":"TM", "\u1D49":"e", "\u00A9":"C", "\u00AE":"R", "\u00BA":"o", "\u00AA":"a", "\u266D":"b"}
REMOVE_IF_START_WITH = "/\\*^+\[\]"
NUM = 12

def find_team_combo(teams, players_left, num_teams, team_size, r):
    if len(teams) == num_teams and len(teams[-1]) == team_size:
        r.append(teams)
    elif len(teams) == 0 or len(teams[-1]) == team_size:
        find_team_combo(teams + [[players_left[0]]] , players_left[1:], num_teams, team_size, r)
    else:
        left = team_size-len(teams[-1])
        for i in range(0, len(players_left)-left+1):
            if teams[-1][-1] < players_left[i]:
                c = copy.deepcopy(teams)
                c[-1].append(players_left[i])

                find_team_combo(c, players_left[:i]+players_left[i+1:], num_teams, team_size, r)


def encode_to_row(teams):
    mat = np.zeros((NUM, NUM), dtype=bool)
    # print(teams) 
    for team in teams:
        num_players = len(team)
        for i in range(num_players):
            for j in range(i+1, num_players):
                mat[team[i]][team[j]] = True
    # print(mat)
    row = []
    for i in range(NUM):
        for j in range(i+1, NUM):
            row.append(mat[i,j])
    # print(row)
    return row


def _get_tag_value(tag, map=False, both = False):
    while len(tag) > 0:
        if tag[0] in REMOVE_IF_START_WITH:
            tag = tag[1:]
        else:
            break
    temp = ""
    for c in tag:
        if c in UNICODE_MAPPINGS_TO_ALPHA:
            temp += UNICODE_MAPPINGS_TO_ALPHA[c] if map else c
        elif c in VALID_CHARS:
            temp += c
    if both:
        return temp.upper(), temp
    return temp.upper()

def get_tags(name):
    tags = set()
    for i in range(len(name)):
        tags.add(name[0:i+1])
        tags.add(name[-i-1:])
    return tags

def get_all_tags(name):
    return get_tags(_get_tag_value(name)).union(get_tags(_get_tag_value(name, map=True)))

def tag_rating(tag, names=[]):
    special = sum([c in UNICODE_MAPPINGS_TO_ALPHA for c in tag])

    front_bonus = 0
    for name in names:
        if name and (get_tag_loc(name, tag)[1] == "front"):
            front_bonus += 2
    front_bonus /= len(names)

    return len(tag) + special/2 + front_bonus

def get_tag_loc(raw_name, tag):
    for upper_name, name in [_get_tag_value(raw_name, both=True), _get_tag_value(raw_name,map=True, both=True)]:
        if upper_name[0:len(tag)] == tag:
            return name[0:len(tag)], "front"
        elif upper_name[-len(tag):] == tag:
            return name[-len(tag):], "back"

def best_shared_tag_rating(a_tags, b_tags, a, b):
    shared = a_tags.intersection(b_tags)

    if len(shared) > 0:
        return max([tag_rating(t, names=[a,b]) for t in shared])
    return 0


def decode_from_row(row):
    k = 0
    teams = []
    for i in range(12):
        for j in range(i+1, 12):
            if row[k]:
                added = False
                for team in teams:
                    if (i in team or j in team):
                        team.update([i,j])
                        added = True
                if not added:
                    teams.append({i,j})
            k+=1
    return teams

def get_teams(players, X):
    score_vec = []
    player_tags = [get_all_tags(p) for p in players]

    for i in range(NUM):
        for j in range(i+1, NUM):
            score = 0
            if i < len(players) and j < len(players):
                score = best_shared_tag_rating(player_tags[i], player_tags[j], players[i], players[j])
            score_vec.append(score)

    score_vec = np.array(score_vec)
    valid_vec = (score_vec>0).astype(int)

    valid_scores = X.dot(valid_vec)

    max_score = np.max(valid_scores)
    max_indices = np.argwhere(valid_scores==max_score).reshape(-1)

    tiebreaker_scores = X[max_indices].dot(score_vec)

    best = np.argmax(tiebreaker_scores)
    teams = decode_from_row(X[max_indices[best]])
    tagged_teams = {}

    unknown_players = 0
    back_tags = 0

    for team in teams:
        team = [t for t in team if t < len(players)]
        if len(team) == 0:
            continue

        team_tags = []
        try:
            team_tags = set.intersection(*[player_tags[i] for i in team])
        except:
            pass

        if len(team_tags)>0:
            team_names = [players[i] for i in team]
            best_tag = max(team_tags, key=lambda x: tag_rating(x, team_names))

            variants = defaultdict(int)
            for i in team:
                tag, loc = get_tag_loc(players[i], best_tag)
                if loc == 'back' and len(tag) <= 1:
                    back_tags += 1
                variants[tag] += 1
            best_tag = max(variants.keys(), key=lambda k: variants[k])

            while best_tag in tagged_teams:
                best_tag += "_"

            if (len(team) == 1):
                best_tag = best_tag[0]

            tagged_teams[best_tag] = team
        else:
            unknown_players += len(team)

            tag_count = defaultdict(int)
            for i in team:
                for tag in player_tags[i]:
                    tag_count[tag] += 1

            if len(tag_count) == 0:
                best_tag = "No Tag"
            else:
                best_tag = max(tag_count.keys(), key=lambda k: tag_count[k])
                if tag_count[best_tag] == 1:
                    longest_name = max([_get_tag_value(players[i], map=True) for i in team], key=len)
                    if len(longest_name) > 0:
                        best_tag = longest_name[0]
                    else:
                        best_tag = "No Tag"

            tagged_teams[best_tag] = team

    return tagged_teams, max_score, tiebreaker_scores[best], {"unknown_players": unknown_players, "back_tags": back_tags}

def get_teams_smart(players, formats=None, target_size=None):
    if formats is None:
        formats = team_formats
    best_score = 0
    best_teams = None
    best_size = 1

    bonus = {2:0, 3:0, 4:0, 5:0, 6:0}
    if len(players) == 10:
        bonus[5] += 0.3

    if not target_size:
        team_sizes = [6,4,5,3,2]
    else:
        team_sizes = [target_size]

    for team_size in team_sizes:
        X = formats[team_size]

        num_teams = math.ceil(len(players)/team_size)

        target_score = num_teams * (team_size)*(team_size-1)/2
        teams, score, tie_score, data = get_teams(players, X)

        adjusted_score = score/target_score + bonus[team_size]

        print(f'Team Size={team_size}; Score={adjusted_score}')

        if target_size:
            return best_size, teams

        if adjusted_score > best_score and adjusted_score>=0.80 and len(teams)>1:
            if team_size == 2:
                if data["unknown_players"] + data["back_tags"] >= 5/12*(num_teams * 2):
                    continue

            best_score = adjusted_score
            best_teams = teams
            best_size = team_size

    print(best_teams)
    return best_size, best_teams

def print_teams(teams, players):
    if teams is None:
        print("FFA ", players)
    else:
        for tag in teams:
            print(tag, [players[i] for i in teams[tag] if i < len(players)])


def initialize():
    for team_size in [2,3,4,5,6]: 
        combos = []
        find_team_combo([], list(range(NUM)), NUM//team_size, team_size, combos)
        team_formats[team_size] = np.array([encode_to_row(c) for c in combos])
    # print(team_formats[2][-1])
    print("Team format matrices generated.")

if __name__ == "__main__":
    import time, random
    # players5 = list({'x#*********************ATSDUAJSDGHASDUYkajsdhalkjdh1':0, 'awasasasdasdasddsdadsddasdsadd':0, 'Ryadadadadddanasdasd@X':0, '??unasdklajsdkajsdhalkjsddsasdasdt':0, 'stop asd;liajds;aosdij;alskdj;alsdkasdasdman': 0, 'coolasdasd kasdlkajsd;laksjdasdsadid cool': 0, "GG EaslkdjahsldkjadshlkajsdhlaksjdahsdasdZ": 0, 'gas moasdalkdsja;lsdb':0, "gasseasdasddsasasdd up":0, "kaya kljaxdlasdkasjdhalksdjhkjyanar":0, "yaya kasdaasdljsdhaosduy98712sdanar":0, "ya123123313233asdASDASDkqeeqweqwea ranar":0}.keys())
    # players6 = list({'helasasdndkzxdkzjxdnzddasdlo':0, 'stupasdalasdsdasda  asda ds adsdasid':0, 'asdl;lajsdhalksdjhlaskdjhaoisudyoaisduVA':0, 'banvannnnansdasdnansdnsdnasdndansdansdasndned':0, '09a8sd79as8d7a9s8d7a9sd87a9sd90':0, 'heaqoiu1p2oiu12981y49yoiusdasdll&*':0, 'whaasdasldajdsh;akjdhlaksjdhladsdsasdasddaat?':0, "a;lsdkja;sldkja;dlkaj;daaslkdja;lsdkjasd;l ad92y?":0, "??xasdasdasd12131311231asddade":0, 'Aaasd;lkasjd;alskdj;alskdjsdasdasAA':0, '??p fraasdaskdkhalksdasdasdadud':0, 'AasdlkajdlaasdasdsdasdkdsjhlaksdBB':0}.keys())
    # players9 = list({'helasasdndkzxdkzjxdnzddasdlo':0, 'stupasdalasdsdasda  asda ds adsdasid':0, 'asdl;lajsdhalksdjhlaskdjhaoisudyoaisduVA':0, 'banvannnnansdasdnansdnsdnasdndansdansdasndned':0, '09a8sd79as8d7a9s8d7a9sd87a9sd90':0, 'heaqoiu1p2oiu12981y49yoiusdasdll&*':0, 'whaasdasldajdsh;akjdhlaksjdhladsdsasdasddaat?':0, "a;lsdkja;sldkja;dlkaj;daaslkdja;lsdkjasd;l ad92y?":0, "??xasdasdasd12131311231asddade":0, 'Aaasd;lkasjd;alskdj;alskdjsdasdasAA':0, '??p fraasdaskdkhalksdasdasdadud':0, 'AasdlkajdlaasdasdsdasdkdsjhlaksdBB':0}.keys())
    # players7 = list({'he1273182376198237619283716932llo':0, 'heasdaklsdhalisduyaosidu123':0, 'borrowasalsdjhalsdkjalsdkjdasded time':0, 'bannasdasdaded':0, 'barasdasdrasda;klsdjakldsjhasd9o8yael':0, 
    #             'hellas1o2y92yoiuasdasdasdasdasddlkjasdlkajdsl&*':0, 'whaskdjhadsklbccmzbnx,mzat?':0, "wasdasdasdlkahsdjho?":0, "??asdasdkjalshdlakshdo9yous&*^&(*&^(*^&%9aksjdhaasdlkasd9qweyasdxe":0, 'AAasldkjadslkjadkajhdslkajdhlaksjdhalsdkjhasdA':0, '??pasdasdas asd;alisdha;lksdhlakdsfraud':0, 'whasd;laskdhasdkjhaosiduyas9od8as9d8yapsd9ere?':0}.keys())
    # players8 = list({'helasdas1231y392y31o2dlo':0, 'stupasdaasasdasdasdddasddssdasid':0, 'asdl;lajsdhalksdjhlaskdjhaoisudyoaisduVA':0, 'banvannnnansdasdnansdnsdnasdndansdansdasndned':0, '09a8sd79as8d7a9s8d7a9sd87a9sd90':0, 'heaqoiu1p2oiu12981y49yoiusdasdll&*':0, 'whaasdasldajdsh;akjdhlaksjdhladsdsasdasddaat?':0, "whasdasdasdasdasdo?":0, "??xasdasdasdasddade":0, 'Aaasd;lkasjd;alskdj;alskdjsdasdasAA':0, '??p fraasdahdsdo9oysda2eoiu oi u  lajsd lassdasdadud':0, 'Aasdlkasdlkj lkj asdadasdajdlakdsjhlaksdBB':0}.keys())
                
    # players4 = list({'pringleMVMMVMVMVMVMVMVMVMVMVMMVMV@MV':0,'5heaskdjhadslkajhdslakhdaiuyo876o876o8768asdadMV':0,'hellasjdhahksdjhalskdjhalsdkjhaldo LTA':0,'Lasdkjahdklajsdhaosd98odTAX':0,
    #         'jaja Lasdkjhdslaiusdyoasudyoasyasdya0sddTA':0,'stupasldasldkj;sdkaj;sdalkdsj;asldkid@LTA':0,'poop asdlakjdshlakjdshadssdMV':0,'MVMVMasdklahdsldssaadVMV':0,'LTA Vvalksjlpvalkjalksuqwealpo':0,"5 guys glajshdl asjh mom's spaghet":0}.keys())
    # players = list({'x#*(*&(&(*&(*&(*&akjsdhasd87asd6a8sd11':0, 'xxxXXXXXXXXXXXXXXXXXXXXXXXXXXXXX':0, 'Ryan@XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX':0, '??uuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuunt':0, 'coolllllllllllkjkjkjkj123l12jk1jlio': 0, 'cool k12o381 102u 2oi1u 2id cool': 0, "GG EZZZZZZZZZZZZZZZZZZZZZZZZZ": 0, 'gas masd12o31uy2398   asdasadsadadsaob':0, "gassessssssssssssssssssd up":0, "kayajksdhasuoday9y098709a yanar":0, "yaya kasmasklaslkadsljladskjldsanar":0, "yaka kakaakakakdskdskasdadsjdsakranar":0}.keys())
    # players2 = ['asldkjadheaslkjdaskjdhlaksjdahdsllo', 'hasd123123213.kjadshaliskdjho876e123', 'borrowed timasd;laasdllndlksdhaposdu98q2ee', 'WAasd.kj.asdas.da.dsasd.asd.asd.a adshiaosda8dsX', 'basdkjasda  sda qe e j12oei1eahdlkajdsyao8ds7yarrel', 
    #             'A-asdlkadslkajdhlla192837192akjsdh1', 'whasdoqiouewiuy12o13y4183476184716894124at?', "WWW.Pasdalj;lsdhaldksjhlkaH.COM", "??xeasdlkahdsasdsd ds adaalsda98", 'Aasdlkaskldjahsd9a8y-2', '??p frasdjlhalkdsjsasdlaksjdhadsd90ayaud', 'WOwowowowowowowowowowoowowowowowowW!!']
    # players3 = ['???? ToOOOOOOOOOOOOOOoooooooooooom', 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA*', 'v?? bvbvbvvvvvvvvvvvvvvvvvvvvvvvvvvvvvbvbvbvbvsauzule', 'sahasdjasdkjadshlkajsdhlakdsarave', 'MasdkjjdslakjdshlaksdjhKW 4Beans', 'cadasdasldhadjh9y01984y1944144avreMK', 'cocia;lskdhklajsdhasdo9y loko', 'Casdkjadhlajdasdasdhlkdsho9shap9sd8y', 'So[akjsdhakljdshaoisduyads8yLLLLLL]', 'Zjazasda,smdda   asddnadsasdasdca', 'Z- stavrosaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa']
    # players+=players2+players7+players8+players4+players5+players6+players3+players9*44
    players = ['?? big', 'PP hi', 'PP powerplant', '?? oo', 'PP gerp', '?? hello', 'shuyx@??', 'PP POWERGRID', 'big PP', '?? vamp']

    NUM = 12

    random.shuffle(players)
    initialize()
    start = time.perf_counter()
    _, teams = get_teams_smart(players, target_size=2)
    print(time.perf_counter()-start)

    print_teams(teams, players)

