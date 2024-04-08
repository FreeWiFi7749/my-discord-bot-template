from discord.ext import commands
import discord

class ShardStatusCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name='shard_info')
    @commands.is_owner()
    async def shard_info(self, ctx):
        """すべてのシャードの情報を表示します。"""

        for shard_id, shard in enumerate(self.bot.shards.values()):
            if shard is None:
                continue

            latency = shard.latency * 1000
            if shard.is_closed():
                connection_status = "lost"
            elif shard.is_ws_ratelimited():
                connection_status = "pending"
            else:
                connection_status = "complete"

            guilds_in_shard = [guild for guild in self.bot.guilds if guild.shard_id == shard_id]
            guild_count = len(guilds_in_shard)
            user_count = sum(len(guild.members) for guild in guilds_in_shard)

            embed = discord.Embed(title=f"シャードID {shard_id} の情報", color=0x00ff00)
            embed.add_field(name="PING", value=f"{latency:.2f} ms", inline=False)
            embed.add_field(name="接続状況", value=connection_status, inline=False)
            embed.add_field(name="管理しているギルド数", value=str(guild_count), inline=False)
            embed.add_field(name="推定ユーザー数", value=str(user_count), inline=True)

            await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(ShardStatusCog(bot))