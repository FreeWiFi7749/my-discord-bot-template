import discord
import random
import asyncio

presences = [
    {"type": "Playing", "name": "/helpでコマンドを確認"},
    {"type": "Playing", "name": "Ver.1.0.0β"},
    {"type": "Watching", "name": "スパムから保護中"}

]

async def update_presence(bot):
    while not bot.is_closed():
        presence = random.choice(presences)
        activity_type = getattr(discord.ActivityType, presence["type"].lower(), discord.ActivityType.playing)
        await bot.change_presence(activity=discord.Activity(type=activity_type, name=presence["name"]))
        await asyncio.sleep(15)