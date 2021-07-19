# -*- coding: utf-8 -*-
from discord.ext import commands
from Utils import SETTINGS

class Settings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=['getprefixes', 'pxs'])
    async def prefixes(self, ctx):
        prefixes = self.bot.get_guild_prefixes(ctx.guild)
        mes = "{} prefixes:\n".format(f'[{ctx.guild.name}]' if ctx.guild else '[DM]')
        if len(prefixes) == 0:
            mes+="No custom prefixes."
        for i, p in enumerate(prefixes):
            mes+=f"{i+1}. {p}\n"
        await ctx.send(f"```css\n{mes}```")

    @commands.group(invoke_without_command=True, aliases=['px'])
    @commands.has_guild_permissions(manage_guild=True)
    async def prefix(self, ctx):
        await ctx.send("```Usage:\n?prefix add <prefix>\n?prefix remove <prefix>\n?prefix set <prefix>\n?prefix reset```")
    
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
                guild_prefixes+=f"- `{p}`\n"
            await ctx.send(f"You need to specify a prefix to be removed:\n{guild_prefixes}")
            return
        
        mes = self.bot.remove_prefix(ctx.guild.id, prefix)
        await ctx.send(mes)
    
    @prefix.command(name='set')
    @commands.has_guild_permissions(manage_guild=True)
    async def _set(self, ctx, *, prefix: str = None):

        mes = self.bot.set_prefix(ctx.guild.id, prefix)
        await ctx.send(mes)
    
    @prefix.command(name='reset')
    @commands.has_guild_permissions(manage_guild=True)
    async def _reset(self, ctx):
        mes = self.bot.reset_prefix(ctx.guild.id)
        await ctx.send(mes)
    
    @commands.command(aliases=['sets'])
    @commands.guild_only()
    async def settings(self, ctx, mes=True):
        settings = self.bot.get_guild_settings(ctx.guild.id)
        spaces = max([len(k[0]) for k in settings.items()])+1
        out = f'css\n[ {ctx.guild.name} server settings ]'
        for name, set in settings.items():
            try:
                set = set['type']
            except:
                set = 'Not set'
            out+="\n.{}{}- {}".format(name, " "*(spaces-len(name)), set)
        
        if mes:
            await ctx.send("```{}```".format(out))
        else:
            return "```{}```".format(out)

    @commands.command(aliases=['setting'])
    @commands.has_guild_permissions(manage_guild=True)
    async def set(self, ctx, settingType: str = None, *,default: str=None):
        if settingType is None:
            await ctx.send("Usage: `?set <settingName> <setting>`\nSee `?settings` for a list of available settingNames.")
            return
        
        if settingType.lower() in ['reset', 'clear']:
            mes = self.bot.reset_settings(ctx.guild.id)
            return await ctx.send(mes)
        
        if not get_avail_settings(settingType):
            return await ctx.send("Invalid setting `{}`. Here is a list of customizable settings:\n{}".format(settingType, await self.settings(ctx, mes=False)))

        if default is None:
            avail_settings = get_avail_settings(settingType)
            if not avail_settings:
                await ctx.send("Invalid setting `{}`. Here is a list of customizable settings:\n{}".format(settingType, await self.settings(ctx, mes=False)))
            else:
                await(await ctx.send("Specify a setting value for `{}`. The value can be any of the following:\n{}".format(settingType, avail_settings))).delete(delay=45)
            return

        settingType = settingType.lower()
        default = default.lower()
        if settingType in ['style', 'graph']:
            valid = False
            if default.isnumeric():
                try:
                    default = SETTINGS.get(settingType)[int(default)]
                    valid=True
                except:
                    pass
            else:
                for i in list(SETTINGS.get(settingType).values()):
                    if default.lower() in map(lambda l: l.lower(), i.values()):
                        default = i
                        valid = True
                        break
            if not valid:
                await ctx.send(f"Invalid value `{default}` for setting `{settingType}`. The value must be one of the following:\n{get_avail_settings(settingType)}")
                return

        mes = self.bot.set_setting(ctx.guild.id, settingType, default)
        await ctx.send(mes)
    
def get_avail_settings(setting):
    setting = SETTINGS.get(setting)
    if setting is None:
        return None

    ret = ""
    for ind, dic in setting.items():
        ret+='`{}.` {}\n'.format(ind," | ".join(map(lambda orig: "`{}`".format(orig), dic.values())))
    
    return ret
    
def setup(bot):
    bot.add_cog(Settings(bot))  
        