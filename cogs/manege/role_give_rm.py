import discord
from discord.ext import commands
from discord.ext.commands import Greedy
from typing import Union, List

class RoleAddRmCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

#<------Commands------>
        
    @commands.hybrid_group(name="role")
    async def role(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send("サブコマンドが無効です...")

    @role.command(name="add")
    @commands.has_permissions(manage_roles=True)
    async def role_add(self, ctx, member: discord.Member, role: discord.Role):
        """ロールを追加します。"""
        await member.add_roles(role)
        await ctx.send(f"{member.mention} に {role.mention} を追加しました。")
        
    @role.command(name="rm")
    @commands.has_permissions(manage_roles=True)
    async def role_remove(self, ctx, member: discord.Member, role: discord.Role):
        """ロールを削除します。"""
        await member.remove_roles(role)
        await ctx.send(f"{member.mention} から {role.mention} を削除しました。")

    @role.command(name="multiple")
    @commands.has_permissions(manage_roles=True)
    async def role_multiple(self, ctx, members: Greedy[discord.Member], roles: Greedy[discord.Role]):
        """複数のロールを追加します。"""
        if not members:
            await ctx.send("メンバーが指定されていません。")
            return
        if not roles:
            await ctx.send("ロールが指定されていません。")
            return
        for member in members:
            for role in roles:
                await member.add_roles(role)
            await ctx.send(f"{member.mention} に {', '.join([role.mention for role in roles])} を追加しました。")

async def setup(bot):
    await bot.add_cog(RoleAddRmCog(bot))
