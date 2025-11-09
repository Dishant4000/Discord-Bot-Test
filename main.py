import discord
import io
import time
import qrcode
import aiohttp
import html
import psutil
import platform
import importlib
import traceback
import json, asyncio, os, sys
from discord.ext import commands
from colorama import Fore, Style
from discord import ui, ButtonStyle
from datetime import datetime, timezone

# --- Load Config ---
with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

bot_config = config["BOT"]
bot_data_config = config["BOT_DATA"]

# --- Intents ---
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=".", intents=intents, help_command=None)

bot_start_time = datetime.now(timezone.utc)

# --- Load Extensions from /cogs and /cogs_shop ---
async def load_extensions():
    """
    Loads all cogs from /cogs and /cogs_shop directories.
    Skips ignored files and logs any load errors.
    """
    print("\n🔧 Loading bot modules from /cogs and /cogs_shop ...\n")
    start_time = time.time()

    folders = ["cogs", "cogs_shop", "manage"]
    ignore_files = {"main.py", "__init__.py", "old_main.py", "database_manager.py"}
    os.makedirs("logs", exist_ok=True)
    error_log_path = os.path.join("logs", "errors.txt")

    results = []  # (filename, status, details)

    for folder in folders:
        if not os.path.exists(folder):
            print(f"⚠️ Folder '{folder}' not found, skipping...\n")
            continue

        for filename in sorted(os.listdir(folder)):
            if not filename.endswith(".py") or filename in ignore_files:
                continue

            mod_name = filename[:-3]  # drop .py
            full_mod_path = f"{folder}.{mod_name}"

            try:
                before_cogs = set(bot.cogs.keys())

                if full_mod_path in sys.modules:
                    importlib.reload(sys.modules[full_mod_path])

                await bot.load_extension(full_mod_path)

                after_cogs = set(bot.cogs.keys())
                new_cogs = after_cogs - before_cogs

                if new_cogs:
                    results.append((f"{folder}/{filename}", "OK", f"Cogs: {', '.join(sorted(new_cogs))}"))
                    print(f"🧩 Loaded {folder}/{filename} — ✅ ({', '.join(sorted(new_cogs))})")
                else:
                    results.append((f"{folder}/{filename}", "WARN", "No Cog registered."))
                    print(f"⚠️ Loaded {folder}/{filename} — WARNING: No Cog registered.")
                    with open(error_log_path, "a", encoding="utf-8") as ef:
                        ef.write(f"[{datetime.now(timezone.utc)}] WARNING: {folder}/{filename} — No Cog registered.\n")

            except Exception as e:
                tb = "".join(traceback.format_exception(type(e), e, e.__traceback__))
                results.append((f"{folder}/{filename}", "ERROR", str(e)))
                print(f"❌ Failed to load {folder}/{filename}: {e}\n")
                with open(error_log_path, "a", encoding="utf-8") as ef:
                    ef.write(f"[{datetime.now(timezone.utc)}] ERROR loading {folder}/{filename}:\n{tb}\n")

    end_time = time.time()
    ok_count = sum(1 for r in results if r[1] == "OK")
    warn_count = sum(1 for r in results if r[1] == "WARN")
    err_count = sum(1 for r in results if r[1] == "ERROR")

    print("\n✅ Module Load Summary:")
    for fn, status, details in results:
        prefix = "  ✅" if status == "OK" else ("  ⚠️" if status == "WARN" else "  ❌")
        print(f"{prefix} {fn} — {status} — {details}")
    print(f"\n🚀 Total Time: {end_time - start_time:.2f}s | OK: {ok_count} | WARN: {warn_count} | ERROR: {err_count}\n")


# ---------- Event ----------
@bot.event
async def on_ready():
    print("=" * 60)
    print(f"🚀  Bot Name     : {bot.user.name}")
    print(f"🤖  Bot ID       : {bot.user.id}")
    print(f"🌐  Connected To : {len(bot.guilds)} Server(s)")
    print(f"✅  Logged in as : {bot.user}")
    print(f"🕒  Started at   : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 60)
    print("📦  Loading modules...")

    try:
        channel_id = bot_data_config["LOG_ID"]
        channel = bot.get_channel(channel_id)

        if channel:
            now = datetime.now(timezone.utc)
            uptime_seconds = (now - bot_start_time).total_seconds()
            uptime_hours = int(uptime_seconds // 3600)
            uptime_minutes = int((uptime_seconds % 3600) // 60)
            uptime_str = f"{uptime_hours}h {uptime_minutes}m"

            embed = discord.Embed(
                title="🤖 Bot Status Update",
                description="**The bot is now online and ready to use!**",
                color=discord.Color.green(),
                timestamp=now
            )
            embed.add_field(name="🧠 Bot Name", value=f"{bot.user.name}", inline=True)
            embed.add_field(name="🆔 Bot ID", value=f"`{bot.user.id}`", inline=True)
            embed.add_field(name="🕒 Started At", value=f"<t:{int(bot_start_time.timestamp())}:F>", inline=False)
            embed.add_field(name="⏳ Uptime", value=uptime_str, inline=True)
            embed.add_field(name="🌍 Servers Connected", value=f"{len(bot.guilds)}", inline=True)
            embed.add_field(name="👥 Users Cached", value=f"{len(bot.users)}", inline=True)

            embed.set_thumbnail(url=bot.user.display_avatar.url)
            embed.set_footer(text="Bot Online Notification")

            await channel.send(embed=embed)
        else:
            print("⚠️ Log channel not found or invalid ID in config.")

    except Exception as e:
        print(f"⚠️ Error in on_ready event: {e}")

    for ext in bot.extensions.keys():
        print(f"🧱 {ext} loaded successfully")
    
    print("-" * 60)
    print("✅  All modules loaded successfully! 😎🔥")
    print("✨  Bot is now online and ready to use.")
    print("💻  Developed by Dishant ⚡")
    print("=" * 60 + "\n")

# --- Main Function ---
async def main():
    async with bot:
        await load_extensions()
        await bot.start(bot_config["TOKEN"])

if __name__ == "__main__":
    asyncio.run(main())
