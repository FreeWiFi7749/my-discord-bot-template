import discord
from discord.ext import commands
import random

class ErrorTestCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name='test_error')
    async def test_error(self, ctx):
        errors = [
            lambda: (_ for _ in ()).throw(Exception('Test error')),
            lambda: 1 / 0,
            lambda: {}['key'],
            lambda: int('string'),
        ]
        random.choice(errors)()

async def setup(bot):
    await bot.add_cog(ErrorTestCog(bot))