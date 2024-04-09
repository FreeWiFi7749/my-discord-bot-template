from discord.ext import commands
import discord
import json
import os
from cogs.backup.backup_auto import BackupAuto

class BackupCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.backup_items = []
        self.BackupAuto = BackupAuto(self.bot)
        
    @commands.hybrid_command(name="backup")
    async def backup(self, ctx, enable: bool):
        """バックアップを有効にしますか？"""
        if enable:
            # セレクターメニューを含むメッセージを送信
            view = BackupSelectorView()
            message = await ctx.send("バックアップ項目を選択してください:", view=view, ephemeral=True)
            await view.wait()  # ユーザーの選択を待つ
            if view.children[0].values:  # ユーザーが選択した場合
                try:
                    await self.BackupAuto.backup_items_setup(view.children[0].values)
                    # バックアップジョブを開始
                    self.BackupAuto.backup_job.start()
                    await message.followup.send(content="バックアップが有効にされました。")
                except Exception as e:
                    await message.followup.send(content=f"エラーが発生しました: {e}")
            else:  # ユーザーが何も選択しなかった場合
                await message.followup.send(content="バックアップの設定がキャンセルされました。")
        else:
            # バックアップジョブを停止
            self.BackupAuto.backup_job.cancel()
            await ctx.send("バックアップが無効にされました。")

class BackupSelector(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="ロール", description="ロールのバックアップを有効にします"),
            discord.SelectOption(label="チャット", description="チャットのバックアップを有効にします"),
            discord.SelectOption(label="チャンネル", description="チャンネルのバックアップを有効にします"),
        ]
        super().__init__(placeholder="バックアップする項目を選択してください...", min_values=1, max_values=3, options=options)

    async def callback(self, interaction: discord.Interaction):
        try:
            os.makedirs(f'data/backup/{interaction.guild.id}', exist_ok=True)
            with open(f'data/backup/{interaction.guild.id}/backup_items.json', 'w', encoding='utf-8') as f:
                json.dump(self.values, f)
            await interaction.response.send_message(content="バックアップ項目が保存されました。", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(content=f"エラーが発生しました: {e}", ephemeral=True)


class BackupSelectorView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(BackupSelector())

async def setup(bot):
    await bot.add_cog(BackupCog(bot))