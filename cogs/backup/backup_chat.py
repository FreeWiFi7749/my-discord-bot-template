import discord
from discord.ext import commands
import json
import os

class BackupChats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def backup_channel_messages(self, channel):
        if isinstance(channel, discord.TextChannel) or isinstance(channel, discord.Thread):
            messages = await channel.history(limit=3).flatten()
            messages_data = []
            for message in messages:
                message_data = {
                    'author_name': message.author.name,
                    'author_id': message.author.id,
                    'content': message.content,
                    'timestamp': message.created_at.isoformat()
                }
                messages_data.append(message_data)
            
            category_name = 'NoCategory' if not channel.category else channel.category.name
            os.makedirs(f'data/backup/{channel.guild.id}/chats/{category_name}', exist_ok=True)
            with open(f'data/backup/{channel.guild.id}/chats/{category_name}/{channel.name}.json', 'w', encoding='utf-8') as f:
                json.dump(messages_data, f, ensure_ascii=False, indent=4)

async def setup(bot):
    await bot.add_cog(BackupChats(bot))
