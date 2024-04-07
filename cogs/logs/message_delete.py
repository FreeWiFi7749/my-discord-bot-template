import discord
from discord.ext import commands
import aiohttp
from PIL import Image, ImageOps
import io
import json
import os
from datetime import datetime, timedelta, timezone
import math

async def fetch_image(session, url):
    async with session.get(url) as response:
        return await response.read()

async def resize_image_if_needed(image_bytes, max_file_size=8*1024*1024, resize_ratio=0.9):
    image = Image.open(io.BytesIO(image_bytes))

    # JPEGで保存してファイルサイズを減らす試み
    with io.BytesIO() as output:
        image.save(output, format='JPEG', quality=85)  # 品質は調整可能
        size = output.tell()
        if size <= max_file_size:
            output.seek(0)
            return output.read()

    # 必要に応じてさらにリサイズ
    while size > max_file_size:
        image = image.resize((int(image.width * resize_ratio), int(image.height * resize_ratio)))
        with io.BytesIO() as output:
            image.save(output, format='JPEG', quality=85)  # 品質はさらに調整可能
            size = output.tell()
            if size <= max_file_size:
                output.seek(0)
                return output.read()

async def merge_images_horizontally(image_urls, max_file_size=8*1024*1024):
    async with aiohttp.ClientSession() as session:
        images = []
        total_width = 0
        max_height = 0

        for url in image_urls:
            async with session.get(url) as resp:
                if resp.status != 200:
                    continue
                image_bytes = await resp.read()
                resized_image_bytes = await resize_image_if_needed(image_bytes, max_file_size)
                image = Image.open(io.BytesIO(resized_image_bytes))
                images.append(image)
                total_width += image.width
                max_height = max(max_height, image.height)

        merged_image = Image.new('RGB', (total_width, max_height))

        x_offset = 0
        for image in images:
            merged_image.paste(image, (x_offset, 0))
            x_offset += image.width

        # 最終合成画像のファイルサイズチェックは不要になるかもしれませんが、必要に応じて実施
        with io.BytesIO() as output:
            merged_image.save(output, format='PNG')
            output.seek(0)
            return discord.File(output, filename="merged_images.png")

async def send_images_in_chunks(image_urls, log_channel, max_images_per_message=10):
    async with aiohttp.ClientSession() as session:
        for i in range(0, len(image_urls), max_images_per_message):
            chunk_urls = image_urls[i:i+max_images_per_message]
            images = []
            for url in chunk_urls:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        continue
                    image_bytes = await resp.read()
                    resized_image_bytes = await resize_image_if_needed(image_bytes)
                    image = Image.open(io.BytesIO(resized_image_bytes))
                    images.append(image)

            if images:
                # 合成画像を作成し、送信する
                total_width = sum(image.width for image in images)
                max_height = max(image.height for image in images)
                merged_image = Image.new('RGB', (total_width, max_height))
                x_offset = 0
                for image in images:
                    merged_image.paste(image, (x_offset, 0))
                    x_offset += image.width

                with io.BytesIO() as output:
                    merged_image.save(output, format='PNG')
                    output.seek(0)
                    file = discord.File(output, filename=f"merged_images_chunk_{i}.png")
                    try:
                        await log_channel.send(content="こちらは合成された添付画像の一部です：", file=file)
                    except discord.HTTPException as e:
                        if e.code == 40005:
                            await log_channel.send("画像が大きすぎるため、送信できませんでした。")

class MessageDeleteLoggingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_config_path(self, guild_id):
        config_dir = f"data/logs/{guild_id}/config"
        os.makedirs(config_dir, exist_ok=True)
        return os.path.join(config_dir, "message_delete.json")

    def load_config(self, guild_id):
        config_path = self.get_config_path(guild_id)
        if not os.path.exists(config_path):
            return {"log_message_delete": True, "log_channel": None}
        with open(config_path, 'r') as f:
            return json.load(f)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        #ここで特定のチャンネルのみオフにすることができる
        #if message.author.bot or message.channel.name == "📮┫グローバルチャット":
        #    return
        
        config = self.load_config(message.guild.id)
        if not config.get("log_message_delete"):
            return
        
        log_channel_id = config.get("log_channel")
        log_channel = self.bot.get_channel(log_channel_id)
        if not log_channel:
            return
        
        deleter = None  # 消去者の初期化
        async for entry in message.guild.audit_logs(limit=1, action=discord.AuditLogAction.message_delete):
            if entry.target.id == message.author.id and entry.extra.channel.id == message.channel.id:
                deleter = entry.user
                break

        JST = timezone(timedelta(hours=+9), 'JST')
        embed = discord.Embed(title="メッセージ消去", color=discord.Color.red(), timestamp=datetime.now(JST))
        embed.set_author(name=message.author.display_name, icon_url=message.author.avatar.url)
        embed.add_field(name="メッセージ", value=message.content if message.content else "なし", inline=False)
        embed.add_field(name="チャンネル", value=message.channel.mention, inline=True)
        embed.set_footer(text=f"メッセージID: {message.id}")
        if deleter:
            embed.add_field(name="消去者", value=deleter.mention, inline=True)
        else:
            embed.add_field(name="消去者", value="不明", inline=True)

        # 最初の埋め込みを送信
        await log_channel.send(embed=embed)

        # 添付ファイルがある場合、リンクを含む別の埋め込みをフォローアップとして送信
        attachment_urls = []
        image_urls = []
        other_files_info = []

        # 添付ファイルを画像とその他に分類
        for attachment in message.attachments:
            filename, file_extension = os.path.splitext(attachment.filename)
            if file_extension.lower() in ['.png', '.jpg', '.jpeg', '.gif']:
                image_urls.append(attachment.url)
            else:
                other_files_info.append(f"[{filename}{file_extension}]({attachment.url})")

        # 画像以外の添付ファイル情報を含む埋め込みを送信
        if other_files_info:
            non_image_files_text = "\n".join(other_files_info)
            embed_links = discord.Embed(title="消去されたメッセージのその他の添付ファイル", description=non_image_files_text, color=discord.Color.greyple())
            await log_channel.send(embed=embed_links)

        # 画像ファイルがある場合、それらを合成して送信
        if image_urls:
            # 最初の埋め込みメッセージを送信
            embed_image = discord.Embed(title="消去されたメッセージの添付画像", description="複数の画像を合成しています...", color=discord.Color.greyple())
            message_embed = await log_channel.send(embed=embed_image)


            # 画像のURLリストを含む新しい埋め込みを作成
            image_links_text = "\n".join([f"[画像{i+1}]({url})" for i, url in enumerate(image_urls)])
            embed_image_links = discord.Embed(title="消去されたメッセージの添付画像", description=image_links_text, color=discord.Color.greyple())

            # 最初に送信したメッセージの埋め込みを更新
            await message_embed.edit(embed=embed_image_links)

            # 合成した画像ファイルを送信
            await send_images_in_chunks(image_urls, log_channel)


async def setup(bot):
    await bot.add_cog(MessageDeleteLoggingCog(bot))