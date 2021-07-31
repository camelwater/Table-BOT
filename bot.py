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
import sqlite3
from Utils import SETTINGS

load_dotenv()
KEY = os.getenv('KEY')
LOG_LOC = 'logs/logs.txt'

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

conn = sqlite3.connect('resources/database.db')
cur = conn.cursor()
cur.execute('''CREATE TABLE IF NOT EXISTS servers (
                id integer PRIMARY KEY,
                prefixes text, 
                graph integer, 
                style integer)''')

def load_json(file):
    with open(file+'.json', 'wr', encoding='utf-8') as f:
        return json.load(f)

def update_json(file, contents):
    with open(file+'.json', 'w', encoding='utf-8') as f:
        json.dump(contents, f, ensure_ascii=True, indent = 4)

SPLIT_CHAR = '¶'
DEFAULT_PREFIXES = ['?', '!']

def fetch_prefixes_and_settings():
    cur.execute('SELECT * FROM servers')
    server_rows = cur.fetchall()
    server_pxs = {k[0]: k[1] for k in server_rows}
    server_sets = {int(k[0]): {"graph": SETTINGS["graph"].get(k[2]),"style": SETTINGS["style"].get(k[3])} for k in server_rows}
   
    return {int(k): (p.split(SPLIT_CHAR) if p else []) for k, p in server_pxs.items()}, server_sets

def callable_prefix(bot, msg, mention=True):
    base = []
    default = DEFAULT_PREFIXES
    if msg.guild is None:
        base = default
    else:
        base.extend(bot.prefixes.get(msg.guild.id, default))

    if mention:
        return commands.when_mentioned_or(*base)(bot, msg)
    # return base, (True if msg.guild is None or bot.prefixes.get(msg.guild.id) is None else False)
    return base


class TableBOT(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix = callable_prefix, case_insensitive=True, intents = discord.Intents.all(), help_command = None)      
        self.prefixes, self.settings = {}, {}
        self.table_instances = {}
        self.presences = cycle(['?help', '{} tables'])
        self.BOT_ID = 844640178630426646

        for ext in INIT_EXT:
            self.load_extension(ext)  

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
        for server in self.guilds:
            cur.execute('''INSERT OR IGNORE INTO servers
                            VALUES (?, ?, ?, ?)''', 
                            (server.id, None, None, None))
            conn.commit()

        self.prefixes, self.settings = fetch_prefixes_and_settings()
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
    
    async def on_guild_join(self, guild):
        cur.execute('''INSERT OR IGNORE INTO servers
                        VALUES (?, ?, ?, ?)''',
                        (guild.id, None, None, None))
        conn.commit()
    
    #remove inactive table instances (inactivity == 30+ minutes)
    @tasks.loop(minutes = 15)
    async def check_inactivity(self):
        self.table_instances = {channel: instance for (channel, instance) in self.table_instances.items() 
                                if instance.last_command_sent is None or datetime.now() - instance.last_command_sent <= timedelta(minutes=30)}

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
                    (SPLIT_CHAR.join(prefixes), guild))
        conn.commit()
        
        return f"`{prefix}` has been registered as a prefix."
    
    def remove_prefix(self, guild, prefix):
        if prefix in [f'<@!{self.BOT_ID}>', f'<@{self.BOT_ID}>']:
            return "My mention is a default prefix and cannot be removed."

        try:
            self.prefixes[guild].remove(prefix)
            cur.execute('''UPDATE servers 
                            SET prefixes=? 
                            WHERE id=?''',
                        (SPLIT_CHAR.join(self.prefixes[guild]) if len(self.prefixes[guild])>0 else None, guild))
            conn.commit()

            return f"Prefix `{prefix}` has been removed." + (f' You must use my mention, {self.user.mention}, as the prefix now.' if len(self.prefixes[guild])==0 else "")
        except KeyError:
            return "You don't have any custom prefixes registered. You can add or set custom prefixes with `?prefix`."
        except:
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
        # if guild in self.prefixes:
        #     self.prefixes.pop(guild)
        self.prefixes[guild] = DEFAULT_PREFIXES
        cur.execute('''UPDATE servers 
                        SET prefixes=? 
                        WHERE id=?''',
                    (SPLIT_CHAR.join(DEFAULT_PREFIXES), guild))
        conn.commit()

        return "Server prefixes have been reset to default."

    def get_guild_settings(self, guild):
        default = {'style': None, 'graph': None}

        return self.settings.get(guild, default)
    
    def reset_settings(self, guild):
        default = {'style': None, 'graph': None}
        self.settings[guild] = default

        cur.execute('''UPDATE servers 
                        SET style=?, graph=? 
                        WHERE id=?''',
                    (None, None, guild))
        conn.commit()

        return "Server settings have been reset to defaults."
    
    def set_setting(self, guild, setting, default):
        if not default:
            try:
                self.settings[guild][setting] = None
            except:
                pass

            cur.execute(f'''UPDATE servers 
                            SET {setting}=? 
                            WHERE id=?''',
                        (None, guild))
            conn.commit()

            return f"`{setting}` setting restored to default."

        key = default
        if setting in ['graph', 'style']:
            default = SETTINGS[setting][default]

        try:
            self.settings[guild][setting] = default
        except:
            self.settings[guild] = {}
            self.settings[guild][setting] = default
        
        cur.execute(f'''UPDATE servers 
                        SET {setting}=? 
                        WHERE id=?''',
                    (key, guild))
        conn.commit()
        # cur.execute('''SELECT graph, style 
        #                 FROM servers''')
        # print(cur.fetchall())

        return "`{}` setting set as `{}`.".format(setting, default.get('type') if setting in ['graph', 'style'] else default)
    
    def get_setting(self, type, guild, raw = False):
        default = {'style': None, 'graph': None}
        if type in ['graph', 'style']:
            if raw:
                return self.settings.get(guild, default).get(type)
            return self.settings.get(guild, default).get(type).get('type')
        else:
            pass
            #for other settings to be added in the future
    
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
