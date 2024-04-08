import discord
from discord.ext import commands
from discord.ui import View
import json
import os
import uuid
from datetime import timedelta

class AntiSpamActionSelectMenu(discord.ui.Select):
    def __init__(self, cog, guild_id, message_list_path):
        self.cog = cog
        self.guild_id = guild_id
        self.message_list_path = message_list_path
        options = [
            discord.SelectOption(label="警戒", description="メッセージを削除し、ユーザーをタイムアウトします", emoji="🚨", value="alert"),
            discord.SelectOption(label="安全", description="スパムとマークされたメッセージを無視します", emoji="✅", value="safe")
        ]
        super().__init__(placeholder="選択してください...", min_values=1, max_values=1, options=options, custom_id="select_action")

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "alert":
            await self.cog.handle_alert(interaction, self.message_list_path)
        elif self.values[0] == "safe":
            await self.cog.handle_safe(interaction, self.message_list_path)

        embed = discord.Embed(title="対応が完了しました", description=f"{interaction.user.mention}によって{self.values}が実行されました", color=discord.Color.green())
        if self.values[0] == "alert":
            embed.description = "スパムと判断されたメッセージを削除し、送信者をタイムアウトしました"
        elif self.values[0] == "safe":
            embed.description = "スパムと判断されたメッセージを無視しました"

        embed.set_author(name=interaction.user, icon_url=interaction.user.avatar.url)
        embed.set_footer(text=f"ファイルID: {os.path.basename(self.message_list_path)}")
        await interaction.followup.send(embed=embed
        
        )

class AntiSpamView(View):
    def __init__(self, cog, guild_id, message_list_path):
        super().__init__()
        self.add_item(AntiSpamActionSelectMenu(cog, guild_id, message_list_path))

class AntiSpamCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.message_cache = {}

#<----Anti Spam---->
    async def check_spam(self, message):
        """メッセージ追跡とログチャンネルへの警告送信を行います。"""
        config = self.load_config(message.guild.id)
        if not config.get("antispam"):
            return
    
        key = (message.content, message.author.id)
        if key not in self.message_cache:
            self.message_cache[key] = {
                "count": 0,
                "messages": []
            }
    
        self.message_cache[key]["count"] += 1
        self.message_cache[key]["messages"].append(message.id)

        if self.message_cache[key]["count"] >= config.get("warning_count", 5):
            await self.send_warning(message.guild.id, message.content, self.message_cache[key]["messages"], key, message.channel)
            del self.message_cache[key]
        elif self.message_cache[key]["count"] >= config.get("deletion_count", 10):
            await self.handle_alert(None, self.save_message_list(message.guild.id, self.message_cache[key]["messages"], message.channel))
            del self.message_cache[key]

    async def send_warning(self, guild_id, message_content, message_ids, key, channel):
        """指定されたギルドのログチャンネルに警告メッセージを送信します。"""
        config = self.load_config(guild_id)
        log_channel_id = config.get("log_channel")
        warning_count = config.get("warning_count", 5)
        mention_role = str(config.get("mention_role"))
        if log_channel_id:
            log_channel = self.bot.get_channel(log_channel_id)
            if log_channel:
                message_list_path = await self.save_message_list(guild_id, message_ids, channel)
                embed = discord.Embed(title="スパム警告", description=f"スパムと思われるメッセージが{warning_count}回送信されました\nこのメッセージを確認したユーザーは以下のボタンから対応してください。\n\n\n   🚨警戒: スパムと思われるメッセージを全て消去し送信者を1時間タイムアウトします。\n   ✅安全: 送信されたメッセージを安全と判断し自動消去を無効化します。", color=discord.Color.orange())
                try:
                    first_message = await channel.fetch_message(message_ids[0])
                except discord.NotFound:
                    # メッセージが見つからない場合の処理
                    return
                embed.add_field(name="メッセージ内容", value=message_content, inline=True)
                embed.add_field(name="正規表現", value=f"{message_content}```", inline=True)
                embed.add_field(name="送信者", value=first_message.author.mention, inline=False)
                embed.add_field(name="最新のメッセージ", value=first_message.jump_url, inline=False)
                embed.set_footer(text=f"ファイルID: {os.path.basename(message_list_path)}")
                view = AntiSpamView(self, guild_id, message_list_path)
                if mention_role is not None:
                    mention = f"<@!{mention_role}>"
                    await log_channel.send(embed=embed, view=view, content=mention)
                else:
                    await log_channel.send(embed=embed, view=view)
    
    async def save_message_list(self, guild_id, message_ids, channel):
        """メッセージリストをファイルに保存します。"""
        message_data = []
        for message_id in message_ids:
            try:
                msg = await channel.fetch_message(message_id)
                message_data.append({"content": msg.content, "message_id": msg.id, "author_id": msg.author.id, "channel_id": msg.channel.id})
            except discord.NotFound:
                continue

        file_id = str(uuid.uuid4())
        path = f"data/antispam/{guild_id}/message_list/{file_id}.json"
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(message_data, f, indent=4)
        return path
#<----Select Menu Actions---->

    def load_message_list(self, message_list_path):
        """メッセージリストをファイルから読み込みます。"""
        with open(message_list_path, 'r', encoding='utf-8') as f:
            return json.load(f)
        
    #<----Select Menu Actions---->
    async def handle_alert(self, interaction: discord.Interaction, message_list_path):
        """スパムと判断されたメッセージを削除し、送信者をタイムアウトします。"""
        messages = self.load_message_list(message_list_path)
        if interaction:
            await interaction.response.defer(ephemeral=True)
        for message_data in messages:
            channel = self.bot.get_channel(int(message_data['channel_id']))
            message = await channel.fetch_message(message_data['message_id'])
            await message.delete()
            member = message.guild.get_member(message_data['author_id'])
            if member:
                await member.edit(communication_disabled_until=discord.utils.utcnow() + timedelta(hours=1), reason="スパム行為")
        if interaction:
            await interaction.followup.send("スパムと判断されたメッセージを削除し、送信者をタイムアウトしました。", ephemeral=True)
        else:
            if messages:  # メッセージリストが空でないことを確認
                guild_id = self.bot.get_channel(messages[0]['channel_id']).guild.id
                config = self.load_config(guild_id)  # config をロード
                log_channel = self.bot.get_channel(config.get("log_channel"))
                embed = discord.Embed(title="[自動消去]", description="スパムと判断されたメッセージを削除し、送信者をタイムアウトしました。", color=discord.Color.red())
                await log_channel.send(embed=embed)

    async def handle_safe(self, interaction, message_list_path):
        """スパムと判断されたメッセージを無視します。"""
        await interaction.response.defer(ephemeral=True)
        os.remove(message_list_path)
        await interaction.followup.send("スパムと判断されたメッセージを無視しました。", ephemeral=True)

#<----Config---->
    def get_config_path(self, guild_id):
        config_dir = f"data/antispam/{guild_id}/config"
        os.makedirs(config_dir, exist_ok=True)
        return os.path.join(config_dir, "antispam.json")

    def load_config(self, guild_id):
        config_path = self.get_config_path(guild_id)
        if not os.path.exists(config_path):
            return {"antispam": False, "log_channel": None, "warning_count": 5, "deletion_count": 10, "mention_role": None}
        with open(config_path, 'r') as f:
            return json.load(f)

    def save_config(self, guild_id, config):
        with open(self.get_config_path(guild_id), 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)

    async def _log_antispam(self, guild_id, message):
        config = self.load_config(guild_id)
        if not config.get("antispam", False):
            return

        log_channel_id = config.get("log_channel")
        if log_channel_id:
            log_channel = self.bot.get_channel(log_channel_id)
            if log_channel:
                await log_channel.send(message)

#<----Events---->
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        guild_id = message.guild.id
        config = self.load_config(guild_id)
        if not config.get("antispam", False):
            return

        await self.check_spam(message)

async def setup(bot):
    await bot.add_cog(AntiSpamCog(bot))