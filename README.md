# Table BOT

Table BOT is a discord bot made to automate the process of scoring and tabling Mario Kart Wii (MKW) private rooms, which is particularly useful for wars and lounge matches. It scrapes room data from [Wiimmfi][mkwxWebsite] and calculates scores for the teams and the players to create a table picture. Additionally, the bot provides several helpful commands to edit and correct tables.

This bot was inspired and influenced conceptually by another similar bot, which can be found [here](https://github.com/BadWolf1023/MKW-Table-Bot). It has greater functionality than this bot and is used in MKW Lounge, a ranked ladder for Mario Kart Wii.

## Documentation

Table BOT's full documentation can be found at this GitHub repository's [Wiki page](https://github.com/camelwater/Table-BOT/wiki).

## Important Information

Here is some terminology that Table BOT uses:

**```rxx```** - an eight character long room id beginning with an *r* and followed by seven numbers or a four character long room name that begins with two letters followed by two numbers (these can be found on [Wiimmfi][mkwxWebsite])\
ex. **r3066483** or **TN67**

**```mii```** - a player's in-game display name, can contain non-ASCII characters

## Bot Usage

> Commands are executed by providing the required arguments [in brackets] and additional, optional arguments (in parentheses). Optional arguments are by default excluded and arguments with an `=` sign have default values if nothing is provided.

To watch a room and score it with Table BOT, these primary commands are used:

```
?start [format] [numTeams] (rxx|<miiName>,...) (gps=3) (sui=no)
``` 
ex. `?start 5v5 2 camelwater123 beffjeff sui=yes gps=5`

Initializes a table instance with the given format (FFA, 2v2, 3v3, etc.) and number of teams. Optionally, if you already know the room id (rxx) of the desired room or the miiNames of players in the room, you can include either of them to skip the next step.

```
?search [mii|rxx] [<miiName>,...|rxx]
```
ex. `?search mii camelwater123, beffjeff`

Searches for a room on [Wiimmfi][mkwxWebsite] that best fits the provided miiName or rxx arguments. If your search arguments are too broad and apply to multiple rooms (for example you provide a very common miiName, such as "Player"), you will need to narrow your search by providing better arugments: either include additional miiNames or provide unique miiNames. 

```
?picture (byrace/race) (showlargetimes=no)
```
ex. `?picture byrace`

Fetches a [table picture][hlorenziWebsite] of the room's scores. `byrace/race` is an optional argument that can be included if you would like to see the table scores organized by each race (by default it is every gp, which is every 4 races).

[mkwxWebsite]: https://www.wiimmfi.de/stats/mkwx
[hlorenziWebsite]: https://gb.hlorenzi.com/table 
