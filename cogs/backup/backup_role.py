import discord
from discord.ext import commands
import json
import os

class BackupRoles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def backup_server_roles(self, guild):
        roles_data = []
        for role in guild.roles:
            if role.is_default():
                continue
            role_data = {
                'id': role.id,
                'name': role.name,
                'permissions': role.permissions.value,
                'position': role.position,
                'color': role.color.value,
                'hoist': role.hoist,
                'mentionable': role.mentionable
            }
            roles_data.append(role_data)
        
        os.makedirs(f'data/backup/{guild.id}/roles/server', exist_ok=True)
        with open(f'data/backup/{guild.id}/roles/server/roles.json', 'w', encoding='utf-8') as f:
            json.dump(roles_data, f, ensure_ascii=False, indent=4)

    async def backup_user_roles(self, guild):
        for member in guild.members:
            roles = [role.id for role in member.roles if not role.is_default()]
            user_data = {
                'roles': roles
            }
            os.makedirs(f'data/backup/{guild.id}/roles/user', exist_ok=True)
            with open(f'data/backup/{guild.id}/roles/user/{member.id}.json', 'w', encoding='utf-8') as f:
                json.dump(user_data, f, ensure_ascii=False, indent=4)

async def setup(bot):
    await bot.add_cog(BackupRoles(bot))