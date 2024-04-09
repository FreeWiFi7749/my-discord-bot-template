import discord
from discord.ext import commands
import json
import os

class BackupChannels(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def backup_channels(self, guild):
        channels_data = []
        for channel in guild.channels:
            if isinstance(channel, discord.TextChannel) or isinstance(channel, discord.VoiceChannel):
                channel_permissions = [{str(permission[0]): permission[1] for permission in channel.overwrites.items()}]
                channel_data = {
                    'name': channel.name,
                    'position': channel.position,
                    'permissions': channel_permissions,
                    'topic': channel.topic,
                    'parent_id': channel.parent_id
                }
                channels_data.append(channel_data)
                os.makedirs(f'data/backup/{guild.id}/channels/channels', exist_ok=True)
                with open(f'data/backup/{guild.id}/channels/channels/{channel.name}.json', 'w', encoding='utf-8') as f:
                    json.dump(channel_data, f, ensure_ascii=False, indent=4)

    async def backup_categories(self, guild):
        for category in guild.categories:
            category_data = {
                'name': category.name,
                'position': category.position,
                'permissions': [{str(permission[0]): permission[1] for permission in category.overwrites.items()}]
            }
            os.makedirs(f'data/backup/{guild.id}/channels/category', exist_ok=True)
            with open(f'data/backup/{guild.id}/channels/category/{category.name}.json', 'w', encoding='utf-8') as f:
                json.dump(category_data, f, ensure_ascii=False, indent=4)

async def setup(bot):
    await bot.add_cog(BackupChannels(bot))
