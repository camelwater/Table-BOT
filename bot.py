# -*- coding: utf-8 -*-
"""
Created on Wed May 19 08:33:13 2021

@author: ryanz
"""

import discord
from discord.ext import commands, tasks
from tabler import Table
import os
from dotenv import load_dotenv
import sys
sys.path.append('C:\\Users\\ryanz\\Anaconda3\\Lib\\site-packages')

load_dotenv()
KEY = os.getenv('KEY')
SERVER_ID = 775253594848886785
home_url = "https://wiimmfi.de/stats/mkwx/list/"
bot = commands.Bot(command_prefix = ('?'), case_insensitive=True, intents = discord.Intents.all(), help_command = None)
table = Table()
choose_message = ""
searching_room = False
choose_room = False
confirm_room = False
confirm_reset = False
#confirm_message = ''
reset_args = None
undo_empty = False
redo_empty = False

num_players = 0
gps = 0
teams = 0
_format = ''
table_running = False

@bot.event
async def on_ready():
    print("Bot logged in as {0.user}".format(bot))
    
async def send_temp_messages(ctx, *args):
    await ctx.send('\n'.join(args), delete_after=25)
async def send_messages(ctx, *args):
    await ctx.send('\n'.join(args))
'''   
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("{}.\nType ?help for a list of commands.".format(error))
    #else:
        #await ctx.send(error)
'''  

#default max teams based on format (currently used for ffa format only)
def max_teams(f):
    f = f[0]
    if f == 'f':
        return 12
    else:
        f = int(f)
        return 12/f
    
#check if number of teams exceeds max possible teams for format
def check_teams(f, teams):
    max_t = max_teams(f)
    if teams>max_t: return True
    return False

def get_num_players(f, teams):
    f = f[0]
    if f == 'f':
        f = 1
    else: f = int(f)
    
    return teams*f

#?start
@bot.command(aliases=['st', 'starttable', 'sw'])
async def start(ctx, *args):
    global searching_room, num_players, teams, gps, _format, confirm_reset, confirm_room, table, choose_message, table_running, reset_args
    global undo_empty, redo_empty
    undo_empty=redo_empty=False
    
    if confirm_room or confirm_reset:
        await send_temp_messages(ctx, "Please answer the last confirmation question:", choose_message)
        return
    if table_running:
        confirm_reset = True
        reset_args = args
        choose_message= "A tabler watching room {} is currently active.\nAre you sure you want to start a new table? (?yes/?no)".format(table.rxx)
        await send_messages(ctx, choose_message)
        return
    usage = "Usage: ?start <format> <number of teams> <gps = 3>"
    
    if isinstance(args[0], tuple) and reset_args !=None:
        args = args[0]
    
    if len(args)<1:
        await send_temp_messages(ctx, usage)
        return
    _format = args[0].lower()
    
    if len(args)<2 and _format[0]!='f':
        await send_temp_messages(ctx, "Missing <teams>.", usage)
        return
    
    
    if _format not in ['ffa', '2v2', '3v3', '4v4', '5v5', '6v6', '2', '3', '4', '5', '6']:
        await send_messages(ctx, "Invalid format. Format must be FFA, 2v2, 3v3, 4v4, 5v5, or 6v6.", usage)
        return
    
    teams = max_teams(_format)
    if len(args)>1:
        try:
            teams = int(args[1].lower())
        except:
            await send_messages(ctx, "Invalid use of ?start: <teams> must be an integer.", usage)
            return
    
    if check_teams(_format, teams):
        await send_messages(ctx, "Invalid number of teams. The number of teams cannot exceed 12 players.", usage)
        return
    table.format = _format
    table.teams = teams
    num_players = get_num_players(_format, teams)    
    gps = 3
    if len(args)>2:
        
        arg3 = args[2].lower()
        if arg3.isnumeric():
            gps = arg3
            table.gps = gps
        else:
            rxx = [arg3]
            wait_mes = await ctx.send('Searching for room...')
            error, ask, choose_message = table.find_room(rid = rxx)
            await wait_mes.delete()
            if error:
                if ask=='reset':
                    table = Table()
                await send_messages(ctx, choose_message, usage)
                return
            if ask=="confirm":
                confirm_room = True
                if table.format[0] == 'f':
                    mes = "Table successfully started. Watching room {}.\n?pic to get table picture.".format(table.rxx)
                    table_running = True
                    await send_messages(ctx, mes)
                    searching_room = False
                    confirm_room = False
                    return
                    
                await send_messages(ctx, choose_message)
                return
        
    searching_room = True   
    await send_messages(ctx, "Provide a room id (rxx) or mii name(s) in the room.", "Make sure at least one race in the room has finished.", "Usage: ?search <rxx or mii> <rxx or mii names(s)>")

#?search   
@bot.command(aliases=['sr'])  
async def search(ctx, *, arg):
    global searching_room, num_players, choose_room, confirm_room, choose_message, table
    global undo_empty, redo_empty
    undo_empty=redo_empty=False
    if confirm_room or confirm_reset:
        await send_temp_messages(ctx, "Please answer the last confirmation question:", choose_message)
        return
   
    if not searching_room:
        await send_messages(ctx, "You cannot search for a room if a table is currently running or a table hasn't been started yet.")
        return
    arg = arg.strip()
    
    usage = "Usage: ?search <rxx or mii> <rxx or name(s)>\nmkwx room list: {}".format(home_url)
    if len(arg)<1:
        await send_temp_messages(ctx, usage)
        return
    #search_type = args[0].lower()
    #search_args = [i.lower() for i in args[1:]] 
    arg_indx = arg.find(' ')
    if arg_indx == -1: arg_indx = len(arg)+1
    search_type = arg[:arg_indx].lower()
    search_args = arg[arg_indx+1:].split(",")
    search_args = [i.lower().strip() for i in search_args]
    
    print(search_args)
    if len(search_args)<1:
        await send_messages("You need to provide <rxx or mii name(s)>.", usage)
    if len(search_args)>num_players:
        await send_messages(ctx, "You cannot provide more than {} mii names.".format(num_players), usage)
        return
    
    if search_type == 'roomid' or search_type=='rxx':
        print("ds")
        if search_args[0].isnumeric():
            await send_messages(ctx, "Invalid room id: missing an 'r' or not in format 'XX00'.", usage)
            return
        wait_mes = await ctx.send('Searching for room...')
        error, ask, choose_message = table.find_room(rid = search_args)
    elif search_type == "mii":   
        wait_mes = await ctx.send('Searching for room...')
        error, ask, choose_message = table.find_room(mii = search_args)
    else:
        await send_messages(ctx, "Invalid argument for ?search: <search type> must be 'rxx' or 'mii'", usage)
        return
    await wait_mes.delete()
    if error:
        if ask=='reset':
            table = Table()
        await send_messages(ctx, choose_message, usage)
        return
    
    if ask == "match":
        choose_room= True
        
        await send_messages(ctx, "There were more than one possible matching rooms. Choose the desired room number.", choose_message)
        return
    elif ask=="confirm":
        confirm_room = True
        await send_messages(ctx, choose_message)
        return

@search.error
async def search_error(ctx, error):
    global undo_empty, redo_empty
    undo_empty=redo_empty=False
    if isinstance(error, commands.MissingRequiredArgument):
        await send_messages(ctx, "Usage: ?search <rxx or mii> <rxx or name(s)>\nmkwx room list: {}".format(home_url)) 

#change one player's tag
@bot.command()
async def changetag(ctx, *args): 
    global undo_empty, redo_empty
    undo_empty=redo_empty=False
    global choose_message
    if confirm_reset or( confirm_room and table_running):
        await send_temp_messages(ctx, "Please answer the last confirmation question:", choose_message)
        return
    if not (confirm_room and not table_running) and not table_running:
        await send_temp_messages(ctx, "You can only use this command if the bot prompts you or a table is currently active.")
        return
    usage = "Usage: ?changetag <player id> <corrected tag>"
    if len(args)==0:
        await send_temp_messages(ctx, table.get_player_list(),'\n',usage)
        return
    
    pID = args[0].lower()
    if not pID.isnumeric():
        await send_temp_messages(ctx, "<player id> must be a number.", usage)
        return
    if len(args)<2:
        await send_temp_messages(ctx, "missing <corrected tag> parameter.", usage)
        return
    
    tag = args[1]
    mes= table.change_tag(pID, tag)
    if confirm_room:
        choose_message = table.get_player_list() +"\nIs this correct? (?yes / ?no)"
        await send_messages(ctx, mes, table.get_player_list(), '\n', "Is this correct? (?yes / ?no)")
    else:
        await send_messages(ctx, mes)
    
@bot.command(aliases=['et', 'edittags']) 
async def edittag(ctx, *, arg): 
    global undo_empty, redo_empty
    undo_empty=redo_empty=False
    global choose_message
    usage = 'Usage: ?edittag <tag> <corrected tag>'
    if confirm_reset or( confirm_room and table_running):
        await send_temp_messages(ctx, "Please answer the last confirmation question:", choose_message)
        return
    if not (confirm_room and not table_running) and not table_running:
        await send_temp_messages(ctx, "You can only use this command if the bot prompts you or a table is currently active.")
        return
    
    arg = [i.strip() for i in arg.strip().split("/")]
    arg  = [i.split(" ") for i in arg]
    if len(arg)==0:
        await send_temp_messages(ctx, table.get_player_list(), '\n', usage)
    for i in arg:
        if len(i)<1:
            await send_temp_messages(ctx, "Missing tag(s) for command.", table.get_player_list(), '\n',usage)
            return
        if len(i)<2:
            await send_temp_messages(ctx, "Error processing command: missing <corrected tag> for tag '{}'".format(i[0]), table.get_player_list(), usage)
            return
    
    
    mes = table.edit_tag_name(arg)
    if confirm_room:
        choose_message = table.get_player_list() +"\nIs this correct? (?yes / ?no)"
        await send_messages(ctx, mes, table.get_player_list(), '\n', "Is this correct? (?yes / ?no)")
    else:
        await send_messages(ctx, mes)
        
@edittag.error
async def edittag_error(ctx, error):
    global undo_empty, redo_empty
    undo_empty=redo_empty=False
    if isinstance(error, commands.MissingRequiredArgument):
        await send_messages(ctx, table.get_player_list(),'\nUsage: ?edittag <tag> <corrected tag>')    

#to manually create tags
@bot.command(aliases=['tag'])
async def tags(ctx, *, arg): 
    global undo_empty, redo_empty
    undo_empty=redo_empty=False
    global choose_message
    usage = "Usage: ?tags <tag> <pID pID> / <tag> <pID pID>\n**ex.** ?tags Player 1 3 / Z 2 4 / B 5 6"
    if confirm_reset or( confirm_room and table_running):
        await send_temp_messages(ctx, "Please answer the last confirmation question:", choose_message)
        return
    if not (confirm_room and not table_running) and not table_running:
        await send_temp_messages(ctx, "You can only use this command if the bot prompts you or a table is currently active.")
        return
    
    arg = [i.strip() for i in arg.strip().split("/")]
    arg  = [i.split(" ") for i in arg]
    if len(arg)==0:
        await send_temp_messages(ctx, table.get_player_list(), '\n',usage)
        return
    for i in arg:
        if len(i)<1:
            await send_temp_messages(ctx, "Missing tag(s) for command.", table.get_player_list(), '\n',usage)
            return
        if len(i)<2:
            await send_temp_messages(ctx, "Error processing command: missing players for tag '{}'".format(i[0]), table.get_player_list(), usage)
            return
        for indx, j in enumerate(i[1:]):
            if not j.isnumeric():
                await send_temp_messages(ctx, "Error processing players for tag '{}': {} is not a number. All players must be numeric.".format(i[0], i[indx]), usage)
                return 
    dic = {}
    for i in arg:
        dic[i[0]] = i[1:]
    
    mes = table.group_tags(dic)
    choose_message = table.get_player_list() +"\nIs this correct? (?yes / ?no)"
    await send_messages(ctx, mes, table.get_player_list(), "\nIs this correct? (?yes / ?no)")
    
@tags.error
async def tags_error(ctx, error):
    global undo_empty, redo_empty
    undo_empty=redo_empty=False
    if isinstance(error, commands.MissingRequiredArgument):
        await send_messages(ctx, table.get_player_list(), "\nUsage: ?tags <tag> <pID pID> / <tag> <pID pID>\n**ex.** ?tags Player 1 3 / Z 2 4 / B 5 6")

@bot.command(aliases=['y'])
async def yes(ctx, *args):
    global undo_empty, redo_empty
    undo_empty=redo_empty=False
    global confirm_room, searching_room, table_running, confirm_reset, table, choose_room
    if not confirm_room and not confirm_reset:
        await send_temp_messages(ctx, "You can only use ?yes if the bot prompts you to do so.")
        return
    if confirm_room:
        if choose_room: choose_room = False
        mes = "Table successfully started. Watching room {}.\n?pic to get table picture.".format(table.rxx)
        table_running = True
        await send_messages(ctx, mes)
        searching_room = False
        confirm_room = False
    elif confirm_reset:
        table = Table()
        table_running=False
        confirm_reset = False
        await send_messages(ctx, "Table has been reset.")
        await start(ctx, reset_args)
    
@bot.command(aliases=['n'])
async def no(ctx, *args):
    global undo_empty, redo_empty
    undo_empty=redo_empty=False
    global confirm_room, searching_room, confirm_reset, table
    if not confirm_room and not confirm_reset:
        await send_temp_messages(ctx, "You can only use ?no if the bot prompts you to do so.")
        return 
    if confirm_room:
        confirm_room = False
        table = Table()
        #await send_messages(ctx, "Search for a room with ?search <search type> <room id or mii name(s)>")
        await send_messages(ctx, "Start a new table with ?start.")
       
    elif confirm_reset:
        confirm_reset = False
        await send_messages(ctx, "Tabler watching room {} will continue running.".format(table.rxx))
 
#choose correct room if multiple matches from mii name search
@bot.command(aliases=['ch'])
async def choose(ctx, *args):
    global undo_empty, redo_empty
    undo_empty=redo_empty=False
    global choose_room
    if confirm_room or confirm_reset:
        await send_temp_messages(ctx, "Please answer the last confirmation question:", choose_message)
        return
    if not choose_room:
        await send_temp_messages(ctx, "You can only use ?choose if the bot prompts you to do so.")
        return
    usage = "Usage: ?choose <room index #>"
    
    room = args[0].lower()
    count = choose_message.count("Players in room:")
    indices = range(1, count+1)
    if room not in indices:
        await send_messages(ctx, "Invalid room index: the room index should be from {} to {}.".format(indices[0], indices[-1]), usage)
        return
    #TODO: show them chosen room, and ask if it it correct ?yes or ?no or ?changetag
    #await send_messages(ctx, )

#?picture
@bot.command(aliases=['p', 'pic', 'wp'])
async def picture(ctx, *args):
    global undo_empty, redo_empty
    undo_empty=redo_empty=False
    global table_running
    if confirm_room or confirm_reset:
        await send_temp_messages(ctx, "Please answer the last confirmation question:", choose_message)
        return
    if not table_running:
        await send_temp_messages(ctx, "You need to start a table before getting the table picture.", "?start <format> <teams> <gps=3>")
        return
    wait_mes = await ctx.send("Fetching table picture. Please wait...")
    mes = table.update_table()
    img = await table.get_table_img()
    await wait_mes.edit(content=mes)
    
    f=discord.File(fp=img, filename='table.png')
    em = discord.Embed(title=table.tag_str(), color=0x00ff6f)
    
    value_field = "[Edit this table on gb.hlorenzi.com]("+table.table_link+")"
    em.add_field(name='\u200b', value= value_field, inline=False)
    em.set_image(url='attachment://table.png')
    em.set_footer(text = table.get_warnings())
    
    #await ctx.send(file = f)
    #await send_messages(ctx, table.get_warnings())
    await ctx.send(embed=em, file=f)

@bot.command()
async def undo(ctx, *args):
    global undo_empty, redo_empty
    
    if confirm_reset or( confirm_room and table_running):
        await send_temp_messages(ctx, "Please answer the last confirmation question:", choose_message)
        return
    if not (confirm_room and not table_running) and not table_running:
        await send_temp_messages(ctx, "You can only use this command if the bot prompts you or a table is currently active.")
        return
    
    usage = 'Usage: ?undo <modification number ("all" if you want to undo all)>'
    
    if undo_empty and len(args)==0:
        mes = table.undo_commands(-1)
        await send_messages(ctx, mes)
        undo_empty = False
        return
    if len(args)==0:
        await send_messages(ctx, table.get_modifications(), '\n'+usage)
        undo_empty = True
        return
    
    else:
        if args[0].lower()=='all':
            args = 0
        elif args[0].isnumeric():
            args = int(args[0])
        else:
            await send_temp_messages(ctx, "{} is not a valid parameter for ?undo. The only valid parameters are 'all' and numbers.".format(args[0]), usage)
            return
    undo_empty = False   
    mes = table.undo_commands(args)
    await send_messages(ctx,mes)
    
@bot.command()
async def redo(ctx, *args):
    global redo_empty
    if confirm_room or confirm_reset:
        await send_temp_messages(ctx, "Please answer the last confirmation question:", choose_message)
        return
    if not table_running:
        await send_temp_messages(ctx, "You cannot use ?dcs if there is no table running.")
        return
    usage = 'Usage: ?redo <undo number ("all" if you want to redo all)>'
    
    if redo_empty and len(args)==0:
        mes = table.redo_commands(-1)
        await send_messages(ctx, mes)
        redo_empty = False
        return
    if len(args)==0:
        await send_messages(ctx, table.get_undos(), '\n'+usage)
        redo_empty = True
        return
    else:
        if args[0].lower()=='all':
            args = 0
        elif args[0].isnumeric():
            args = int(args[0])
        else:
            await send_temp_messages(ctx, "{} is not a valid parameter for ?redo. The only valid parameters are 'all' and a number.".format(args[0]), usage)
            return
    redo_empty = False
    mes = table.redo_commands(args)
    await send_messages(ctx,mes)
   
 
#?reset
@bot.command()
async def reset(ctx, *args):
    global undo_empty, redo_empty
    undo_empty=redo_empty=False
    global table, table_running, confirm_room, confirm_reset, choose_message
    #if confirm_room or confirm_reset:
        #await send_temp_messages(ctx, "Please answer the last confirmation question:", choose_message)
        #return
    if not table_running and not confirm_room:
        await send_temp_messages(ctx, "You need to have an active table to be able to reset.")
        return
    table = Table()
    table_running = False
    choose_message = None 
    confirm_reset = False
    confirm_room= False
    await send_messages(ctx, "Reset the table. ?start to start a new table.")

@bot.command(aliases = ['dc'])
async def dcs(ctx, *, arg): 
    global undo_empty, redo_empty
    undo_empty=redo_empty=False
    if confirm_room or confirm_reset:
        await send_temp_messages(ctx, "Please answer the last confirmation question:", choose_message)
        return
    if not table_running:
        await send_temp_messages(ctx, "You cannot use ?dcs if there is no table running.")
        return
    usage = '\nUsage: ?dcs <DC number> <"on"/"during" or "off"/"before">'
    
    arg = [i.strip() for i in arg.strip().split("/")]
    arg  = [i.split(" ") for i in arg]
    
    for i in arg:
        if len(i)<1:
            await send_temp_messages(ctx, "Error: Missing <DC number>.", table.dc_list_str(), usage)
            return
        if len(i)<2:
            await send_temp_messages(ctx, "Error processing command: missing DC status for DC number {}.".format(i[0]), table.dc_list_str(), usage)
            return
        if len(i)>2:
            await send_temp_messages(ctx, "Too many arguments for player number {}. The only arguments should be <DC number> and <DC status>.".format(i[0]), table.dc_list_str(), usage)
        if not i[0].isnumeric():
            await send_temp_messages(ctx, "DC numbers must be numeric.", table.dc_list_str(), usage)
            return
        if not (i[1] == "on" or i[1]=='during') and not (i[1]=='off' or i[1] == "before"):
            await send_temp_messages(ctx, "The DC status argument must be either 'on'/'during' or 'off'/'before'.", table.dc_list_str(), usage)
        
    mes = table.edit_dc_status(arg)
    await send_messages(ctx, mes)
    
      
@dcs.error
async def dcs_error(ctx, error):
    global undo_empty, redo_empty
    undo_empty=redo_empty=False
    if confirm_room or confirm_reset:
        await send_temp_messages(ctx, "Please answer the last confirmation question:", choose_message)
        return
    if not table_running:
        await send_temp_messages(ctx, "You need to have an active table first before using ?dcs.")
        return
    
    if isinstance(error, commands.MissingRequiredArgument):
        await send_messages(ctx, table.dc_list_str(), '\nUsage: ?dcs <DC number> <"on"/"during" or "off"/"before">')
    
@bot.command()
async def sub(ctx, *args): #TODO
    global undo_empty, redo_empty
    undo_empty=redo_empty=False
    usage = "Usage: ?sub <sub out> <sub in>"
    if len(args)==0:
        await send_temp_messages(ctx, table.get_player_list(), usage)
        return
    if len(args)<2:
        await send_temp_messages(ctx, "Missing <sub in> player.", table.get_player_list(), usage)
        return
    subIn = args[1]
    subOut = args[0]
    if not (subIn.isnumeric() or subOut.isnumeric()):
        await send_temp_messages(ctx, "<sub in> and <sub out> must be numbers.", table.get_player_list(), usage)
        return
    mes = table.sub(subIn, subOut)
    await send_messages(ctx, mes)
    
@bot.command(aliases=['pl', 'players'])
async def playerlist(ctx):
    global undo_empty, redo_empty
    undo_empty=redo_empty=False
    if confirm_room or confirm_reset:
        await send_temp_messages(ctx, "Please answer the last confirmation question:", choose_message)
        return
    if not table_running:
        await send_temp_messages(ctx, "You need to have an active table first before using ?players.")
        return
    await send_messages(ctx, table.get_player_list())

@bot.command()
async def edit(ctx, *args):
    global undo_empty, redo_empty
    undo_empty=redo_empty=False
    usage = "Usage: ?edit <player id> <gp number> <gp score>"
    if confirm_room or confirm_reset:
        await send_temp_messages(ctx, "Please answer the last confirmation question:", choose_message)
        return
    if not table_running:
        await send_temp_messages(ctx, "You need to have an active table first before using ?edit.")
        return
    if len(args)==0:
        await send_temp_messages(ctx, table.get_player_list(), '\n',usage)
        return
    if len(args)<3:
        if len(args)<2:
            await send_temp_messages(ctx, "Missing <gp number>.", usage)
            return 
        await send_temp_messages(ctx, "Missing <gp score>.", usage)
        return
    pID = args[0]
    gp = args[1]
    score = args[2]
    if not pID.isnumeric():
        await send_temp_messages(ctx, "<player id> must be a number.", usage)
        return
    if not gp.isnumeric():
        await send_temp_messages(ctx, "<gp> must be a number.", usage)
        return
    if not score.lstrip('-').isnumeric() and not score.lstrip('+').isnumeric():
        await send_temp_messages(ctx, "<score> must be a number.", usage)
        return
    mes = table.edit(pID, gp, score)
    await send_messages(ctx, mes)

    
@bot.command(aliases = ['rr', 'res', 'results', 'race'])
async def raceresults(ctx, *args):
    global undo_empty, redo_empty
    undo_empty=redo_empty=False
    if confirm_room or confirm_reset:
        await send_temp_messages(ctx, "Please answer the last confirmation question:", choose_message)
        return
    if not table_running:
        await send_temp_messages(ctx, "You need to have an active table to be able to view race results.")
        return
    usage = "Usage: ?rr <race # = last race>"
    race = -1
    if len(args)>0:
        if not args[0].isnumeric():
            await send_temp_messages(ctx, "<race number> must be a number.", usage)
            return
        race = int(args[0])
    error, mes = table.race_results(race)
    if error:
        await send_temp_messages(ctx, mes, usage)
        return
    await send_messages(ctx, mes)
    
@bot.command(aliases=['tl', 'tracks', 'races'])
async def tracklist(ctx, *args):
    global undo_empty, redo_empty
    undo_empty=redo_empty=False
    if confirm_room or confirm_reset:
        await send_temp_messages(ctx, "Please answer the last confirmation question:", choose_message)
        return
    if not table_running:
        await send_temp_messages(ctx, "You need to have an active table to be able to view the tracklist.")
        return
    await send_messages(ctx, table.tracklist())
    
@bot.command(aliases=['rxx', 'rid', 'room'])
async def roomid(ctx):
    global undo_empty, redo_empty
    undo_empty=redo_empty=False
    if confirm_room or confirm_reset:
        await send_temp_messages(ctx, "Please answer the last confirmation question:", choose_message)
        return
    if not table_running:
        await send_temp_messages(ctx, "You need to have an active table to be able to view the room id.")
        return
    
    await send_messages(ctx, 'Current table is watching room: '+table.rxx)
  
@bot.command(aliases=['pen', 'pens'])
async def penalty(ctx, *args):
    global undo_empty, redo_empty
    undo_empty=redo_empty=False
    if confirm_room or confirm_reset:
        await send_temp_messages(ctx, "Please answer the last confirmation question:", choose_message)
        return
    if not table_running:
        await send_temp_messages(ctx, "You need to have an active table to use ?pens.")
        return
    usage = "Usage: ?pen <player id> <pen amount>"
    
    if len(args)==0:
        await send_messages(ctx, table.get_pen_player_list(), '\n'+usage)
        return
    pID = args[0].lower()
    if not pID.isnumeric():
        await send_temp_messages(ctx, "The player id needs to be a number.", usage)
        return
    if len(args)<2:
        await send_temp_messages(ctx, "Missing <pen amount>.",usage)
        return
    pen = args[1].lower()
    if not pen.lstrip('-').lstrip('=').isnumeric():
        await send_temp_messages(ctx, "The penalty amount must be a number (negative allowed).", usage)
        return
    
    mes = table.penalty(pID, pen)
    await send_messages(ctx, mes)

@bot.command(aliases=['unpen'])
async def unpenalty(ctx, *args):
    global undo_empty, redo_empty
    undo_empty=redo_empty=False
    if confirm_room or confirm_reset:
        await send_temp_messages(ctx, "Please answer the last confirmation question:", choose_message)
        return
    if not table_running:
        await send_temp_messages(ctx, "You need to have an active table to use ?pens.")
        return
    usage = "Usage: ?unpen <player id> <unpen amount = current pen>"
    
    if len(args)==0:
        await send_messages(ctx, table.get_pen_player_list(), '\n'+usage)
        return
    
    pID = args[0].lower()
    
    if not pID.isnumeric():
        await send_temp_messages(ctx, "The player id needs to be a number.", usage)
        return
    unpen = None
    if len(args)>1:
        unpen = args[1].lower()
    mes = table.unpenalty(pID, unpen)
    await send_messages(ctx, mes)
                            
@bot.command(aliases=['mr', 'merge'])
async def mergeroom(ctx, *args): #TODO
    global undo_empty, redo_empty
    undo_empty=redo_empty=False
    if confirm_room or confirm_reset:
        await send_temp_messages(ctx, "Please answer the last confirmation question:", choose_message)
        return
    if not table_running:
        await send_temp_messages(ctx, "You need to have an active table to be able to merge rooms.")
        return
    
    usage = 'Usage: ?mergeroom <rxx or host> <rxx or host mii name>'

@bot.command(aliases=['gp', 'gps', 'changegp'])
async def changegps(ctx, *args):
    global undo_empty, redo_empty
    undo_empty=redo_empty=False
    usage = "Usage: ?changegps <num gps>"
    if len(args)==0: 
        await send_temp_messages(ctx, usage)
        return
    try:
        gps = int(args[1])
        assert gps>0
    except:
        await send_temp_messages(ctx, "<num gps> must be a real number.", usage)
        return
    table.gps = gps
    await send_messages(ctx, "Changed total gps to {}.".format(gps))
    
@bot.command(aliases=['quickedit', 'qedit'])
async def editrace(ctx, *, arg):
    global undo_empty, redo_empty
    undo_empty=redo_empty=False
    if confirm_room or confirm_reset:
        await send_temp_messages(ctx, "Please answer the last confirmation question:", choose_message)
        return
    if not table_running:
        await send_temp_messages(ctx, "You need to have an active table to be able to merge rooms.")
        return
    usage = "Usage: ?editrace <race number> <player id> <corrected placement>"
    arg = [i.strip() for i in arg.strip().split("/")]
    arg  = [i.split(" ") for i in arg]
    if len(arg)==0:
        await send_temp_messages(ctx, table.get_player_list(), '\n',usage)
        return
    for i in arg:
        if len(i)<1:
            await send_temp_messages(ctx, "Missing <race number> for command.", table.get_player_list(), '\n',usage)
            return
        if len(i)<2:
            await send_temp_messages(ctx, "Error processing command: missing players for command on race {}".format(i[0]), table.get_player_list(), usage)
            return
        if len(i)<3:
            await send_temp_messages(ctx, "Error: missing <corrected placement> for race {}, player {}.".format(i[0], i[1]), table.get_player_list(), usage)
        
        for t in i:
            if not t.isnumeric():
                await send_temp_messages(ctx, "Argument '{}' for the command must be a real number.".format(t), table.get_player_list(), usage)
                return
            
    mes = table.edit_race(arg)
    await send_messages(ctx, mes)
    
@editrace.error
async def editrace_error(ctx, error):
    global undo_empty, redo_empty
    undo_empty=redo_empty=False
    if isinstance(error, commands.MissingRequiredArgument):
        await send_messages(ctx, table.get_player_list(),"\nUsage: ?editrace <race number> <player id> <corrected placement>")

@bot.command(aliases=['crs', 'roomsize'])
async def changeroomsize(ctx, *, arg): #TODO: editing room size (for when mkwx bugs and shows wrong players)
    global undo_empty, redo_empty
    undo_empty=redo_empty=False
    if confirm_room or confirm_reset:
        
        await send_temp_messages(ctx, "Please answer the last confirmation question:", choose_message)
        return
    if not table_running:
        await send_temp_messages(ctx, "You need to have an active table to be able to merge rooms.")
        return
    usage = "Usage: ?changeroomsize <race number> <corrected room size (num players)>"
    arg = [i.strip() for i in arg.strip().split("/")]
    arg  = [i.split(" ") for i in arg]
    if len(arg)==0:
        await send_temp_messages(ctx, usage)
        return
    for i in arg:
        if len(i)<1:
            await send_temp_messages(ctx, "Missing <race number> for command.",usage)
            return
        if len(i)<2:
            await send_temp_messages(ctx, "Error processing command: missing <corrected room size> for race {}".format(i[0]), usage)
            return
    mes = table.change_room_size(arg)
    await send_messages(ctx, mes)
    
@changeroomsize.error
async def changeroomsize_error(ctx, error):
    global undo_empty, redo_empty
    undo_empty=redo_empty=False
    if isinstance(error, commands.MissingRequiredArgument):
        await send_messages(ctx, "Usage: ?changeroomsize <race number> <corrected room size (num players)>")
    
    
@bot.command(name='help',aliases = ['h'])
async def _help(ctx):
    global undo_empty, redo_empty
    undo_empty=redo_empty=False
    info = 'List of commands:\n\t**?start**\n\t**?search**\n\t**?reset**\n\t**?players**\n\t**?tracks**\n\t**?rxx**\n\t**?raceresults\n\t?editrace\n\t?changeroomsize\n\t?dcs\n\t?penalty, ?unpenalty\n\t?tags\n\t?edittag\n\t?changetag\n\t?changegps\n\t?edit\n\t?undo, ?redo\n\t?pic**'
    await send_messages(ctx, info)
    
bot.run(KEY)