from discord.ext import commands
import json
import os
import discord

class LogSetupCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def toggle_logging(self, ctx, log_type: str, setting: bool, channel: discord.TextChannel = None):
        guild_id = ctx.guild.id
        setting_bool = setting
        config_dir = f"data/logs/{guild_id}/config"
        config_file_path = f"{config_dir}/{log_type}.json"
        
        if not os.path.exists(config_dir):
            os.makedirs(config_dir, exist_ok=True)
        
        if not os.path.exists(config_file_path):
            with open(config_file_path, 'w') as f:
                json.dump({}, f)

        with open(config_file_path, 'r+') as f:
            config = json.load(f)
            config["log_" + log_type] = setting_bool
            if channel:
                config["log_channel"] = channel.id
            else:
                config.pop("log_channel", None)
            f.seek(0)
            json.dump(config, f, indent=4)
            f.truncate()

        channel_info = f"in {channel.mention}" if channel else "in the current channel"
        status = 'オン' if setting_bool else 'オフ'
        await ctx.send(f"{log_type.replace('_', ' ')}のログは{status}になりました。ログは{channel_info}に送信されます。")

    @commands.hybrid_group(name="logs")
    async def logs_group(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send("ログの設定を行います。")

    @logs_group.command(name='role')
    async def logs_role(self, ctx, setting: bool, channel: discord.TextChannel=None):
        """ロールログの設定を行います。"""
        await self.toggle_logging(ctx, 'role', setting, channel=channel)

    @logs_group.command(name='message_edit')
    async def logs_message_edit(self, ctx, setting: bool, channel: discord.TextChannel=None):
        """メッセージログの設定を行います。"""
        await self.toggle_logging(ctx, 'message_edit', setting, channel=channel)

    @logs_group.command(name='message_delete')
    async def logs_message_delete(self, ctx, setting: bool, channel: discord.TextChannel=None):
        """メッセージ削除ログの設定を行います。"""
        await self.toggle_logging(ctx, 'message_delete', setting, channel=channel)

    @logs_group.command(name='join_remove')
    async def logs_join_remove(self, ctx, setting: bool, channel: discord.TextChannel=None):
        """参加・退出ログの設定を行います。"""
        await self.toggle_logging(ctx, 'join_remove', setting, channel=channel)

    @logs_group.command(name='voice')
    async def logs_voice(self, ctx, setting: bool, channel: discord.TextChannel=None):
        """ボイスチャンネルログの設定を行います。"""
        await self.toggle_logging(ctx, 'voice', setting, channel=channel)

    @logs_group.command(name='kick')
    async def logs_kick(self, ctx, setting: bool, channel: discord.TextChannel=None):
        """キックログの設定を行います。"""
        await self.toggle_logging(ctx, 'kick', setting, channel=channel)

    @logs_group.command(name='ban')
    async def logs_ban(self, ctx, setting: bool, channel: discord.TextChannel=None):
        """Banログの設定を行います。"""
        await self.toggle_logging(ctx, 'ban', setting, channel=channel)

    @logs_group.command(name='timeout')
    async def logs_timeout(self, ctx, setting: bool, channel: discord.TextChannel=None):
        """タイムアウトログの設定を行います。"""
        await self.toggle_logging(ctx, 'timeout', setting, channel=channel)

    @logs_group.command(name='nickname')
    async def logs_nickname(self, ctx, setting: bool, channel: discord.TextChannel=None):
        """ニックネームログの設定を行います。"""
        await self.toggle_logging(ctx, 'nickname', setting, channel=channel)

    @logs_group.command(name='channel')
    async def logs_channel(self, ctx, setting: bool, channel: discord.TextChannel=None):
        """チャンネルログの設定を行います。"""
        await self.toggle_logging(ctx, 'channellog', setting, channel=channel)
async def setup(bot):
    await bot.add_cog(LogSetupCog(bot))