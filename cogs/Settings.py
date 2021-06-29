import discord
from discord.ext import commands

class Settings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=['getprefixes', 'pxs'])
    async def prefixes(self, ctx):
        prefixes = self.bot.get_guild_prefixes(ctx.guild)
        mes = "Server prefixes:\n"
        if len(prefixes) == 0:
            mes+="No custom prefixes."
        for i, p in enumerate(prefixes):
            mes+="{}. {}\n".format(i+1, p)
        await ctx.send("```{}```".format(mes))

    @commands.group(invoke_without_command=True, aliases=['px'])
    @commands.has_guild_permissions(manage_guild=True)
    async def prefix(self, ctx):
        await ctx.send("```Usage:\n?prefix add <prefix>\n?prefix remove <prefix>\n?prefix set <prefix>```")
    
    @prefix.command(aliases=['+'])
    @commands.has_guild_permissions(manage_guild=True)
    async def add(self, ctx, *, prefix: str = None):
        if prefix is None:
            await ctx.send("You need to specify a prefix to be added.")
            return

        mes = self.bot.add_prefix(ctx.guild.id, prefix)
        
        await ctx.send(mes)
    
    @prefix.command(aliases=['-'])
    @commands.has_guild_permissions(manage_guild=True)
    async def remove(self, ctx, *, prefix: str = None):
        if prefix is None:
            guild_prefixes = ''
            for p in self.bot.get_guild_prefixes(ctx.guild):
                guild_prefixes+="- `{}`\n".format(p)
            await ctx.send("You need to specify a prefix to be removed:\n{}".format(guild_prefixes))
            return
        
        mes = self.bot.remove_prefix(ctx.guild.id, prefix)
        await ctx.send(mes)
    
    @prefix.command()
    @commands.has_guild_permissions(manage_guild=True)
    async def set(self, ctx, *, prefix: str = None):
        
        mes = self.bot.set_prefix(ctx.guild.id, prefix)
        await ctx.send(mes)
        
def setup(bot):
    bot.add_cog(Settings(bot))  
        