# -*- coding: utf-8 -*-
import discord
from discord.ext import commands
from collections import Counter
import json
import os
from fnmatch import fnmatch

class Stats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        load = load_stats_json()
        if load:
            self.bot.command_stats = Counter(load)
    
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot or message.author.bot: return
        if not self.bot.user.mentioned_in(message): return
        if message.content.rstrip() in [f'<@!{self.bot.user.id}>', f'<@{self.bot.user.id}>']:
            await self._help(await self.bot.get_context(message))
            if hasattr(self.bot, "command_stats"):
                self.bot.command_stats['help']+=1

    @commands.Cog.listener()
    async def on_command(self, ctx: commands.Context):
        command = ctx.command.qualified_name
        self.bot.command_stats[command] +=1

    @commands.Cog.listener()
    async def on_command_completion(self,ctx):
        command = ctx.command.qualified_name
        if command != 'picture':
            return
        command +='_generated'
        self.bot.command_stats[command]+=1

    @commands.command(aliases=['commandstats', 'cstats'])
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
        counter = Counter({k:v for k,v in dict(counter).items() if k!="picture_generated" and k!="yes" and k!="no"})
        
        total = sum(counter.values())

        if num>len(counter):
            num = len(counter)
        common = counter.most_common(num)
        spaces = max([len(k[0]) for k in common])+1

        out = "[ Totals ]"
        out += "\nTotal_Commands_Processed = {}\nPictures_Generated = {}\n\n".format(total, pic_total)
        out+='[ {} ]\n'.format('{} Most Used Commands'.format(num) if num<len(counter) else "Command Stats")
        if len(common)==0:
            out+="Commands haven't been used yet."
        else:
            out += '\n'.join("{}{}= {}".format(k.replace(" ","_"), " "*(spaces-len(k)), c) for k,c in common)
         
        await ctx.send("```ini\n{}\n```".format(out))
    
    
    @commands.command(aliases=['info'])
    async def about(self, ctx):
        e = discord.Embed(title='Table BOT', description='')

        e.add_field(name='\u200b', value=f'_WRITTEN IN:_ python with discord.py v1.7.3\n\
                                    _LINES OF CODE:_ {count_LOC()}\n_SERVER:_ AWS - Amazon Linux 2 AMI', inline=False)

        link = "[GitHub Repository](https://github.com/camelwater/Table-BOT)"
        e.add_field(name='\u200b', value= link, inline=False)

        await ctx.send(embed=e)
    
    @commands.command(name='help',aliases = ['h'])
    async def _help(self, ctx: commands.Context):
        link1 = "[Basics](https://github.com/camelwater/Table-BOT/blob/main/README.md)"
        link2 = "[Documentation](https://github.com/camelwater/Table-BOT/wiki)"
        e = discord.Embed(title="Help", description=link1+'\n'+link2)
        # e.add_field(name='\u200b', value= link1 +'\n'+link, inline=False)

        await ctx.send(embed=e)

def count_LOC():
    LOC_count = 0
    for dir in ['.', './cogs', './utils', './classes']:
        for file in os.listdir(dir):   
            if fnmatch(file, '*.py'):
                with open(f"{dir}/{file}", encoding='utf-8') as f:
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
