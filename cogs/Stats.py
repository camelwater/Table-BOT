# -*- coding: utf-8 -*-
import discord
from discord.ext import commands
from collections import Counter
import json
import os
import fnmatch
from pathlib import Path

class Stats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        load = load_stats_json()
        if load:
            self.bot.command_stats = Counter(load)

    @commands.Cog.listener()
    async def on_command(self, ctx):
        command = ctx.command.qualified_name
        self.bot.command_stats[command] +=1

    @commands.Cog.listener()
    async def on_command_completion(self,ctx):
        command = ctx.command.qualified_name
        if command != 'picture':
            return
        command +='_generated'
        self.bot.command_stats[command]+=1

    @commands.command(aliases=['commandstats'])
    async def stats(self, ctx, num = None):
        counter = self.bot.command_stats
        if num is None:
            num = 5
        else:
            try:
                num = int(num)
            except:
                num = len(counter) if num.lower()=='all' else 5

        pic_total = counter['picture_generated']
        counter = Counter({k:v for k,v in dict(counter).items() if "generated" not in k})
        
        total = sum(counter.values())

        if num>len(counter):
            num = len(counter)
        common = counter.most_common(num)
        spaces = max([len(k[0]) for k in common])+1

        out = "Total commands processed: {}\nPictures generated: {}\n\n".format(total, pic_total)
        out+='{}:\n'.format('{} most used commands'.format(num) if num<len(counter) else "Command stats")
        if len(common)==0:
            out+="Commands haven't been used yet."
        else:
            out += '\n'.join("{}{}: {}".format(k, " "*(spaces-len(k)), c) for k,c in common)
         
        await ctx.send("```\n{}\n```".format(out))
    
    
    @commands.command(aliases=['info'])
    async def about(self, ctx):
        e = discord.Embed(title='Table BOT', description='')

        # e.add_field(name='Written in:', value='python', inline=False)
        # e.add_field(name='Lines of code:', value="~4675 (cba to figure out exact number)", inline=False)
        # e.add_field(name="Libraries used:", value='discord.py, collections, urllib, aiohttp, and others', inline=False)
        e.add_field(name='\u200b', value=f'_WRITTEN IN:_ python\n_LINES OF CODE:_ {get_LOC()}\n_LIBRARIES:_ discord.py, \
        collections, urllib, aiohttp, and others', inline=False)

        link = "[GitHub Repository](https://github.com/camelwater/Table-BOT)"
        e.add_field(name='\u200b', value= link, inline=False)

        await ctx.send(embed=e)

def get_LOC():
    LOC_count = 0
    for file in os.listdir('.') + os.listdir('./cogs'):
        if fnmatch.fnmatch(file, '*.py'):
            with open('./cogs/'+file if file in os.listdir('./cogs') else file, encoding='utf-8') as f:
                for _ in f:
                    LOC_count+=1

    return LOC_count

def load_stats_json():
    with open('resources/stats.json', 'r') as sjson:
        return json.load(sjson)

def setup(bot):
    if not hasattr(bot, "command_stats"):
        bot.command_stats = Counter()
    bot.add_cog(Stats(bot))
