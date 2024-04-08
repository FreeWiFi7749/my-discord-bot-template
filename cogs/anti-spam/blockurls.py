# <-----Imports----->
import discord
from discord.ext import commands
import aiohttp
import json
import os
from urllib.parse import urlparse
import re
import asyncio
from discord.ui import View, Button

# <-----Cog Definition----->
class URLBlock(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data_path = 'data/urlblock'
        if not os.path.exists(self.data_path):
            os.makedirs(self.data_path)

    # <-----Error Handling----->
    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.CommandError):
            await ctx.send(f'エラーが発生しました: {error}')

    # <-----Utility Methods----->
    def get_domain(self, url):
        return urlparse(url).netloc

    def load_blocklist(self, guild_id):
        file_path = os.path.join(self.data_path, str(guild_id), 'blocklist.json')
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as file:
                return json.load(file)
        return []

    def save_blocklist(self, guild_id, blocklist):
        os.makedirs(os.path.join(self.data_path, str(guild_id)), exist_ok=True)
        file_path = os.path.join(self.data_path, str(guild_id), 'blocklist.json')
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(blocklist, file, ensure_ascii=False)

    def load_settings(self, guild_id):
        settings_path = os.path.join(self.data_path, str(guild_id), 'settings.json')
        if os.path.exists(settings_path):
            with open(settings_path, 'r', encoding='utf-8') as file:
                return json.load(file)
        else:
            return {"timeout": True, "messageblock": True, "timeout_duration": 3600}

    def save_settings(self, guild_id, settings):
        os.makedirs(os.path.join(self.data_path, str(guild_id)), exist_ok=True)
        settings_path = os.path.join(self.data_path, str(guild_id), 'settings.json')
        with open(settings_path, 'w', encoding='utf-8') as file:
            json.dump(settings, file, ensure_ascii=False)

    # <-----Commands----->
    @commands.hybrid_group(name="urlblock")
    async def urlblock(self, ctx):
        """URLブロックのためのコマンド群です。"""
        if ctx.invoked_subcommand is None:
            await ctx.send('有効なサブコマンドを使用してください: set, rm, setup, setting')

    @urlblock.command()
    async def set(self, ctx, *, url):
        """指定されたURLをブロックリストに追加します。"""
        print(f"setコマンドが呼び出されました: URL={url}")  # 追加
        guild_id = ctx.guild.id
        domain = self.get_domain(url)
        print(f"取得したドメイン: {domain}")  # 追加
        if not domain:
            await ctx.send('有効なURLを指定してください。')
            return

        blocklist = self.load_blocklist(guild_id)
        print(f"現在のブロックリスト: {blocklist}")  # 追加
        if domain not in blocklist:
            blocklist.append(domain)
            print(f"ブロックリストに追加後: {blocklist}")  # 追加
            self.save_blocklist(guild_id, blocklist)
            await ctx.send(f'`{domain}`をブロックリストに追加しました。')
            await self.add_or_update_automod_rule(guild_id, blocklist, ctx)
            print("add_or_update_automod_ruleを呼び出しました")  # 追加
        else:
            await ctx.send('このドメインは既にブロックリストに含まれています。')

    @urlblock.command()
    async def rm(self, ctx, *, url):
        """ブロックリストから指定されたURLを削除します。"""
        guild_id = ctx.guild.id
        domain = self.get_domain(url)

        blocklist = self.load_blocklist(guild_id)
        if domain in blocklist:
            blocklist.remove(domain)
            self.save_blocklist(guild_id, blocklist)
            await ctx.send(f'`{domain}`をブロックリストから削除しました。')
            await self.add_or_update_automod_rule(guild_id, blocklist, ctx)
        else:
            await ctx.send('このドメインはブロックリストに含まれていません。')

    @urlblock.command()
    async def list(self, ctx):
        """ブロックリストを表示します。"""
        await ctx.defer()
        guild_id = ctx.guild.id
        headers = {
            "Authorization": f"Bot {self.bot.http.token}"
        }
        url = f"https://discord.com/api/v9/guilds/{guild_id}/auto-moderation/rules"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    rules = await response.json()
                    found = False
                    for rule in rules:
                        if rule["name"] == "Blocked URLs by Anti Spam System":
                            found = True
                            embed = discord.Embed(title="AutoModルール情報: Blocked URLs by Anti Spam System", color=0x00ff00)
                            embed.add_field(name="ルールID", value=rule["id"], inline=False)
                            embed.add_field(name="名前", value=rule["name"], inline=False)
                            embed.add_field(name="ブロック内容", value="```, ```".join(rule["trigger_metadata"]["regex_patterns"]), inline=False)
                            
                            action_descriptions = []
                            for action in rule["actions"]:
                                action_type = action["type"]
                                if action_type == 3:
                                    action_descriptions.append("タイムアウト")
                                elif action_type == 1:
                                    action_descriptions.append("メッセージブロック")   
                            
                            embed.add_field(name="アクション", value=", ".join(action_descriptions), inline=False)
                            await ctx.send(embed=embed)
                            break
                    if not found:
                        await ctx.send("「Blocked URLs by Anti Spam System」ルールが見つかりませんでした。`/urlblock set` コマンドでURLをブロックリストに追加して、ルールを作成してください。")
                else:
                    await ctx.send("AutoModルールの取得に失敗しました。")
    # <-----Utility Methods----->
    def dict_list_to_sorted_json_string(self, dict_list):
        return json.dumps(sorted(dict_list, key=lambda x: json.dumps(x)), sort_keys=True)

    # <-----Automod Methods----->
    async def add_or_update_automod_rule(self, guild_id, blocklist, ctx):
        if not blocklist: 
            return

        settings = self.load_settings(guild_id)
        actions = []
        if settings.get("messageblock", True):
            actions.append({"type": 1, "metadata": {"context": "Blocked URLs by Anti Spam System"}})
        if settings.get("timeout", True):
            timeout_duration = settings.get("timeout_duration", 3600)
            actions.append({"type": 3, "metadata": {"duration": timeout_duration}})
        if settings.get("send_alert", False):
            actions.append({"type": 2, "metadata": {"channel_id": settings.get("log_channel")}})
            
        print(f"アクション: {actions}")
        regex_pattern = r"(?i)(" + "|".join(re.escape(domain) for domain in blocklist) + r")"
        headers = {
            "Authorization": f"Bot {self.bot.http.token}",
            "Content-Type": "application/json"
        }

        get_url = f"https://discord.com/api/v8/guilds/{guild_id}/auto-moderation/rules"
        print(f"既存のAutoModルールを取得中: {get_url}")

        async with aiohttp.ClientSession() as session:
            async with session.get(get_url, headers=headers) as response:
                print(f"取得したレスポンスのステータスコード: {response.status}")
                rules = await response.json()
                print(f"取得したルール: {rules}")
                print("ルールの更新を開始します。")
                for rule in rules:
                    print(f"ルール名: {rule['name']}")
                    if rule["name"] == "Blocked URLs by Anti Spam System":
                        print("既存のAutoModルールが見つかりました。")
                        try:
                            update_url = f"https://discord.com/api/v8/guilds/{guild_id}/auto-moderation/rules/{rule['id']}"
                            json_data = rule

                            current_actions = rule.get("actions", [])
                            if self.dict_list_to_sorted_json_string(current_actions) != self.dict_list_to_sorted_json_string(actions):
                                json_data["actions"] = actions

                            json_data["trigger_metadata"]["regex_patterns"] = [regex_pattern]
                            print(f"既存のルールを更新中: {update_url}")
                            async with session.patch(update_url, headers=headers, json=json_data) as update_response:
                                try:

                                    response_status = update_response.status
                                    response_text = await update_response.text()
                                    print(f"更新レスポンスのステータスコード: {response_status}")
                                    print(f"更新レスポンスのテキスト: {response_text}")
                                    if update_response.status == 200:
                                        print("Automodルールを更新しました。")
                                        return
                                    else:
                                        print("Automodルールの更新に失敗しました。")
                                        return
                                except Exception as e:
                                    print(f"エラーが発生しました: {e}")
                                    return
                        except Exception as e:
                            print(f"エラーが発生しました: {e}")
                            return
                    else:
                        print("既存のAutoModルールが見つかりませんでした。")
                        continue
                    

        print("新しいAutoModルールを作成中...")
        json_data = {
            "name": "Blocked URLs by Anti Spam System",
            "event_type": 1,
            "trigger_type": 1,
            "trigger_metadata": {
                "regex_patterns": [regex_pattern],
                "presets": []
            },
            "actions": actions,
            "enabled": True
        }
        post_url = f"https://discord.com/api/v8/guilds/{guild_id}/auto-moderation/rules"
        async with aiohttp.ClientSession() as session:
            async with session.post(post_url, headers=headers, json=json_data) as post_response:
                print(f"新しいルール作成のレスポンスステータスコード: {post_response.status}")
                if post_response.status == 200:
                    print("Automodルールを追加しました。")
                else:
                    error_message = await post_response.text()
                    print(f"Automodルールの追加または更新に失敗しました。ステータスコード: {post_response.status}, エラーメッセージ: {error_message}")

    async def delete_automod_rule(self, guild_id, rule_id):
        """特定のAutomodルールを削除します。"""
        url = f"https://discord.com/api/v8/guilds/{guild_id}/auto-moderation/rules/{rule_id}"
        headers = {
            "Authorization": f"Bot {self.bot.http.token}"
        }

        async with aiohttp.ClientSession() as session:
            async with session.delete(url, headers=headers) as response:
                if response.status == 200:
                    print("Automodルールを削除しました。")
                else:
                    print(f"Automodルールの削除に失敗しました。ステータスコード: {response.status}")
# <-----Cog Setup----->
async def setup(bot):
    await bot.add_cog(URLBlock(bot))
