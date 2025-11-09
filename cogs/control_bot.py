import discord
import asyncio
import os
import sys
import json
from datetime import datetime, timezone, timedelta
from discord.ext import commands
from manage.permissions import check_perm
from manage.database_manager import add_embed_log, add_normal_log

# --- Load Config ---
with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

bot_config = config["BOT"]
bot_data_config = config["BOT_DATA"]


class ControlBot(commands.Cog):
    """Owner-only system control commands (shutdown + restart)."""

    def __init__(self, bot):
        self.bot = bot

    # =============================
    # 🛑 SHUTDOWN COMMAND
    # =============================
    @commands.command(name="shutdown")
    @check_perm("FULL_ACCESS")
    async def shutdown(self, ctx):
        """Safely shut down the bot (Owner only)."""
        try:
            await ctx.message.delete()
        except:
            pass

        if ctx.author.id != bot_config["OWNER_ID"]:
            msg = await ctx.send("❌ You are not authorized to shut down the bot.")
            await asyncio.sleep(5)
            return await msg.delete()

        embed = discord.Embed(
            title="🛑 System Shutdown Initiated",
            description=(
                f"Bot is preparing to safely shut down...\n\n"
                f"**Requested by:** {ctx.author.mention}\n"
                f"🕒 **Time:** <t:{int(datetime.now(timezone.utc).timestamp())}:F>\n"
                f"⚙️ **Status:** Saving data, closing connections..."
            ),
            color=discord.Color.dark_red(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_footer(
            text="Ninja Official System • Shutting Down...",
            icon_url=ctx.author.display_avatar.url
        )

        add_embed_log(
            title="🛑 System Shutdown Initiated",
            ddescription=(
                f"Bot is preparing to safely shut down...\n\n"
                f"Requested by: {ctx.author.mention}\n"
                f"🕒 Time: <t:{int(datetime.now(timezone.utc).timestamp())}:F>\n"
                f"⚙️ Status: Saving data, closing connections..."
            ),
            footer_text="Ninja Official System • Shutting Down...",
            footer_icon=ctx.author.display_avatar.url
        )

        msg = await ctx.send(embed=embed)
        await asyncio.sleep(3)

        final_embed = discord.Embed(
            title="🔻 Bot Shutdown Complete",
            description=(
                "The bot has been safely powered off.\n\n"
                "🛡️ **All systems saved and connections closed.**\n"
                "🕒 **Restart manually or use `.restart` command later.**"
            ),
            color=discord.Color.red(),
            timestamp=datetime.now(timezone.utc)
        )
        final_embed.set_footer(
            text=f"Shutdown by {ctx.author}",
            icon_url=ctx.author.display_avatar.url
        )

        await msg.edit(embed=final_embed)
        await asyncio.sleep(3)

        # Log to channel
        log_id = bot_data_config.get("LOG_ID")
        if log_id:
            log_channel = self.bot.get_channel(log_id)
            if log_channel:
                await log_channel.send(embed=final_embed)

        # --- Force safe shutdown ---
        print("🛑 [SYSTEM] Closing bot and terminating process...")
        try:
            await self.bot.close()
        except Exception as e:
            print(f"⚠️ Bot close failed: {e}")

        # Give 1s delay for graceful closure
        await asyncio.sleep(1)

        # --- Kill process ---
        os._exit(0)

    # =============================
    # 🔁 RESTART COMMAND
    # =============================
    @commands.command(name="restart")
    @check_perm("FULL_ACCESS")
    async def restart(self, ctx):
        """Safely restart the bot (Owner only)."""
        try:
            await ctx.message.delete()
        except:
            pass

        if ctx.author.id != bot_config["OWNER_ID"]:
            msg = await ctx.send("❌ You are not authorized to restart the bot.")
            await asyncio.sleep(5)
            return await msg.delete()

        log_channel = self.bot.get_channel(bot_data_config.get("LOG_ID"))
        now = datetime.now(timezone.utc)

        # --- Embed Log for Restart Initiation ---
        if log_channel:
            embed = discord.Embed(
                title="🔁 Restart Initiated",
                description="The bot is restarting...",
                color=discord.Color.orange(),
                timestamp=now
            )
            embed.add_field(name="👤 Initiated By", value=ctx.author.mention, inline=True)
            embed.add_field(name="📅 Time", value=f"<t:{int(now.timestamp())}:F>", inline=True)
            embed.set_footer(text="Restart process started")
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)

            add_embed_log(
                title="🔁 Restart Initiated",
                description="The bot is restarting...",
                fields=[
                    {"name": "👤 Initiated By", "value": ctx.author.mention, "inline": False},
                    {"name": "📅 Time", "value": datetime.now(timezone(timedelta(hours=5, minutes=30))).strftime("%A, %B %d, %Y %I:%M %p"), "inline": False},
                ],
                footer_text="Restart process started",
                footer_icon=ctx.author.display_avatar.url
            )

            await log_channel.send(embed=embed)

        # --- Send Confirmation Message in Chat ---
        msg = await ctx.send("🔄 Restarting... Please wait a moment.")
        await asyncio.sleep(1)
        await msg.edit(content="⚙️ Shutting down and restarting now...\nWait 10 seconds for online!")

        # 🟡 Console message for dev clarity
        print("🔁 [SYSTEM] Restarting bot — saving state and relaunching process...")

        # --- Restart Bot ---
        python = sys.executable
        script = os.path.abspath(sys.argv[0])
        try:
            os.execl(python, f'"{python}"', f'"{script}"')
        except Exception as e:
            await ctx.send(f"⚠️ Restart failed: `{e}`")
    
    @commands.command(name="reload")
    @check_perm("FULL_ACCESS")
    async def reload(self, ctx, module_name: str = None):
        """♻️ Reload bot modules or configuration (Owner only)."""
        global config, bot_config, bot_data_config

        # 🧹 Try deleting user command message instantly
        try:
            await ctx.message.delete()
        except:
            pass

        # Load current config
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
        bot_config = config["BOT"]
        bot_data_config = config["BOT_DATA"]

        # 🔒 Owner-only protection
        if ctx.author.id != bot_config["OWNER_ID"]:
            msg = await ctx.send("❌ You are not authorized to reload modules.")
            await asyncio.sleep(5)
            return await msg.delete()

        ignored_files = ["main.py", "__init__.py", "database_manager.py"]
        log_channel = self.bot.get_channel(bot_data_config.get("LOG_ID"))

        # ==========================
        # ⚙️ CONFIG RELOAD SECTION
        # ==========================
        if module_name and module_name.lower() == "config":
            try:
                with open("config.json", "r", encoding="utf-8") as f:
                    config = json.load(f)
                bot_config = config["BOT"]
                bot_data_config = config["BOT_DATA"]

                embed = discord.Embed(
                    title="⚙️ Config Reloaded",
                    description="The bot configuration file (`config.json`) has been successfully reloaded.",
                    color=discord.Color.green(),
                    timestamp=datetime.now(timezone.utc)
                )
                embed.set_footer(
                    text=f"Reloaded by {ctx.author}",
                    icon_url=ctx.author.display_avatar.url
                )

                msg = await ctx.send(embed=embed, delete_after=8)
                if log_channel:
                    await log_channel.send(embed=embed)
                print("⚙️  [SYSTEM] Config reloaded successfully.")
                return
            except Exception as e:
                err = f"❌ Failed to reload config: {e}"
                msg = await ctx.send(err, delete_after=8)
                if log_channel:
                    await log_channel.send(f"⚠️ {err}")
                print(err)
                return

        # ==========================
        # 📦 MODULE RELOAD SECTION
        # ==========================
        folders = ["cogs", "cogs_shop", "manage"]
        module_files = []

        # Collect modules from both folders
        for folder in folders:
            if not os.path.exists(folder):
                continue
            for f in os.listdir(folder):
                if f.endswith(".py") and f not in ignored_files:
                    module_files.append(f"{folder}.{f.replace('.py', '')}")

        reloaded = []
        failed = []

        # --- Reload ALL modules ---
        if module_name is None:
            msg = await ctx.send("♻️ Reloading **all cogs** from both folders... Please wait.")
            for mod in module_files:
                try:
                    await self.bot.reload_extension(mod)
                    reloaded.append(mod)
                except Exception as e:
                    failed.append((mod, str(e)))

            embed = discord.Embed(
                title="♻️ Modules Reload Summary",
                description="Here’s the status of all module reloads.",
                color=discord.Color.green() if not failed else discord.Color.orange(),
                timestamp=datetime.now(timezone.utc)
            )

            # ✅ Reloaded Modules Section
            if reloaded:
                reloaded_text = "\n".join(f"🟢 `{mod}`" for mod in reloaded)
            else:
                reloaded_text = "⚙️ *No modules were reloaded.*"
            embed.add_field(
                name="✅ Successfully Reloaded",
                value=reloaded_text,
                inline=False
            )

            # ❌ Failed Modules Section
            if failed:
                failed_text = "\n".join(f"🔴 `{mod}` - {err}" for mod, err in failed)
                embed.add_field(
                    name="⚠️ Failed to Reload",
                    value=failed_text,
                    inline=False
                )

            embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/190/190411.png")
            embed.set_footer(
                text=f"Reload executed by {ctx.author}",
                icon_url=ctx.author.display_avatar.url
            )

            await msg.edit(content=None, embed=embed)
            if log_channel:
                await log_channel.send(embed=embed)

            print(f"♻️  [SYSTEM] Reloaded all modules: {reloaded}\n")
            if failed:
                print(f"⚠️ [WARNING] Failed modules: {failed}")

            await asyncio.sleep(8)
            await msg.delete()

        # --- Reload specific module ---
        else:
            module_name = module_name.lower().replace(".py", "")

            # Try to detect folder automatically
            target_module = None
            for folder in folders:
                if os.path.exists(os.path.join(folder, f"{module_name}.py")):
                    target_module = f"{folder}.{module_name}"
                    break

            if not target_module:
                msg = await ctx.send(f"⚠️ Cog `{module_name}` not found in any folder.")
                await asyncio.sleep(5)
                return await msg.delete()

            if f"{module_name}.py" in ignored_files:
                msg = await ctx.send(f"🚫 `{module_name}.py` is ignored and cannot be reloaded.")
                await asyncio.sleep(5)
                return await msg.delete()

            msg = await ctx.send(f"♻️ Reloading `{target_module}`...")

            try:
                await self.bot.reload_extension(target_module)
                embed = discord.Embed(
                    title="✅ Module Reloaded",
                    description=f"`{target_module}` reloaded successfully.",
                    color=discord.Color.green(),
                    timestamp=datetime.now(timezone.utc)
                )
                embed.set_footer(
                    text=f"Reloaded by {ctx.author}",
                    icon_url=ctx.author.display_avatar.url
                )

                await msg.edit(content=None, embed=embed)
                if log_channel:
                    await log_channel.send(embed=embed)
                print(f"♻️  [SYSTEM] Reloaded module: {target_module}")

                await asyncio.sleep(8)
                await msg.delete()

            except Exception as e:
                err = f"❌ Failed to reload `{target_module}`: {e}"
                await msg.edit(content=err)
                if log_channel:
                    await log_channel.send(f"⚠️ {err}")
                print(err)

# =============================
# 🧩 SETUP (Required for Cogs)
# =============================
async def setup(bot):
    await bot.add_cog(ControlBot(bot))
    print("🧱 control_bot.py loaded successfully")