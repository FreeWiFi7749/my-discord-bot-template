from discord.ext import commands
from datetime import datetime
import pytz

class DiscordTimestampCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name='timestamp')
    @commands.has_permissions(administrator=True)
    async def generate_timestamp(self, ctx, *, time: str):
        """指定した時間のタイムスタンプを生成します。"""
        try:
            dt = datetime.strptime(time, "%Y-%m-%d %H:%M")
            dt = dt.replace(tzinfo=pytz.timezone('Asia/Tokyo'))
            unix_time = int(dt.timestamp())
        except ValueError:
            await ctx.reply("時間の形式が正しくありません。YYYY-MM-DD HH:MMの形式で指定してください。")
            return

        formats = ['R', 'F', 'd', 'D', 't', 'T']
        message = ""
        for fmt in formats:
            timestamp = f"<t:{unix_time}:{fmt}> "
            message += timestamp + "\n"

        await ctx.send(message)

async def setup(bot):
    await bot.add_cog(DiscordTimestampCog(bot))