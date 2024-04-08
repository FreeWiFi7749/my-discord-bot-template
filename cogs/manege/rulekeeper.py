import discord
from discord.ext import commands
import os
import json

class RuleKeeperCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config_folder = "data/rulekeeper/"

#<------Event Handler------>
        
    @commands.Cog.listener()
    async def On_member_update(self, before, after):
        if before.roles != after.roles:
            guild_id = str(after.guild.id)
            user_id = str(after.id)
            self.save_user_roles(guild_id, user_id, [role.id for role in after.roles])

    @commands.Cog.listener()
    async def on_member_join(self, member):
        guild_id = str(member.guild.id)
        user_id = str(member.id)
        roles_to_add = self.load_user_roles(guild_id, user_id)
        for role_id in roles_to_add:
            role = discord.utils.get(member.guild.roles, id=int(role_id))
            if role is not None:
                await member.add_roles(role)

#<------Commands------>
                    
    @commands.hybrid_group(name="rulekeeper")
    async def rulekeeper(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send("サブコマンドが無効です...")

    @rulekeeper.command(name="settings")
    async def rolekeeper_settings(self, ctx, 設定: bool):
        """ロールキーパーの設定を変更します。"""
        guild_id = str(ctx.guild.id)
        self.set_guild_config(guild_id, "enabled", 設定)
        await ctx.send("ロールキーパーの設定を変更しました。")

    @rulekeeper.command(name="list")
    async def rolekeeper_list(self, ctx, user: discord.Member):
        """ユーザーのロールリストを表示します。(開発用コマンド)"""
        guild_id = str(ctx.guild.id)
        user_id = str(user.id)
        roles = self.load_user_roles(guild_id, user_id)
        role_names = [discord.utils.get(ctx.guild.roles, id=int(role_id)).name for role_id in roles]
        e = discord.Embed(title="ロールリスト", description=f"{user.mention} のロールリスト")
        e.add_field(name="ロール", value=", ".join(role_names))
        await ctx.send(embed=e)


#<------Config------>

    def save_user_roles(self, guild_id: int,  user_id: int , roles: list):
        file_path = f"{self.config_folder}/{guild_id}/user/{user_id}.json"
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {}

        data["roles"] = roles

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)


    def load_user_roles(self, guild_id: int, user_id: int):
        file_path = f"{self.config_folder}/{guild_id}/user/{user_id}.json"
        os.makedirs(os.path.dirname(file_path), exist_ok=True)  # ディレクトリを作成
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("roles", [])
        return []
    

    def set_guild_config(self, guild_id: int, key: str, value):
        file_path = f"{self.config_folder}/{guild_id}/config.json"
        os.makedirs(os.path.dirname(file_path), exist_ok=True)  # ディレクトリを作成
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {}

        data[key] = value

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
            
async def setup(bot):
    await bot.add_cog(RuleKeeperCog(bot))