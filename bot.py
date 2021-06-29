# -*- coding: utf-8 -*-
"""
Created on Wed Jun  2 11:51:05 2021

@author: ryanz
"""
import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import json
import atexit
import logging

#sys.path.append('C:\\Users\\ryanz\\Anaconda3\\Lib\\site-packages')

load_dotenv()
KEY = os.getenv('KEY')
#SERVER_ID = 775253594848886785

INIT_EXT = ['cogs.table_cog', 'cogs.Stats', 'cogs.Settings']

log = logging.getLogger(__name__) #TODO: implement logging, also change prefixes to server settings in general

def load_prefixes():
    with open('prefixes.json') as p:
        load = json.load(p)
        if load: 
            return load
        return {}

def callable_prefix(bot, msg, mention=True):
    base = []
    default = ['?', '^']
    if msg.guild is None:
        base.extend(default)
    else:
        base.extend(bot.prefixes.get(str(msg.guild.id), default))
    if mention:
        return commands.when_mentioned_or(*base)(bot, msg)
    else:
        return base


class TableBOT(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix = callable_prefix, case_insensitive=True, intents = discord.Intents.all(), help_command = None)      
        self.prefixes = load_prefixes()
        
        self.table_instances = {}
        self.BOT_ID = 844640178630426646
        for l in INIT_EXT:
            self.load_extension(l)  

    #TODO: catch invalid form errors (too long fields)        
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            #await ctx.send("I don't recognize command that command.\nType `?help` for a list of commands.")
            pass
        if isinstance(error, commands.MissingPermissions):
            #await(await ctx.send("Sorry, you don't have permission to use this command. You are missing the following permission(s):\n{}".format(','.join(map(lambda l: '`{}`'.format(l), error.missing_perms))))).delete(delay=10.0)
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
            #log.log()
            raise error

    async def on_ready(self):
        print("Bot logged in as {0.user}".format(self)) 

    def get_guild_prefixes(self, guild, local_inject = callable_prefix):
        fill_msg = discord.Object(id=1)
        fill_msg.guild = guild

        return local_inject(self, fill_msg, mention=False)
    
    def add_prefix(self, guild, prefix):
        guild = str(guild)
        if len(self.prefixes.get(guild, [])) >=3:
            return "You cannot have more than 3 custom prefixes."

        if prefix in ['<@!{}>'.format(self.BOT_ID), '<@{}>'.format(self.BOT_ID)]:
            return "The bot mention is a default prefix and cannot be added as a custom prefix."

        if prefix in self.prefixes.get(guild, []):
            return "`{}` is already registered as a prefix.".format(prefix)
        
        prefixes = self.prefixes.get(guild, [])
        prefixes.append(prefix)
        self.prefixes[guild] = prefixes
        self.write_prefix_json()
        
        return "`{}` has been registered as a prefix.".format(prefix)
    
    def remove_prefix(self, guild, prefix):
        guild = str(guild)

        if prefix in ['<@!{}>'.format(self.BOT_ID), '<@{}>'.format(self.BOT_ID)]:
            return "The bot mention is a default prefix and cannot be removed."

        try:
            self.prefixes[guild].remove(prefix)
            self.write_prefix_json()

            return "Prefix `{}` has been removed.".format(prefix)
        except KeyError:
            return "You don't have any custom prefixes registered."
        except:
            return "`{}` is not a registered prefix.".format(prefix)
        
    
    def set_prefix(self, guild, prefix):
        guild = str(guild)
        if not prefix:
            self.prefixes[guild] = []
            self.write_prefix_json()
            return "All custom prefixes have been removed. Use the bot mention as a prefix."
        
        if prefix in ['<@!{}>'.format(self.BOT_ID), '<@{}>'.format(self.BOT_ID)]:
            return "The bot mention is a default prefix and cannot be set as a custom prefix."
        
        self.prefixes[guild] = [prefix]
        self.write_prefix_json()

        return "`{}` has been set as the prefix.".format(prefix)
    
    def write_prefix_json(self):
        with open("prefixes.json", 'w') as p:
            json.dump(self.prefixes, p, ensure_ascii=True, indent=4)
    
    def dump_stats_json(self):
        if not hasattr(self, "command_stats"): return
        print("\nDumping command stats to stats.json...")
        with open('stats.json', 'w') as sjson:
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
        #bot.write_prefix_json()
