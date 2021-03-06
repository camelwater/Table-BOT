# FROM: https://github.com/willsigg/mkwtools
import hashlib

def fc_to_pid(pid, gameid):
    name = bytes([
    (pid >>  0) & 0xFF,
    (pid >>  8) & 0xFF,
    (pid >> 16) & 0xFF,
    (pid >> 24) & 0xFF,
    int(gameid[3]),
    int(gameid[2]),
    int(gameid[1]),
    int(gameid[0])])
    return pid & 0xFFFFFFFF

def pid_to_fc(pid, gameid):
    name = bytes([
        (pid >>  0) & 0xFF,
        (pid >>  8) & 0xFF,
        (pid >> 16) & 0xFF,
        (pid >> 24) & 0xFF,
        int(gameid[3]),
        int(gameid[2]),
        int(gameid[1]),
        int(gameid[0])])
    hash_ = int(hashlib.md5(name).hexdigest()[:2], 16) >> 1
    return (hash_ << 32) | (pid & 0xFFFFFFFF)

def get_country_code(countryId: int):
    return COUNTRY_MAP.get(countryId, None)

COUNTRY_MAP = {
    1:'JP',
    2:'AQ',
    3:'NL',
    4:'FK',
    5:'GB',
    6:'GB',
    7:'SX',
    8:'AI',
    9:'AG',
    10:'AR',
    11:'AW',
    12:'BS',
    13:'BB',
    14:'BZ',
    15:'BO',
    16:'BR',
    17:'VG',
    18:'CA',
    19:'KY',
    20:'CL',
    21:'CO',
    22:'CR',
    23:'DM',
    24:'DO',
    25:'EC',
    26:'SV',
    27:'GF',
    28:'GD',
    29:'GP',
    30:'GT',
    31:'GY',
    32:'HT',
    33:'HN',
    34:'JM',
    35:'MQ',
    36:'MX',
    37:'MS',
    38:'AN',
    39:'NI',
    40:'PA',
    41:'PY',
    42:'PE',
    43:'KN',
    44:'LC',
    45:'VC',
    46:'SR',
    47:'TT',
    48:'TC',
    49:'US',
    50:'UY',
    51:'VI',
    52:'VE',
    53:'AM',
    54:'BY',
    55:'GE',
    56:'XK',
    57:'AK',
    58:'AH',
    59:'NY',
    62:'AX',
    63:'FO',
    64:'AL',
    65:'AU',
    66:'AT',
    67:'BE',
    68:'BA',
    69:'BW',
    70:'BG',
    71:'HR',
    72:'CY',
    73:'CZ',
    74:'DK',
    75:'EE',
    76:'FI',
    77:'FR',
    78:'DE',
    79:'GR',
    80:'HU',
    81:'IS',
    82:'IE',
    83:'IT',
    84:'LV',
    85:'LS',
    86:'LI',
    87:'LT',
    88:'LU',
    89:'MK',
    90:'MT',
    91:'ME',
    92:'MZ',
    93:'NA',
    94:'NL',
    95:'NZ',
    96:'NO',
    97:'PL',
    98:'PT',
    99:'RO',
    100:'RU',
    101:'RS',
    102:'SK',
    103:'SI',
    104:'ZA',
    105:'ES',
    106:'SZ',
    107:'SE',
    108:'CH',
    109:'TR',
    110:'GB',
    111:'ZM',
    112:'ZW',
    113:'AZ',
    114:'MR',
    115:'ML',
    116:'NE',
    117:'TD',
    118:'SD',
    119:'ER',
    120:'DJ',
    121:'SO',
    122:'AD',
    123:'GI',
    124:'GG',
    125:'IM',
    126:'JE',
    127:'MC',
    128:'TW',
    129:'KH',
    130:'LA',
    131:'MN',
    132:'MM',
    133:'NP',
    134:'VN',
    135:'KP',
    136:'KR',
    137:'BD',
    138:'BT',
    139:'BN',
    140:'MV',
    141:'LK',
    142:'TL',
    143:'IO',
    144:'HK',
    145:'MO',
    146:'CK',
    147:'NU',
    148:'NF',
    149:'MP',
    150:'AS',
    151:'GU',
    152:'ID',
    153:'SG',
    154:'TH',
    155:'PH',
    156:'MY',
    157:'BL',
    158:'MF',
    159:'PM',
    160:'CN',
    161:'AF',
    162:'KZ',
    163:'KG',
    164:'PK',
    165:'TJ',
    166:'TM',
    167:'UZ',
    168:'AE',
    169:'IN',
    170:'EG',
    171:'OM',
    172:'QA',
    173:'KW',
    174:'SA',
    175:'SY',
    176:'BH',
    177:'JO',
    178:'IR',
    179:'IQ',
    180:'IL',
    181:'LB',
    182:'PS',
    183:'YE',
    184:'SM',
    185:'VS',
    186:'BM',
    187:'PF',
    188:'RE',
    189:'YT',
    190:'NC',
    191:'WF',
    192:'NG',
    193:'AO',
    194:'GH',
    195:'TG',
    196:'BJ',
    197:'BF',
    198:'CI',
    199:'LR',
    200:'SL',
    201:'GN',
    202:'GW',
    203:'SN',
    204:'GM',
    205:'CV',
    206:'SH',
    207:'MD',
    208:'UA',
    209:'CM',
    211:'CD',
    212:'CG',
    213:'GQ',
    214:'GA',
    215:'ST',
    216:'DZ',
    217:'ET',
    218:'LY',
    219:'MA',
    220:'SS',
    221:'TN',
    222:'EH',
    223:'CU',
    224:'BI',
    225:'KM',
    226:'KE',
    227:'MG',
    228:'MW',
    229:'MU',
    230:'RW',
    231:'SC',
    232:'TZ',
    233:'UG',
    234:'FR',
    235:'PN',
    236:'GB',
    237:'GS',
    238:'FM',
    239:'FJ',
    240:'KI',
    241:'MH',
    242:'NR',
    243:'PW',
    244:'PG',
    245:'WS',
    246:'SB',
    247:'TK',
    248:'TO',
    249:'TV',
    250:'VU',
    251:'CX',
    252:'CC',
    253:'PR',
    254:'GL'
}
