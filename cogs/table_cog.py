# -*- coding: utf-8 -*-
"""
Created on Wed May 19 08:33:13 2021

@author: ryanz
"""

import discord
from discord.ext import commands, tasks
from cogs.tabler import Table

class table_bot(commands.Cog):
    def __init__(self, bot):
        self.home_url = "https://wiimmfi.de/stats/mkwx/list/"
        self.bot = bot
        self.table = Table()
        self.choose_message = ""
        self.searching_room = False
        self.choose_room = False
        self.confirm_room = False
        self.confirm_reset = False
        #confirm_message = ''
        self.reset_args = None
        self.undo_empty = False
        self.redo_empty = False
        
        self.num_players = 0
        self.gps = 0
        self.teams = 0
        self._format = ''
        self.table_running = False
    
    @commands.Cog.listener()
    async def on_ready(self):
        print("Bot logged in as {0.user}".format(self.bot))
        
    async def send_temp_messages(self,ctx, *args):
        await ctx.send('\n'.join(args), delete_after=25)
    async def send_messages(self,ctx, *args):
        await ctx.send('\n'.join(args))
       
    @commands.Cog.listener()
    async def on_command_error(self,ctx, error):
        if isinstance(error, commands.CommandNotFound):
            await ctx.send("{}.\nType ?help for a list of commands.".format(error.__str__().replace("is not found", "is not a valid command")))
        #else:
            #await ctx.send(error)
      
    #default max teams based on format (currently used for ffa format only)
    def max_teams(self,f):
        f = f[0]
        if f == 'f':
            return 12
        else:
            f = int(f)
            return 12/f
        
    #check if number of teams exceeds max possible teams for format
    def check_teams(self,f, teams):
        max_t = self.max_teams(f)
        if teams>max_t: return True
        return False
    
    def get_num_players(self,f, teams):
        f = f[0]
        if f == 'f':
            f = 1
        else: f = int(f)
        
        return teams*f
    
    async def check_callable(self, ctx, command): #for most commands
        if self.confirm_room or self.confirm_reset:
            await self.send_temp_messages(ctx, "Please answer the last confirmation question:", self.choose_message)
            return True
        if command in ['yes', 'no']:
            if not self.choose_room:
                await self.send_temp_messages(ctx, "You can only use ?{} if the bot prompts you to do so.".format(command))
                return True
        else:
            if not self.table_running:
                await self.send_temp_messages(ctx, "You need to have an active table before using ?{}.".format(command))
                return True
            
    async def check_special_callable(ctx,self): #used for commands that can be used when confirm_room == True
        if self.confirm_reset or( self.confirm_room and self.table_running):
            await self.send_temp_messages(ctx, "Please answer the last confirmation question:", self.choose_message)
            return True
        if not (self.confirm_room and not self.table_running) and not self.table_running:
            await self.send_temp_messages(ctx, "You can only use this command if the bot prompts you or a table is currently active.")
            return True
    
    #?start
    @commands.command(aliases=['st', 'starttable', 'sw'])
    async def start(self,ctx, *args):
        self.undo_empty=self.redo_empty=False
        
        if self.confirm_room or self.confirm_reset:
            await self.send_temp_messages(ctx, "Please answer the last confirmation question:", self.choose_message)
            return
        if self.table_running:
            self.confirm_reset = True
            self.reset_args = args
            self.choose_message= "A tabler watching room {} is currently active.\nAre you sure you want to start a new table? (?yes/?no)".format(self.table.rxx)
            await self.send_messages(ctx, self.choose_message)
            return
        usage = "Usage: ?start <format> <number of teams> <gps = 3>"
        
        if isinstance(args[0], tuple) and self.reset_args !=None:
            args = args[0]
        
        if len(args)<1:
            await self.send_temp_messages(ctx, usage)
            return
        self._format = args[0].lower()
        
        if len(args)<2 and self._format[0]!='f':
            await self.send_temp_messages(ctx, "Missing <teams>.", usage)
            return
        
        
        if self._format not in ['ffa', '2v2', '3v3', '4v4', '5v5', '6v6', '2', '3', '4', '5', '6']:
            await self.send_messages(ctx, "Invalid format. Format must be FFA, 2v2, 3v3, 4v4, 5v5, or 6v6.", usage)
            return
        
        self.teams = self.max_teams(self._format)
        if len(args)>1:
            try:
                self.teams = int(args[1].lower())
            except:
                await self.send_messages(ctx, "Invalid use of ?start: <teams> must be an integer.", usage)
                return
        
        if self.check_teams(self._format, self.teams):
            await self.send_messages(ctx, "Invalid number of teams. The number of teams cannot exceed 12 players.", usage)
            return
        self.table.format = self._format
        self.table.teams = self.teams
        self.num_players = self.get_num_players(self._format, self.teams)    
        self.gps = 3
        if len(args)>2:
            
            arg3 = args[2].lower()
            if arg3.isnumeric():
                self.gps = arg3
                self.table.gps = self.gps
            else:
                rxx = [arg3]
                wait_mes = await ctx.send('Searching for room...')
                error, ask, self.choose_message = self.table.find_room(rid = rxx)
                await wait_mes.delete()
                if error:
                    if ask=='reset':
                        self.table = Table()
                    await self.send_messages(ctx, self.choose_message, usage)
                    return
                if ask=="confirm":
                    self.confirm_room = True
                    if self.table.format[0] == 'f':
                        mes = "Table successfully started. Watching room {}.\n?pic to get table picture.".format(self.table.rxx)
                        self.table_running = True
                        await self.send_messages(ctx, mes)
                        self.searching_room = False
                        self.confirm_room = False
                        return
                        
                    await self.send_messages(ctx, self.choose_message)
                    return
            
        self.searching_room = True   
        await self.send_messages(ctx, "Provide a room id (rxx) or mii name(s) in the room.", "Make sure at least one race in the room has finished.", "Usage: ?search <rxx or mii> <rxx or mii names(s)>")
    
    #?search   
    @commands.command(aliases=['sr'])  
    async def search(self,ctx, *, arg):
        self.undo_empty=self.redo_empty=False
        
        if self.confirm_room or self.confirm_reset:
            await self.send_temp_messages(ctx, "Please answer the last confirmation question:", self.choose_message)
            return
       
        if not self.searching_room:
            await self.send_messages(ctx, "You cannot search for a room if a table is currently running or a table hasn't been started yet.")
            return
        
        arg = arg.strip()
        
        usage = "Usage: ?search <rxx or mii> <rxx or name(s)>\nmkwx room list: {}".format(self.home_url)
        if len(arg)<1:
            await self.send_temp_messages(ctx, usage)
            return
         
        arg_indx = arg.find(' ')
        if arg_indx == -1: arg_indx = len(arg)+1
        search_type = arg[:arg_indx].lower()
        search_args = arg[arg_indx+1:].split(",")
        search_args = [i.lower().strip() for i in search_args]
        
        #print(search_args)
        if len(search_args)<1:
            await self.send_messages("You need to provide <rxx or mii name(s)>.", usage)
        if len(search_args)>self.num_players:
            await self.send_messages(ctx, "You cannot provide more than {} mii names.".self.format(self.num_players), usage)
            return
        
        if search_type == 'roomid' or search_type=='rxx':
            print("ds")
            if search_args[0].isnumeric():
                await self.send_messages(ctx, "Invalid room id: missing an 'r' or not in format 'XX00'.", usage)
                return
            wait_mes = await ctx.send('Searching for room...')
            error, ask, self.choose_message = self.table.find_room(rid = search_args)
        elif search_type == "mii":   
            wait_mes = await ctx.send('Searching for room...')
            error, ask, self.choose_message = self.table.find_room(mii = search_args)
        else:
            await self.send_messages(ctx, "Invalid argument for ?search: <search type> must be 'rxx' or 'mii'", usage)
            return
        await wait_mes.delete()
        if error:
            if ask=='reset':
                self.table = Table()
            await self.send_messages(ctx, self.choose_message, usage)
            return
        
        if ask == "match":
            self.choose_room= True
            
            await self.send_messages(ctx, "There were more than one possible matching rooms. Choose the desired room number.", self.choose_message)
            return
        elif ask=="confirm":
            self.confirm_room = True
            await self.send_messages(ctx, self.choose_message)
            return
    
    @search.error
    async def search_error(self,ctx, error):
        self.undo_empty=self.redo_empty=False
        if isinstance(error, commands.MissingRequiredArgument):
            await self.send_messages(ctx, "Usage: ?search <rxx or mii> <rxx or name(s)>\nmkwx room list: {}".format(self.home_url)) 
    
    #change one player's tag
    @commands.command()
    async def changetag(self,ctx, *args): 

        self.undo_empty=self.redo_empty=False
        
        if self.check_special_callable(ctx)[0]: return
        
        usage = "Usage: ?changetag <player id> <corrected tag>"
        if len(args)==0:
            await self.send_temp_messages(ctx, self.table.get_player_list(),'\n',usage)
            return
        
        pID = args[0].lower()
        if not pID.isnumeric():
            await self.send_temp_messages(ctx, "<player id> must be a number.", usage)
            return
        if len(args)<2:
            await self.send_temp_messages(ctx, "missing <corrected tag> parameter.", usage)
            return
        
        tag = args[1]
        mes= self.table.change_tag(pID, tag)
        if self.confirm_room:
            self.choose_message = self.table.get_player_list() +"\nIs this correct? (?yes / ?no)"
            await self.send_messages(ctx, mes, self.table.get_player_list(), '\n', "Is this correct? (?yes / ?no)")
        else:
            await self.send_messages(ctx, mes)
        
    @commands.command(aliases=['et', 'edittags']) 
    async def edittag(self,ctx, *, arg): 
        self.undo_empty=self.redo_empty=False
        usage = 'Usage: ?edittag <tag> <corrected tag>'
        if self.check_special_callable(ctx)[0]: return
        
        arg = [i.strip() for i in arg.strip().split("/")]
        arg  = [i.split(" ") for i in arg]
        if len(arg)==0:
            await self.send_temp_messages(ctx, self.table.get_player_list(), '\n', usage)
        for i in arg:
            if len(i)<1:
                await self.send_temp_messages(ctx, "Missing tag(s) for command.", self.table.get_player_list(), '\n',usage)
                return
            if len(i)<2:
                await self.send_temp_messages(ctx, "Error processing command: missing <corrected tag> for tag '{}'".format(i[0]), self.table.get_player_list(), usage)
                return
        
        
        mes = self.table.edit_tag_name(arg)
        if self.confirm_room:
            self.choose_message = self.table.get_player_list() +"\nIs this correct? (?yes / ?no)"
            await self.send_messages(ctx, mes, self.table.get_player_list(), '\n', "Is this correct? (?yes / ?no)")
        else:
            await self.send_messages(ctx, mes)
            
    @edittag.error
    async def edittag_error(self,ctx, error):
        
        self.undo_empty=self.redo_empty=False
        if self.check_special_callable(ctx)[0]: return
        if isinstance(error, commands.MissingRequiredArgument):
            await self.send_messages(ctx, self.table.get_player_list(),'\nUsage: ?edittag <tag> <corrected tag>')    
    
    #to manually create tags
    @commands.command(aliases=['tag'])
    async def tags(self,ctx, *, arg): 
        self.undo_empty=self.redo_empty=False
        usage = "Usage: ?tags <tag> <pID pID> / <tag> <pID pID>\n**ex.** ?tags Player 1 3 / Z 2 4 / B 5 6"
        if self.check_special_callable(ctx)[0]: return
        
        arg = [i.strip() for i in arg.strip().split("/")]
        arg  = [i.split(" ") for i in arg]
        if len(arg)==0:
            await self.send_temp_messages(ctx, self.table.get_player_list(), '\n',usage)
            return
        for i in arg:
            if len(i)<1:
                await self.send_temp_messages(ctx, "Missing tag(s) for command.", self.table.get_player_list(), '\n',usage)
                return
            if len(i)<2:
                await self.send_temp_messages(ctx, "Error processing command: missing players for tag '{}'".format(i[0]), self.table.get_player_list(), usage)
                return
            for indx, j in enumerate(i[1:]):
                if not j.isnumeric():
                    await self.send_temp_messages(ctx, "Error processing players for tag '{}': {} is not a number. All players must be numeric.".format(i[0], i[indx]), usage)
                    return 
        dic = {}
        for i in arg:
            dic[i[0]] = i[1:]
        
        mes = self.table.group_tags(dic)
        self.choose_message = self.table.get_player_list() +"\nIs this correct? (?yes / ?no)"
        await self.send_messages(ctx, mes, self.table.get_player_list(), "\nIs this correct? (?yes / ?no)")
        
    @tags.error
    async def tags_error(self,ctx, error):
        self.undo_empty=self.redo_empty=False
        if self.check_special_callable(ctx)[0]: return
        if isinstance(error, commands.MissingRequiredArgument):
            await self.send_messages(ctx, self.table.get_player_list(), "\nUsage: ?tags <tag> <pID pID> / <tag> <pID pID>\n**ex.** ?tags Player 1 3 / Z 2 4 / B 5 6")
    
    @commands.command(aliases=['y'])
    async def yes(self,ctx, *args):
        self.undo_empty=self.redo_empty=False
        if not self.confirm_room and not self.confirm_reset:
            await self.send_temp_messages(ctx, "You can only use ?yes if the bot prompts you to do so.")
            return
        
        if self.confirm_room:
            if self.choose_room: self.choose_room = False
            mes = "Table successfully started. Watching room {}.\n?pic to get table picture.".format(self.table.rxx)
            self.table_running = True
            await self.send_messages(ctx, mes)
            self.searching_room = False
            self.confirm_room = False
        elif self.confirm_reset:
            self.table = Table()
            self.table_running=False
            self.confirm_reset = False
            await self.send_messages(ctx, "Table has been reset.")
            await self.start(ctx, self.reset_args)
        
    @commands.command(aliases=['n'])
    async def no(self,ctx, *args):
        self.undo_empty=self.redo_empty=False
        if not self.confirm_room and not self.confirm_reset:
            await self.send_temp_messages(ctx, "You can only use ?no if the bot prompts you to do so.")
            return 
        if self.confirm_room:
            self.confirm_room = False
            self.table = Table()
            #await send_messages(ctx, "Search for a room with ?search <search type> <room id or mii name(s)>")
            await self.send_messages(ctx, "Start a new table with ?start.")
           
        elif self.confirm_reset:
            self.confirm_reset = False
            await self.send_messages(ctx, "Tabler watching room {} will continue running.".format(self.table.rxx))
     
    #choose correct room if multiple matches from mii name search
    @commands.command(aliases=['ch'])
    async def choose(self,ctx, *args):
        self.undo_empty=self.redo_empty=False
        if await self.check_callable(ctx, "choose"): return
        usage = "Usage: ?choose <room index #>"
        
        room = args[0].lower()
        count = self.choose_message.count("Players in room:")
        indices = range(1, count+1)
        if room not in indices:
            await self.send_messages(ctx, "Invalid room index: the room index should be from {} to {}.".format(indices[0], indices[-1]), usage)
            return
        #TODO: show them chosen room, and ask if it it correct ?yes or ?no or ?changetag
        #await send_messages(ctx, )
    
    #?picture
    @commands.command(aliases=['p', 'pic', 'wp'])
    @commands.max_concurrency(number=1, wait=True)
    async def picture(self,ctx, *args):
        self.undo_empty=self.redo_empty=False

        if await self.check_callable(ctx, "pic"): return
        
        wait_mes = await ctx.send("Updating scores...")
        mes = self.table.update_table()
        await wait_mes.edit(content="Fetching table picture. Please wait...")
        img = await self.table.get_table_img()
        await wait_mes.edit(content=mes)
        
        f=discord.File(fp=img, filename='table.png')
        em = discord.Embed(title=self.table.tag_str(), color=0x00ff6f)
        
        value_field = "[Edit this table on gb.hlorenzi.com]("+self.table.table_link+")"
        em.add_field(name='\u200b', value= value_field, inline=False)
        em.set_image(url='attachment://table.png')
        em.set_footer(text = self.table.get_warnings())
        
        await ctx.send(embed=em, file=f)
    
    @commands.command()
    async def undo(self,ctx, *args):
        self.redo_empty = False
        if await self.check_callable(ctx, "undo"): return
        
        usage = 'Usage: ?undo <modification number ("all" if you want to undo all)>'
        
        if self.undo_empty and len(args)==0:
            mes = self.table.undo_commands(-1)
            await self.send_messages(ctx, mes)
            self.undo_empty = False
            return
        if len(args)==0:
            await self.send_messages(ctx, self.table.get_modifications(), '\n'+usage)
            self.undo_empty = True
            return
        
        else:
            if args[0].lower()=='all':
                args = 0
            elif args[0].isnumeric():
                args = int(args[0])
            else:
                await self.send_temp_messages(ctx, "{} is not a valid parameter for ?undo. The only valid parameters are 'all' and numbers.".format(args[0]), usage)
                return
        self.undo_empty = False   
        mes = self.table.undo_commands(args)
        await self.send_messages(ctx,mes)
        
    @commands.command()
    async def redo(self,ctx, *args):
        self.undo_empty = False
        if await self.check_callable(ctx, "redo"): return
        
        usage = 'Usage: ?redo <undo number ("all" if you want to redo all)>'
        
        if self.redo_empty and len(args)==0:
            mes = self.table.redo_commands(-1)
            await self.send_messages(ctx, mes)
            self.redo_empty = False
            return
        if len(args)==0:
            await self.send_messages(ctx, self.table.get_undos(), '\n'+usage)
            self.redo_empty = True
            return
        else:
            if args[0].lower()=='all':
                args = 0
            elif args[0].isnumeric():
                args = int(args[0])
            else:
                await self.send_temp_messages(ctx, "{} is not a valid parameter for ?redo. The only valid parameters are 'all' and a number.".format(args[0]), usage)
                return
        self.redo_empty = False
        mes = self.table.redo_commands(args)
        await self.send_messages(ctx,mes)
       
     
    #?reset
    @commands.command()
    async def reset(self,ctx, *args):
        self.undo_empty=self.redo_empty=False
        
        if not self.table_running and not self.confirm_room:
            await self.send_temp_messages(ctx, "You need to have an active table to be able to reset.")
            return
        
        self.table = Table()
        self.table_running = False
        self.choose_message = None 
        self.confirm_reset = False
        self.confirm_room= False
        await self.send_messages(ctx, "Reset the table. ?start to start a new table.")
    
    @commands.command(aliases = ['dc'])
    async def dcs(self,ctx, *, arg): 
        self.undo_empty=self.redo_empty=False
        if await self.check_callable(ctx, "dcs"): return
        
        usage = '\nUsage: ?dcs <DC number> <"on"/"during" or "off"/"before">'
        
        arg = [i.strip() for i in arg.strip().split("/")]
        arg  = [i.split(" ") for i in arg]
        
        for i in arg:
            if len(i)<1:
                await self.send_temp_messages(ctx, "Error: Missing <DC number>.", self.table.dc_list_str(), usage)
                return
            if len(i)<2:
                await self.send_temp_messages(ctx, "Error processing command: missing DC status for DC number {}.".format(i[0]), self.table.dc_list_str(), usage)
                return
            if len(i)>2:
                await self.send_temp_messages(ctx, "Too many arguments for player number {}. The only arguments should be <DC number> and <DC status>.".format(i[0]), self.table.dc_list_str(), usage)
            if not i[0].isnumeric():
                await self.send_temp_messages(ctx, "DC numbers must be numeric.", self.table.dc_list_str(), usage)
                return
            if not (i[1] == "on" or i[1]=='during') and not (i[1]=='off' or i[1] == "before"):
                await self.send_temp_messages(ctx, "The DC status argument must be either 'on'/'during' or 'off'/'before'.", self.table.dc_list_str(), usage)
            
        mes = self.table.edit_dc_status(arg)
        await self.send_messages(ctx, mes)
        
          
    @dcs.error
    async def dcs_error(self,ctx, error):
        self.undo_empty=self.redo_empty=False
        if await self.check_callable(ctx, "dcs"): return
        
        if isinstance(error, commands.MissingRequiredArgument):
            await self.send_messages(ctx, self.table.dc_list_str(), '\nUsage: ?dcs <DC number> <"on"/"during" or "off"/"before">')
    '''   
    @commands.command()
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
    '''
        
    @commands.command(aliases=['pl', 'players'])
    async def playerlist(self,ctx):
        self.undo_empty=self.redo_empty=False
        if await self.check_callable(ctx, "players"): return
        await self.send_messages(ctx, self.table.get_player_list())
    
    @commands.command()
    async def edit(self,ctx, *args):
        self.undo_empty=self.redo_empty=False
        usage = "Usage: ?edit <player id> <gp number> <gp score>"
        if await self.check_callable(ctx, "edit"): return
        
        if len(args)==0:
            await self.send_temp_messages(ctx, self.table.get_player_list(), '\n',usage)
            return
        if len(args)<3:
            if len(args)<2:
                await self.send_temp_messages(ctx, "Missing <gp number>.", usage)
                return 
            await self.send_temp_messages(ctx, "Missing <gp score>.", usage)
            return
        pID = args[0]
        gp = args[1]
        score = args[2]
        if not pID.isnumeric():
            await self.send_temp_messages(ctx, "<player id> must be a number.", usage)
            return
        if not gp.isnumeric():
            await self.send_temp_messages(ctx, "<gp> must be a number.", usage)
            return
        if not score.lstrip('-').isnumeric() and not score.lstrip('+').isnumeric():
            await self.send_temp_messages(ctx, "<score> must be a number.", usage)
            return
        mes = self.table.edit(pID, gp, score)
        await self.send_messages(ctx, mes)
    
        
    @commands.command(aliases = ['rr', 'res', 'results', 'race'])
    async def raceresults(self,ctx, *args):
        self.undo_empty=self.redo_empty=False
        if await self.check_callable(ctx, "raceresults"): return
        usage = "Usage: ?rr <race # = last race>"
        race = -1
        if len(args)>0:
            if not args[0].isnumeric():
                await self.send_temp_messages(ctx, "<race number> must be a number.", usage)
                return
            race = int(args[0])
        error, mes = self.table.race_results(race)
        if error:
            await self.send_temp_messages(ctx, mes, usage)
            return
        await self.send_messages(ctx, mes)
        
    @commands.command(aliases=['tl', 'tracks', 'races'])
    async def tracklist(self,ctx, *args):
        self.undo_empty=self.redo_empty=False
        if await self.check_callable(ctx, "tracklist"): return
        await self.send_messages(ctx, self.table.tracklist())
        
    @commands.command(aliases=['rxx', 'rid', 'room'])
    async def roomid(self, ctx):
        self.undo_empty=self.redo_empty=False
        if await self.check_callable(ctx, "rxx"): return
        
        await self.send_messages(ctx, 'Current table is watching room: '+self.table.rxx)
      
    @commands.command(aliases=['pen', 'pens'])
    async def penalty(self, ctx, *args):
        self.undo_empty=self.redo_empty=False
        if await self.check_callable(ctx, "penalty"): return
        usage = "Usage: ?pen <player id> <pen amount>"
        
        if len(args)==0:
            await self.send_messages(ctx, self.table.get_pen_player_list(), '\n'+usage)
            return
        pID = args[0].lower()
        if not pID.isnumeric():
            await self.send_temp_messages(ctx, "The player id needs to be a number.", usage)
            return
        if len(args)<2:
            await self.send_temp_messages(ctx, "Missing <pen amount>.",usage)
            return
        pen = args[1].lower()
        if not pen.lstrip('-').lstrip('=').isnumeric():
            await self.send_temp_messages(ctx, "The penalty amount must be a number (negative allowed).", usage)
            return
        
        mes = self.table.penalty(pID, pen)
        await self.send_messages(ctx, mes)
    
    @commands.command(aliases=['unpen'])
    async def unpenalty(self, ctx, *args):
        self.undo_empty=self.redo_empty=False
        if await self.check_callable(ctx, "unpenalty"): return
        usage = "Usage: ?unpen <player id> <unpen amount = current pen>"
        
        if len(args)==0:
            await self.send_messages(ctx, self.table.get_pen_player_list(), '\n'+usage)
            return
        
        pID = args[0].lower()
        
        if not pID.isnumeric():
            await self.send_temp_messages(ctx, "The player id needs to be a number.", usage)
            return
        unpen = None
        if len(args)>1:
            unpen = args[1].lower()
        mes = self.table.unpenalty(pID, unpen)
        await self.send_messages(ctx, mes)
                                
    @commands.command(aliases=['mr', 'merge'])
    async def mergeroom(self, ctx, *args): #TODO
        self.undo_empty=self.redo_empty=False
        if await self.check_callable(ctx, "mergeroom"): return
        
        usage = 'Usage: ?mergeroom <rxx or host> <rxx or host mii name>'
    
    @commands.command(aliases=['gp', 'gps', 'changegp'])
    async def changegps(self, ctx, *args):
        self.undo_empty=self.redo_empty=False
        if await self.check_callable(ctx, "changegps"): return
        usage = "Usage: ?changegps <num gps>"
        if len(args)==0: 
            await self.send_temp_messages(ctx, usage)
            return
        try:
            gps = int(args[1])
            assert gps>0
        except:
            await self.send_temp_messages(ctx, "<num gps> must be a real number.", usage)
            return
        self.table.gps = self.gps = gps
        await self.send_messages(ctx, "Changed total gps to {}.".format(self.gps))
        
    @commands.command(aliases=['quickedit', 'qedit'])
    async def editrace(self,ctx, *, arg):
        self.undo_empty=self.redo_empty=False
        if await self.check_callable(ctx, "editrace"): return
        
        usage = "Usage: ?editrace <race number> <player id> <corrected placement>"
        arg = [i.strip() for i in arg.strip().split("/")]
        arg  = [i.split(" ") for i in arg]
        if len(arg)==0:
            await self.send_temp_messages(ctx, self.table.get_player_list(), '\n',usage)
            return
        for i in arg:
            if len(i)<1:
                await self.send_temp_messages(ctx, "Missing <race number> for command.", self.table.get_player_list(), '\n',usage)
                return
            if len(i)<2:
                await self.send_temp_messages(ctx, "Error processing command: missing players for command on race {}".format(i[0]), self.table.get_player_list(), usage)
                return
            if len(i)<3:
                await self.send_temp_messages(ctx, "Error: missing <corrected placement> for race {}, player {}.".format(i[0], i[1]), self.table.get_player_list(), usage)
            
            for t in i:
                if not t.isnumeric():
                    await self.send_temp_messages(ctx, "Argument '{}' for the command must be a real number.".format(t), self.table.get_player_list(), usage)
                    return
                
        mes = self.table.edit_race(arg)
        await self.send_messages(ctx, mes)
        
    @editrace.error
    async def editrace_error(self, ctx, error):
        self.undo_empty=self.redo_empty=False
        if await self.check_callable(ctx, 'editrace'): return
        if isinstance(error, commands.MissingRequiredArgument):
            await self.send_messages(ctx, self.table.get_player_list(),"\nUsage: ?editrace <race number> <player id> <corrected placement>")
    
    @commands.command(aliases=['crs', 'roomsize'])
    async def changeroomsize(self, ctx, *, arg): 
        self.undo_empty=self.redo_empty=False
        if await self.check_callable(ctx, "changeroomsize"): return
        
        usage = "Usage: ?changeroomsize <race number> <corrected room size (num players)>"
        arg = [i.strip() for i in arg.strip().split("/")]
        arg  = [i.split(" ") for i in arg]
        if len(arg)==0:
            await self.send_temp_messages(ctx, usage)
            return
        for i in arg:
            if len(i)<1:
                await self.send_temp_messages(ctx, "Missing <race number> for command.",usage)
                return
            if len(i)<2:
                await self.send_temp_messages(ctx, "Error processing command: missing <corrected room size> for race {}".format(i[0]), usage)
                return
        mes = self.table.change_room_size(arg)
        await self.send_messages(ctx, mes)
        
    @changeroomsize.error
    async def changeroomsize_error(self, ctx, error):
        self.undo_empty=self.redo_empty=False
        if await self.check_callable(ctx, "changeroomsize"): return
        if isinstance(error, commands.MissingRequiredArgument):
            await self.send_messages(ctx, "Usage: ?changeroomsize <race number> <corrected room size (num players)>")
        
        
    @commands.command(name='help',aliases = ['h'])
    async def _help(self,ctx):
        self.undo_empty=self.redo_empty=False
        info = 'List of commands:\n\t**?start**\n\t**?search**\n\t**?reset**\n\t**?players**\n\t**?tracks**\n\t**?rxx**\n\t**?raceresults\n\t?editrace\n\t?changeroomsize\n\t?dcs\n\t?penalty, ?unpenalty\n\t?tags\n\t?edittag\n\t?changetag\n\t?changegps\n\t?edit\n\t?undo, ?redo\n\t?pic**'
        await self.send_messages(ctx, info)
    
#bot.run(KEY)
def setup(bot):
    bot.add_cog(table_bot((bot)))