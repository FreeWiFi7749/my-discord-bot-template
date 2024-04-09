from discord.ext import commands
import discord
import subprocess
import difflib
from pathlib import Path
import pathlib
from utils import startup
import asyncio
import re
class ManagementCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
                
    def _get_available_cogs(self):
        folder_name = 'cogs'
        cur = pathlib.Path('.')
        
        available_cogs = []
        for p in cur.glob(f"{folder_name}/**/*.py"):
            if p.stem == "__init__":
                continue
            module_path = p.relative_to(cur).with_suffix('').as_posix().replace('/', '.')
            if module_path.startswith('cogs.'):
                available_cogs.append(module_path)
        print(available_cogs)
        return available_cogs

    @commands.hybrid_command(name='reload', hidden=True)
    @commands.is_owner()
    async def reload_cog(self, ctx, *, cog: str):
        """指定したcogを再読み込みします"""
        matches = await asyncio.wait_for(self.find_closest_match_with_regex('cogs.' + cog if not cog.startswith('cogs.') else cog), timeout=3)
        if not matches:
            await ctx.reply(f"'{cog}' は読み込まれていません。")
            return

        if len(matches) > 1:
            suggestions = '\n'.join(matches)
            await ctx.reply(f"'{cog}' には複数のマッチが見つかりました。もしかして:\n{suggestions}")
            return

        closest_match = matches[0]
        await ctx.defer()
        try:
            await self.bot.reload_extension(closest_match)
            await self.bot.tree.sync()
            await ctx.reply(f"{closest_match}を再読み込みしました")
        except commands.ExtensionNotLoaded:
            await ctx.reply(f"'{closest_match}' は読み込まれていません。")
        except commands.ExtensionFailed as e:
            await ctx.reply(f"'{closest_match}' の再読み込み中にエラーが発生しました。\n{type(e).__name__}: {e}")

    async def find_closest_match_with_regex(self, user_input):
        available_cogs = self._get_available_cogs()
        pattern = re.compile(re.escape(user_input), re.IGNORECASE)
        matches = [cog for cog in available_cogs if pattern.search(cog)]
        return difflib.get_close_matches(user_input, available_cogs, n=5, cutoff=0.0)

    @commands.hybrid_command(name='list_cogs', with_app_command=True)
    @commands.is_owner()
    async def list_cogs(self, ctx):
        """現在ロードされているCogsをリスト表示します"""
        embed = discord.Embed(title="ロードされているCogs", color=discord.Color.blue())
        cog_names = [cog for cog in self.bot.cogs.keys()]
        if cog_names:
            embed.add_field(name="Cogs", value='\n'.join(cog_names), inline=False)
        else:
            embed.add_field(name="Cogs", value="ロードされているCogはありません。", inline=False)

        if hasattr(self.bot, 'failed_cogs') and self.bot.failed_cogs:
            failed_cogs_list = [f'{cog}: {error}' for cog, error in self.bot.failed_cogs.items()]
            e_failed_cogs = discord.Embed(title="正常に読み込めなかったCogファイル一覧", color=discord.Color.red())
            e_failed_cogs.add_field(name="Failed Cogs", value='\n'.join(failed_cogs_list), inline=False)
        else:
            e_failed_cogs = discord.Embed(title="正常に読み込めなかったCogファイル一覧", color=discord.Color.green())
            e_failed_cogs.add_field(name="Failed Cogs", value="なし", inline=False)

        await ctx.send(embed=embed)
        await ctx.send(embed=e_failed_cogs)

async def setup(bot):
    await bot.add_cog(ManagementCog(bot))
