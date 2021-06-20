import discord
from discord.ext import tasks, commands
from collections import Counter
import json

#TODO: add pickle file and atexit thing (to store command usage)

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
    async def stats(self, ctx):
        counter = self.bot.command_stats
        
        pic_total = counter['picture_generated']
        counter = Counter({k:v for k,v in dict(counter).items() if "generated" not in k})
        
        total = sum(counter.values())
        common = counter.most_common(5)

        out = "Total commands processed: {}\nPictures generated: {}\n\n".format(total, pic_total)
        out+='Most used commands:\n'
        if len(common)==0:
            out+="Commands haven't been used yet."
        else:
            out += '\n'.join("{}: {}".format(k, c) for k,c in common)
         
        await ctx.send("```\n{}\n```".format(out))
    
    @commands.command(aliases=['info'])
    async def about(self, ctx):
        e = discord.Embed(title='Table BOT', description='\u200b')

        #e.add_field(name='\u200b', value= "\u200b", inline=False)
        e.add_field(name='Written in:', value='python', inline=False)
        e.add_field(name='Lines of code:', value='4050', inline=False)
        e.add_field(name="Libraries used:", value='discord.py, collections, urllib, aiohttp, and others', inline=False)

        link = "[Github Repository](https://github.com/camelwater/Table-BOT)"
        e.add_field(name='\u200b', value= link, inline=False)

        await ctx.send(embed=e)

def load_stats_json():
    with open('stats.json', 'r') as sjson:
        return json.load(sjson)

def setup(bot):
    if not hasattr(bot, "command_stats"):
        bot.command_stats = Counter()
    bot.add_cog(Stats(bot))