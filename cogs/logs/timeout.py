import discord
from discord.ext import commands
import os
import json
import datetime

class TimeoutLoggingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_config_path(self, guild_id):
        config_dir = f"data/logs/{guild_id}/config"
        os.makedirs(config_dir, exist_ok=True)
        return os.path.join(config_dir, "timeout.json")

    def load_config(self, guild_id):
        config_path = self.get_config_path(guild_id)
        if not os.path.exists(config_path):
            return {"log_timeout": True, "log_channel": None}
        with open(config_path, 'r') as f:
            return json.load(f)

    def save_config(self, guild_id, config):
        with open(self.get_config_path(guild_id), 'w') as f:
            json.dump(config, f, indent=4)

    async def _log_role_change(self, guild_id, embed):
        config = self.load_config(guild_id)
        if not config.get("log_timeout", True):
            print("Role logging is disabled.")
            return

        log_channel_id = config.get("log_channel")
        if log_channel_id:
            log_channel = self.bot.get_channel(log_channel_id)
            if log_channel:
                await log_channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.timed_out_until != after.timed_out_until:
            guild_id = before.guild.id
            config = self.load_config(guild_id)
            if not config.get("log_timeout"):
                return

            log_channel_id = config.get("log_channel")
            if not log_channel_id:
                return

            log_channel = self.bot.get_channel(log_channel_id)
            if not log_channel:
                return

            if after.timed_out_until is None:
                
                timeout_time = after.timed_out_until.timestamp()
                timeout_time_stamp = "<t:{}>:<t:{}>".format(int(timeout_time), int(timeout_time))

                embed = discord.Embed(title=f"{after.display_name} がタイムアウトしました", color=discord.Color.red())
                embed.set_thumbnail(url=after.avatar.url)
                embed.set_author(name=after.display_name, icon_url=after.avatar.url)
                embed.add_field(name="タイムアウト期限", value=after.timeout_time_stamp, inline=False)
                embed.set_footer(text=before.guild.name, icon_url=before.guild.icon.url)

            if after.timed_out_until is not None:
                embed = discord.Embed(title=f"{after.display_name} のタイムアウトが解除されました", color=discord.Color.green())
                embed.set_thumbnail(url=after.avatar.url)
                embed.set_author(name=after.display_name, icon_url=after.avatar.url)
                embed.set_footer(text=before.guild.name, icon_url=before.guild.icon.url)

async def setup(bot):
    await bot.add_cog(TimeoutLoggingCog(bot))
