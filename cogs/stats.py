import discord
from discord.ext import tasks, commands
from collections import Counter

class stats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def on_command(self, ctx):
        command = ctx.command.qualified_name
        self.bot.command_stats[command] +=1

    @commands.command(aliases=['commandstats'])
    async def stats(self, ctx):
        counter = self.bot.command_stats
        total = sum(counter.values())
        pic_total = counter['picture']

        common = counter.most_common(5)

        out = "Total commands processed: {}\nPictures generated: {}".format(total, pic_total)
        out += '\n'.join("{}: {}".format(k, c) for k,c in common)
         
        await ctx.send("```\n{}\n```".format(out))
    
    @commands.command(aliases=['info'])
    async def about(self, ctx):
        e = discord.Embed(title='Table BOT')

        e.add_field(name='Written in:', value='python')
        e.add_field(name='Lines of code:', value='3750')
        e.add_field(name="Libraries used:", value='discord.py, collections, urllib, aiohttp, and others')

        value_field = "[Github Repository](https://github.com/camelwater/Table-BOT)"
        e.add_field(name='\u200b', value= value_field, inline=False)

def setup(bot):
    if not hasattr(bot, "command_stats"):
        bot.command_stats = Counter()