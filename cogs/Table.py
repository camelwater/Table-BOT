# -*- coding: utf-8 -*-
"""
Created on Wed May 19 08:33:13 2021

@author: ryanz
"""
import discord
from discord.ext import commands
from datetime import datetime
import bot
import utils.Utils as Utils
from classes.tabler import Table
import classes.Channel as Channel


class Table_cog(commands.Cog):
    def __init__(self, bot: bot.TableBOT):
        self.HOME_URL = "https://wiimmfi.de/stats/mkwx/list/"
        self.bot = bot
        self.TESTING = False
        
        if self.TESTING:
            Table(testing=True)
    
    @commands.Cog.listener()
    async def on_command(self, ctx: commands.Context):
        if ctx.command not in self.bot.get_cog('Table_cog').get_commands(): return
        self.set_instance(ctx)
        self.bot.channel_instances[ctx.channel.id].last_command_sent = datetime.now()
    
    def set_instance(self, ctx: commands.Context):
        channel_id = ctx.channel.id
        
        if channel_id in self.bot.channel_instances: 
            self.bot.channel_instances[channel_id].prefix = ctx.prefix
            return

        self.bot.channel_instances[channel_id] = Channel.Channel(bot=self.bot, ctx=ctx, table=Table())
        if ctx.guild:
            self.bot.channel_instances[channel_id].get_table().graph = self.bot.get_setting('graph',ctx.guild.id, raw=True)
            self.bot.channel_instances[channel_id].get_table().style = self.bot.get_setting('style', ctx.guild.id, raw=True)
     
    async def send_temp_messages(self, ctx, *args):
        try:
            await ctx.send('\n'.join(args), delete_after=25)
        except discord.errors.Forbidden:
            await ctx.send(f"I do not have adequate permissions. Check `{ctx.prefix}help` for a list of the permissions that I need.")
    async def send_messages(self,ctx, *args):
        try:
            await ctx.send('\n'.join(args))
        except discord.errors.Forbidden:
            await ctx.send(f"I do not have adequate permissions. Check `{ctx.prefix}help` for a list of the permissions that I need.")
      
    async def check_callable(self, ctx, command): #for most commands
        if self.bot.channel_instances[ctx.channel.id].confirm_room or self.bot.channel_instances[ctx.channel.id].confirm_reset:
            await self.send_temp_messages(ctx, "Please answer the last confirmation question:", self.bot.channel_instances[ctx.channel.id].choose_message)
            return True
        if command in ['yes', 'no']:
            if not self.bot.channel_instances[ctx.channel.id].confirm_room and not self.bot.channel_instances[ctx.channel.id].confirm_reset:
                await self.send_temp_messages(ctx, f"You can only use `{ctx.prefix}{command}` when the bot prompts you to do so.")
                return True
        else:
            if not self.bot.channel_instances[ctx.channel.id].table_running:
                await self.send_temp_messages(ctx, f"You need to have an active table before using `{ctx.prefix}{command}`.")
                return True
            
    async def check_special_callable(self, ctx): #used for commands that can be used when confirm_room == True
        if self.bot.channel_instances[ctx.channel.id].confirm_reset or(self.bot.channel_instances[ctx.channel.id].confirm_room and self.bot.channel_instances[ctx.channel.id].table_running):
            await self.send_temp_messages(ctx, "Please answer the last confirmation question:", self.bot.channel_instances[ctx.channel.id].choose_message)
            return True
        if not (self.bot.channel_instances[ctx.channel.id].confirm_room and not self.bot.channel_instances[ctx.channel.id].table_running) and not self.bot.channel_instances[ctx.channel.id].table_running:
            await self.send_temp_messages(ctx, "You can only use this command when the bot prompts you or when a table is active.")
            return True
        
    async def skip_search(self, ctx, arg, is_rxx):
        wait_mes = await ctx.send('Searching for room...')
        if is_rxx:
            error, self.bot.channel_instances[ctx.channel.id].choose_message = await self.bot.channel_instances[ctx.channel.id].get_table().find_room(rid = arg)
        else:
            error, self.bot.channel_instances[ctx.channel.id].choose_message = await self.bot.channel_instances[ctx.channel.id].get_table().find_room(mii = arg)

        if error:
            await wait_mes.delete()
            return await self.send_messages(ctx, self.bot.channel_instances[ctx.channel.id].choose_message)
        
        self.bot.channel_instances[ctx.channel.id].confirm_room = True

        if self.bot.channel_instances[ctx.channel.id].get_table().format[0] == 'f':
            mes = "Table successfully started. Watching room {}{}.".format(self.bot.channel_instances[ctx.channel.id].get_table().rxx, " (suppressing large finish time warnings)" if self.bot.channel_instances[ctx.channel.id].get_table().sui else '')
            self.bot.channel_instances[ctx.channel.id].table_running = True
            await wait_mes.delete()
            await self.send_messages(ctx, mes)
            self.bot.channel_instances[ctx.channel.id].searching_room = False
            self.bot.channel_instances[ctx.channel.id].confirm_room = False
            self.bot.channel_instances[ctx.channel.id].get_table().check_num_teams()
            self.bot.channel_instances[ctx.channel.id].get_table().populate_table_flags()
            self.bot.channel_instances[ctx.channel.id].check_mkwx_update.start()
            return

        await wait_mes.delete()   
        await self.send_messages(ctx, self.bot.channel_instances[ctx.channel.id].choose_message)
        
    async def cog_before_invoke(self,ctx):
        self.set_instance(ctx)
    
    #?start
    @commands.command(aliases=['st', 'starttable', 'sw', 'startwar'])
    async def start(self,ctx: commands.Context, *args):
        
        if self.bot.channel_instances[ctx.channel.id].confirm_room or self.bot.channel_instances[ctx.channel.id].confirm_reset:
            await self.send_temp_messages(ctx, "Please answer the last confirmation question:", self.bot.channel_instances[ctx.channel.id].choose_message)
            return
        if self.bot.channel_instances[ctx.channel.id].table_running:
            self.bot.channel_instances[ctx.channel.id].confirm_reset = True
            self.bot.channel_instances[ctx.channel.id].reset_args = args
            self.bot.channel_instances[ctx.channel.id].choose_message= f"A tabler watching room {self.bot.channel_instances[ctx.channel.id].get_table().rxx} is currently active.\nAre you sure you want to start a new table? (`{ctx.prefix}yes` / `{ctx.prefix}no`)"
            await self.send_messages(ctx, self.bot.channel_instances[ctx.channel.id].choose_message)
            return

        prefix = ctx.prefix
        usage = f"Usage: `{prefix}start [format] [number of teams]  [rxx|miiNames] [gps=3] [sui=no]`"
        
        if len(args)<1:
            return await ctx.send(usage)
#             self.bot.channel_instances[ctx.channel.id].searching_room = True   
#             return await self.send_messages(ctx, f"Provide a room id (rxx) or mii name(s) to search for a room. Make sure the room has finished at least one race.", f"\nUsage: `{prefix}search <rxx or mii> <rxx or mii names(s)>`")
    
         
        if isinstance(args[0], tuple) and self.bot.channel_instances[ctx.channel.id].reset_args !=None:
            args = args[0]
        args = list(args)
            
        _format = args[0].lower()
        
        # if len(args)<2 and _format[0]!='f':
        #     await self.send_temp_messages(ctx, "Missing <teams>.", usage)
        #     return

        teams = Utils.max_teams(_format)
        if len(args)<2 or not args[1].isnumeric():
            args.insert(1, teams)
        
        if _format not in ['ffa', '2v2', '3v3', '4v4', '5v5', '6v6', '2', '3', '4', '5', '6']:
            await self.send_messages(ctx, "Invalid format. Format must be FFA, 2v2, 3v3, 4v4, 5v5, or 6v6.", usage)
            return
        
        if len(args)>1:
            try:
                teams = int(args[1])
                assert(teams>0)
            except (ValueError, AssertionError):
                await self.send_messages(ctx, "<teams> must be a postive number.", usage)
                return
        
        if Utils.check_teams(_format, teams):
            return await self.send_messages(ctx, f"Invalid number of teams. For a {Utils.full_format(_format)}, the maximum number of teams you can have is {Utils.max_teams(_format)}.", usage)

        self.bot.channel_instances[ctx.channel.id].get_table().format = _format
        self.bot.channel_instances[ctx.channel.id].get_table().set_teams(teams)
        num_players = Utils.get_num_players(_format, teams) 
        self.bot.channel_instances[ctx.channel.id].get_table().num_players = num_players
        gps = 3
        sui=None
        for i in args:
            if isinstance(i, str) and i.find('sui=')==0:
                sui = args.pop(args.index(i))
                break
        for i in args:
            if isinstance(i, str) and i.find("gps=")==0:
                gps = args.pop(args.index(i))[4:]
                if not gps.isnumeric() or int(gps)<1:
                    await self.sent_temp_messages(ctx, "Invalid number of gps. <gps> must a positive non-zero number.", usage)
                break
        self.bot.channel_instances[ctx.channel.id].get_table().gps = int(gps)

        if sui!=None:
            self.bot.channel_instances[ctx.channel.id].get_table().sui = True if sui[4:][0]=='y' else False 
        else:
            if ctx.guild:
                self.bot.channel_instances[ctx.channel.id].get_table().set_sui(self.bot.get_setting('IgnoreLargeTimes', ctx.guild.id))

        if len(args)>2:
            arg3 = args[2]
            if Utils.is_rxx(arg3) and len(args[2:])==1:
                data = [arg3]
                is_rxx = True
            else:
                data = args[2:]
                is_rxx = False
            
            await self.skip_search(ctx, data, is_rxx)
            return
            
        self.bot.channel_instances[ctx.channel.id].searching_room = True   
        await self.send_messages(ctx, f"Provide a room id (rxx) or mii name(s) to search for a room. Make sure the room has finished at least one race.", f"\nUsage: `{prefix}search <rxx or mii> <rxx or mii names(s)>`")
    
    #?search   
    @commands.command(aliases=['sr'])  
    async def search(self,ctx: commands.Context, *, arg):
        prefix = ctx.prefix
        if self.bot.channel_instances[ctx.channel.id].confirm_room or self.bot.channel_instances[ctx.channel.id].confirm_reset:
            await self.send_temp_messages(ctx, "Please answer the last confirmation question:", self.bot.channel_instances[ctx.channel.id].choose_message)
            return
       
        if not self.bot.channel_instances[ctx.channel.id].searching_room:
            await self.send_temp_messages(ctx, f"You cannot search for a room right now. You can only use this command after the `{prefix}start` command.")
            return
        
        arg = arg.strip()
        
        usage = f"\nUsage: `{prefix}search <rxx or mii> <rxx or name(s)>`\nmkwx room list: {self.HOME_URL}"
        if len(arg)<1:
            await self.send_temp_messages(ctx, usage)
            return
         
        arg_indx = arg.find(' ')
        if arg_indx == -1: arg_indx = len(arg)+1
        search_type = arg[:arg_indx].lower()
        search_args = arg[arg_indx+1:].split(",")
        search_args = [i.lower().strip() for i in search_args]
        
        if len(search_args)<1:
            return await self.send_messages("You need to provide <rxx or mii name(s)>.", usage)
        if len(search_args)>self.bot.channel_instances[ctx.channel.id].get_table().num_players:
            await self.send_messages(ctx, "You cannot provide more than {} mii names.".self.format(self.bot.channel_instances[ctx.channel.id].get_table().num_players), usage)
            return
        
        if search_type == 'roomid' or search_type=='rxx':
            if search_args[0].isnumeric():
                await self.send_messages(ctx, "Invalid room id: missing an 'r' or not in format 'XX00'.", usage)
                return
            wait_mes = await ctx.send('Searching for room...')
            error, self.bot.channel_instances[ctx.channel.id].choose_message = await self.bot.channel_instances[ctx.channel.id].get_table().find_room(rid = search_args)
        elif search_type == "mii":   
            wait_mes = await ctx.send('Searching for room...')
            error, self.bot.channel_instances[ctx.channel.id].choose_message = await self.bot.channel_instances[ctx.channel.id].get_table().find_room(mii = search_args)
        else:
            await self.send_messages(ctx, f"Invalid argument for `{prefix}search`: <search type> must be 'rxx' or 'mii'", usage)
            return
        
        if error:
            await wait_mes.delete()
            return await self.send_messages(ctx, self.bot.channel_instances[ctx.channel.id].choose_message, usage)
        
        self.bot.channel_instances[ctx.channel.id].confirm_room = True
        await wait_mes.delete()
        await self.send_messages(ctx, self.bot.channel_instances[ctx.channel.id].choose_message)
    
    @search.error
    async def search_error(self,ctx: commands.Context, error):
        self.set_instance(ctx)
        if isinstance(error, commands.MissingRequiredArgument):
            if not self.bot.channel_instances[ctx.channel.id].searching_room:
                await self.send_temp_messages(ctx, f"You cannot search for a room right now. You can only use this command after the `{ctx.prefix}start` command.")
                return

            await self.send_messages(ctx, f"Usage: `{ctx.prefix}search <rxx or mii> <rxx or name(s)>`\nmkwx room list: {self.HOME_URL}") 
    
    @commands.command(aliases=['name'])
    async def changename(self, ctx: commands.Context, *, arg):
        px = ctx.prefix
        usage = f'Usage: `{px}changename <player number> <name>`'
        if await self.check_callable(ctx, "changename"): return

        arg = [i.strip() for i in arg.strip().split("/")]
        arg  = [i.split(" ") for i in arg]

        for i in arg:
            if len(i)<1:
                await self.send_temp_messages(ctx, "Missing player number(s) for command.", self.bot.channel_instances[ctx.channel.id].get_table().get_player_list(), '\n',usage)
                return
            # if len(i)<2:
            #     await self.send_temp_messages(ctx, "Error processing command: missing <name> for player '{}'".format(i[0]), self.bot.channel_instances[ctx.channel.id].get_table().get_player_list(), usage)
            #     return
            if not i[0].isnumeric():
                await self.send_temp_messages(ctx, "<player number>(s) must be numeric.")
                return
        
        mes = self.bot.channel_instances[ctx.channel.id].get_table().change_name(arg)
        await ctx.send(mes)
        
    
    @changename.error
    async def changename_error(self,ctx, error):
        self.set_instance(ctx)
        if await self.check_callable(ctx, "changename"): return
        if isinstance(error, commands.MissingRequiredArgument):
            await self.send_messages(ctx, self.bot.channel_instances[ctx.channel.id].get_table().get_player_list(),f'\nUsage: `{ctx.prefix}changename <player number> <name>`')       
    
    #change one player's tag
    @commands.command(aliases=['ct'])
    async def changetag(self,ctx, *args): 
        if await self.check_special_callable(ctx): return
        if Utils.isFFA(self.bot.channel_instances[ctx.channel.id].get_table().format): 
            await ctx.send("This command cannot be used in FFAs.")
        
        px = ctx.prefix
        usage = f"Usage: `{px}changetag <player id> <corrected tag>`"
        if len(args)==0:
            await self.send_temp_messages(ctx, self.bot.channel_instances[ctx.channel.id].get_table().get_player_list(),'\n',usage)
            return
        
        pID = args[0].lower()
        if not pID.isnumeric():
            await self.send_temp_messages(ctx, "<player id> must be a number.", usage)
            return
        if len(args)<2:
            await self.send_temp_messages(ctx, "missing <corrected tag> parameter.", usage)
            return
        
        tag = args[1]
        mes= self.bot.channel_instances[ctx.channel.id].get_table().change_tag(pID, tag)
        if self.bot.channel_instances[ctx.channel.id].confirm_room:
            self.bot.channel_instances[ctx.channel.id].choose_message = self.bot.channel_instances[ctx.channel.id].get_table().get_player_list() +f"\n**Is this correct?** (`{px}yes` / `{px}no`)"
            await self.send_messages(ctx, mes, self.bot.channel_instances[ctx.channel.id].get_table().get_player_list(p_form=False), f"\n**Is this correct?** (`{px}yes` / `{px}no`)")
        else:
            await self.send_messages(ctx, mes)
        
    @commands.command(aliases=['et', 'edittags']) 
    async def edittag(self,ctx: commands.Context, *, arg): 
        px = ctx.prefix
        usage = f'Usage: `{px}edittag <tag> <corrected tag>`'
        if await self.check_special_callable(ctx): return
        if Utils.isFFA(self.bot.channel_instances[ctx.channel.id].get_table().format): 
            await ctx.send("This command cannot be used in FFAs.")
        
        arg = [i.strip() for i in arg.strip().split("/")]
        arg  = [i.split(" ") for i in arg]
        if len(arg)==0:
            await self.send_temp_messages(ctx, self.bot.channel_instances[ctx.channel.id].get_table().get_player_list(), '\n', usage)
        for i in arg:
            if len(i)<1:
                await self.send_temp_messages(ctx, "Missing tag(s) for command.", self.bot.channel_instances[ctx.channel.id].get_table().get_player_list(), '\n',usage)
                return
            if len(i)<2:
                await self.send_temp_messages(ctx, "Error processing command: missing <corrected tag> for tag `{}`.".format(i[0]), self.bot.channel_instances[ctx.channel.id].get_table().get_player_list(), usage)
                return
        
        mes = self.bot.channel_instances[ctx.channel.id].get_table().edit_tag_name(arg)
        if self.bot.channel_instances[ctx.channel.id].confirm_room:
            self.bot.channel_instances[ctx.channel.id].choose_message = self.bot.channel_instances[ctx.channel.id].get_table().get_player_list() + f"\n**Is this correct?** (`{px}yes` / `{px}no`)"
            await self.send_messages(ctx, mes, self.bot.channel_instances[ctx.channel.id].get_table().get_player_list(p_form=False), f"\n**Is this correct?** (`{px}yes` / `{px}no`)")
        else:
            await self.send_messages(ctx, mes)
            
    @edittag.error
    async def edittag_error(self,ctx, error):
        self.set_instance(ctx)
        
        if await self.check_special_callable(ctx): return
        if Utils.isFFA(self.bot.channel_instances[ctx.channel.id].get_table().format): 
            await ctx.send("This command cannot be used in FFAs.")
        if isinstance(error, commands.MissingRequiredArgument):
            await self.send_messages(ctx, self.bot.channel_instances[ctx.channel.id].get_table().get_player_list(team_command=True),f'\nUsage: `{ctx.prefix}edittag <tag> <corrected tag>`')    
    
    #to manually create tags
    @commands.command(aliases=['tag'])
    async def tags(self,ctx, *, arg): 
        px = ctx.prefix
        usage = f"Usage: `{px}tags <tag> <pID(s)> / <tag> <pID(s)>`\n**ex.** `{px}tags Player 1 3 / Z 2 4 / B 5 6`"
        if await self.check_special_callable(ctx): return
        if Utils.isFFA(self.bot.channel_instances[ctx.channel.id].get_table().format): 
            await ctx.send("This command cannot be used in FFAs.")
        
        arg = [i.strip() for i in arg.strip().split("/")]
        arg  = [i.split(" ") for i in arg]
        if len(arg)==0:
            await self.send_temp_messages(ctx, self.bot.channel_instances[ctx.channel.id].get_table().get_player_list(), '\n',usage)
            return
        for i in arg:
            if len(i)<1:
                await self.send_temp_messages(ctx, "Missing tag(s) for command.", self.bot.channel_instances[ctx.channel.id].get_table().get_player_list(), '\n',usage)
                return
            if len(i)<2:
                await self.send_temp_messages(ctx, "Error processing command: missing players for tag `{}`".format(i[0]), self.bot.channel_instances[ctx.channel.id].get_table().get_player_list(), usage)
                return
            for indx, j in enumerate(i[1:]):
                if not j.isnumeric():
                    await self.send_temp_messages(ctx, "Error processing players for tag `{}`: `{}` is not a number. All players must be numeric.".format(i[0], i[indx]), usage)
                    return 
        dic = {}
        for i in arg:
            dic[i[0]] = i[1:]
        
        mes = self.bot.channel_instances[ctx.channel.id].get_table().group_tags(dic)
        if self.bot.channel_instances[ctx.channel.id].confirm_room:
            self.bot.channel_instances[ctx.channel.id].choose_message = self.bot.channel_instances[ctx.channel.id].get_table().get_player_list(p_form=False) +f"\n**Is this correct?** (`{px}yes` / `{px}no`)"
            await self.send_messages(ctx, mes, self.bot.channel_instances[ctx.channel.id].get_table().get_player_list(p_form=False), f"\n**Is this correct?** (`{px}yes` / `{px}no`)")
        else:
            await self.send_messages(ctx, self.bot.channel_instances[ctx.channel.id].get_table().get_player_list(p_form=True), mes)
        
    @tags.error
    async def tags_error(self,ctx, error):
        self.set_instance(ctx)
        
        if await self.check_special_callable(ctx): return
        if Utils.isFFA(self.bot.channel_instances[ctx.channel.id].get_table().format): 
            await ctx.send("This command cannot be used in FFAs.")
        
        if isinstance(error, commands.MissingRequiredArgument):
            await self.send_messages(ctx, self.bot.channel_instances[ctx.channel.id].get_table().get_player_list(p_form=True), f"\nUsage: `{ctx.prefix}tags <tag> <pID(s)> / <tag> <pID(s)>`\n**ex.** `{ctx.prefix}tags Player 1 3 / Z 2 4 / B 5 6`")
    
    @commands.command(aliases=['y'])
    async def yes(self,ctx):
        px = ctx.prefix
        if not self.bot.channel_instances[ctx.channel.id].confirm_room and not self.bot.channel_instances[ctx.channel.id].confirm_reset:
            await self.send_temp_messages(ctx, f"You can only use `{px}yes` if the bot prompts you to do so.")
            return
        
        if self.bot.channel_instances[ctx.channel.id].confirm_room:
            # if self.bot.channel_instances[ctx.channel.id].get_table().choose_room: self.bot.channel_instances[ctx.channel.id].get_table().choose_room = False
            if len(self.bot.channel_instances[ctx.channel.id].get_table().players)> self.bot.channel_instances[ctx.channel.id].get_table().num_players:
                mes = "**Warning:** *The number of players in the room doesn't match the given format and teams.*\nTable started, *but will likely be inaccurate*. Watching room {}{}.".format(self.bot.channel_instances[ctx.channel.id].get_table().rxx, " (suppressing large finish time warnings)" if self.bot.channel_instances[ctx.channel.id].get_table().sui else '')
            else:   
                mes = "Table successfully started. Watching room {}{}.".format(self.bot.channel_instances[ctx.channel.id].get_table().rxx, " (suppressing large finish time warnings)" if self.bot.channel_instances[ctx.channel.id].get_table().sui else '')

            self.bot.channel_instances[ctx.channel.id].table_running = True
            self.bot.channel_instances[ctx.channel.id].searching_room = False
            self.bot.channel_instances[ctx.channel.id].confirm_room = False
            self.bot.channel_instances[ctx.channel.id].get_table().check_num_teams()
            
            await self.send_messages(ctx, mes)
            self.bot.channel_instances[ctx.channel.id].get_table().populate_table_flags()
            self.bot.channel_instances[ctx.channel.id].mkwx_update.start()
            
        elif self.bot.channel_instances[ctx.channel.id].confirm_reset:
            self.bot.channel_instances[ctx.channel.id].mkwx_update.stop()
            reset_args = self.bot.channel_instances[ctx.channel.id].reset_args
            self.bot.channel_instances.pop(ctx.channel.id)
            await self.send_messages(ctx, "Table has been reset.")
            
            self.set_instance(ctx)
            self.bot.channel_instances[ctx.channel.id].reset_args = reset_args
            await self.start(ctx, self.bot.channel_instances[ctx.channel.id].reset_args)
        
    @commands.command(aliases=['n'])
    async def no(self,ctx):
        if not self.bot.channel_instances[ctx.channel.id].confirm_room and not self.bot.channel_instances[ctx.channel.id].confirm_reset:
            await self.send_temp_messages(ctx, f"You can only use `{ctx.prefix}no` if the bot prompts you to do so.")
            return 
        if self.bot.channel_instances[ctx.channel.id].confirm_room:
            self.bot.channel_instances[ctx.channel.id].confirm_room = False
            self.bot.channel_instances.pop(ctx.channel.id)
            await self.send_messages(ctx, f"Table stopped. `{ctx.prefix}start` to start a new table")
           
        elif self.bot.channel_instances[ctx.channel.id].confirm_reset:
            self.bot.channel_instances[ctx.channel.id].confirm_reset = False
            await self.send_messages(ctx, "Tabler watching room {} will continue running.".format(self.bot.channel_instances[ctx.channel.id].get_table().rxx))
    
    @commands.command(aliases=['theme'])
    async def style(self, ctx, *, choice):
        if await self.check_callable(ctx, "style"): return

        mes = self.bot.channel_instances[ctx.channel.id].get_table().change_style(choice)
        await ctx.send(mes)
    
    @style.error
    async def style_error(self, ctx, error):
        self.set_instance(ctx)
        if await self.check_callable(ctx, "style"): return
        if isinstance(error, commands.MissingRequiredArgument):
            await self.send_messages(ctx, self.bot.channel_instances[ctx.channel.id].get_table().style_options(), f"\nUsage: `{ctx.prefix}style <styleNumber|styleName>`")

    @commands.command()
    async def graph(self, ctx, *, choice):
        if await self.check_callable(ctx, "graph"): return

        mes = self.bot.channel_instances[ctx.channel.id].get_table().change_graph(choice)
        await ctx.send(mes)
    
    @graph.error
    async def graph_error(self, ctx, error):
        self.set_instance(ctx)
        if await self.check_callable(ctx, "graph"): return

        if isinstance(error, commands.MissingRequiredArgument):
            await self.send_messages(ctx, self.bot.channel_instances[ctx.channel.id].get_table().graph_options(), f"\nUsage: `{ctx.prefix}graph <graphNumber|graphName>`")        
    
    @commands.command(aliases=['showlarge', 'showlargefinishtimes', 'large', 'largefinish', 'showlargefinish', 
                        'largefinishtimes', 'largetimes', 'showlargetimes', 'ignorelarge', 'ignoretimes', 'ignorelargefinish', 'ignorelargefinishtimes',
                        'ignorefinishtimes'])
    async def ignorelargetimes(self,ctx: commands.Context, choice: str):
        if await self.check_callable(ctx, "ignorelargetimes"): return
        if choice.lower() not in {'yes', 'y', 'no', 'n'}: 
            return await ctx.send(f"Invalid value `{choice}`. You must put either yes or no.")

        show_large = True if choice.lower() in {'yes', 'y'} else False
        if 'ignore' not in ctx.invoked_with:
            show_large = not show_large
        self.bot.channel_instances[ctx.channel.id].get_table().change_sui(show_large)
        await ctx.send("Table now showing large finish times." if not show_large else "Table now suppressing large finish times.")

    @ignorelargetimes.error
    async def largefinishtimes_error(self, ctx, error):
        self.set_instance(ctx)
        if await self.check_callable(ctx, "ignorelargetimes"): return

        if isinstance(error, commands.MissingRequiredArgument):
            await self.send_messages(ctx, f"\nUsage: `{ctx.prefix}ignorelargetimes <yes/no>`")     

    @commands.command(aliases=['showerrors', 'warnings', 'showwarnigns', 'err', 'warn', 'errs', 'warns'])
    async def errors(self, ctx: commands.Context):
        if await self.check_callable(ctx, "errors"): return

        path = "./error_footers/"
        filename = f"warnings_and_errors-{ctx.channel.id}.txt"
        warn_content = self.bot.channel_instances[ctx.channel.id].get_table().get_warnings(override=True)
        if "No warnings or room errors." in warn_content: 
            return await ctx.send("*No warnings or room errors.*")
        err_file = Utils.create_temp_file(filename, warn_content, dir=path)
        Utils.delete_file(path+filename)

        # err_file = Utils.get_errors_file(filename)
        # if isinstance(err_file, str):
        #     return await ctx.send(err_file)
        
        await ctx.send(file = discord.File(fp=err_file, filename=filename))
    
    #?picture
    @commands.command(aliases=['p', 'pic', 'wp', 'warpicture', 'tablepic', 'tablepicture', 'table', 'tp'])
    @commands.max_concurrency(number=1, wait=True, per = commands.BucketType.channel)
    @commands.cooldown(1, 10, type=commands.BucketType.channel)
    async def picture(self,ctx, *arg):
        if self.bot.channel_instances[ctx.channel.id].picture_running:
            return await self.send_temp_messages(ctx, "This command is currently in use. Please wait.")
        
        if await self.check_callable(ctx, "picture"): return
        self.bot.channel_instances[ctx.channel.id].picture_running = True
        byrace = False
        large_times = None
        arg = list(map(lambda l: l.lower(), arg))
        if len(arg)>0:
            if 'byrace' in arg or 'race' in arg: byrace = True
            bool_list = ['largetimes=' in i for i in arg]
            if any(bool_list): 
                check_arg = arg[bool_list[::-1].index(True)]

                if check_arg[check_arg.find('=')+1:][0]=='y': large_times = True
                elif check_arg[check_arg.find('=')+1:][0]=='n': large_times = False

        wait_mes = await ctx.send("Updating scores...")
        mes = await self.bot.channel_instances[ctx.channel.id].get_table().update_table()
        await wait_mes.edit(content=mes)
        pic_mes = await ctx.send("Fetching table picture...")
        img = await self.bot.channel_instances[ctx.channel.id].get_table().get_table_img(by_race=byrace)
        if isinstance(img, str):
            await pic_mes.delete()
            return await ctx.send(img)
        
        f=discord.File(fp=img, filename='table.png')
        em = discord.Embed(title=self.bot.channel_instances[ctx.channel.id].get_table().title_str(),
                        description="\n[Edit this table on gb.hlorenzi.com]("+self.bot.channel_instances[ctx.channel.id].get_table().table_link+")")
        
        em.set_image(url='attachment://table.png')
        is_overflow, error_footer, full_footer = self.bot.channel_instances[ctx.channel.id].get_table().get_warnings(show_large_times = large_times)
        em.set_footer(text = error_footer)
        
        await ctx.send(embed=em, file=f)
        await pic_mes.delete()
        self.bot.channel_instances[ctx.channel.id].picture_running = False

        if is_overflow: #send file of errors
            path = "./error_footers/"
            filename = f'warnings_and_errors-{ctx.channel.id}.txt'
            e_file = Utils.create_temp_file(filename, full_footer, dir=path)
            Utils.delete_file(path+filename)
            # e_file = Utils.get_errors_file(filename)
            # if isinstance(e_file, str):
            #     return await ctx.send(e_file) 

            await ctx.send(file = discord.File(fp=e_file, filename=filename))
        
    
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
        if len(self.bot.channel_instances[ctx.channel.id].get_table().modifications) == 0:
            return await ctx.send("No table modifications to undo.")

        del_mes = await ctx.send("Undoing...")
        mes = await self.bot.channel_instances[ctx.channel.id].get_table().undo_commands(args)
        await del_mes.delete()
        await self.send_messages(ctx,mes)
    
    @commands.command(aliases=['undolist'])
    async def undos(self, ctx):
        if await self.check_callable(ctx, "undos"): return
        await self.send_messages(ctx, self.bot.channel_instances[ctx.channel.id].get_table().get_modifications())
        
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
        
        if len(self.bot.channel_instances[ctx.channel.id].get_table().undos) == 0:
            return await ctx.send("No table modifications to redo.")
        del_mes = await ctx.send("Redoing...")
        mes = await self.bot.channel_instances[ctx.channel.id].get_table().redo_commands(args)
        await del_mes.delete()
        await self.send_messages(ctx,mes)
    
    @commands.command(aliases=['redolist'])
    async def redos(self, ctx):
        if await self.check_callable(ctx, "redos"): return
        await self.send_messages(ctx, self.bot.channel_instances[ctx.channel.id].get_table().get_undos())
       
     
    #?reset
    @commands.command(aliases=['stop', 'clear', 'quit', 'end', 'done', 'finish', 'destroy'])
    async def reset(self,ctx):
        if not self.bot.channel_instances[ctx.channel.id].table_running and not self.bot.channel_instances[ctx.channel.id].confirm_room:
            await self.send_temp_messages(ctx, "You don't have an active table to reset.")
            return
        
        self.bot.channel_instances[ctx.channel.id].mkwx_update.stop()
        # Utils.destroy_temp_files(ctx.channel.id)
        self.bot.channel_instances.pop(ctx.channel.id)
       
        await self.send_messages(ctx, f"Table has been reset. `{ctx.prefix}start` to start a new table.")
        
    
    @commands.command(aliases = ['dc'])
    async def dcs(self,ctx, *, arg): 
        
        if await self.check_callable(ctx, "dcs"): return
        px = ctx.prefix
        usage = f'\nUsage: `{px}dc <DC number> <"on"/"during" or "off"/"before">`' if len(self.bot.channel_instances[ctx.channel.id].get_table().dc_list)>0 else ""
        
        arg = [i.strip() for i in arg.strip().split("/")]
        arg  = [i.split(" ") for i in arg]
        
        for i in arg:
            if len(i)<1:
                await self.send_temp_messages(ctx, "Error: Missing <DC number>.", self.bot.channel_instances[ctx.channel.id].get_table().dc_list_str(), usage)
                return
            if len(i)<2:
                await self.send_temp_messages(ctx, "Error processing command: missing <DC status> for DC number {}.".format(i[0]), self.bot.channel_instances[ctx.channel.id].get_table().dc_list_str(), usage)
                return
            if len(i)>2:
                return await self.send_temp_messages(ctx, "Too many arguments for player number {}. The only arguments should be <DC number> and <DC status>.".format(i[0]), self.bot.channel_instances[ctx.channel.id].get_table().dc_list_str(), usage)
            if not i[0].isnumeric():
                return await self.send_temp_messages(ctx, "DC numbers must be numeric.", self.bot.channel_instances[ctx.channel.id].get_table().dc_list_str(), usage)

            if not (i[1] == "on" or i[1]=='during') and not (i[1]=='off' or i[1] == "before"):
                return await self.send_temp_messages(ctx, "The <DC status> argument must be either 'on'/'during' or 'off'/'before'.", self.bot.channel_instances[ctx.channel.id].get_table().dc_list_str(), usage)
            
        mes = self.bot.channel_instances[ctx.channel.id].get_table().edit_dc_status(arg)
        await self.send_messages(ctx, mes)
        
          
    @dcs.error
    async def dcs_error(self,ctx, error):
        self.set_instance(ctx)
        
        if await self.check_callable(ctx, "dcs"): return
        
        usage = f'\nUsage: `{ctx.prefix}dcs <DC number> <"on"/"during" or "off"/"before">`' if len(self.bot.channel_instances[ctx.channel.id].get_table().dc_list)>0 else ""
        if isinstance(error, commands.MissingRequiredArgument):
            await self.send_messages(ctx, self.bot.channel_instances[ctx.channel.id].get_table().dc_list_str(), usage)
            return
    
    @commands.command(aliases=['substitute', 'subin', 'subout'])
    async def sub(self, ctx, *args): 
        
        if await self.check_callable(ctx, "sub"): return
        
        usage = f"\n**Note:** *It is advised to use this command when all races have finished, rather than right when the subsitution occurs.* \
                \nUsage: `{ctx.prefix}sub <sub out> <sub out races played> <sub in>`"
        if len(args)==0:
            await self.send_messages(ctx, self.bot.channel_instances[ctx.channel.id].get_table().get_player_list(), usage) 
            return
        if len(args)<2:
            await self.send_temp_messages(ctx, "Missing <sub out races played> and <sub in>.", self.bot.channel_instances[ctx.channel.id].get_table().get_player_list(), usage)
            return
        if len(args)<3:
            await self.send_temp_messages(ctx, "Missing <sub in>.",self.bot.channel_instances[ctx.channel.id].get_table().get_player_list(), usage)
            return
        
        subIn = args[2]
        subOut = args[0]
        subOut_races = args[1]
        
        if not subIn.isnumeric():
            await self.send_temp_messages(ctx, "<sub in> must be a number.", self.bot.channel_instances[ctx.channel.id].get_table().get_player_list(), usage)
            return
        if not subOut.isnumeric():
            await self.send_temp_messages(ctx, "<sub out> must be a number.", self.bot.channel_instances[ctx.channel.id].get_table().get_player_list(), usage)
            return
        if not subOut_races.isnumeric():
            await self.send_temp_messages(ctx, "<sub out races played> must be a number.", self.bot.channel_instances[ctx.channel.id].get_table().get_player_list(), usage)
            return
        
        mes = self.bot.channel_instances[ctx.channel.id].get_table().sub_in(subIn, subOut, subOut_races)
        await self.send_messages(ctx, mes)

    @commands.command(aliases=['subins', 'subouts'])
    async def subs(self, ctx):
        if await self.check_callable(ctx, "subs"): return

        await ctx.send(self.bot.channel_instances[ctx.channel.id].get_table().get_subs())

    @commands.command(aliases=['editsubraces', 'subraces'])
    async def editsub(self, ctx, *args):
        if await self.check_callable(ctx, "editsub"): return
        
        usage = f"\nUsage: `{ctx.prefix}editsub <player number> <correct races> <in/out> (sub out index)`"
        if len(args)==0:
            await self.send_messages(ctx, self.bot.channel_instances[ctx.channel.id].get_table().get_player_list(), usage)
            return
        
        if len(args)<2:
            await self.send_temp_messages(ctx, "Missing <correct races> and <in/out>.", self.bot.channel_instances[ctx.channel.id].get_table().get_player_list(), usage)
            return
        if len(args)<3:
            await self.send_temp_messages(ctx, "Missing <in/out>.", self.bot.channel_instances[ctx.channel.id].get_table().get_player_list(), usage)
            return
        
        try:
            p_indx = int(args[0])
        except ValueError:
            await self.send_temp_messages(ctx, "<player number> must be a number.", self.bot.channel_instances[ctx.channel.id].get_table().get_player_list(), usage)
            return
        try:
            races = int(args[1])
        except ValueError:
            await self.send_temp_messages(ctx, "<correct races> must be a number.", self.bot.channel_instances[ctx.channel.id].get_table().get_player_list(), usage)
            return
        is_in = args[2].lower()=='in'
        
        if len(args)>3 and not is_in:
            try:
                out_index = int(args[3])
            except ValueError:
                await self.send_temp_messages(ctx, "<sub out index> must be a number.", self.bot.channel_instances[ctx.channel.id].get_table().get_player_list(), usage)
                return
            mes = self.bot.channel_instances[ctx.channel.id].get_table().edit_sub_races(p_indx, races, is_in, out_index)
        else:
            mes = self.bot.channel_instances[ctx.channel.id].get_table().edit_sub_races(p_indx, races, is_in)
        
        await self.send_messages(ctx, mes)
            
    @commands.command(aliases=['ap'])
    async def allplayers(self, ctx):
        
        if await self.check_callable(ctx, "allplayers"): return
        await self.send_messages(ctx, self.bot.channel_instances[ctx.channel.id].get_table().get_all_players())
        
    @commands.command(aliases=['pl', 'players'])
    async def playerlist(self,ctx):
        
        if await self.check_callable(ctx, "players"): return
        await self.send_messages(ctx, self.bot.channel_instances[ctx.channel.id].get_table().get_player_list(p_form=False, include_tag=False))
    
    @commands.command(aliases=['e'])
    async def edit(self,ctx: commands.Context, * , arg):
        
        usage = f"Usage: `{ctx.prefix}edit <player id> <gp number> <gp score>`"
        if await self.check_callable(ctx, "edit"): return
        
        if len(arg)==0:
            await self.send_messages(ctx, self.bot.channel_instances[ctx.channel.id].get_table().get_player_list(), '\n',usage)
            return
        arg = [i.strip() for i in arg.strip().split("/")]
        arg  = [i.split(" ") for i in arg]
        
        for i in arg:
            if len(i)<1:
                await self.send_temp_messages(ctx, "Error: Missing <player number>.", usage)
                return
            if len(i)<2:
                await self.send_temp_messages(ctx, "Error processing command: missing <gp number> for player number {}.".format(i[0]), usage)
                return
            if len(i)<3:
                await self.send_temp_messages(ctx, f"Error: missing <gp score> for player number {i[0]}.")
                return
            if len(i)>3:
                await self.send_temp_messages(ctx, "Too many arguments for player number {}. The only arguments should be <player number>, <gp number>, and <gp score>.".format(i[0]), usage)
                return
            for j in i:
                try:
                    int(j)
                except ValueError:
                    await self.send_temp_messages(ctx, "All arguments for this command must be numeric.")
                    return

        mes = self.bot.channel_instances[ctx.channel.id].get_table().edit(arg)
        await ctx.send(mes)
        
    @edit.error
    async def edit_error(self, ctx, error): 
        self.set_instance(ctx)
        if await self.check_callable(ctx, "edit"): return
        if isinstance(error, commands.MissingRequiredArgument): 
            await self.send_messages(ctx, self.bot.channel_instances[ctx.channel.id].get_table().get_player_list(), f"\nUsage: `{ctx.prefix}edit <player id> <gp number> <gp score>`")

    @commands.command(aliases = ['rr', 'res', 'results', 'race'])
    async def raceresults(self,ctx, *args):
        
        if await self.check_callable(ctx, "raceresults"): return
        usage = f"Usage: `{ctx.prefix}rr <race # = last race>`"
        race = -1
        if len(args)>0:
            if not args[0].isnumeric():
                await self.send_temp_messages(ctx, "<race number> must be a number.", usage)
                return
            race = int(args[0])
        error, mes = self.bot.channel_instances[ctx.channel.id].get_table().race_results(race)
        if error:
            await self.send_temp_messages(ctx, mes, usage)
            return
        await self.send_messages(ctx, mes)
        
    @commands.command(aliases=['tl', 'tracks', 'races'])
    async def tracklist(self,ctx):
        
        if await self.check_callable(ctx, "tracklist"): return
        await self.send_messages(ctx, self.bot.channel_instances[ctx.channel.id].get_table().tracklist())
        
    @commands.command(aliases=['rxx', 'rid', 'room'])
    async def roomid(self, ctx):
        
        if await self.check_callable(ctx, "rxx"): return
        
        await self.send_messages(ctx, self.bot.channel_instances[ctx.channel.id].get_table().get_rxx())
      
    @commands.command(aliases=['pens'])
    async def penalties(self, ctx):
        if await self.check_callable(ctx, "penalties"): return
        await ctx.send(self.bot.channel_instances[ctx.channel.id].get_table().get_pen_player_list(c_form=False))
        
    @commands.command(aliases=['pen'])
    async def penalty(self, ctx, *args):
        
        if await self.check_callable(ctx, "penalty"): return
        usage = f"Usage: `{ctx.prefix}pen <player id> <pen amount>`"
        
        if len(args)==0:
            await self.send_messages(ctx, self.bot.channel_instances[ctx.channel.id].get_table().get_pen_player_list(), '\n'+usage)
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
        
        mes = self.bot.channel_instances[ctx.channel.id].get_table().penalty(pID, pen)
        await self.send_messages(ctx, mes)
    
    @commands.command(aliases=['unpen'])
    async def unpenalty(self, ctx, *args):
        
        if await self.check_callable(ctx, "unpenalty"): return
        usage = f"Usage: `{ctx.prefix}unpen <player id> <unpen amount = current pen>`"
        
        if len(args)==0:
            await self.send_messages(ctx, self.bot.channel_instances[ctx.channel.id].get_table().get_pen_player_list(), '\n'+usage)
            return
        
        pID = args[0].lower()
        
        if not pID.isnumeric():
            await self.send_temp_messages(ctx, "The player id needs to be a number.", usage)
            return
        unpen = None
        if len(args)>1:
            unpen = args[1].lower()
        mes = self.bot.channel_instances[ctx.channel.id].get_table().unpenalty(pID, unpen)
        await self.send_messages(ctx, mes)
                                
    @commands.command(aliases=['tpen', 'teampen'])
    async def teampenalty(self, ctx, *args):
        
        if await self.check_callable(ctx, "teampenalty"): return
        if Utils.isFFA(self.bot.channel_instances[ctx.channel.id].get_table().format):
            await self.send_temp_messages(ctx, "You cannot use team penalty commands in FFAs.")
            return
        usage = f"Usage: `{ctx.prefix}teampen <team> <penalty>`"
        
        if len(args)==0:
            await self.send_messages(ctx, self.bot.channel_instances[ctx.channel.id].get_table().get_pen_player_list(team_command=True), '\n'+usage)
            return
        team = args[0]
        
        if len(args)<2:
            await self.send_temp_messages(ctx, "Missing <pen amount>.",usage)
            return
        pen = args[1].lower()
        if not pen.lstrip('=').lstrip('-').isnumeric():
            await self.send_temp_messages(ctx, "The penalty amount must be a number (negative allowed).", usage)
            return
        
        mes = self.bot.channel_instances[ctx.channel.id].get_table().team_penalty(team, pen)
        await self.send_messages(ctx, mes)
        
    @commands.command(aliases=['teamunpen', 'tunpen'])
    async def teamunpenalty(self, ctx, *args):
        
        if await self.check_callable(ctx, "teamunpenalty"): return
        if Utils.isFFA(self.bot.channel_instances[ctx.channel.id].get_table().format):
            await self.send_temp_messages(ctx, "You cannot use team penalty commands in FFAs.")
            return
        
        usage = f"Usage: `{ctx.prefix}teamunpen <team> <unpen amount = current pen>`"
        
        if len(args)==0:
            await self.send_messages(ctx, self.bot.channel_instances[ctx.channel.id].get_table().get_pen_player_list(team_command=True), '\n'+usage)
            return
        
        team = args[0]
        
        unpen = None
        if len(args)>1:
            unpen = args[1].lower()
        mes = self.bot.channel_instances[ctx.channel.id].get_table().team_unpenalty(team, unpen)
        await self.send_messages(ctx, mes)
            
        
    @commands.command(aliases=['mr', 'merge'])
    async def mergeroom(self, ctx, *, arg):
        
        if await self.check_callable(ctx, "mergeroom"): return
        
        usage = f'Usage: `{ctx.prefix}mergeroom <rxx or mii name(s) in room>`'
        arg = arg.strip()
        search_args = arg.split(",")
        search_args = [i.strip() for i in search_args]

        table_races = 4*self.bot.channel_instances[ctx.channel.id].get_table().gps
        if len(self.bot.channel_instances[ctx.channel.id].get_table().races)>=table_races:
            return await ctx.send(f"You cannot merge rooms because all races have finished ({table_races} races). If you would like to add more races, use `{ctx.prefix}gps`.")
        
        del_mes = await ctx.send("Merging rooms...")
        error, mes = await self.bot.channel_instances[ctx.channel.id].get_table().merge_room(search_args)
        await del_mes.delete()
        if error:
            await self.send_temp_messages(ctx, mes, '\n'+usage)
            return
        await self.send_messages(ctx, mes)
        
    @mergeroom.error
    async def mergeroom_error(self, ctx, error):
        self.set_instance(ctx)
        if await self.check_callable(ctx, "mergeroom"): return
        if isinstance(error, commands.MissingRequiredArgument):
            await self.send_temp_messages(ctx, f'Usage: `{ctx.prefix}mergeroom <rxx or mii name(s) in room>`')
    
    @commands.command(aliases=['remove'])
    async def removerace(self, ctx, raceNum = -1):
        if await self.check_callable(ctx, "removerace"): return
        usage = f"Usage: `{ctx.prefix}removerace <race number>`"

        if not raceNum.isnumeric():
            await self.send_temp_messages(ctx, "The <race number> must be a number.", usage)
            return
        
        await ctx.send("**Note:** *This command should be used with caution as it is unstable and could cause unintended consequences on the table.\nIdeally, this command should be used immediately after the table picture updates with the race that needs to be removed.*")
        mes = await self.bot.channel_instances[ctx.channel.id].get_table().remove_race(int(raceNum))
        await self.send_messages(ctx, mes)
    
    @commands.command(aliases=['gps'])
    async def changegps(self, ctx, *args):
        
        if await self.check_callable(ctx, "changegps"): return
        usage = f"Usage: `{ctx.prefix}changegps <num gps>`"
        if len(args)==0: 
            await self.send_temp_messages(ctx, usage)
            return
        try:
            gps = int(args[0])
            if args[0][0] == '+' or args[0][0] == '-':
                gps = self.bot.channel_instances[ctx.channel.id].get_table().gps+gps 
            assert(0<gps<13)
        except (ValueError, AssertionError):
            return await self.send_temp_messages(ctx, "<num gps> must be an integer from 1-12.", usage)
        
        self.bot.channel_instances[ctx.channel.id].get_table().change_gps(gps)
        self.bot.channel_instances[ctx.channel.id].restart_auto_update()
        await self.send_messages(ctx, "Changed total gps to `{}`.".format(self.bot.channel_instances[ctx.channel.id].get_table().gps))
        
        
    @commands.command(aliases=['cp', 'changepos','changeplace', 'changeposition', 
        'changeplacement', 'quickedit', 'editrace', 'qe', 'er', 'editplace', 'editpos', 'ep', 'pe'])
    async def editplacement(self,ctx, *, arg):
        if await self.check_callable(ctx, "editplacement"): return
        
        usage = f"Usage: `{ctx.prefix}editplacement <race number> <player id> <corrected placement>`"
        arg = [i.strip() for i in arg.strip().split("/")]
        arg  = [i.split(" ") for i in arg]
        if len(arg)==0:
            await self.send_temp_messages(ctx, self.bot.channel_instances[ctx.channel.id].get_table().get_player_list(), '\n',usage)
            return
        for i in arg:
            if len(i)<1:
                await self.send_temp_messages(ctx, "Missing <race number> for command.", self.bot.channel_instances[ctx.channel.id].get_table().get_player_list(), '\n',usage)
                return
            if len(i)<2:
                await self.send_temp_messages(ctx, f"Error processing command: missing players for command on race `{i[0]}`.", self.bot.channel_instances[ctx.channel.id].get_table().get_player_list(), usage)
                return
            if len(i)<3:
                await self.send_temp_messages(ctx, f"Error: missing <corrected placement> for race `{i[0]}`, player `{i[1]}`.", self.bot.channel_instances[ctx.channel.id].get_table().get_player_list(), usage)
            
            for t in i:
                if not t.isnumeric():
                    await self.send_temp_messages(ctx, f"Argument `{t}` for must be a real number.", self.bot.channel_instances[ctx.channel.id].get_table().get_player_list(), usage)
                    return
                
        mes = self.bot.channel_instances[ctx.channel.id].get_table().edit_race(arg)
        await self.send_messages(ctx, mes)
        
    @editplacement.error
    async def editplacement_error(self, ctx, error):
        self.set_instance(ctx)
        
        if await self.check_callable(ctx, 'editplacement'): return
        
        if isinstance(error, commands.MissingRequiredArgument):
            await self.send_messages(ctx, self.bot.channel_instances[ctx.channel.id].get_table().get_player_list(),f"\nUsage: `{ctx.prefix}editplacement <race number> <player id> <corrected placement>`")
    
    @commands.command(aliases=['crs', 'roomsize'])
    async def changeroomsize(self, ctx, *, arg): 
        
        if await self.check_callable(ctx, "changeroomsize"): return
        
        usage = f"Usage: `{ctx.prefix}changeroomsize <race number> <corrected room size>`"
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
                await self.send_temp_messages(ctx, "Error processing command: missing <corrected room size> for race `{}`.".format(i[0]), usage)
                return
        mes = self.bot.channel_instances[ctx.channel.id].get_table().change_room_size(arg)
        await self.send_messages(ctx, mes)

        
    @changeroomsize.error
    async def changeroomsize_error(self, ctx, error):
        self.set_instance(ctx)
        if await self.check_callable(ctx, "changeroomsize"): return
        
        if isinstance(error, commands.MissingRequiredArgument):
            await self.send_messages(ctx, f"Usage: `{ctx.prefix}changeroomsize <race number> <corrected room size>`")
    
    @commands.command(aliases=['tt', 'text', 'str', 'ts', 'tablestring', 'tablestr'])
    async def tabletext(self, ctx):
        
        if await self.check_callable(ctx, "tabletext"): return
        await self.send_messages(ctx, self.bot.channel_instances[ctx.channel.id].get_table().get_table_text())
    

def setup(bot):
    bot.add_cog(Table_cog(bot))
