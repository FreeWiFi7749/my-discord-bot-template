import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import re
import pathlib
import uuid
from datetime import datetime
import logging
from utils import presence
from utils.logging import save_log
from utils.startup import startup_send_webhook, startup_send_botinfo

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
            
            error_channel = self.get_channel(self.ERROR_LOG_CHANNEL_ID)
            if error_channel:
                embed = discord.Embed(title="エラーログ", description=f"エラーID: {error_id}", color=discord.Color.red())
                embed.add_field(name="ユーザー", value=ctx.author.mention, inline=False)
                embed.add_field(name="コマンド", value=ctx.command.qualified_name if ctx.command else "N/A", inline=False)
                embed.add_field(name="エラーメッセージ", value=str(error), inline=False)
                await error_channel.send(embed=embed)
            
            embed_dm = discord.Embed(
                title="エラー通知",
                description=(
                    "コマンド実行中にエラーが発生しました。\n"
                    f"エラーID: `{error_id}`\n\n"
                    "</bug_report:1226307114943774786>コマンドにこのIDとエラー発生時の状況とその際のスクリーンショットを一緒に報告お願いします。"
                ),
                color=discord.Color.red()
            )
            embed_dm.set_footer(text="このメッセージはあなたにのみ表示されています。")
            msg_error_id = error_id
            await ctx.author.send(embed=embed_dm)
            await ctx.author.send(f"このメッセージをコピーしてください\nエラーID: `{msg_error_id}`")

intent: discord.Intents = discord.Intents.all()
bot = MyBot(command_prefix=command_prefix, intents=intent, help_command=CustomHelpCommand())

bot.run(TOKEN)  