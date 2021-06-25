# Table BOT

Table BOT is a discord bot made to automate the process of scoring and tabling an MKW private room, especially wars and lounge matches.
It scrapes the data of rooms from www.wiimmfi.de/stats/mkwx and calculates scores for the teams and the players to create a table picture, as well as providing additional tools to edit and correct tables.

## Important Information

Here is some terminology that the bot uses:

**rxx** - an eight character long room id beginning with an 'r' and followed by seven numbers or a four character long room name that begins with two letters followed by two numbers (based on www.wiimmfi.de/stats/mkwx website)\
ex. **r3066483** or **TN67**

**mii** - a player's in-game display name, can be non-ASCII

## Bot Usage

Commands are executed by providing the required arguments (in brackets) and additional, optional arguments (in parentheses). Arguments with an `=` sign have default values if nothing is provided.

`?start [format] [numTeams] (room rxx) (gps=3) (sui=no)`\
ex. `?start 5v5 2 sui=yes`

Initializes a table instance with the given format (FFA 2v2, 3v3, etc.) and number of teams. Optionally, if you already know the room id (rxx) of the desired room, you can include it to skip the next step.

`?search [mii|rxx] [<miiName>,...|rxx]`\
ex. `?search mii camelwater123, beffjeff`

Searches for a room on www.wiimmfi.de/stats/mkwx that best fits the arguments provided. If your search arguments are too broad and apply to multiple rooms (for example you provide a very common miiName such as 'Player'), you will need to narrow your search by providing better arguments. 

`?picture (byrace|race)`\
ex. `?picture byrace`

Fetches a table picture (from https://gb.hlorenzi.com/table) of the room's scores. `byrace` is an optional argument that can be included if you would like to see the table scores organized by each race (it defaults to every gp, which is every 4 races).


### Correction Commands

These commands are used to correct the table. These commands are sometimes necessary, as the website from where room data comes from (www.wiimmfi.de/stats/mkwx) is quite unreliable and often reports information that contradicts in-game results.

`?dcs`

`?editrace`

`?changeroomsize`


### Utility Commands

These commands can be used to edit the table based on your custom ruleset outside of MKW's basic system. For example, penalizing players.

`?edit`

`?pen` and `?unpen`

`?teampen` and `?teamunpen`

`?removerace`

`?mergeroom`

`?sub` and `?editsub`

`?changename`, `?changetag`, `?edittag`, and `?tags`

`?undo` and `?redo`

`?reset`

### Information Commands

These commands provide extra information and useful insight to the room.

`?players`

`?allplayers`

`?races`

`?tabletext`

`?raceresults`

`?rxx`

`?picture`

