import discord
import io
import time
import qrcode
import aiohttp
import html
import psutil
import platform
import json, asyncio, os, sys
from discord.ext import commands
from discord import ui
from datetime import datetime, timezone
from manage.permissions import check_perm

# --- Load Config ---
with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

bot_config = config["BOT"]
bot_data_config = config["BOT_DATA"]
ticket_config = config["TICKET"]

class Inventory(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

async def setup(bot):
    await bot.add_cog(Inventory(bot))
    print("🧱 inventory.py loaded successfully")