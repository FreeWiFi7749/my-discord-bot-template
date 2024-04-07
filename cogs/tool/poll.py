from discord.ext import commands
import discord
import re
import uuid
import json
from pathlib import Path
from discord.ui import Select, View

def to_emoji(c: int) -> str:
    base = 0x1F1E6
    return chr(base + c)

#<--------------View-------------->

class PollSumSelectMenu(Select):
    def __init__(self, polls, bot, ctx):
        self.bot = bot
        self.ctx = ctx
        options = [
            discord.SelectOption(label=poll["question"][:100], description=f"ID: {poll_id}", value=poll_id)
            for poll_id, poll in polls.items()
        ]
        super().__init__(placeholder="集計したい投票を選択してください...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        poll_id = self.values[0]
        guild_id = self.ctx.guild.id
        user_dirs = Path(f'data/polls/{guild_id}').iterdir()

        poll_path = None
        poll_data = None

        for user_dir in user_dirs:
            if user_dir.is_dir():
                active_polls_path = user_dir / 'active'
                if active_polls_path.exists():
                    potential_poll_file = active_polls_path / f'{poll_id}.json'
                    if potential_poll_file.exists():
                        poll_path = potential_poll_file
                        break

        if not poll_path.exists():
            await interaction.response.send_message("指定された投票が見つかりません。", ephemeral=True)
            return
        
        with poll_path.open('r', encoding='utf-8') as f:
            poll_data = json.load(f)
        await interaction.response.defer()
        message_id = poll_data.get('message_id')
        if not message_id:
            await interaction.response.send_message("メッセージIDが見つかりません。", ephemeral=True)
            return

        try:
            message = await self.ctx.channel.fetch_message(message_id)
        except discord.NotFound:
            await interaction.response.send_message("投票メッセージが見つかりません。", ephemeral=True)
            return
        
        results = {}
        for reaction in message.reactions:

            emoji = str(reaction.emoji)
            results[emoji] = reaction.count - 1

        sorted_results = sorted(results.items(), key=lambda x: x[1], reverse=True)
        max_length = 10

        result_text = ""
        total_votes = sum(results.values())
        for emoji, count in sorted_results:
            percentage = (count / total_votes) * 100 if total_votes else 0
            bar_length = int((percentage / 100) * max_length)
            bar = '█' * bar_length
            trophy = ' 🏆' if count == sorted_results[0][1] else ''
            result_text += f"{emoji}: {count}票 ({percentage:.1f}%) {bar}{trophy}\n"
    
        embed = discord.Embed(
            title=poll_data['question'],
            description=result_text,
            color=0x00ff00
        )
        message_link = f"https://discord.com/channels/{self.ctx.guild.id}/{self.ctx.channel.id}/{message_id}"
        embed.add_field(name="投票を見る", value=f"[メッセージへ]({message_link})", inline=False)

        await interaction.followup.send(embed=embed)

class PollSumView(View):
    def __init__(self, polls, bot, ctx):
        super().__init__()
        self.add_item(PollSumSelectMenu(polls, bot, ctx))

class PollEndSelectMenu(Select):
    def __init__(self, polls, bot, ctx):
        self.bot = bot
        self.ctx = ctx
        options = [
            discord.SelectOption(label=poll["question"][:100], description=f"ID: {poll_id}", value=poll_id)
            for poll_id, poll in polls.items()
        ]
        super().__init__(placeholder="終了させたい投票を選択してください...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        poll_id = self.values[0]
        poll_path = Path(f'data/polls/{self.ctx.guild.id}/{interaction.user.id}/active/{poll_id}.json')
        archive_path = Path(f'data/polls/{self.ctx.guild.id}/{interaction.user.id}/archive/{poll_id}.json')
        if not poll_path.exists():
            await interaction.response.send_message("指定された投票が見つかりません。", ephemeral=True)
            return
        
        with poll_path.open('r', encoding='utf-8') as f:
            poll = json.load(f)
        await interaction.response.defer()
        message_id = poll.get('message_id')
        if not message_id:
            await interaction.response.send_message("メッセージIDが見つかりません。", ephemeral=True)
            return

        try:
            message = await self.ctx.channel.fetch_message(message_id)
        except discord.NotFound:
            await interaction.response.send_message("投票メッセージが見つかりません。", ephemeral=True)
            return
        
        results = {}
        for reaction in message.reactions:

            emoji = str(reaction.emoji)
            results[emoji] = reaction.count - 1

        sorted_results = sorted(results.items(), key=lambda x: x[1], reverse=True)

        result_text = "\n".join([f"{emoji}: {count} 票" for emoji, count in sorted_results])
    
        embed = message.embeds[0]
        embed.add_field(name="投票結果", value=result_text or "結果がありません", inline=False)
        embed.color = discord.Color.red()
        await message.edit(embed=embed)
        await message.clear_reactions()
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        poll_path.rename(archive_path)
        
        await interaction.channel.send("投票が終了しました。", ephemeral=True)

class PollEndView(View):
    def __init__(self, polls, bot, ctx):
        super().__init__()
        self.add_item(PollEndSelectMenu(polls, bot, ctx))

#<--------------Cog-------------->
        
class PollsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

#<--------------Utility-------------->

    async def save_poll_data(self, guild_id: int, user_id: int, poll_id: str, data: dict, message_id: int):
        """投票データを保存する"""
        active_polls_path = Path(f'data/polls/{guild_id}/{user_id}/active')
        active_polls_path.mkdir(parents=True, exist_ok=True)
        data['message_id'] = message_id
        with open(active_polls_path / f'{poll_id}.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

#<--------------Commands-------------->

    @commands.hybrid_group(name='polls', aliases=['vote'])
    async def polls_group(self, ctx: commands.Context):
        """投票に関するコマンド"""
        await ctx.send("投票に関するサブコマンドを使ってください")

    @polls_group.command(name='poll', aliases=['po'])
    async def quickpoll(self, ctx: commands.Context, *, 質問と選択肢: str):
        """複数投票可能な投票を作成します。"""
        args = re.split(r'[ 　]+', 質問と選択肢)

        if len(args) < 3:
            return await ctx.send('質問と最低2つの選択肢を入力してください。')

        question = args[0]
        choices = args[1:]
    
        if len(choices) > 20:
            return await ctx.send('選択肢は最大20個までです。',)

        poll_id = str(uuid.uuid4())

        poll_data = {
            "question": question,
            "answers": [[f"{index+1}", choice] for index, choice in enumerate(choices)],
            "author": ctx.author.id,
        }

        choices_description = "\n".join([f"{index}\N{COMBINING ENCLOSING KEYCAP} {choice}" for index, choice in enumerate(choices, start=1)])

        embed = discord.Embed(
            title=question,
            description=f"{choices_description}\n🗳️</polls sum:1221715714579103804>で集計",
            color=0x00ff00
        )        
        embed.set_footer(text="/polls end で終了")
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar.url)
        poll_message = await ctx.send(embed=embed)
    
        for index in range(len(choices)):
            emoji = f'{index+1}\N{COMBINING ENCLOSING KEYCAP}'
            await poll_message.add_reaction(emoji)

        await self.save_poll_data(ctx.guild.id, ctx.author.id, poll_id, poll_data, poll_message.id)

    @polls_group.command(name='expoll', aliases=['exclusivepoll'])
    async def exclusive_poll(self, ctx: commands.Context, *, 質問と選択肢: str):
        """一つの選択肢しか選べない投票を作成します。"""
        args = re.split(r'[ 　]+', 質問と選択肢)

        if len(args) < 3:
            return await ctx.send('質問と最低2つの選択肢を入力してください。')

        question = args[0]
        choices = args[1:]

        if len(choices) > 20:
            return await ctx.send('選択肢は最大20個までです。')

        poll_id = str(uuid.uuid4())

        poll_data = {
            "question": question,
            "answers": [[f"{index+1}", choice] for index, choice in enumerate(choices)],
            "author": ctx.author.id,
            "exclusive": True
        }

        choices_description = "\n".join([f"{index}\N{COMBINING ENCLOSING KEYCAP} {choice}" for index, choice in enumerate(choices, start=1)])

        embed = discord.Embed(
            title=question,
            description=f"{choices_description}\n🗳️</polls sum:1221715714579103804>で集計",
            color=0x00ff00
        )        
        embed.set_footer(text="/polls end で終了")
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar.url)
        poll_message = await ctx.send(embed=embed)

        for index in range(len(choices)):
            emoji = f'{index+1}\N{COMBINING ENCLOSING KEYCAP}'
            await poll_message.add_reaction(emoji)

        await self.save_poll_data(ctx.guild.id, ctx.author.id, poll_id, poll_data, poll_message.id)

    @polls_group.command(name="sum")
    async def sum_poll(self, ctx: commands.Context):
        """指定した投票の集計をします。"""
        guild_id = ctx.guild.id
        user_dirs = Path(f'data/polls/{guild_id}').iterdir()

        polls = {}
        for user_dir in user_dirs:
            if user_dir.is_dir():
                active_polls_path = user_dir / 'active'
                if active_polls_path.exists():
                    for poll_file in active_polls_path.glob('*.json'):
                        with poll_file.open('r', encoding='utf-8') as f:
                            poll = json.load(f)
                            polls[poll_file.stem] = poll

        if not polls:
            await ctx.send("集計する投票がありません。", ephemeral=True)
            return
        
        view = PollSumView(polls, self.bot, ctx)
        await ctx.send("集計したい投票を選択してください：", view=view, ephemeral=True)

    @polls_group.command(name="end")
    async def end_poll(self, ctx: commands.Context):
        """自分で作成した投票を終了します。"""
        guild_id = ctx.guild.id
        polls_path = Path(f'data/polls/{guild_id}/{ctx.author.id}/active')
        polls = {}

        if polls_path.exists() and polls_path.is_dir():
            for poll_file in polls_path.iterdir():
                if poll_file.suffix == '.json':
                    with poll_file.open('r', encoding='utf-8') as f:
                        polls[poll_file.stem] = json.load(f)

        if not polls:
            await ctx.send("終了する投票がありません。", ephemeral=True)
            return

        view = PollEndView(polls, self.bot, ctx)
        await ctx.send("終了させたい投票を選択してください：", view=view, ephemeral=True)

#<--------------Event Handlers-------------->

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.guild_id is None or payload.user_id == self.bot.user.id:
            return

        channel = self.bot.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)

        for reaction in message.reactions:
            if reaction.emoji != payload.emoji.name:
                async for user in reaction.users():
                    if user.id == payload.user_id:
                        await message.remove_reaction(reaction.emoji, user)

async def setup(bot: commands.Bot):
    await bot.add_cog(PollsCog(bot))