import discord

async def fetch_latest_announcement(bot, channel_id):
    """指定されたチャンネルIDから最新のお知らせを取得する"""
    channel = bot.get_channel(channel_id)
    if channel is not None:
        try:
            messages = [message async for message in channel.history(limit=1)]
            if messages:
                return messages[0].content
            else:
                return "お知らせはありません。"
        except discord.DiscordException as e:
            return f"お知らせの取得に失敗しました。エラー: {e}"
    else:
        return "指定されたチャンネルが見つかりません。"