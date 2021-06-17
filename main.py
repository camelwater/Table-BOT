# -*- coding: utf-8 -*-
"""
Created on Wed Jun  2 11:51:05 2021

@author: ryanz
"""
import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import sys

sys.path.append('C:\\Users\\ryanz\\Anaconda3\\Lib\\site-packages')

load_dotenv()
KEY = os.getenv('KEY')
SERVER_ID = 775253594848886785
INIT_EXT = ['cogs.table_cog', 'cogs.Stats']
bot = commands.Bot(command_prefix = ('?', '^'), case_insensitive=True, intents = discord.Intents.all(), help_command = None)      

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("{}.\nType ?help for a list of commands.".format(error.__str__().replace("is not found", "doesn't exist")))
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send("This command can only be used once every {:.0f} seconds. You can retry in {:.1f} seconds.".format(error.cooldown.per, error.retry_after))
    elif isinstance(error, commands.MaxConcurrencyReached):
        await ctx.send("This command can only be used by {} user at a time. Try again later.".format(error.number))
    elif isinstance(error, commands.MissingRequiredArgument):
        raise error
    else:
        await ctx.send("There was an unidentified internal bot error. Wait a bit and try again later.\nIf the issue persists, ?reset the table.")
        raise error

@bot.event
async def on_ready():
    print("Bot logged in as {0.user}".format(bot))  


if __name__ == "__main__":
    for l in INIT_EXT:
        bot.load_extension(l)  
        
    bot.run(KEY, reconnect=True)

