import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import re
import pathlib
import uuid
from datetime import datetime
import logging
import asyncio
from utils import presence
from utils.logging import save_log
from utils.startup import startup_send_webhook, startup_send_botinfo
from discord.ui import View, Button, Modal, TextInput

load_dotenv()

class CustomHelpCommand(commands.DefaultHelpCommand):
    def command_not_found(self, string):
        return f"'{string}' というコマンドは見つかりませんでした。"

    def get_command_signature(self, command):
        return f'使い方: {self.context.clean_prefix}{command.qualified_name} {command.signature}'

    async def send_bot_help(self, mapping):
        for cog, commands in mapping.items():
            filtered = await self.filter_commands(commands, sort=True)
            command_signatures = [self.get_command_signature(c) for c in filtered]
            self.paginator.add_line(f'**{cog.qualified_name if cog else "その他のコマンド"}:**')
            for signature in command_signatures:
                self.paginator.add_line(signature)
        await self.get_destination().send("\n".join(self.paginator.pages))

session_id = None

class SessionIDHandler(logging.Handler):
    def emit(self, record):
        global session_id
        message = record.getMessage()
        match = re.search(r'Session ID: ([a-f0-9]+)', message)
        if match:
            session_id = match.group(1)
            print(f"セッションIDを検出しました: {session_id}")

logger = logging.getLogger('discord.gateway')
logger.setLevel(logging.INFO)
logger.addHandler(SessionIDHandler())

TOKEN = os.getenv('BOT_TOKEN')
command_prefix = ['anti:/', 'a／', 'a/', 'a!/', 'a!／', 'a!']
main_guild_id = int(os.getenv('MAIN_GUILD_ID'))
startup_channel_id = int(os.getenv('STARTUP_CHANNEL_ID'))
main_dev_channel_id = int(os.getenv('BUG_REPORT_CHANNLE_ID'))
main_dev_server_id = int(os.getenv('MAIN_GUILD_ID'))
bug_report_channel_id = int(os.getenv('BUG_REPORT_CHANNLE_ID'))

class BugReportModal(discord.ui.Modal, title="バグ報告"):
    reason = discord.ui.TextInput(
        label="バグの詳細",
        style=discord.TextStyle.paragraph,
        placeholder="ここにバグの詳細を記載してください...",
        required=True,
        max_length=1024
    )
    image = discord.ui.TextInput(
        label="参考画像",
        style=discord.TextStyle.paragraph,
        placeholder="[必須ではありません]画像のURLを貼り付けてください...",
        required=False,
        max_length=1024
    )

    def __init__(self, bot, error_id, channel_id, server_id, command_name, server_name):
        super().__init__()
        self.bot = bot
        self.error_id = error_id
        self.channel_id = channel_id
        self.server_id = server_id
        self.command_name = command_name
        self.server_name = server_name

    async def on_submit(self, interaction: discord.Interaction):
        dev_channel = self.bot.get_channel(bug_report_channel_id)
        if dev_channel:

            user_mention = interaction.user.mention
            channel_mention = f"<#{self.channel_id}>"

            embed = discord.Embed(title="エラーログ", description=f"エラーID: {self.error_id}", color=discord.Color.red())
            embed.add_field(name="ユーザー", value=user_mention, inline=False)
            embed.add_field(name="チャンネル", value=channel_mention, inline=False)
            embed.add_field(name="サーバー", value=self.server_name, inline=False)
            embed.add_field(name="コマンド", value=f"/{self.command_name}", inline=False)
            embed.add_field(name="エラーメッセージ", value=self.reason.value, inline=False)
            if self.image.value:
                embed.set_image(url=self.image.value)
            await dev_channel.send(embed=embed)
            
            await interaction.response.send_message("バグを報告しました。ありがとうございます！", ephemeral=True)
        else:
            e = discord.Embed(title="エラー", description="> 予期せぬエラーです\n\n<@707320830387814531>にDMを送信するか、[サポートサーバー](https://hfspro.co/asb-discord)にてお問い合わせください", color=discord.Color.red())
            await interaction.response.send_message(embed=e)

class BugReportView(discord.ui.View):
    def __init__(self, bot, error_id, channel_id, server_id, command_name, server_name):
        super().__init__()
        self.bot = bot
        self.error_id = error_id
        self.channel_id = channel_id
        self.server_id = server_id
        self.command_name = command_name
        self.server_name = server_name

    async def disable_button(self, interaction):
        await asyncio.sleep(120)
        for item in self.children:
            if item.custom_id == "my_button":
                item.disabled = True
        await interaction.edit_original_response(view=self)

    @discord.ui.button(label="バグを報告する", style=discord.ButtonStyle.red, custom_id="report_bug_button", emoji="<:bug_hunter:1226787664020242482>")
    async def report_bug_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = BugReportModal(self.bot, self.error_id, self.channel_id, self.server_id, self.command_name, self.server_name)
        await interaction.response.send_modal(modal)
        asyncio.create_task(self.disable_button(interaction))



class MyBot(commands.AutoShardedBot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initialized = False
        self.cog_classes = {}
        self.ERROR_LOG_CHANNEL_ID = int(os.getenv('ERROR_LOG_CHANNEL_ID'))

    async def setup_hook(self):
        self.loop.create_task(self.after_ready())

    async def after_ready(self):
        await self.wait_until_ready()
        print("setup_hook is called")
        await self.load_cogs('cogs')
        await self.load_backup_cogs('cogs/backup')
        await self.tree.sync()
        if not self.initialized:
            print("Initializing...")
            await self.change_presence(activity=discord.Game(name="起動中.."))
            self.loop.create_task(presence.update_presence(self))
            self.initialized = True
            print('------')
            print('All cogs have been loaded and bot is ready.')
            print('------')

    async def on_ready(self):
        print("on_ready is called")
        log_data = {
            "event": "BotReady",
            "description": f"{self.user} has successfully connected to Discord.",
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "session_id": session_id
        }
        save_log(log_data)
        if not self.initialized:
            try:
                await startup_send_webhook(self, guild_id=main_guild_id)
                await startup_send_botinfo(self)
            except Exception as e:
                print(f"Error during startup: {e}")
            self.initialized = True


    async def load_cogs(self, folder_name: str):
        cur = pathlib.Path('.')
        for p in cur.glob(f"{folder_name}/**/*.py"):
            if p.stem == "__init__" or "backup" in p.parts:
                continue
            try:
                cog_path = p.relative_to(cur).with_suffix('').as_posix().replace('/', '.')
                await self.load_extension(cog_path)
                print(f'{cog_path} loaded successfully.')
            except commands.ExtensionFailed as e:
                print(f'Failed to load extension {p.stem}: {e}')

    async def load_backup_cogs(self, folder_name: str):
        if folder_name == "cogs/backup":
            cur = pathlib.Path('.')
            for p in cur.glob(f"{folder_name}/**/*.py"):
                if p.stem == "__init__":
                    continue
                try:
                    cog_path = p.relative_to(cur).with_suffix('').as_posix().replace('/', '.')
                    await self.load_extension(cog_path)
                    print(f'{cog_path} loaded successfully.')
                except commands.ExtensionFailed as e:
                    print(f'Failed to load extension {p.stem}: {e}')

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandError):
            error_id = uuid.uuid4()

            channel_id = ctx.channel.id
            server_id = ctx.guild.id if ctx.guild else 'DM'
            server_name = ctx.guild.name if ctx.guild else 'DM'
            channel_mention = f"<#{channel_id}>"

            e = discord.Embed(
                title="エラー通知",
                description=(
                    "> <:error:1226790218552836167>コマンド実行中にエラーが発生しました。\n"
                    f"**エラーID**: `{error_id}`\n"
                    f"**コマンド**: {ctx.command.qualified_name if ctx.command else 'N/A'}\n"
                    f"**ユーザー**: {ctx.author.mention}\n"
                    f"**エラーメッセージ**: {error}\n"
                ),
                color=discord.Color.red()
            )
            e.set_footer(text=f"サーバー: {server_name}")
            await self.get_channel(self.ERROR_LOG_CHANNEL_ID).send(embed=e)

            view = BugReportView(self, str(error_id), str(channel_id), str(server_id), ctx.command.qualified_name if ctx.command else "N/A", server_name)

            embed_dm = discord.Embed(
                title="エラー通知",
                description=(
                    "> <:error:1226790218552836167>コマンド実行中にエラーが発生しました。\n"
                    f"エラーID: `{error_id}`\n"
                    f"チャンネル: {channel_mention}\n"
                    f"サーバー: `{server_name}`\n\n"
                    "__下のボタンを押してバグを報告してください。__\n参考となるスクリーンショットがある場合は**__事前に画像URL__**を準備してください。"
                ),
                color=discord.Color.red()
            )
            embed_dm.set_footer(text="バグ報告に貢献してくれた方にはサポート鯖で特別なロールを付与します。")

            await ctx.author.send(embed=embed_dm, view=view)

intent: discord.Intents = discord.Intents.all()
bot = MyBot(command_prefix=command_prefix, intents=intent, help_command=CustomHelpCommand())

bot.run(TOKEN)  