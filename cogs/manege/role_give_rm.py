import discord
from discord.ext import commands
from typing import Union

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
    async def role_multiple(self, ctx, members: Union[discord.Member, List[discord.Member]], roles: List[discord.Role]):
        """複数のロールを追加します。"""
        if not isinstance(members, list):
            members = [members]
        for member in members:
            for role in roles:
                await member.add_roles(role)
            await ctx.send(f"{member.mention} に {', '.join([role.mention for role in roles])} を追加しました。")

async def setup(bot):
    await bot.add_cog(RoleAddRmCog(bot))
