import classes.tabler as tabler
from discord.ext import tasks, commands
import datetime
import discord
import utils.Utils as Utils
import bot

class Channel:
    '''
    class representing a discord channel on which a table instance is running

    sort of acts like a bridge between Table_cog and Table instances because it deals with automatic updates, 
    
    which use both Table instance methods and discord Contexts
    '''

    def __init__(self, bot: bot.TableBOT, ctx: commands.Context, table: tabler.Table):
        self.ctx = ctx
        self.bot = bot
        self.table = table
        
        self.last_command_sent = None
        self.choose_message = ""
        self.searching_room = False
        self.confirm_room = False
        self.confirm_reset = False
        self.reset_args = None
        self.table_running = False
        self.picture_running = False
        self.prefix = ctx.prefix

        self.table.channel = self

    def get_table(self) -> tabler.Table:
        return self.table
    def get_ctx(self) -> commands.Context:
        return self.ctx
    
    def restart_auto_update(self, auto_send=False):
        '''
        tries to restart the table's auto-update if it should be started again
        '''
        # if len(self.table.races)<4*self.table.gps and not self.mkwx_update.is_running():
        try:
            self.mkwx_update.restart()
        except RuntimeError:
            pass
        # elif auto_send and not self.mkwx_update.is_running():
        #     self.auto_send_pic()
    

    @tasks.loop(seconds=5)
    async def mkwx_update(self): 
        if len(self.table.races)>=self.table.gps*4 or (self.table.last_race_update is not None and datetime.datetime.now()-self.table.last_race_update>datetime.timedelta(minutes=25)):
            self.mkwx_update.stop()

        # cur_iter = self.mkwx_update.current_loop
        # print(cur_iter)
        if not await self.table.room_is_updated(): return

        await self.auto_send_pic()


    async def auto_send_pic(self):
        self.bot.command_stats['picture_generated']+=1
        self.picture_running = True
        self.last_command_sent = datetime.datetime.now()
        detect_mes = await self.ctx.send("Detected race finish.")
        wait_mes = await self.ctx.send("Updating scores...")
        mes = await self.table.update_table(auto=True)
        await wait_mes.edit(content=mes)
        pic_mes = await self.ctx.send("Fetching table picture...")
        img = await self.table.get_table_img()
        if isinstance(img, str): #error while fetching picture
            await pic_mes.delete()
            await detect_mes.delete()
            self.picture_running=False
            return await self.ctx.send(img)
        
        f=discord.File(fp=img, filename='table.png')
        em = discord.Embed(title=self.table.title_str(), 
                        description="\n[Edit this table on gb.hlorenzi.com]("+self.table.table_link+")")
        
        em.set_image(url='attachment://table.png')
        is_overflow, error_footer, full_footer= self.table.get_warnings()
        em.set_footer(text = error_footer)
        
        self.picture_running=False 
        await self.ctx.send(embed=em, file=f)
        await pic_mes.delete()
        await detect_mes.delete()

        if is_overflow: #send file of errors
            path = "./error_footers/"
            filename = f'warnings_and_errors-{self.ctx.channel.id}.txt'
            e_file = Utils.create_temp_file(filename, full_footer, dir=path)
            Utils.delete_file(path+filename)
            
            await self.ctx.send(file = discord.File(fp=e_file, filename=filename))
    

