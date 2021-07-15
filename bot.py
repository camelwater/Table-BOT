# -*- coding: utf-8 -*-
"""
Created on Wed Jun  2 11:51:05 2021

@author: ryanz
"""
import discord
from discord.ext import tasks, commands
import os
from dotenv import load_dotenv
import json
import atexit
import logging
from logging.handlers import RotatingFileHandler
import traceback as tb
from itertools import cycle
from datetime import datetime, timedelta

load_dotenv()
KEY = os.getenv('KEY')
LOG_LOC = 'logs/logs.txt'
#SERVER_ID = 775253594848886785

INIT_EXT = ['cogs.Stats', 'cogs.Settings', 'cogs.Table']

handlers = [ RotatingFileHandler(filename=LOG_LOC, 
            mode='w', 
            maxBytes=512000, 
            backupCount=4)
           ]
logging.basicConfig(handlers = handlers,
                            format='%(asctime)s %(levelname)s -> %(message)s\n',
                            level=logging.ERROR)
log = logging.getLogger(__name__)

def load_settings():
    with open('resources/settings.json') as d:
        load = json.load(d)
        if load:
            return load
        else:
            return {}

def load_prefixes():
    with open('resources/prefixes.json') as p:
        load = json.load(p)
        if load: 
            return load
        return {}

def callable_prefix(bot, msg, mention=True):
    base = []
    default = ['?', '!', '$']
    if msg.guild is None:
        base = default
    else:
        base.extend(bot.prefixes.get(str(msg.guild.id), default))
    if mention:
        return commands.when_mentioned_or(*base)(bot, msg)
    return base


class TableBOT(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix = callable_prefix, case_insensitive=True, intents = discord.Intents.all(), help_command = None)      
        self.prefixes = load_prefixes()
        self.settings = load_settings()
        self.table_instances = {}
        self.presences = cycle(['?help', '{} tables'])
        self.BOT_ID = 844640178630426646

        for l in INIT_EXT:
            self.load_extension(l)  

    #TODO: catch invalid form errors (too long fields)        
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            if not ctx.guild:
                await(await ctx.send("I don't recognize that command. Use `?help` for a list of available commands.")).delete(delay=25)
            pass
        elif isinstance(error, commands.NoPrivateMessage):
            await(await ctx.send("This command cannot be used in DMs.")).delete(delay=7)
        elif isinstance(error, commands.MissingPermissions):
            await(await ctx.send("Sorry {}, you don't have permission to use this command.".format(ctx.author.mention))).delete(delay=10.0)
        elif isinstance(error, commands.CommandOnCooldown):
            await(await ctx.send("This command can only be used once every {:.0f} seconds. You can retry in {:.1f} seconds.".format(error.cooldown.per, error.retry_after))).delete(delay=7)
        elif isinstance(error, commands.MaxConcurrencyReached):
            await(await ctx.send("This command can only be used by {} user at a time. Try again later.".format(error.number))).delete(delay=7)
        elif isinstance(error, commands.MissingRequiredArgument):
            pass
            #raise error
        else:
            await ctx.send("An unidentified internal bot error occurred. Wait a bit and try again later.\nIf this issue persists, `?reset` the table.")
            error_tb = ''.join(tb.format_exception(type(error), error, error.__traceback__))
            error_tb = error_tb[:error_tb.find('\nThe above exception was the direct cause of the following exception:')]
            log.error(msg=f"in command: {ctx.command}\n{error_tb}")
            raise error

    async def on_ready(self):
        print("Bot logged in as {0.user}".format(self)) 
        try:
            self.cycle_presences.start()
        except RuntimeError:
            pass
        try:
            self.check_inactivity.start()
        except RuntimeError:
            pass
        # try:
        #     self.routine_stats_dump.start()
        # except RuntimeError:
        #     pass
    
    # async def on_message(self, message: discord.Message):
    #     if message.author == self or message.author.bot: return
    #     #if not self.user.mentioned_in(message): return
    #     if message.content.rstrip() in [f'<@!{self.user.id}>', f'<@{self.user.id}>']:
    #         await self.send_help(await self.get_context(message))
    #         if hasattr(self, "command_stats"):
    #             self.command_stats['help']+=1
    #     await self.process_commands(message)
    
    #remove inactive table instances (inactivity == 30+ minutes)
    @tasks.loop(minutes = 15)
    async def check_inactivity(self):
        self.table_instances = {channel: instance for (channel, instance) in self.table_instances.items() if 
                                instance.last_command_sent is None or datetime.now() - instance.last_command_sent <= timedelta(minutes=30)}

    @tasks.loop(seconds=15)
    async def cycle_presences(self):
        next_pres = next(self.presences)
        if "tables" in next_pres:
            active_tables= self.get_active_tables()
            next_pres = next_pres.format(active_tables)
            if active_tables==1: next_pres = next_pres.replace("tables", "table")
        pres = discord.Activity(type=discord.ActivityType.watching, name=next_pres)
        await self.change_presence(status=discord.Status.online, activity=pres)
    
    def get_active_tables(self):
        count = 0
        for t in list(self.table_instances.values()):
            if t.table_running:
                count+=1
        return count

    def get_guild_prefixes(self, guild, local_callable = callable_prefix):
        temp_msg = discord.Object(id=0)
        temp_msg.guild = guild

        return local_callable(self, temp_msg, mention=False)
    
    def add_prefix(self, guild, prefix):
        guild = str(guild)
        if len(self.prefixes.get(guild, [])) >=3:
            return "You cannot have more than 3 custom prefixes."

        if prefix in [f'<@!{self.BOT_ID}>', f'<@{self.BOT_ID}>']:
            return "The bot mention is a default prefix and cannot be added as a custom prefix."

        if prefix in self.prefixes.get(guild, []):
            return f"`{prefix}` is already registered as a prefix."
        
        prefixes = self.prefixes.get(guild, [])
        prefixes.append(prefix)
        self.prefixes[guild] = prefixes
        self.update_prefix_json()
        
        return f"`{prefix}` has been registered as a prefix."
    
    def remove_prefix(self, guild, prefix):
        guild = str(guild)

        if prefix in [f'<@!{self.BOT_ID}>', f'<@{self.BOT_ID}>']:
            return "The bot mention is a default prefix and cannot be removed."

        try:
            self.prefixes[guild].remove(prefix)
            self.update_prefix_json()

            return f"Prefix `{prefix}` has been removed." + ' Use the bot mention as a prefix.' if len(self.prefixes[guild])==0 else ""
        except KeyError:
            return "You don't have any custom prefixes registered."
        except:
            return f"`{prefix}` is not a registered prefix."
        
    def set_prefix(self, guild, prefix):
        guild = str(guild)
        if not prefix:
            self.prefixes[guild] = []
            self.update_prefix_json()
            return "All custom prefixes have been removed. Use the bot mention as a prefix."
        
        if prefix in [f'<@!{self.BOT_ID}>', f'<@{self.BOT_ID}>']:
            return "The bot mention is a default prefix and cannot be set as a custom prefix."
        
        self.prefixes[guild] = [prefix]
        self.update_prefix_json()

        return f"`{prefix}` has been set as the prefix."
    
    def reset_prefix(self, guild):
        guild = str(guild)
        self.prefixes.pop(guild)
        self.update_prefix_json()

        return "Custom prefixes have been reset to default."

    def get_guild_settings(self, guild):
        guild = str(guild)
        default = {'style': None, 'graph': None}
      
        if self.settings.get(guild) is None:
            self.settings[guild] = default
            self.update_settings_json()
            return default
        return self.settings.get(guild, default)
    
    def reset_settings(self, guild):
        guild = str(guild)
        self.settings.pop(guild)
        self.update_settings_json()

        return "Server settings have been reset to defaults."
    
    def set_setting(self, guild, setting, default):
        guild = str(guild)
        if not default:
            try:
                self.settings.get(guild, {}).pop(setting)
            except:
                pass
            self.update_settings_json()
            return f"`{setting}` setting restored to default."
        
        try:
            self.settings[guild][setting] = default
        except:
            self.settings[guild] = {}
            self.settings[guild][setting] = default
        
        self.update_settings_json()
        return "`{}` setting set as `{}`.".format(setting, default.get('type') if setting in ['graph', 'style'] else default)
    
    def get_setting(self, type, guild, raw = False):
        guild = str(guild)
        default = {'style': None, 'graph': None}
        if type in ['graph', 'style']:
            if raw:
                return self.settings.get(guild, default).get(type)
            return self.settings.get(guild, default).get(type).get('type')
        else:
            pass
            #for other settings to be added in the future

    def update_prefix_json(self):
        with open("resources/prefixes.json", 'w') as p:
            json.dump(self.prefixes, p, ensure_ascii=True, indent=4)
    
    def update_settings_json(self):
        with open("resources/settings.json", 'w') as s:
            json.dump(self.settings, s, ensure_ascii=True, indent=4)
    
    @tasks.loop(hours=1)
    async def routine_stats_dump(self):
        self.dump_stats_json()

    def dump_stats_json(self):
        if not hasattr(self, "command_stats") or len(self.command_stats) == 0: return
        print("\nDumping command stats...")
        with open('resources/stats.json', 'w') as sjson:
            json.dump(dict(self.command_stats), sjson, ensure_ascii=True, indent=4)

    async def close(self):
        await super().close()

    def run(self):
        super().run(KEY, reconnect=True)

if __name__ == "__main__":
    bot = TableBOT()
    bot.run()

    @atexit.register
    def on_exit():
        bot.dump_stats_json()
