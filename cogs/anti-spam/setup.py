from discord.ext import commands
import json
import os
import discord

class AntiSpamSetupCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def toggle_antispam(self, ctx, setting: bool, channel: discord.TextChannel=None, warning_count: int=None, deletion_count: int=None, mention_role: discord.Role=None):
        guild_id = ctx.guild.id
        config_dir = f"data/antispam/{guild_id}/config"
        config_file_path = f"{config_dir}/antispam.json"
        
        if not os.path.exists(config_dir):
            os.makedirs(config_dir, exist_ok=True)
        
        if not os.path.exists(config_file_path):
            with open(config_file_path, 'w') as f:
                json.dump({}, f)

        with open(config_file_path, 'r+') as f:
            config = json.load(f)
            config["antispam"] = setting
            if channel:
                config["log_channel"] = channel.id
            if warning_count is not None:
                config["warning_count"] = warning_count
            if deletion_count is not None:
                config["deletion_count"] = deletion_count
            if mention_role:
                config["mention_role"] = mention_role.id

            f.seek(0)
            json.dump(config, f, indent=4)
            f.truncate()

        channel_info = f"{channel.mention}" if channel else "現在のチャンネル"
        status = 'オン' if setting else 'オフ'
        await ctx.send(f"アンチスパムは{status}になりました。ログは{channel_info}に送信されます。")

    @commands.hybrid_group(name="antispam")
    async def antispam_group(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send("アンチスパムの設定を行います。")

    @antispam_group.command(name='settings')
    async def antispam_settings(self, ctx, setting: bool, channel: discord.TextChannel=None, warning_count: int=None, deletion_count: int=None, mention_role: discord.Role=None):
        """アンチスパムの詳細設定を行います。"""
        await self.toggle_antispam(ctx, setting, channel=channel, warning_count=warning_count, deletion_count=deletion_count, mention_role=mention_role)

async def setup(bot):
    await bot.add_cog(AntiSpamSetupCog(bot))