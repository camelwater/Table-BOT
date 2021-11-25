# -*- coding: utf-8 -*-
"""
Created on Wed Jun  2 11:51:05 2021

@author: ryanz
"""
import discord
from discord.ext import tasks, commands
from dotenv import dotenv_values
import json
import atexit
import logging
from logging.handlers import RotatingFileHandler
import traceback as tb
from itertools import cycle
from datetime import datetime, timedelta
import sqlite3
import copy
import argparse
from fnmatch import fnmatch
import os
from utils.Utils import SETTINGS
import utils.Utils as Utils
import classes.Channel as Channel
from typing import Dict, List, Tuple, Any

creds = dotenv_values(".env.testing") or dotenv_values(".env") #.env.testing for local testing, .env for deployment
KEY = creds['KEY']
LOG_LOC = 'logs/logs.log'

INIT_EXT = ['cogs.Stats', 'cogs.Settings', 'cogs.Table']

handlers = [RotatingFileHandler(filename=LOG_LOC, 
            mode='w', 
            maxBytes=512000, 
            backupCount=4)
           ]
logging.basicConfig(handlers = handlers,
                    format='%(asctime)s %(levelname)s -> %(message)s\n',
                    level=logging.ERROR)
log = logging.getLogger(__name__)

conn = sqlite3.connect('resources/database.db')
cur = conn.cursor()
cur.execute('''CREATE TABLE IF NOT EXISTS servers (
                id integer PRIMARY KEY,
                prefixes text, 
                graph integer, 
                style integer, 
                IgnoreLargeTimes text)''')
# cur.execute('''IF COL_LENGTH ('servers.IgnoreLargeTimes') IS NULL
#                 BEGIN
#                 ALTER TABLE servers
#                     ADD IgnoreLargeTimes text NULL
#                 END''')

def load_json(file):
    with open(file+'.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def update_json(file, contents):
    with open(file+'.json', 'w', encoding='utf-8') as f:
        json.dump(contents, f, ensure_ascii=True, indent = 4)

def clean_up_temp_files():
    print("Deleting all temp files...")
    for dir in ['./error_footers']: #, './save_states'
        for file in os.listdir(dir):
            if fnmatch(file, '*.txt'): #or fnmatch(file, '*.pickle')
                Utils.delete_file(f"{dir}/{file}")

SPLIT_DELIM = '{d/D17¤85xu§ey¶}'
DEFAULT_PREFIXES = ['?', '!']

def fetch_prefixes_and_settings() -> Tuple[Dict, Dict]:
    cur.execute('SELECT * FROM servers')
    server_rows = cur.fetchall()
    server_pxs = {k[0]: k[1] for k in server_rows}
    server_sets = {int(k[0]): {"IgnoreLargeTimes": k[4] or "0","graph": SETTINGS["graph"].get(k[2]),"style": SETTINGS["style"].get(k[3])} for k in server_rows}
   
    return {int(k): (p.split(SPLIT_DELIM) if p else []) for k, p in server_pxs.items()}, server_sets

def callable_prefix(bot, msg: discord.Message, mention=True) -> List[str]:
    base = []
    default = DEFAULT_PREFIXES
    if msg.guild is None:
        base = default
    else:
        base.extend(bot.prefixes.get(msg.guild.id, default))
        # base.append('$')

    if mention:
        return commands.when_mentioned_or(*base)(bot, msg)
    return base


class TableBOT(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix = callable_prefix, case_insensitive=True, intents = discord.Intents.all(), help_command = None)      
        self.prefixes, self.settings = fetch_prefixes_and_settings()
        self.channel_instances: Dict[int, Channel.Channel] = {}
        self.presences = cycle(['?help', '{} tables'])
        self.BOT_ID = 844640178630426646

        for ext in INIT_EXT:
            self.load_extension(ext) 

             
    async def on_command_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.CommandNotFound):
            if not ctx.guild:
                await(await ctx.send(f"I don't recognize that command. Use `{ctx.prefix}help` for a list of available commands.")).delete(delay=25)
            pass
        elif isinstance(error, commands.NoPrivateMessage):
            await(await ctx.send("This command cannot be used in DMs.")).delete(delay=7)
        elif isinstance(error, commands.MissingPermissions):
            await(await ctx.send(f"Sorry {ctx.author.mention}, you don't have permission to use this command.")).delete(delay=10.0)
        elif isinstance(error, commands.CommandOnCooldown):
            await(await ctx.send(f"This command can only be used once every {error.cooldown.per:.0f} seconds. You can retry in {error.retry_after:.1f} seconds.")).delete(delay=7)
        elif isinstance(error, commands.MaxConcurrencyReached):
            await(await ctx.send(f"This command can only be used by {error.number} user at a time. Try again later.")).delete(delay=7)
        elif isinstance(error, commands.MissingRequiredArgument):
            pass
            #raise error
        elif isinstance(error, commands.errors.ExpectedClosingQuoteError):
            await(ctx.send("Bad command input: missing a closing `\"`.", delete_after=10))
        else:
            await ctx.send(f"An unidentified internal bot error occurred. Wait a bit and try again later.\nIf this issue persists, `{ctx.prefix}reset` the table.")
            error_tb = ''.join(tb.format_exception(type(error), error, error.__traceback__))
            error_tb = error_tb[:error_tb.find('\nThe above exception was the direct cause of the following exception:')]
            log.error(msg=f"in command: {ctx.command}\n{error_tb}")
            raise error

    async def on_ready(self):
        clean_up_temp_files()
        print(f"Bot logged in as {self.user}") 
        for server in self.guilds:
            cur.execute('''INSERT OR IGNORE INTO servers
                            VALUES (?, ?, ?, ?, ?)''', 
                            (server.id, SPLIT_DELIM.join(DEFAULT_PREFIXES), None, None, "0")) # id, prefixes, graph, style, IgnoreLargeTimes (all default values)
            conn.commit()

        self.prefixes, self.settings = fetch_prefixes_and_settings()
        try:
            self.cycle_presences.start()
        except RuntimeError:
            print("cycle_presences task failed to start.")
        try:
            self.check_inactivity.start()
        except RuntimeError:
            print("check_inactivity task failed to start.")
    
    async def on_guild_join(self, guild: discord.Guild):
        cur.execute('''INSERT OR IGNORE INTO servers
                        VALUES (?, ?, ?, ?, ?)''',
                        (guild.id, SPLIT_DELIM.join(DEFAULT_PREFIXES), None, None, "0")) #id, prefixes, graph, style, IgnoreLargeTimes
        conn.commit()
    
    #remove inactive table instances (inactivity == 30+ minutes)
    @tasks.loop(minutes = 15)
    async def check_inactivity(self):
        # for channel, instance in list(self.channel_instances.items())[::-1]:
        #     if instance.last_command_sent is not None and datetime.now() - instance.last_command_sent > timedelta(minutes=30):
        #         Utils.destroy_temp_files(channel)
        #         self.channel_instances.pop(channel)
        self.channel_instances = {channel: instance for (channel, instance) in self.channel_instances.items() 
                                if instance.last_command_sent is None or datetime.now() - instance.last_command_sent <= timedelta(minutes=30)}

    @tasks.loop(seconds=15)
    async def cycle_presences(self):
        next_pres = next(self.presences)
        if "tables" in next_pres:
            active_tables = self.count_active_channels()
            next_pres = next_pres.format(active_tables)
            if active_tables==1: next_pres = next_pres.replace("tables", "table")
        pres = discord.Activity(type=discord.ActivityType.watching, name=next_pres)
        await self.change_presence(status=discord.Status.online, activity=pres)
    
    # @tasks.loop(hours=1)
    # async def routine_stats_dump(self):
    #     self.dump_stats_json()    
    
    def count_active_channels(self):
        return sum([1 for chan in list(self.channel_instances.values()) if chan.table_running])

    def get_guild_prefixes(self, guild, local_callable = callable_prefix) -> List[str]:
        temp_msg = discord.Object(id=0)
        temp_msg.guild = guild

        return local_callable(self, temp_msg, mention=False)
    
    def add_prefix(self, guild, prefix):
        if len(self.prefixes.get(guild, [])) >=5:
            return "You cannot have more than 5 custom prefixes."
        if prefix in [f'<@!{self.BOT_ID}>', f'<@{self.BOT_ID}>']:
            return "My mention is a default prefix and cannot be added as a custom prefix."
        if prefix in self.prefixes.get(guild, []):
            return f"`{prefix}` is already registered as a prefix."
        
        prefixes = self.prefixes.get(guild, [])
        prefixes.append(prefix)
        self.prefixes[guild] = prefixes
        cur.execute('''UPDATE servers 
                        SET prefixes=? 
                        WHERE id=?''',
                    (SPLIT_DELIM.join(prefixes), guild))
        conn.commit()
        
        return f"`{prefix}` has been registered as a prefix."
    
    def remove_prefix(self, ctx_prefix, guild, prefix):
        if prefix in [f'<@!{self.BOT_ID}>', f'<@{self.BOT_ID}>']:
            return "My mention is a default prefix and cannot be removed."

        try:
            self.prefixes[guild].remove(prefix)
            cur.execute('''UPDATE servers 
                            SET prefixes=? 
                            WHERE id=?''',
                        (SPLIT_DELIM.join(self.prefixes[guild]) if len(self.prefixes[guild])>0 else None, guild))
            conn.commit()

            return f"Prefix `{prefix}` has been removed." + (f' You must use my mention, {self.user.mention}, as the prefix now.' if len(self.prefixes[guild])==0 else "")
        except KeyError:
            return f"You don't have any custom prefixes registered. You can add or set custom prefixes with `{ctx_prefix}prefix`."
        except ValueError:
            return f"`{prefix}` is not a registered prefix."
        
    def set_prefix(self, guild, prefix):
        if not prefix:
            self.prefixes[guild] = []
            cur.execute('''UPDATE servers 
                            SET prefixes=? 
                            WHERE id=?''',
                        (None, guild))
            conn.commit()
            return f"All prefixes have been removed. Use my mention, {self.user.mention}, as the prefix."
        
        if prefix in [f'<@!{self.BOT_ID}>', f'<@{self.BOT_ID}>']:
            return "The bot mention is a default prefix and cannot be set as a custom prefix."
        
        self.prefixes[guild] = [prefix]
        cur.execute('''UPDATE servers 
                        SET prefixes=? 
                        WHERE id=?''', 
                    (str(prefix), guild))
        conn.commit()

        return f"`{prefix}` has been set as the prefix."
    
    def reset_prefix(self, guild):
        self.prefixes[guild] = copy.copy(DEFAULT_PREFIXES)
        cur.execute('''UPDATE servers 
                        SET prefixes=? 
                        WHERE id=?''',
                    (SPLIT_DELIM.join(DEFAULT_PREFIXES), guild))
        conn.commit()

        return "Server prefixes have been reset to default."

    def get_guild_settings(self, guild) -> Dict[str, Any]:
        default = {'IgnoreLargeTimes': "0", 'graph': None, 'style': None}

        return self.settings.get(guild, default)
    
    def reset_settings(self, guild):
        default = {'IgnoreLargeTimes': "0", 'graph': None, 'style': None}
        self.settings[guild] = default

        cur.execute('''UPDATE servers 
                        SET IgnoreLargeTimes=?, style=?, graph=? 
                        WHERE id=?''',
                    (None, None, None, guild))
        conn.commit()

        return "Server settings have been reset to default values."
    
    def set_setting(self, guild, setting, default):
        default_sets = {'IgnoreLargeTimes': "0", 'graph': None, 'style': None}
        if not default:
            try:
                default = default_sets.get(setting)
                self.settings[guild][setting] = default
            except KeyError:
                pass

            cur.execute(f'''UPDATE servers 
                            SET {setting}=? 
                            WHERE id=?''',
                            (default, guild))
            conn.commit()

            return f"`{setting}` setting restored to default."

        key = default
        if setting in ['graph', 'style']:
            default = SETTINGS[setting][default]

        try:
            self.settings[guild][setting] = default
        except KeyError:
            self.settings[guild] = {}
            self.settings[guild][setting] = default
        
        cur.execute(f'''UPDATE servers 
                        SET {setting}=? 
                        WHERE id=?''',
                        (key, guild))
        conn.commit()
        # cur.execute('''SELECT * 
        #                 FROM servers''')
        # print(cur.fetchall())

        if setting in ['IgnoreLargeTimes']:
            return f"`{setting}` setting set to `{Utils.insert_formats(default)}`."
        return "`{}` setting set to `{}`.".format(setting, default.get('type') if setting in ['graph', 'style'] else SETTINGS[setting].get(default, default))
    
    def get_setting(self, type, guild, raw = False):
        default = {'IgnoreLargeTimes': "0", 'graph': None, 'style': None}
        if type in ['graph', 'style']:
            if raw:
                return self.settings.get(guild, default).get(type)
            return self.settings.get(guild, default).get(type).get('type')
        else:
            return self.settings.get(guild, default).get(type)

    def dump_stats_json(self):
        if not hasattr(self, "command_stats") or len(self.command_stats) == 0: return
        print("\nDumping command stats...")
        with open('resources/stats.json', 'w') as sjson:
            json.dump(dict(self.command_stats), sjson, ensure_ascii=True, indent=4)

    async def close(self):
        await super().close()

    def run(self):
        super().run(KEY, reconnect=True)

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('key', metavar='KEY', type=str, nargs='?')
    return parser.parse_args().key

if __name__ == "__main__":
    bot_key = parse_args()
    if bot_key: KEY = bot_key

    bot = TableBOT()
    bot.run()

    @atexit.register
    def on_exit():
        bot.dump_stats_json()
        clean_up_temp_files()
        conn.close()
    