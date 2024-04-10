import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Button, View, Select
from discord import SelectOption
import os
from dotenv import load_dotenv

load_dotenv()

help_commnad_id = int(os.getenv("HELP_COMMAND_ID"))

class HelpView(View):
    def __init__(self):
        super().__init__()
        self.add_item(HelpSelect())
        self.add_item(HelpButton())

class HelpSelect(Select):
    def __init__(self):
        options = [
            SelectOption(label="ここに表示したいヘルプの名前(例: anti-spam)", value="ここも同じく(例: anti-spam)"),
        ]
        super().__init__(placeholder="カテゴリを選択してください。", options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_value = self.values[0]
        if interaction.guild:
            member = interaction.guild.get_member(interaction.user.id)
            if member:
                color = member.color
            else:
                color = discord.Color.blurple()
        else:
            color = discord.Color.blurple()
        if selected_value == "anti-spam":
            e = discord.Embed(title='アンチスパムヘルプ', colour=color)
            e.add_field(name='anti-spam', value='アンチスパム機能に関するヘルプ', inline=False)
            e.set_thumbnail(url=interaction.client.user.avatar.url)
            e.set_author(name=f"{interaction.client.user.name}のヘルプ", icon_url=interaction.client.user.avatar.url)

        elif selected_value == "これを参考にどんどん追加":
            e = discord.Embed(title='バックアップヘルプ', colour=color)
            e.add_field(name='backup', value='バックアップ機能に関するヘルプ', inline=False)
            e.set_footer(text="バックアップ機能に関するヘルプです。")
            e.set_thumbnail(url=interaction.client.user.avatar.url)
            e.set_author(name=f"{interaction.client.user.name}のヘルプ", icon_url=interaction.client.user.avatar.url)

        else:
            e = discord.Embed(title="エラー", description="不明なカテゴリが選択されました。", color=discord.Color.red())

        await interaction.response.edit_message(embed=e, view=HelpView(), ephemeral=True)
class HelpButton(Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.link, label="サポートサーバに参加する", url="サポートサーバーの招待リンク")

async def autocomplete_help_options(interaction: discord.Interaction, current: str):
    options = ["anti-spam", "backup", "manege", "mod", "report", "tools"]
    return [option for option in options if current.lower() in option.lower()]


class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.help_commnad_id = help_commnad_id

    @app_commands.command(name="help", description="ヘルプを表示します")
    @app_commands.describe(option="ヘルプを表示するカテゴリ名")
    @app_commands.choices(option=[
        app_commands.Choice(name="anti-spam", value="anti-spam"),
        app_commands.Choice(name="これを参考にどんどん追加", value="これを参考にどんどん追加")
    ])
    async def help(self, interaction: discord.Interaction, option: app_commands.Choice[str] = None):
        if option is None:
            if interaction.guild:
                member = interaction.guild.get_member(interaction.user.id)
                if member:
                    color = member.color
                else:
                    color = discord.Color.blurple()
            else:
                color = discord.Color.blurple()
            e = discord.Embed(title='ヘルプ', colour=color)
            e.add_field(name='anti-spam', value=f'アンチスパムに関するヘルプ\n</help:{help_commnad_id}> anti-spam', inline=False)
            e.add_field(name='これを参考にどんどん追加', value=f'hogehoge\n</help:{help_commnad_id}> backup', inline=False)
            e.set_footer(text="ヘルプを表示するには、/help <カテゴリ名>を入力してください。\nもしこれをみても解決しない場合は、ボタンを押してサポートサーバに参加してください。")
            e.set_thumbnail(url=interaction.client.user.avatar.url)
            e.set_author(name=f"{interaction.client.user.name}のヘルプ", icon_url=interaction.client.user.avatar.url)

            await interaction.response.send_message(embed=e, view=HelpView(), ephemeral=True)

        if option in(["anti-spam", "これを参考にどんどん追加"]):
            await HelpSelect().callback(interaction)

async def setup(bot):
    await bot.add_cog(HelpCog(bot))
