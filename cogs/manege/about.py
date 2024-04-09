import discord
from discord.ext import commands
import platform
import psutil
import datetime
import subprocess
import os
from dotenv import load_dotenv

load_dotenv()
bot_owner_id = int(os.getenv('BOT_OWNER_ID'))
ba_channel_id = int(os.getenv('BOT_ANNOUNCEMENT_CHANNEL_ID'))

def create_usage_bar(usage, length=20):
    """使用率に基づいて視覚的なバーを生成する"""
    filled_length = int(length * usage // 100)
    bar = '█' * filled_length + '─' * (length - filled_length)
    return f"[{bar}] {usage}%"

def get_cpu_model_name():
    """CPUモデル名を取得する"""
    try:
        result = subprocess.run(["lscpu"], capture_output=True, text=True, check=True)
        if result.stdout:
            for line in result.stdout.split('\n'):
                if "Model name" in line:
                    return line.split(':')[1].strip()
    except subprocess.CalledProcessError:
        return "取得に失敗しました"

def get_service_uptime(service_name: str):
    try:
        result = subprocess.run(["sudo", "systemctl", "show", "-p", "ActiveEnterTimestamp", service_name], capture_output=True, text=True, check=True)
        output = result.stdout.strip()

        utc_zone = datetime.timezone.utc
        jst_zone = datetime.timezone(datetime.timedelta(hours=9))

        start_time_str = output.split("=")[-1].strip()
        start_time_utc = datetime.datetime.strptime(start_time_str, "%a %Y-%m-%d %H:%M:%S %Z")

        start_time_jst = start_time_utc.replace(tzinfo=utc_zone).astimezone(jst_zone)
        now_jst = datetime.datetime.now(jst_zone)
        uptime = now_jst - start_time_jst

        return str(uptime).split('.')[0]
    except Exception:
        return "現在は開発者モードで起動しています。"
    
class BotInfoCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command()
    async def about(self, ctx):
        """BOTの情報を表示します"""

        os_info = f"{platform.system()} {platform.release()} ({platform.version()})"
        cpu_info = get_cpu_model_name()
        cpu_cores = f"論理コア: {psutil.cpu_count(logical=True)}, 物理コア: {psutil.cpu_count(logical=False)}"
        uptime = get_service_uptime("nijiiro_yume.service")

        memory = psutil.virtual_memory()
        memory_usage = memory.percent
        cpu_usage = psutil.cpu_percent()

        host = subprocess.run(["hostname"], capture_output=True, text=True, check=True).stdout.strip()

        host_ping = subprocess.run(["ping", "-c", "1", host], capture_output=True, text=True, check=True)
        ping1 = host_ping.stdout.splitlines()[-1].split()
        ping2 = float(ping1[3].split("/")[2]) * 1000
        pong = int(ping2)

        total_memory_gb = round(memory.total / (1024 ** 3), 2)

        cpu_bar = create_usage_bar(cpu_usage)
        memory_bar = create_usage_bar(memory_usage)

        embed = discord.Embed(title="BOT情報", description="バグ発見時: </bug_report:1226307114943774786>\nまたは<@707320830387814531>にDM",color=0x00ff00)
        embed.add_field(name="ーーーーーーーー", value="", inline=False)

        shard_id = ctx.guild.shard_id if ctx.guild is not None else 'N/A'
        total_shards = self.bot.shard_count if hasattr(self.bot, 'shard_count') else 'N/A'

        embed.add_field(name="シャードID", value=f"{shard_id}/{total_shards}", inline=True)
        embed.add_field(name="ーーーーーーーー", value="", inline=False)

        embed.add_field(name="BOT", value=f"開発元: <@{bot_owner_id}>", inline=True)
        embed.add_field(name="ホスト", value="momiji VPS", inline=True)
        embed.add_field(name="ホストPING", value=f"{pong}ms", inline=True)
        embed.add_field(name="OS", value=os_info, inline=False)
        embed.add_field(name="CPU", value=cpu_info, inline=False)
        embed.add_field(name="CPU コア", value=cpu_cores, inline=False)
        embed.add_field(name="稼働時間", value=uptime, inline=False)
        embed.add_field(name="CPU 使用率", value=cpu_bar, inline=False)
        embed.add_field(name="メモリ使用率", value=f"{memory_bar} / {total_memory_gb}GB", inline=False)

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(BotInfoCog(bot))