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

if __name__ == "__main__":
    load_dotenv()
    KEY = os.getenv('KEY')
    SERVER_ID = 775253594848886785
    bot = commands.Bot(command_prefix = ('?'), case_insensitive=True, intents = discord.Intents.all(), help_command = None)
    
    load_extensions = ['cogs.table_cog']
    for l in load_extensions:
        bot.load_extension(l)
    bot.run(KEY)