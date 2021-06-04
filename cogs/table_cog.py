# -*- coding: utf-8 -*-
"""
Created on Wed May 19 08:33:13 2021

@author: ryanz
"""

import discord
from discord.ext import commands, tasks
from cogs.tabler import Table
from itertools import cycle

class table_bot(commands.Cog):
    def __init__(self, bot):
        self.home_url = "https://wiimmfi.de/stats/mkwx/list/"
        self.bot = bot
        self.table_instances = {}
        #self.table = None
        self.presences = cycle(['?help for help', '{} active tables'])
        
    
    @commands.Cog.listener()
    async def on_ready(self):
        print("Bot logged in as {0.user}".format(self.bot))
        if not self.cycle_presences.is_running():
            try:
                self.cycle_presences.start()
            except:
                pass
    
    @tasks.loop(seconds=30)
    async def cycle_presences(self):
        next_pres = next(self.presences)
        if "active tables" in next_pres:
            next_pres = next_pres.replace('{}', str(len(self.table_instances)))
        game = discord.Game(next_pres)
        await self.bot.change_presence(status=discord.Status.online, activity=game)
                
    def set_instance(self, ctx):
        channel_id = ctx.message.channel.id
        if channel_id not in self.table_instances:
            self.table_instances[channel_id] = Table()
        #self.table = self.table_instances[channel_id]
        self.table_instances[ctx.channel.id].ctx = ctx
     
    async def send_temp_messages(self,ctx, *args):
        await ctx.send('\n'.join(args), delete_after=25)
    async def send_messages(self,ctx, *args):
        await ctx.send('\n'.join(args))
       
    @commands.Cog.listener()
    async def on_command_error(self,ctx, error):
        self.set_instance(ctx)
        
        if isinstance(error, commands.CommandNotFound):
            await ctx.send("{}.\nType ?help for a list of commands.".format(error.__str__().replace("is not found", "is not a valid command")))
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send("This command can only be used once every {} seconds. You can retry in {:.1f} seconds.".format(error.cooldown.per, error.retry_after))
        elif isinstance(error, commands.MaxConcurrencyReached):
            await ctx.send("This command can only be used by once at a time. Try again later.".format(error.number))
        elif isinstance(error, commands.MissingRequiredArgument):
            pass
        else:
            raise error
      
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
        
    async def cog_before_invoke(self,ctx):
        self.set_instance(ctx)
    
    #?start
    @commands.command(aliases=['st', 'starttable', 'sw'])
    async def start(self,ctx, *args):
        #print(self.table_instances)
        self.table_instances[ctx.channel.id].undo_empty=self.table_instances[ctx.channel.id].redo_empty=False
        if self.table_instances[ctx.channel.id].confirm_room or self.table_instances[ctx.channel.id].confirm_reset:
            await self.send_temp_messages(ctx, "Please answer the last confirmation question:", self.table_instances[ctx.channel.id].choose_message)
            return
        if self.table_instances[ctx.channel.id].table_running:
            self.table_instances[ctx.channel.id].confirm_reset = True
            self.reset_args = args
            self.table_instances[ctx.channel.id].choose_message= "A tabler watching room {} is currently active.\nAre you sure you want to start a new table? (?yes/?no)".format(self.table_instances[ctx.channel.id].rxx)
            await self.send_messages(ctx, self.table_instances[ctx.channel.id].choose_message)
            return
        usage = "Usage: ?start <format> <number of teams> <gps = 3>"
        
        if len(args)<1:
            await self.send_temp_messages(ctx, usage)
            return
         
        if isinstance(args[0], tuple) and self.reset_args !=None:
            args = args[0]
            
        _format = args[0].lower()
        #print(args)
        
        if len(args)<2 and _format[0]!='f':
            await self.send_temp_messages(ctx, "Missing <teams>.", usage)
            return
        
        
        if _format not in ['ffa', '2v2', '3v3', '4v4', '5v5', '6v6', '2', '3', '4', '5', '6']:
            await self.send_messages(ctx, "Invalid format. Format must be FFA, 2v2, 3v3, 4v4, 5v5, or 6v6.", usage)
            return
        
        teams = self.max_teams(_format)
        if len(args)>1:
            try:
                teams = int(args[1].lower())
            except:
                await self.send_messages(ctx, "Invalid use of ?start: <teams> must be an integer.", usage)
                return
        
        if self.check_teams(_format, teams):
            await self.send_messages(ctx, "Invalid number of teams. The number of teams cannot exceed 12 players.", usage)
            return
        self.table_instances[ctx.channel.id].format = _format
        self.table_instances[ctx.channel.id].teams = teams
        num_players = self.get_num_players(_format, teams) 
        self.table_instances[ctx.channel.id].num_players = num_players
        gps = 3
        if len(args)>2:
            
            arg3 = args[2].lower()
            if arg3.isnumeric():
                gps = arg3
                self.table_instances[ctx.channel.id].gps = gps
            else:
                rxx = [arg3]
                wait_mes = await ctx.send('Searching for room...')
                error, ask, self.table_instances[ctx.channel.id].choose_message = self.table_instances[ctx.channel.id].find_room(rid = rxx)
                await wait_mes.delete()
                if error:
                    if ask=='reset':
                        self.table_instances.pop(ctx.message.channel.id)
                    await self.send_messages(ctx, self.table_instances[ctx.channel.id].choose_message, usage)
                    return
                if ask=="confirm":
                    self.table_instances[ctx.channel.id].confirm_room = True
                    if self.table_instances[ctx.channel.id].format[0] == 'f':
                        mes = "Table successfully started. Watching room {}.".format(self.table_instances[ctx.channel.id].rxx)
                        self.table_instances[ctx.channel.id].table_running = True
                        await self.send_messages(ctx, mes)
                        self.table_instances[ctx.channel.id].searching_room = False
                        self.table_instances[ctx.channel.id].confirm_room = False
                        self.table_instances[ctx.channel.id].check_mkwx_update.start()
                        return
                        
                    await self.send_messages(ctx, self.table_instances[ctx.channel.id].choose_message)
                    return
            
        self.table_instances[ctx.channel.id].searching_room = True   
        await self.send_messages(ctx, "Provide a room id (rxx) or mii name(s) in the room.", "Make sure at least one race in the room has finished.", "Usage: ?search <rxx or mii> <rxx or mii names(s)>")
    
    #?search   
    @commands.command(aliases=['sr'])  
    async def search(self,ctx, *, arg):
        self.table_instances[ctx.channel.id].undo_empty=self.table_instances[ctx.channel.id].redo_empty=False
        
        if self.table_instances[ctx.channel.id].confirm_room or self.table_instances[ctx.channel.id].confirm_reset:
            await self.send_temp_messages(ctx, "Please answer the last confirmation question:", self.table_instances[ctx.channel.id].choose_message)
            return
       
        if not self.table_instances[ctx.channel.id].searching_room:
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
        if len(search_args)>self.table_instances[ctx.channel.id].num_players:
            await self.send_messages(ctx, "You cannot provide more than {} mii names.".self.format(self.table_instances[ctx.channel.id].num_players), usage)
            return
        
        if search_type == 'roomid' or search_type=='rxx':
            print("ds")
            if search_args[0].isnumeric():
                await self.send_messages(ctx, "Invalid room id: missing an 'r' or not in format 'XX00'.", usage)
                return
            wait_mes = await ctx.send('Searching for room...')
            error, ask, self.table_instances[ctx.channel.id].choose_message = self.table_instances[ctx.channel.id].find_room(rid = search_args)
        elif search_type == "mii":   
            wait_mes = await ctx.send('Searching for room...')
            error, ask, self.table_instances[ctx.channel.id].choose_message = self.table_instances[ctx.channel.id].find_room(mii = search_args)
        else:
            await self.send_messages(ctx, "Invalid argument for ?search: <search type> must be 'rxx' or 'mii'", usage)
            return
        await wait_mes.delete()
        if error:
            if ask=='reset':
                self.table_instances.pop(ctx.message.channel.id)
            await self.send_messages(ctx, self.table_instances[ctx.channel.id].choose_message, usage)
            return
        
        if ask == "match":
            self.table_instances[ctx.channel.id].choose_room= True
            
            await self.send_messages(ctx, "There were more than one possible matching rooms. Choose the desired room number.", self.table_instances[ctx.channel.id].choose_message)
            return
        elif ask=="confirm":
            self.table_instances[ctx.channel.id].confirm_room = True
            await self.send_messages(ctx, self.table_instances[ctx.channel.id].choose_message)
            return
    
    @search.error
    async def search_error(self,ctx, error):
        self.set_instance(ctx)
        self.table_instances[ctx.channel.id].undo_empty=self.table_instances[ctx.channel.id].redo_empty=False
        
        if isinstance(error, commands.MissingRequiredArgument):
            await self.send_messages(ctx, "Usage: ?search <rxx or mii> <rxx or name(s)>\nmkwx room list: {}".format(self.home_url)) 
    
    #change one player's tag
    @commands.command()
    async def changetag(self,ctx, *args): 

        self.table_instances[ctx.channel.id].undo_empty=self.table_instances[ctx.channel.id].redo_empty=False
        
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
        self.table_instances[ctx.channel.id].undo_empty=self.table_instances[ctx.channel.id].redo_empty=False
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
        self.table_instances[ctx.channel.id].undo_empty=self.table_instances[ctx.channel.id].redo_empty=False
        if await self.check_special_callable(ctx): return
        if isinstance(error, commands.MissingRequiredArgument):
            await self.send_messages(ctx, self.table_instances[ctx.channel.id].get_player_list(),'\nUsage: ?edittag <tag> <corrected tag>')    
    
    #to manually create tags
    @commands.command(aliases=['tag'])
    async def tags(self,ctx, *, arg): 
        self.table_instances[ctx.channel.id].undo_empty=self.table_instances[ctx.channel.id].redo_empty=False
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
        self.table_instances[ctx.channel.id].choose_message = self.table_instances[ctx.channel.id].get_player_list() +"\n**Is this correct?** (?yes / ?no)"
        await self.send_messages(ctx, mes, self.table_instances[ctx.channel.id].get_player_list(), "\n**Is this correct?** (?yes / ?no)")
        
    @tags.error
    async def tags_error(self,ctx, error):
        self.set_instance(ctx)
        self.table_instances[ctx.channel.id].undo_empty=self.table_instances[ctx.channel.id].redo_empty=False
        if await self.check_special_callable(ctx): return
        
        if isinstance(error, commands.MissingRequiredArgument):
            await self.send_messages(ctx, self.table_instances[ctx.channel.id].get_player_list(), "\nUsage: ?tags <tag> <pID pID> / <tag> <pID pID>\n**ex.** ?tags Player 1 3 / Z 2 4 / B 5 6")
    
    @commands.command(aliases=['y'])
    async def yes(self,ctx, *args):
        self.table_instances[ctx.channel.id].undo_empty=self.table_instances[ctx.channel.id].redo_empty=False
        if not self.table_instances[ctx.channel.id].confirm_room and not self.table_instances[ctx.channel.id].confirm_reset:
            await self.send_temp_messages(ctx, "You can only use ?yes if the bot prompts you to do so.")
            return
        
        if self.table_instances[ctx.channel.id].confirm_room:
            if self.table_instances[ctx.channel.id].choose_room: self.table_instances[ctx.channel.id].choose_room = False
            mes = "Table successfully started. Watching room {}.".format(self.table_instances[ctx.channel.id].rxx)
            self.table_instances[ctx.channel.id].table_running = True
            await self.send_messages(ctx, mes)
            self.table_instances[ctx.channel.id].searching_room = False
            self.table_instances[ctx.channel.id].confirm_room = False
            self.table_instances[ctx.channel.id].check_mkwx_update.start()
        elif self.table_instances[ctx.channel.id].confirm_reset:
            self.table_instances[ctx.channel.id].check_mkwx_update.stop()
            self.table_instances.pop(ctx.message.channel.id)
            '''
            self.table_instances[ctx.channel.id].table_running=False
            self.table_instances[ctx.channel.id].confirm_reset = False
            '''
            await self.send_messages(ctx, "Table has been reset.")
            
            self.set_instance(ctx)
            await self.start(ctx, self.reset_args)
        
    @commands.command(aliases=['n'])
    async def no(self,ctx, *args):
        self.table_instances[ctx.channel.id].undo_empty=self.table_instances[ctx.channel.id].redo_empty=False
        if not self.table_instances[ctx.channel.id].confirm_room and not self.table_instances[ctx.channel.id].confirm_reset:
            await self.send_temp_messages(ctx, "You can only use ?no if the bot prompts you to do so.")
            return 
        if self.table_instances[ctx.channel.id].confirm_room:
            self.table_instances[ctx.channel.id].confirm_room = False
            self.table_instances.pop(ctx.message.channel.id)
            #await send_messages(ctx, "Search for a room with ?search <search type> <room id or mii name(s)>")
            await self.send_messages(ctx, "Start a new table with ?start.")
           
        elif self.table_instances[ctx.channel.id].confirm_reset:
            self.table_instances[ctx.channel.id].confirm_reset = False
            await self.send_messages(ctx, "Tabler watching room {} will continue running.".format(self.table_instances[ctx.channel.id].rxx))
     
    #choose correct room if multiple matches from mii name search
    @commands.command(aliases=['ch'])
    async def choose(self,ctx, *args):
        self.table_instances[ctx.channel.id].undo_empty=self.table_instances[ctx.channel.id].redo_empty=False
        if await self.check_callable(ctx, "choose"): return
        usage = "Usage: ?choose <room index #>"
        
        room = args[0].lower()
        count = self.table_instances[ctx.channel.id].choose_message.count("Players in room:")
        indices = range(1, count+1)
        if room not in indices:
            await self.send_messages(ctx, "Invalid room index: the room index should be from {} to {}.".format(indices[0], indices[-1]), usage)
            return
        #TODO: show them chosen room, and ask if it it correct ?yes or ?no or ?changetag
        #await send_messages(ctx, )
    
    #?picture
    @commands.command(aliases=['p', 'pic', 'wp'])
    @commands.max_concurrency(number=1, wait=True, per = commands.BucketType.channel)
    @commands.cooldown(1, 10, type=commands.BucketType.channel)
    async def picture(self,ctx):
        if self.table_instances[ctx.channel.id].picture_running:
            await self.send_temp_messages(ctx, "This command is currently in use. Please wait.")
            return
        self.table_instances[ctx.channel.id].undo_empty=self.table_instances[ctx.channel.id].redo_empty=False

        if await self.check_callable(ctx, "pic"): return
        
        wait_mes = await ctx.send("Updating scores...")
        mes = self.table_instances[ctx.channel.id].update_table()
        await wait_mes.edit(content="Fetching table picture. Please wait...")
        img = await self.table_instances[ctx.channel.id].get_table_img()
        await wait_mes.edit(content=mes)
        
        f=discord.File(fp=img, filename='table.png')
        em = discord.Embed(title=self.table_instances[ctx.channel.id].tag_str(), color=0x00ff6f)
        
        value_field = "[Edit this table on gb.hlorenzi.com]("+self.table_instances[ctx.channel.id].table_link+")"
        em.add_field(name='\u200b', value= value_field, inline=False)
        em.set_image(url='attachment://table.png')
        em.set_footer(text = self.table_instances[ctx.channel.id].get_warnings())
        
        await ctx.send(embed=em, file=f)
    
    @commands.command()
    async def undo(self,ctx, *args):
        self.table_instances[ctx.channel.id].redo_empty = False
        if await self.check_callable(ctx, "undo"): return
        
        usage = 'Usage: ?undo <modification number ("all" if you want to undo all)>' if len(self.table_instances[ctx.channel.id].modifications)>0 else ""
        
        if self.table_instances[ctx.channel.id].undo_empty and len(args)==0:
            mes = self.table_instances[ctx.channel.id].undo_commands(-1)
            await self.send_messages(ctx, mes)
            self.table_instances[ctx.channel.id].undo_empty = False
            return
        if len(args)==0:
            await self.send_messages(ctx, self.table_instances[ctx.channel.id].get_modifications(), '\n'+usage)
            self.table_instances[ctx.channel.id].undo_empty = True
            return
        
        else:
            if args[0].lower()=='all':
                args = 0
            elif args[0].isnumeric():
                args = int(args[0])
            else:
                await self.send_temp_messages(ctx, "{} is not a valid parameter for ?undo. The only valid parameters are 'all' and numbers.".format(args[0]), usage)
                return
        self.table_instances[ctx.channel.id].undo_empty = False   
        mes = self.table_instances[ctx.channel.id].undo_commands(args)
        await self.send_messages(ctx,mes)
        
    @commands.command()
    async def redo(self,ctx, *args):
        self.table_instances[ctx.channel.id].undo_empty = False
        if await self.check_callable(ctx, "redo"): return
        
        usage = 'Usage: ?redo <undo number ("all" if you want to redo all)>' if len(self.table_instances[ctx.channel.id].undos)>0 else ""
        
        if self.table_instances[ctx.channel.id].redo_empty and len(args)==0:
            mes = self.table_instances[ctx.channel.id].redo_commands(-1)
            await self.send_messages(ctx, mes)
            self.table_instances[ctx.channel.id].redo_empty = False
            return
        if len(args)==0:
            await self.send_messages(ctx, self.table_instances[ctx.channel.id].get_undos(), '\n'+usage)
            self.table_instances[ctx.channel.id].redo_empty = True
            return
        else:
            if args[0].lower()=='all':
                args = 0
            elif args[0].isnumeric():
                args = int(args[0])
            else:
                await self.send_temp_messages(ctx, "{} is not a valid parameter for ?redo. The only valid parameters are 'all' and a number.".format(args[0]), usage)
                return
        self.table_instances[ctx.channel.id].redo_empty = False
        mes = self.table_instances[ctx.channel.id].redo_commands(args)
        await self.send_messages(ctx,mes)
       
     
    #?reset
    @commands.command(aliases=['stop'])
    async def reset(self,ctx, *args):
        self.table_instances[ctx.channel.id].undo_empty=self.table_instances[ctx.channel.id].redo_empty=False
        
        if not self.table_instances[ctx.channel.id].table_running and not self.table_instances[ctx.channel.id].confirm_room:
            await self.send_temp_messages(ctx, "You need to have an active table to be able to reset.")
            return
        
        self.table_instances[ctx.channel.id].check_mkwx_update.stop()
        self.table_instances.pop(ctx.message.channel.id)
        '''
        self.table_instances[ctx.channel.id].table_running = False
        self.table_instances[ctx.channel.id].choose_message = None 
        self.table_instances[ctx.channel.id].confirm_reset = False
        self.table_instances[ctx.channel.id].confirm_room= False
        '''
        await self.send_messages(ctx, "Table has been reset. ?start to start a new table.")
        
    
    @commands.command(aliases = ['dc'])
    async def dcs(self,ctx, *, arg): 
        self.table_instances[ctx.channel.id].undo_empty=self.table_instances[ctx.channel.id].redo_empty=False
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
        self.table_instances[ctx.channel.id].undo_empty=self.table_instances[ctx.channel.id].redo_empty=False
        if await self.check_callable(ctx, "dcs"): return
        
        usage = '\nUsage: ?dcs <DC number> <"on"/"during" or "off"/"before">' if len(self.table_instances[ctx.channel.id].dc_list)>0 else ""
        if isinstance(error, commands.MissingRequiredArgument):
            await self.send_messages(ctx, self.table_instances[ctx.channel.id].dc_list_str(), usage)
            return
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
        self.table_instances[ctx.channel.id].undo_empty=self.table_instances[ctx.channel.id].redo_empty=False
        if await self.check_callable(ctx, "players"): return
        await self.send_messages(ctx, self.table_instances[ctx.channel.id].get_player_list())
    
    @commands.command()
    async def edit(self,ctx, *args):
        self.table_instances[ctx.channel.id].undo_empty=self.table_instances[ctx.channel.id].redo_empty=False
        usage = "Usage: ?edit <player id> <gp number> <gp score>"
        if await self.check_callable(ctx, "edit"): return
        
        if len(args)==0:
            await self.send_temp_messages(ctx, self.table_instances[ctx.channel.id].get_player_list(), '\n',usage)
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
        self.table_instances[ctx.channel.id].undo_empty=self.table_instances[ctx.channel.id].redo_empty=False
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
        self.table_instances[ctx.channel.id].undo_empty=self.table_instances[ctx.channel.id].redo_empty=False
        if await self.check_callable(ctx, "tracklist"): return
        await self.send_messages(ctx, self.table_instances[ctx.channel.id].tracklist())
        
    @commands.command(aliases=['rxx', 'rid', 'room'])
    async def roomid(self, ctx):
        self.table_instances[ctx.channel.id].undo_empty=self.table_instances[ctx.channel.id].redo_empty=False
        if await self.check_callable(ctx, "rxx"): return
        
        await self.send_messages(ctx, 'Current table is watching room: '+self.table_instances[ctx.channel.id].rxx)
      
    @commands.command(aliases=['pen', 'pens'])
    async def penalty(self, ctx, *args):
        self.table_instances[ctx.channel.id].undo_empty=self.table_instances[ctx.channel.id].redo_empty=False
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
        if not pen.lstrip('-').lstrip('=').isnumeric():
            await self.send_temp_messages(ctx, "The penalty amount must be a number (negative allowed).", usage)
            return
        
        mes = self.table_instances[ctx.channel.id].penalty(pID, pen)
        await self.send_messages(ctx, mes)
    
    @commands.command(aliases=['unpen'])
    async def unpenalty(self, ctx, *args):
        self.table_instances[ctx.channel.id].undo_empty=self.table_instances[ctx.channel.id].redo_empty=False
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
                                
    @commands.command(aliases=['mr', 'merge'])
    async def mergeroom(self, ctx, *args): #TODO
        self.table_instances[ctx.channel.id].undo_empty=self.table_instances[ctx.channel.id].redo_empty=False
        if await self.check_callable(ctx, "mergeroom"): return
        
        usage = 'Usage: ?mergeroom <rxx or host> <rxx or host mii name>'
        if len(args)==0:
            await self.send_temp_messages(ctx, "Missing <rxx or host mii name> parameter.", usage)
            return
        
        rxx = args[0].lower()
    
    @commands.command(aliases=['gp', 'gps', 'changegp'])
    async def changegps(self, ctx, *args):
        self.table_instances[ctx.channel.id].undo_empty=self.table_instances[ctx.channel.id].redo_empty=False
        if await self.check_callable(ctx, "changegps"): return
        usage = "Usage: ?changegps <num gps>"
        if len(args)==0: 
            await self.send_temp_messages(ctx, usage)
            return
        try:
            if args[0][1] == '+' or args[0][1] == '-':
                gps = int(args[0])
                self.table_instances[ctx.channel.id].gps+=gps
            else:   
                gps = int(args[0])
                assert(gps>0)
                self.table_instances[ctx.channel.id].gps = gps
        except:
            await self.send_temp_messages(ctx, "<num gps> must be a real number.", usage)
            return
        
        await self.send_messages(ctx, "Changed total gps to {}.".format(gps))
        self.table_instances[ctx.channel.id].check_mkwx_update.start()
        
    @commands.command(aliases=['quickedit', 'qedit'])
    async def editrace(self,ctx, *, arg):
        self.table_instances[ctx.channel.id].undo_empty=self.table_instances[ctx.channel.id].redo_empty=False
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
        self.table_instances[ctx.channel.id].undo_empty=self.table_instances[ctx.channel.id].redo_empty=False
        if await self.check_callable(ctx, 'editrace'): return
        
        if isinstance(error, commands.MissingRequiredArgument):
            await self.send_messages(ctx, self.table_instances[ctx.channel.id].get_player_list(),"\nUsage: ?editrace <race number> <player id> <corrected placement>")
    
    @commands.command(aliases=['crs', 'roomsize'])
    async def changeroomsize(self, ctx, *, arg): 
        self.table_instances[ctx.channel.id].undo_empty=self.table_instances[ctx.channel.id].redo_empty=False
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
        self.table_instances[ctx.channel.id].undo_empty=self.table_instances[ctx.channel.id].redo_empty=False
        if await self.check_callable(ctx, "changeroomsize"): return
        
        if isinstance(error, commands.MissingRequiredArgument):
            await self.send_messages(ctx, "Usage: ?changeroomsize <race number> <corrected room size (num players)>")
        
        
    @commands.command(name='help',aliases = ['h'])
    async def _help(self,ctx):
        self.table_instances[ctx.channel.id].undo_empty=self.table_instances[ctx.channel.id].redo_empty=False
        info = 'List of commands:\n\t**?start**\n\t**?search**\n\t**?reset**\n\t**?players**\n\t**?tracks**\n\t**?rxx**\n\t**?raceresults\n\t?editrace\n\t?changeroomsize\n\t?dcs\n\t?penalty, ?unpenalty\n\t?tags\n\t?edittag\n\t?changetag\n\t?changegps\n\t?edit\n\t?undo, ?redo\n\t?pic**'
        await self.send_messages(ctx, info)
    
#bot.run(KEY)
def setup(bot):
    bot.add_cog(table_bot((bot)))