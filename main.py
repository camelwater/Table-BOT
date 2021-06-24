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

#sys.path.append('C:\\Users\\ryanz\\Anaconda3\\Lib\\site-packages')

load_dotenv()
KEY = os.getenv('KEY')
#SERVER_ID = 775253594848886785
BOT_ID = 844640178630426646
INIT_EXT = ['cogs.table_cog', 'cogs.Stats']

class TableBOT(commands.Bot):
    def __init__(self):
        #TODO: add changeable prefixes by server
        self.prefixes = {}
        super().__init__(command_prefix = ('<@!{}> '.format(BOT_ID), '<@{}> '.format(BOT_ID),'?', '^'), case_insensitive=True, intents = discord.Intents.all(), help_command = None)      
        for l in INIT_EXT:
            self.load_extension(l)  
            
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            await ctx.send("{}.\nType `?help` for a list of commands.".format(error.__str__().replace("is not found", "doesn't exist")))
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send("This command can only be used once every {:.0f} seconds. You can retry in {:.1f} seconds.".format(error.cooldown.per, error.retry_after))
        elif isinstance(error, commands.MaxConcurrencyReached):
            await ctx.send("This command can only be used by {} user at a time. Try again later.".format(error.number))
        elif isinstance(error, commands.MissingRequiredArgument):
            pass
            #raise error
        else:
            await ctx.send("An unidentified internal bot error occurred. Wait a bit and try again later.\nIf this issue persists, `?reset` the table.")
            raise error

    async def on_ready(self):
        print("Bot logged in as {0.user}".format(self)) 

    async def close(self):
        await super().close()

    def run(self):
        super().run(KEY, reconnect=True) 
    
    def dump_stats_json(self):
        if not hasattr(self, "command_stats"): return
        print("\nDumping command stats to stats.json...")
        with open('stats.json', 'w') as sjson:
            json.dump(dict(self.command_stats), sjson, ensure_ascii=True, indent=4)

if __name__ == "__main__":
    bot = TableBOT()
    bot.run()

    @atexit.register
    def on_exit():
        bot.dump_stats_json()
