import discord
from discord.ext import commands
import json
import os
from cogs.backup.backup_role import BackupRoles
from cogs.backup.backup_channel import BackupChannels
from cogs.backup.backup_chat import BackupChats
from discord.ext import tasks

class BackupAuto(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.backup_roles_instance = BackupRoles(bot)
        self.backup_channels_instance = BackupChannels(bot)
        self.backup_chats_instance = BackupChats(bot)
        self.backup_items = []
        self.backup_job = tasks.loop(minutes=2)(self.backup_task_wrapper)

    async def backup_task_wrapper(self):
        try:
            await self.backup_task()
        except discord.app_commands.AppCommandError as error:
            print(f"{error}")
        except Exception as e:
            raise e

    async def backup_task(self):
        print("バックアップ処理を開始します。")
        for guild in self.bot.guilds:
            backup_items = await self.load_backup_items(guild.id)
            if not backup_items:
                print(f"{guild.name} ({guild.id}) ではバックアップが無効です。")
                continue
            e = discord.Embed(title="", description="", color=0x7ec4ff)


            if 'ロール' in backup_items:
                await self.backup_roles_instance.backup_server_roles(guild)
                await self.backup_roles_instance.backup_user_roles(guild)
            if 'チャンネル' in backup_items:
                await self.backup_channels_instance.backup_channels(guild)
                await self.backup_channels_instance.backup_categories(guild)
            if 'チャット' in backup_items:
                for channel in guild.channels:
                    await self.backup_chats_instance.backup_channel_messages(channel)
                for thread in guild.threads:
                    await self.backup_chats_instance.backup_channel_messages(thread)

    async def load_backup_items(self, guild_id):
        try:
            with open(f'data/backup/{guild_id}/backup_items.json', 'r', encoding='utf-8') as f:
                items = json.load(f)
            return items
        except FileNotFoundError:
            os.makedirs(f'data/backup/{guild_id}', exist_ok=True)
            with open(f'data/backup/{guild_id}/backup_items.json', 'w', encoding='utf-8') as f:
                json.dump([], f)
            return []

    async def backup_items_setup(self, items):
        self.backup_items = items
        print("")

async def setup(bot):
    await bot.add_cog(BackupAuto(bot))
