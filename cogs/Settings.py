# -*- coding: utf-8 -*-
from discord.ext import commands
import bot
from utils.Utils import SETTINGS
import utils.Utils as Utils
RESERVED_DELIM = '{d/D17¤85xu§ey¶}'

class Settings(commands.Cog):
    def __init__(self, bot: bot.TableBOT):
        self.bot = bot

    @commands.command(aliases=['getprefixes', 'pxs'])
    async def prefixes(self, ctx: commands.Context):
        prefixes = self.bot.get_guild_prefixes(ctx.guild)
        mes = "{} prefixes:\n".format(f'[{ctx.guild.name}]' if ctx.guild else '[DM]')
        if len(prefixes) == 0:
            mes+="No prefixes."
        for i, p in enumerate(prefixes):
            mes+=f"{i+1}. {p}\n"
        await ctx.send(f"```css\n{mes}```")

    @commands.group(invoke_without_command=True, aliases=['px'],  case_insensitive=True)
    @commands.has_guild_permissions(manage_guild=True)
    async def prefix(self, ctx: commands.Context):
        px = ctx.prefix
        await ctx.send(f"```Usage:\n{px}prefix add <prefix>\n{px}prefix remove <prefix>\n{px}prefix set <prefix>\n{px}prefix reset```")
    
    @prefix.command(aliases=['+'])
    @commands.has_guild_permissions(manage_guild=True)
    async def add(self, ctx: commands.Context, *, prefix: str = None):
        if prefix is None:
            await ctx.send("You need to specify a prefix to be added.")
            return
        if RESERVED_DELIM in prefix:
            return await ctx.send("You cannot add this prefix because it contains forbidden characters.")
        mes = self.bot.add_prefix(ctx.guild.id, prefix)
        
        await ctx.send(mes)
    
    @prefix.command(aliases=['-'])
    @commands.has_guild_permissions(manage_guild=True)
    async def remove(self, ctx: commands.Context, *, prefix: str = None):
        if prefix is None:
            guild_prefixes = ''
            pfxs = self.bot.get_guild_prefixes(ctx.guild)
            if len(pfxs) == 0:
                return await ctx.send(f"You don't have any prefixes registered. You can add or set custom prefixes with `{ctx.prefix}prefix`.")
            for p in pfxs:
                guild_prefixes+=f"- `{p}`\n"
            await ctx.send(f"You need to specify a prefix to be removed:\n{guild_prefixes}")
            return
        
        mes = self.bot.remove_prefix(ctx.prefix, ctx.guild.id, prefix)
        await ctx.send(mes)
    
    @prefix.command(name='set')
    @commands.has_guild_permissions(manage_guild=True)
    async def _set(self, ctx: commands.Context, *, prefix: str = None):
        if RESERVED_DELIM in prefix:
            return await ctx.send("You cannot set this prefix because it contains forbidden characters.")

        mes = self.bot.set_prefix(ctx.guild.id, prefix)
        await ctx.send(mes)
    
    @prefix.command(name='reset')
    @commands.has_guild_permissions(manage_guild=True)
    async def _reset(self, ctx: commands.Context):
        mes = self.bot.reset_prefix(ctx.guild.id)
        await ctx.send(mes)
    
    @commands.command(aliases=['sets'])
    @commands.guild_only()
    async def settings(self, ctx: commands.Context, mes=True):
        settings = self.bot.get_guild_settings(ctx.guild.id)
        spaces = max([len(k[0]) for k in settings.items()])+1
        out = f'asciidoc\n== [{ctx.guild.name}] server settings =='
        for name, val in settings.items():
            if name in ['graph', 'style']:
                try:
                    val = val['type']
                except:
                    val = ''
            elif name == 'IgnoreLargeTimes':
                val = Utils.insert_formats(val)
            else:
                val = SETTINGS[name].get(val, val)
            out+="\n{}{}:: {}".format(name, " "*(spaces-len(name)), val)
        
        if mes:
            await ctx.send("```{}```".format(out))
        else:
            return "```{}```".format(out)

    @commands.command(aliases=['setting'])
    @commands.has_guild_permissions(manage_guild=True)
    async def set(self, ctx: commands.Context, settingType: str = None, *,default: str=None):
        if settingType is None:
            px = ctx.prefix
            await ctx.send(f"```asciidoc\n[Usage]\n{px}set <settingName> <value>\n{px}set reset <settingName>\nSee `{px}settings' for a list of customizable settings.\n```")
            return
        
        if settingType.lower() in ['reset', 'clear']:
            if default: #resetting specific setting (default becomes settingType)
                mes = self.bot.set_setting(ctx.guild.id, correct_settingName(default), None)
            else: #resetting all settings
                mes = self.bot.reset_settings(ctx.guild.id)
            return await ctx.send(mes)
        
        settingType = correct_settingName(settingType)
        avail_settings = get_avail_settings(settingType)
        
        if not avail_settings:
            return await ctx.send("Invalid setting `{}`. Here are the customizable settings:\n{}".format(settingType, await self.settings(ctx, mes=False)))

        if default is None:
            if not avail_settings:
                await ctx.send("Invalid setting `{}`. Here are the customizable settings:\n{}".format(settingType, await self.settings(ctx, mes=False)))
            else:
                await(await ctx.send(f"Specify a setting value for `{settingType}`. The value can be any of the following"
                                + f"{' or any combination of the following separated by commas' if settingType=='IgnoreLargeTimes' else ''}:\n{avail_settings}")).delete(delay=60)
            return

        valid = False
        if settingType in ['style', 'graph']:
            if default.isnumeric():
                default = int(default)
                if default in SETTINGS[settingType]: valid = True
            else:
                for k, v in SETTINGS[settingType].items():
                    if default.lower() in map(lambda l: l.lower(), v.values()):
                        default = k
                        valid = True
                        break
        else:
            #other settings (currently only IgnoreLargeTimes)
            if settingType == "IgnoreLargeTimes":
                if any([True if ('never' in entry and 'always' in entry) else False for entry in default.split(',')]):
                    valid = False
                else:
                    try:
                        default = Utils.parse_ILT_setting(default)
                        valid = True
                    except (ValueError, IndexError):
                        valid = False

        if not valid:
            await ctx.send(f"Invalid value `{default}` for setting `{settingType}`. The value must be"+
                        f"{' a combination of the following separated by commas' if settingType == 'IgnoreLargeTimes' else ''}:\n{get_avail_settings(settingType)}")
            return

        mes = self.bot.set_setting(ctx.guild.id, settingType, default)
        await ctx.send(mes)
    
def get_avail_settings(settingType):
    setting_vals = SETTINGS.get(settingType)
    if setting_vals is None:
        return None

    ret = ""
    for ind, dic in setting_vals.items():
        ret+='`{}.` {}\n'.format(ind, " | ".join(map(lambda orig: "`{}`".format(orig), dic.values())) if settingType in ['graph', 'style']
                                        else f'`{dic}`')
    
    return ret

def correct_settingName(setting: str):
    try:
        assert(setting in SETTINGS)
        return setting
    except AssertionError:
        try:
            lowered_keys = list(map(lambda l: l.lower(), SETTINGS.keys()))
            assert(setting.lower() in lowered_keys)
            return list(SETTINGS.keys())[lowered_keys.index(setting.lower())]
        except AssertionError:
            return setting
    
def setup(bot):
    bot.add_cog(Settings(bot))  
        