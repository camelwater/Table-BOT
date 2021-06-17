# -*- coding: utf-8 -*-
"""
Created on Wed May 19 08:33:13 2021

@author: ryanz
"""

import discord
from discord.ext import commands, tasks
from cogs.tabler import Table
from itertools import cycle
import Utils

class table_bot(commands.Cog):
    def __init__(self, bot):
        self.home_url = "https://wiimmfi.de/stats/mkwx/list/"
        self.bot = bot
        self.table_instances = {}
        self.presences = cycle(['?help for help', '{} active tables'])
        self.TESTING = False
        
        if self.TESTING:
            table = Table()
            table.players = {'pringle@MV':0,'5headMV':0,'hello MV':0,'LTAX':0,'jaja LTA':0,'stupid@LTA':0,'MV poop':0,'MVMVMVMV':0,
                            'LTA Valpo':0,"Mom's LTA":0}
            table.split_teams('5', 2)
        
    
    @commands.Cog.listener()
    async def on_ready(self):
        print("Bot logged in as {0.user}".format(self.bot))
        if not self.cycle_presences.is_running():
            try:
                self.cycle_presences.start()
            except:
                pass
    
    @tasks.loop(seconds=15)
    async def cycle_presences(self):
        next_pres = next(self.presences)
        if "active tables" in next_pres:
            active_tables= self.get_active_tables()
            next_pres = next_pres.format(active_tables)
            if active_tables==1: next_pres = next_pres.replace("tables", "table")
        pres = discord.Activity(type=discord.ActivityType.watching, name=next_pres)
        await self.bot.change_presence(status=discord.Status.online, activity=pres)
                
    def get_active_tables(self):
        count = 0
        for t in list(self.table_instances.values()):
            if t.table_running:
                count+=1
        return count
    
    def set_instance(self, ctx):
        channel_id = ctx.message.channel.id
        if channel_id not in self.table_instances:
            self.table_instances[channel_id] = Table()
        self.table_instances[ctx.channel.id].ctx = ctx
     
    async def send_temp_messages(self,ctx, *args):
        await ctx.send('\n'.join(args), delete_after=25)
    async def send_messages(self,ctx, *args):
        await ctx.send('\n'.join(args))
       
    @commands.Cog.listener()
    async def on_command_error(self,ctx, error):
        self.set_instance(ctx)
        
        if isinstance(error, commands.CommandNotFound):
            await ctx.send("{}.\nType ?help for a list of commands.".format(error.__str__().replace("is not found", "doesn't exist")))
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send("This command can only be used once every {} seconds. You can retry in {:.1f} seconds.".format(error.cooldown.per, error.retry_after))
        elif isinstance(error, commands.MaxConcurrencyReached):
            await ctx.send("This command can only be used by {} user at a time. Try again later.".format(error.number))
        elif isinstance(error, commands.MissingRequiredArgument):
            raise error
        else:
            await ctx.send("There was an unidentified internal bot error. Wait a bit and try again later.\nIf the issue persists, ?reset the table.")
            raise error

    async def check_callable(self, ctx, command): #for most commands
        if self.table_instances[ctx.channel.id].confirm_room or self.table_instances[ctx.channel.id].confirm_reset:
            await self.send_temp_messages(ctx, "Please answer the last confirmation question:", self.table_instances[ctx.channel.id].choose_message)
            return True
        if command in ['yes', 'no']:
            if not self.table_instances[ctx.channel.id].choose_room:
                await self.send_temp_messages(ctx, "You can only use ?{} if the bot prompts you to do so.".format(command))
                return True
        else:
            if not self.table_instances[ctx.channel.id].table_running:
                await self.send_temp_messages(ctx, "You need to have an active table before using ?{}.".format(command))
                return True
            
    async def check_special_callable(self, ctx): #used for commands that can be used when confirm_room == True
        if self.table_instances[ctx.channel.id].confirm_reset or(self.table_instances[ctx.channel.id].confirm_room and self.table_instances[ctx.channel.id].table_running):
            await self.send_temp_messages(ctx, "Please answer the last confirmation question:", self.table_instances[ctx.channel.id].choose_message)
            return True
        if not (self.table_instances[ctx.channel.id].confirm_room and not self.table_instances[ctx.channel.id].table_running) and not self.table_instances[ctx.channel.id].table_running:
            await self.send_temp_messages(ctx, "You can only use this command if the bot prompts you or a table is currently active.")
            return True
        
    async def skip_search(self, ctx, rxx):
        usage = "Usage: ?start <format> <number of teams> <gps = 3>"
        wait_mes = await ctx.send('Searching for room...')
        error, ask, self.table_instances[ctx.channel.id].choose_message = await self.table_instances[ctx.channel.id].find_room(rid = rxx)
        
        if error:
            if ask=='reset':
                self.table_instances.pop(ctx.message.channel.id)
            await wait_mes.delete()
            await self.send_messages(ctx, self.table_instances[ctx.channel.id].choose_message, usage)
            return
        if ask=="confirm":
            self.table_instances[ctx.channel.id].confirm_room = True
            if self.table_instances[ctx.channel.id].format[0] == 'f':
                mes = "Table successfully started. Watching room {}{}.".format(self.table_instances[ctx.channel.id].rxx, " (ignoring large finish times)" if self.table_instances[ctx.channel.id].sui else '')
                self.table_instances[ctx.channel.id].table_running = True
                await wait_mes.delete()
                await self.send_messages(ctx, mes)
                self.table_instances[ctx.channel.id].searching_room = False
                self.table_instances[ctx.channel.id].confirm_room = False
                self.table_instances[ctx.channel.id].check_mkwx_update.start()
                return
            await wait_mes.delete()    
            await self.send_messages(ctx, self.table_instances[ctx.channel.id].choose_message)
            return
        
    async def cog_before_invoke(self,ctx):
        self.set_instance(ctx)
    
    #?start
    @commands.command(aliases=['st', 'starttable', 'sw'])
    async def start(self,ctx, *args):
        
        if self.table_instances[ctx.channel.id].confirm_room or self.table_instances[ctx.channel.id].confirm_reset:
            await self.send_temp_messages(ctx, "Please answer the last confirmation question:", self.table_instances[ctx.channel.id].choose_message)
            return
        if self.table_instances[ctx.channel.id].table_running:
            self.table_instances[ctx.channel.id].confirm_reset = True
            self.table_instances[ctx.channel.id].reset_args = args
            #print(self.table_instances[ctx.channel.id].reset_args)
            self.table_instances[ctx.channel.id].choose_message= "A tabler watching room {} is currently active.\nAre you sure you want to start a new table? (?yes/?no)".format(self.table_instances[ctx.channel.id].rxx)
            await self.send_messages(ctx, self.table_instances[ctx.channel.id].choose_message)
            return
        usage = "Usage: ?start <format> <number of teams> <gps = 3>"
        
        #print(args)
        if len(args)<1:
            await self.send_temp_messages(ctx, usage)
            return
         
        if isinstance(args[0], tuple) and self.table_instances[ctx.channel.id].reset_args !=None:
            args = args[0]
        args = list(args)
            
        _format = args[0].lower()
        
        if len(args)<2 and _format[0]!='f':
            await self.send_temp_messages(ctx, "Missing <teams>.", usage)
            return
        
        
        if _format not in ['ffa', '2v2', '3v3', '4v4', '5v5', '6v6', '2', '3', '4', '5', '6']:
            await self.send_messages(ctx, "Invalid format. Format must be FFA, 2v2, 3v3, 4v4, 5v5, or 6v6.", usage)
            return
        
        teams = Utils.max_teams(_format)
        if len(args)>1:
            try:
                teams = int(args[1].lower())
            except:
                await self.send_messages(ctx, "Invalid use of ?start: <teams> must be an integer.", usage)
                return
        
        if Utils.check_teams(_format, teams):
            await self.send_messages(ctx, "Invalid number of teams. The number of teams cannot exceed 12 players.", usage)
            return
        self.table_instances[ctx.channel.id].format = _format
        self.table_instances[ctx.channel.id].teams = teams
        num_players = Utils.get_num_players(_format, teams) 
        self.table_instances[ctx.channel.id].num_players = num_players
        gps = 3
        sui=None
        for i in args:
            if 'sui=' in i:
                sui = args.pop(args.index(i))
                break
        if sui!=None:
            self.table_instances[ctx.channel.id].sui = True if sui[4:]=='yes' or sui[4:]=='y' else False 
        
        if len(args)==3:
            
            arg3 = args[2].lower()
            if arg3.isnumeric():
                gps = int(arg3)
                self.table_instances[ctx.channel.id].gps = gps
            else:
                try:
                    assert((arg3[0]=='r' and len(arg3)==8) or (arg3[2:].isnumeric() and len(arg3)==4))
                except:
                    await self.send_temp_messages(ctx, "Invalid rxx/room name.")
                    return
                rxx = [arg3]
                await self.skip_search(ctx,rxx)
                return
        if len(args)>3:
            try:
                assert((arg3[0]=='r' and len(arg3)==8) or (arg3[2:].isnumeric() and len(arg3)==4))
            except:
                await self.send_temp_messages(ctx, "Invalid rxx/room name.")
                return
            arg4 = args[3]
            rxx = [arg4]
            await self.skip_search(ctx, rxx)
            return
            
        self.table_instances[ctx.channel.id].searching_room = True   
        await self.send_messages(ctx, "Provide a room id (rxx) or mii name(s) in the room.", "Make sure at least one race in the room has finished.", "\nUsage: ?search <rxx or mii> <rxx or mii names(s)>")
    
    #?search   
    @commands.command(aliases=['sr'])  
    async def search(self,ctx, *, arg):
        
        
        if self.table_instances[ctx.channel.id].confirm_room or self.table_instances[ctx.channel.id].confirm_reset:
            await self.send_temp_messages(ctx, "Please answer the last confirmation question:", self.table_instances[ctx.channel.id].choose_message)
            return
       
        if not self.table_instances[ctx.channel.id].searching_room:
            await self.send_temp_messages(ctx, "You cannot search for a room if a table is currently running or a table hasn't been started yet.")
            return
        
        arg = arg.strip()
        
        usage = "\nUsage: ?search <rxx or mii> <rxx or name(s)>\nmkwx room list: {}".format(self.home_url)
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
        if len(search_args)>self.table_instances[ctx.channel.id].num_players:
            await self.send_messages(ctx, "You cannot provide more than {} mii names.".self.format(self.table_instances[ctx.channel.id].num_players), usage)
            return
        
        if search_type == 'roomid' or search_type=='rxx':
            print("ds")
            if search_args[0].isnumeric():
                await self.send_messages(ctx, "Invalid room id: missing an 'r' or not in format 'XX00'.", usage)
                return
            wait_mes = await ctx.send('Searching for room...')
            error, ask, self.table_instances[ctx.channel.id].choose_message = await self.table_instances[ctx.channel.id].find_room(rid = search_args)
        elif search_type == "mii":   
            wait_mes = await ctx.send('Searching for room...')
            error, ask, self.table_instances[ctx.channel.id].choose_message = await self.table_instances[ctx.channel.id].find_room(mii = search_args)
        else:
            await self.send_messages(ctx, "Invalid argument for ?search: <search type> must be 'rxx' or 'mii'", usage)
            return
        
        if error:
            if ask=='reset':
                self.table_instances.pop(ctx.message.channel.id)
            await wait_mes.delete()
            await self.send_messages(ctx, self.table_instances[ctx.channel.id].choose_message, usage)
            return
        
        if ask == "match":
            self.table_instances[ctx.channel.id].choose_room= True
            await wait_mes.delete()
            await self.send_messages(ctx, "There were more than one possible matching rooms. Choose the desired room number.", self.table_instances[ctx.channel.id].choose_message)
            return
        elif ask=="confirm":
            self.table_instances[ctx.channel.id].confirm_room = True
            await wait_mes.delete()
            await self.send_messages(ctx, self.table_instances[ctx.channel.id].choose_message)
            return
    
    @search.error
    async def search_error(self,ctx, error):
        self.set_instance(ctx)
        
        
        if isinstance(error, commands.MissingRequiredArgument):
            await self.send_messages(ctx, "Usage: ?search <rxx or mii> <rxx or name(s)>\nmkwx room list: {}".format(self.home_url)) 
    
    #change one player's tag
    @commands.command()
    async def changetag(self,ctx, *args): 
        
        
        if await self.check_special_callable(ctx): return
        
        usage = "Usage: ?changetag <player id> <corrected tag>"
        if len(args)==0:
            await self.send_temp_messages(ctx, self.table_instances[ctx.channel.id].get_player_list(),'\n',usage)
            return
        
        pID = args[0].lower()
        if not pID.isnumeric():
            await self.send_temp_messages(ctx, "<player id> must be a number.", usage)
            return
        if len(args)<2:
            await self.send_temp_messages(ctx, "missing <corrected tag> parameter.", usage)
            return
        
        tag = args[1]
        mes= self.table_instances[ctx.channel.id].change_tag(pID, tag)
        if self.table_instances[ctx.channel.id].confirm_room:
            self.table_instances[ctx.channel.id].choose_message = self.table_instances[ctx.channel.id].get_player_list() +"\n**Is this correct?** (?yes / ?no)"
            await self.send_messages(ctx, mes, self.table_instances[ctx.channel.id].get_player_list(), '\n', "**Is this correct?** (?yes / ?no)")
        else:
            await self.send_messages(ctx, mes)
        
    @commands.command(aliases=['et', 'edittags']) 
    async def edittag(self,ctx, *, arg): 
        
        usage = 'Usage: ?edittag <tag> <corrected tag>'
        if await self.check_special_callable(ctx): return
        
        arg = [i.strip() for i in arg.strip().split("/")]
        arg  = [i.split(" ") for i in arg]
        if len(arg)==0:
            await self.send_temp_messages(ctx, self.table_instances[ctx.channel.id].get_player_list(), '\n', usage)
        for i in arg:
            if len(i)<1:
                await self.send_temp_messages(ctx, "Missing tag(s) for command.", self.table_instances[ctx.channel.id].get_player_list(), '\n',usage)
                return
            if len(i)<2:
                await self.send_temp_messages(ctx, "Error processing command: missing <corrected tag> for tag '{}'".format(i[0]), self.table_instances[ctx.channel.id].get_player_list(), usage)
                return
        
        
        mes = self.table_instances[ctx.channel.id].edit_tag_name(arg)
        if self.table_instances[ctx.channel.id].confirm_room:
            self.table_instances[ctx.channel.id].choose_message = self.table_instances[ctx.channel.id].get_player_list() +"\n**Is this correct?** (?yes / ?no)"
            await self.send_messages(ctx, mes, self.table_instances[ctx.channel.id].get_player_list(), '\n', "**Is this correct?** (?yes / ?no)")
        else:
            await self.send_messages(ctx, mes)
            
    @edittag.error
    async def edittag_error(self,ctx, error):
        self.set_instance(ctx)
        
        if await self.check_special_callable(ctx): return
        if isinstance(error, commands.MissingRequiredArgument):
            await self.send_messages(ctx, self.table_instances[ctx.channel.id].get_player_list(),'\nUsage: ?edittag <tag> <corrected tag>')    
    
    #to manually create tags
    @commands.command(aliases=['tag'])
    async def tags(self,ctx, *, arg): 
        
        usage = "Usage: ?tags <tag> <pID pID> / <tag> <pID pID>\n**ex.** ?tags Player 1 3 / Z 2 4 / B 5 6"
        if await self.check_special_callable(ctx): return
        
        arg = [i.strip() for i in arg.strip().split("/")]
        arg  = [i.split(" ") for i in arg]
        if len(arg)==0:
            await self.send_temp_messages(ctx, self.table_instances[ctx.channel.id].get_player_list(), '\n',usage)
            return
        for i in arg:
            if len(i)<1:
                await self.send_temp_messages(ctx, "Missing tag(s) for command.", self.table_instances[ctx.channel.id].get_player_list(), '\n',usage)
                return
            if len(i)<2:
                await self.send_temp_messages(ctx, "Error processing command: missing players for tag '{}'".format(i[0]), self.table_instances[ctx.channel.id].get_player_list(), usage)
                return
            for indx, j in enumerate(i[1:]):
                if not j.isnumeric():
                    await self.send_temp_messages(ctx, "Error processing players for tag '{}': {} is not a number. All players must be numeric.".format(i[0], i[indx]), usage)
                    return 
        dic = {}
        for i in arg:
            dic[i[0]] = i[1:]
        
        mes = self.table_instances[ctx.channel.id].group_tags(dic)
        if self.table_instances[ctx.channel.id].confirm_room:
            self.table_instances[ctx.channel.id].choose_message = self.table_instances[ctx.channel.id].get_player_list() +"\n**Is this correct?** (?yes / ?no)"
            await self.send_messages(ctx, mes, self.table_instances[ctx.channel.id].get_player_list(), "\n**Is this correct?** (?yes / ?no)")
        else:
            await self.send_messages(ctx, mes, self.table_instances[ctx.channel.id].get_player_list())
        
    @tags.error
    async def tags_error(self,ctx, error):
        self.set_instance(ctx)
        
        if await self.check_special_callable(ctx): return
        
        if isinstance(error, commands.MissingRequiredArgument):
            await self.send_messages(ctx, self.table_instances[ctx.channel.id].get_player_list(), "\nUsage: ?tags <tag> <pID pID> / <tag> <pID pID>\n**ex.** ?tags Player 1 3 / Z 2 4 / B 5 6")
    
    @commands.command(aliases=['y'])
    async def yes(self,ctx, *args):
        
        if not self.table_instances[ctx.channel.id].confirm_room and not self.table_instances[ctx.channel.id].confirm_reset:
            await self.send_temp_messages(ctx, "You can only use ?yes if the bot prompts you to do so.")
            return
        
        if self.table_instances[ctx.channel.id].confirm_room:
            if self.table_instances[ctx.channel.id].choose_room: self.table_instances[ctx.channel.id].choose_room = False
            mes = "Table successfully started. Watching room {}{}.".format(self.table_instances[ctx.channel.id].rxx, " (ignoring large finish times)" if self.table_instances[ctx.channel.id].sui else '')
            self.table_instances[ctx.channel.id].table_running = True
            
            self.table_instances[ctx.channel.id].searching_room = False
            self.table_instances[ctx.channel.id].confirm_room = False
            self.table_instances[ctx.channel.id].check_mkwx_update.start()
            await self.send_messages(ctx, mes)
            
        elif self.table_instances[ctx.channel.id].confirm_reset:
            self.table_instances[ctx.channel.id].check_mkwx_update.stop()
            reset_args = self.table_instances[ctx.channel.id].reset_args
            self.table_instances.pop(ctx.channel.id)
            await self.send_messages(ctx, "Table has been reset.")
            
            self.set_instance(ctx)
            self.table_instances[ctx.channel.id].reset_args = reset_args
            await self.start(ctx, self.table_instances[ctx.channel.id].reset_args)
        
    @commands.command(aliases=['n'])
    async def no(self,ctx, *args):
        
        if not self.table_instances[ctx.channel.id].confirm_room and not self.table_instances[ctx.channel.id].confirm_reset:
            await self.send_temp_messages(ctx, "You can only use ?no if the bot prompts you to do so.")
            return 
        if self.table_instances[ctx.channel.id].confirm_room:
            self.table_instances[ctx.channel.id].confirm_room = False
            self.table_instances.pop(ctx.message.channel.id)
            await self.send_messages(ctx, "Start a new table with ?start.")
           
        elif self.table_instances[ctx.channel.id].confirm_reset:
            self.table_instances[ctx.channel.id].confirm_reset = False
            await self.send_messages(ctx, "Tabler watching room {} will continue running.".format(self.table_instances[ctx.channel.id].rxx))
    
    '''    
    #choose correct room if multiple matches from mii name search
    @commands.command(aliases=['ch'])
    async def choose(self,ctx, *args):
        
        if await self.check_callable(ctx, "choose"): return
        usage = "Usage: ?choose <room index #>"
        
        room = args[0].lower()
        count = self.table_instances[ctx.channel.id].choose_message.count("Players in room:")
        indices = range(1, count+1)
        if room not in indices:
            await self.send_messages(ctx, "Invalid room index: the room index should be from {} to {}.".format(indices[0], indices[-1]), usage)
            return
        
        #await send_messages(ctx, )
    '''
    
    #?picture
    @commands.command(aliases=['p', 'pic', 'wp'])
    @commands.max_concurrency(number=1, wait=True, per = commands.BucketType.channel)
    @commands.cooldown(1, 10, type=commands.BucketType.channel)
    async def picture(self,ctx, *arg):
        if self.table_instances[ctx.channel.id].picture_running:
            await self.send_temp_messages(ctx, "This command is currently in use. Please wait.")
            return
        
        if await self.check_callable(ctx, "pic"): return
        byrace = False
        if len(arg)>0 and arg[0] in ['byrace', 'race']:
            byrace = True
        
        wait_mes = await ctx.send("Updating scores...")
        mes = await self.table_instances[ctx.channel.id].update_table()
        await wait_mes.edit(content=mes)
        pic_mes = await ctx.send("Fetching table picture...")
        img = await self.table_instances[ctx.channel.id].get_table_img(by_race=byrace)
        
        
        f=discord.File(fp=img, filename='table.png')
        em = discord.Embed(title=self.table_instances[ctx.channel.id].tag_str(), color=0x00ff6f)
        
        value_field = "[Edit this table on gb.hlorenzi.com]("+self.table_instances[ctx.channel.id].table_link+")"
        em.add_field(name='\u200b', value= value_field, inline=False)
        em.set_image(url='attachment://table.png')
        em.set_footer(text = self.table_instances[ctx.channel.id].get_warnings())
        await pic_mes.delete()
        await ctx.send(embed=em, file=f)
    
    @commands.command()
    async def undo(self,ctx, *args):
        if await self.check_callable(ctx, "undo"): return
                
        if len(args)==0:
            args=-1
        else:
            if args[0].lower()=='all':
                args = 0
            else:
                args=-1
        mes = self.table_instances[ctx.channel.id].undo_commands(args)
        await self.send_messages(ctx,mes)
    
    @commands.command(aliases=['undolist'])
    async def undos(self, ctx):
        if await self.check_callable(ctx, "undos"): return
        await self.send_messages(ctx, self.table_instances[ctx.channel.id].get_modifications())
        
    @commands.command()
    async def redo(self,ctx, *args):
        if await self.check_callable(ctx, "redo"): return
                
        if len(args)==0:
            args=-1
        else:
            if args[0].lower()=='all':
                args = 0
            else:
                args = -1
        mes = self.table_instances[ctx.channel.id].redo_commands(args)
        await self.send_messages(ctx,mes)
    
    @commands.command(aliases=['redolist'])
    async def redos(self, ctx):
        if await self.check_callable(ctx, "redos"): return
        await self.send_messages(ctx, self.table_instances[ctx.channel.id].get_undos())
       
     
    #?reset
    @commands.command(aliases=['stop'])
    async def reset(self,ctx, *args):
        if not self.table_instances[ctx.channel.id].table_running and not self.table_instances[ctx.channel.id].confirm_room:
            await self.send_temp_messages(ctx, "You need to have an active table to be able to reset.")
            return
        
        self.table_instances[ctx.channel.id].check_mkwx_update.stop()
        self.table_instances.pop(ctx.message.channel.id)
       
        await self.send_messages(ctx, "Table has been reset. ?start to start a new table.")
        
    
    @commands.command(aliases = ['dc'])
    async def dcs(self,ctx, *, arg): 
        
        if await self.check_callable(ctx, "dcs"): return
        
        usage = '\nUsage: ?dcs <DC number> <"on"/"during" or "off"/"before">' if len(self.table_instances[ctx.channel.id].dc_list)>0 else ""
        
        arg = [i.strip() for i in arg.strip().split("/")]
        arg  = [i.split(" ") for i in arg]
        
        for i in arg:
            if len(i)<1:
                await self.send_temp_messages(ctx, "Error: Missing <DC number>.", self.table_instances[ctx.channel.id].dc_list_str(), usage)
                return
            if len(i)<2:
                await self.send_temp_messages(ctx, "Error processing command: missing DC status for DC number {}.".format(i[0]), self.table_instances[ctx.channel.id].dc_list_str(), usage)
                return
            if len(i)>2:
                await self.send_temp_messages(ctx, "Too many arguments for player number {}. The only arguments should be <DC number> and <DC status>.".format(i[0]), self.table_instances[ctx.channel.id].dc_list_str(), usage)
            if not i[0].isnumeric():
                await self.send_temp_messages(ctx, "DC numbers must be numeric.", self.table_instances[ctx.channel.id].dc_list_str(), usage)
                return
            if not (i[1] == "on" or i[1]=='during') and not (i[1]=='off' or i[1] == "before"):
                await self.send_temp_messages(ctx, "The DC status argument must be either 'on'/'during' or 'off'/'before'.", self.table_instances[ctx.channel.id].dc_list_str(), usage)
            
        mes = self.table_instances[ctx.channel.id].edit_dc_status(arg)
        await self.send_messages(ctx, mes)
        
          
    @dcs.error
    async def dcs_error(self,ctx, error):
        self.set_instance(ctx)
        
        if await self.check_callable(ctx, "dcs"): return
        
        usage = '\nUsage: ?dcs <DC number> <"on"/"during" or "off"/"before">' if len(self.table_instances[ctx.channel.id].dc_list)>0 else ""
        if isinstance(error, commands.MissingRequiredArgument):
            await self.send_messages(ctx, self.table_instances[ctx.channel.id].dc_list_str(), usage)
            return
    
    @commands.command(aliases=['substitute'])
    async def sub(self, ctx, *args): #NOTE: needs more testing but seems to work fine 
        
        if await self.check_callable(ctx, "sub"): return
        
        usage = "\nUsage: ?sub <sub out> <sub out races played> <sub in>"
        if len(args)==0:
            await self.send_messages(ctx, self.table_instances[ctx.channel.id].get_player_list(), usage)
            return
        if len(args)<2:
            await self.send_temp_messages(ctx, "Missing <sub out races played> and <sub in>.", self.table_instances[ctx.channel.id].get_player_list(), usage)
            return
        if len(args)<3:
            await self.send_temp_messages(ctx, "Missing <sub in>.",self.table_instances[ctx.channel.id].get_player_list(), usage)
        
        subIn = args[2]
        subOut = args[0]
        subOut_races = args[1]
        
        if not subIn.isnumeric():
            await self.send_temp_messages(ctx, "<sub in> must be a number.", self.table_instances[ctx.channel.id].get_player_list(), usage)
            return
        if not subOut.isnumeric():
            await self.send_temp_messages(ctx, "<sub out> must be a number.", self.table_instances[ctx.channel.id].get_player_list(), usage)
            return
        if not subOut_races.isnumeric():
            await self.send_temp_messages(ctx, "<sub out races played> must be a number.", self.table_instances[ctx.channel.id].get_player_list(), usage)
            return
        
        mes = self.table_instances[ctx.channel.id].sub_in(subIn, subOut, subOut_races)
        await self.send_messages(ctx, mes)
        
    @commands.command(aliases=['editsubraces', 'subraces'])
    async def editsub(self, ctx, *args):
        
        if await self.check_callable(ctx, "editsub"): return
        
        usage = "\nUsage: ?editsub <player number> <correct races> <in/out> <(sub out index)>"
        if len(args)==0:
            await self.send_messages(ctx, self.table_instances[ctx.channel.id].get_player_list(), usage)
            return
        
        if len(args)<2:
            await self.send_temp_messages(ctx, "Missing <correct races> and <in/out>.", self.table_instances[ctx.channel.id].get_player_list(), usage)
            return
        if len(args)<3:
            await self.send_temp_messages(ctx, "Missing <in/out>.", self.table_instances[ctx.channel.id].get_player_list(), usage)
            return
        
        try:
            p_indx = int(args[0])
        except:
            await self.send_temp_messages(ctx, "<player number> must be a number.", self.table_instances[ctx.channel.id].get_player_list(), usage)
            return
        try:
            races = int(args[1])
        except:
            await self.send_temp_messages(ctx, "<correct races> must be a number.", self.table_instances[ctx.channel.id].get_player_list(), usage)
            return
        is_in = args[2].lower()=='in'
        
        if len(args)>3 and not is_in:
            try:
                out_index = int(args[3])
            except:
                await self.send_temp_messages(ctx, "<sub out index> must be a number.", self.table_instances[ctx.channel.id].get_player_list(), usage)
                return
            mes = self.table_instances[ctx.channel.id].edit_sub_races(p_indx, races, is_in, out_index)
            await self.send_messages(ctx, mes)
        else:
            mes = self.table_instances[ctx.channel.id].edit_sub_races(p_indx, races, is_in)
            await self.send_messages(ctx, mes)
            
    @commands.command(aliases=['ap'])
    async def allplayers(self, ctx):
        
        if await self.check_callable(ctx, "allplayers"): return
        await self.send_messages(ctx, self.table_instances[ctx.channel.id].get_all_players())
        
    @commands.command(aliases=['pl', 'players'])
    async def playerlist(self,ctx):
        
        if await self.check_callable(ctx, "players"): return
        await self.send_messages(ctx, self.table_instances[ctx.channel.id].get_player_list())
    
    @commands.command()
    async def edit(self,ctx, *args):
        
        usage = "Usage: ?edit <player id> <gp number> <gp score>"
        if await self.check_callable(ctx, "edit"): return
        
        if len(args)==0:
            await self.send_messages(ctx, self.table_instances[ctx.channel.id].get_player_list(), '\n',usage)
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
        mes = self.table_instances[ctx.channel.id].edit(pID, gp, score)
        await self.send_messages(ctx, mes)
    
        
    @commands.command(aliases = ['rr', 'res', 'results', 'race'])
    async def raceresults(self,ctx, *args):
        
        if await self.check_callable(ctx, "raceresults"): return
        usage = "Usage: ?rr <race # = last race>"
        race = -1
        if len(args)>0:
            if not args[0].isnumeric():
                await self.send_temp_messages(ctx, "<race number> must be a number.", usage)
                return
            race = int(args[0])
        error, mes = self.table_instances[ctx.channel.id].race_results(race)
        if error:
            await self.send_temp_messages(ctx, mes, usage)
            return
        await self.send_messages(ctx, mes)
        
    @commands.command(aliases=['tl', 'tracks', 'races'])
    async def tracklist(self,ctx, *args):
        
        if await self.check_callable(ctx, "tracklist"): return
        await self.send_messages(ctx, self.table_instances[ctx.channel.id].tracklist())
        
    @commands.command(aliases=['rxx', 'rid', 'room'])
    async def roomid(self, ctx):
        
        if await self.check_callable(ctx, "rxx"): return
        
        await self.send_messages(ctx, self.table_instances[ctx.channel.id].get_rxx())
      
    @commands.command(aliases=['pens'])
    async def penalties(self, ctx):
        if await self.check_callable(ctx, "penalties"): return
        await ctx.send(self.table_instances[ctx.channel.id].get_pen_player_list())
        
    @commands.command(aliases=['pen'])
    async def penalty(self, ctx, *args):
        
        if await self.check_callable(ctx, "penalty"): return
        usage = "Usage: ?pen <player id> <pen amount>"
        
        if len(args)==0:
            await self.send_messages(ctx, self.table_instances[ctx.channel.id].get_pen_player_list(), '\n'+usage)
            return
        pID = args[0].lower()
        if not pID.isnumeric():
            await self.send_temp_messages(ctx, "The player id needs to be a number.", usage)
            return
        if len(args)<2:
            await self.send_temp_messages(ctx, "Missing <pen amount>.",usage)
            return
        pen = args[1].lower()
        if not pen.lstrip('=').lstrip('-').isnumeric():
            await self.send_temp_messages(ctx, "The penalty amount must be a number (negative allowed).", usage)
            return
        
        mes = self.table_instances[ctx.channel.id].penalty(pID, pen)
        await self.send_messages(ctx, mes)
    
    @commands.command(aliases=['unpen'])
    async def unpenalty(self, ctx, *args):
        
        if await self.check_callable(ctx, "unpenalty"): return
        usage = "Usage: ?unpen <player id> <unpen amount = current pen>"
        
        if len(args)==0:
            await self.send_messages(ctx, self.table_instances[ctx.channel.id].get_pen_player_list(), '\n'+usage)
            return
        
        pID = args[0].lower()
        
        if not pID.isnumeric():
            await self.send_temp_messages(ctx, "The player id needs to be a number.", usage)
            return
        unpen = None
        if len(args)>1:
            unpen = args[1].lower()
        mes = self.table_instances[ctx.channel.id].unpenalty(pID, unpen)
        await self.send_messages(ctx, mes)
                                
    @commands.command(aliases=['tp', 'tpen', 'teampen'])
    async def teampenalty(self, ctx, *args):
        
        if await self.check_callable(ctx, "teampenalty"): return
        if self.table_instances[ctx.channel.id].format[0].lower()=='f':
            await self.send_temp_messages(ctx, "You cannot use team penalty commands in FFAs.")
            return
        usage = "?teampen <team> <penalty>"
        
        if len(args)==0:
            await self.send_messages(ctx, self.table_instances[ctx.channel.id].get_pen_player_list(), '\n'+usage)
            return
        team = args[0]
        
        if len(args)<2:
            await self.send_temp_messages(ctx, "Missing <pen amount>.",usage)
            return
        pen = args[1].lower()
        if not pen.lstrip('=').lstrip('-').isnumeric():
            await self.send_temp_messages(ctx, "The penalty amount must be a number (negative allowed).", usage)
            return
        
        mes = self.table_instances[ctx.channel.id].team_penalty(team, pen)
        await self.send_messages(ctx, mes)
        
    @commands.command(aliases=['teamunpen', 'tunpen'])
    async def teamunpenalty(self, ctx, *args):
        
        if await self.check_callable(ctx, "teamunpenalty"): return
        if self.table_instances[ctx.channel.id].format[0].lower()=='f':
            await self.send_temp_messages(ctx, "You cannot use team penalty commands in FFAs.")
            return
        
        usage = "Usage: ?unpen <team> <unpen amount = current pen>"
        
        if len(args)==0:
            await self.send_messages(ctx, self.table_instances[ctx.channel.id].get_pen_player_list(), '\n'+usage)
            return
        
        team = args[0]
        
        unpen = None
        if len(args)>1:
            unpen = args[1].lower()
        mes = self.table_instances[ctx.channel.id].team_unpenalty(team, unpen)
        await self.send_messages(ctx, mes)
            
        
    @commands.command(aliases=['mr', 'merge'])
    async def mergeroom(self, ctx, *, arg):
        
        if await self.check_callable(ctx, "mergeroom"): return
        
        usage = 'Usage: ?mergeroom <rxx or mii name(s) in room>'
        arg = arg.strip()
        search_args = arg.split(",")
        search_args = [i.strip() for i in search_args]
        
        del_mes = await ctx.send("Merging rooms...")
        error, mes = await self.table_instances[ctx.channel.id].merge_room(search_args)
        await del_mes.delete()
        if error:
            await self.send_temp_messages(ctx, mes, '\n'+usage)
            return
        await self.send_messages(ctx, mes)
        
    @mergeroom.error
    async def mergeroom_error(self, ctx, error):
        
        if await self.check_callable(ctx, "mergeroom"): return
        if isinstance(error, commands.MissingRequiredArgument):
            await self.send_temp_messages(ctx, 'Usage: ?mergeroom <rxx or mii name(s) in room>')
    
    @commands.command(aliases=['remove'])
    async def removerace(self, ctx, *arg):
        
        if await self.check_callable(ctx, "removerace"): return
        usage = "Usage: ?removerace <race number>"
        
        if len(arg)==0:
            await ctx.send("**Note: This command should be used with caution as it is unstable and could cause unintended consequences on the table.\nIdeally this command should be used immediately after the table picture updates with the race that needs to be removed.**")
            mes = self.table_instances[ctx.channel.id].remove_race(-1)
            await self.send_messages(ctx, mes)
            return
        arg = arg[0]
        if not arg.isnumeric():
            await self.send_temp_messages(ctx, "The <race number> must be a real number.", usage)
            return
        
        await ctx.send("**Note: This command should be used with caution as it is unstable and could cause unintended consequences on the table.\nIdeally this command should be used immediately after the table picture updates with the race that needs to be removed.**")
        mes = self.table_instances[ctx.channel.id].remove_race(int(arg))
        await self.send_messages(ctx, mes)
        
    @removerace.error
    async def removerace_error(self, ctx, error):
        if await self.check_callable(ctx, "removerace"): return
        
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("**Note: This command should be used with caution as it is unstable and could cause unintended consequences on the table.\nIdeally this command should be used immediately after the table picture updates with the race that needs to be removed.**")
            mes = self.table_instances[ctx.channel.id].remove_race(-1)
            await self.send_messages(ctx, mes)
    
    @commands.command(aliases=['gp', 'gps', 'changegp'])
    async def changegps(self, ctx, *args):
        
        if await self.check_callable(ctx, "changegps"): return
        usage = "Usage: ?changegps <num gps>"
        if len(args)==0: 
            await self.send_temp_messages(ctx, usage)
            return
        try:
            if args[0][0] == '+' or args[0][0] == '-':
                gps = int(args[0])
                self.table_instances[ctx.channel.id].change_gps(self.table_instances[ctx.channel.id].gps+gps)
            else:   
                gps = int(args[0])
                assert(gps>0)
                self.table_instances[ctx.channel.id].change_gps(gps)
        except:
            await self.send_temp_messages(ctx, "<num gps> must be a real number.", usage)
            return
        
        await self.send_messages(ctx, "Changed total gps to {}.".format(gps))
        self.table_instances[ctx.channel.id].check_mkwx_update.start()
        
    @commands.command(aliases=['quickedit', 'qedit'])
    async def editrace(self,ctx, *, arg):
        
        if await self.check_callable(ctx, "editrace"): return
        
        usage = "Usage: ?editrace <race number> <player id> <corrected placement>"
        arg = [i.strip() for i in arg.strip().split("/")]
        arg  = [i.split(" ") for i in arg]
        if len(arg)==0:
            await self.send_temp_messages(ctx, self.table_instances[ctx.channel.id].get_player_list(), '\n',usage)
            return
        for i in arg:
            if len(i)<1:
                await self.send_temp_messages(ctx, "Missing <race number> for command.", self.table_instances[ctx.channel.id].get_player_list(), '\n',usage)
                return
            if len(i)<2:
                await self.send_temp_messages(ctx, "Error processing command: missing players for command on race {}".format(i[0]), self.table_instances[ctx.channel.id].get_player_list(), usage)
                return
            if len(i)<3:
                await self.send_temp_messages(ctx, "Error: missing <corrected placement> for race {}, player {}.".format(i[0], i[1]), self.table_instances[ctx.channel.id].get_player_list(), usage)
            
            for t in i:
                if not t.isnumeric():
                    await self.send_temp_messages(ctx, "Argument '{}' for the command must be a real number.".format(t), self.table_instances[ctx.channel.id].get_player_list(), usage)
                    return
                
        mes = self.table_instances[ctx.channel.id].edit_race(arg)
        await self.send_messages(ctx, mes)
        
    @editrace.error
    async def editrace_error(self, ctx, error):
        self.set_instance(ctx)
        
        if await self.check_callable(ctx, 'editrace'): return
        
        if isinstance(error, commands.MissingRequiredArgument):
            await self.send_messages(ctx, self.table_instances[ctx.channel.id].get_player_list(),"\nUsage: ?editrace <race number> <player id> <corrected placement>")
    
    @commands.command(aliases=['crs', 'roomsize'])
    async def changeroomsize(self, ctx, *, arg): 
        
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
        mes = self.table_instances[ctx.channel.id].change_room_size(arg)
        await self.send_messages(ctx, mes)

        
    @changeroomsize.error
    async def changeroomsize_error(self, ctx, error):
        self.set_instance(ctx)
        
        if await self.check_callable(ctx, "changeroomsize"): return
        
        if isinstance(error, commands.MissingRequiredArgument):
            await self.send_messages(ctx, "Usage: ?changeroomsize <race number> <corrected room size (num players)>")
    
    @commands.command(aliases=['tt', 'text'])
    async def tabletext(self, ctx):
        
        if await self.check_callable(ctx, "tabletext"): return
        await self.send_messages(ctx, self.table_instances[ctx.channel.id].get_table_text())
        
    @commands.command(name='help',aliases = ['h'])
    async def _help(self,ctx):
        
        info = 'List of commands:\n\t**?start**\n\t**?search**\n\t**?reset**\n\t**?players**\n\t**?tracks**\n\t**?rxx**\n\t**?raceresults\n\t?editrace\n\t?changeroomsize\n\t?removerace\n\t?mergeroom\n\t?dcs\n\t?penalty, ?unpenalty\n\t?tags\n\t?edittag\n\t?changetag\n\t?changegps\n\t?edit\n\t?sub, ?editsub\n\t?tabletext\n\t?undo, ?redo\n\t?pic**'
        await self.send_messages(ctx, info)
    

def setup(bot):
    bot.add_cog(table_bot((bot)))