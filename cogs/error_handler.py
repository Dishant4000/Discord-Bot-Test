import discord
import traceback
import sys
import io
import textwrap
from discord.ext import commands
from datetime import datetime, timezone
from manage.permissions import check_perm

class ErrorHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ======================================
    # 🔥 GLOBAL ERROR HANDLER
    # ======================================
    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: Exception):
        """Global error catcher for all commands."""
        # Ignore certain harmless errors
        if isinstance(error, commands.CommandNotFound):
            return  await ctx.send(f"⚠️ Command: `{ctx.message.content}` not found.", delete_after=6)
        if isinstance(error, commands.CheckFailure):
            return await ctx.send("🚫 You don't have permission to use this command.", delete_after=6)
        if isinstance(error, commands.MissingRequiredArgument):
            return await ctx.send(f"⚠️ Missing argument: `{error.param.name}`", delete_after=6)

        # Clean original error
        error = getattr(error, "original", error)

        # ========== 🖥️ LOG TO CONSOLE ==========
        print("\n" + "=" * 80)
        print(f"❌ [ERROR] Command: {ctx.command}")
        print(f"👤 User: {ctx.author} ({ctx.author.id}) | Channel: #{ctx.channel}")
        print(f"🕒 Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print("-" * 80)
        traceback.print_exception(type(error), error, error.__traceback__, file=sys.stdout)
        print("=" * 80 + "\n")

        # ========== 🧠 FRIENDLY DISCORD EMBED ==========
        err_text = "".join(traceback.format_exception(type(error), error, error.__traceback__))
        short_err = textwrap.shorten(err_text, width=300, placeholder="...")

        embed = discord.Embed(
            title="⚠️ Command Error",
            description=(
                f"**Command:** `{ctx.command}`\n"
                f"**User:** {ctx.author.mention}\n\n"
                f"```py\n{short_err}\n```"
            ),
            color=discord.Color.red(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_footer(text="Ninja Official Error Handler")

        # Send error embed (and auto-delete after some time)
        try:
            await ctx.send(embed=embed, delete_after=15)
        except discord.Forbidden:
            pass  # ignore if bot can't send in this channel

        # Optionally log to a Discord log channel if set in config
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                cfg = __import__("json").load(f)
            log_id = cfg["BOT_DATA"].get("ERROR_LOG")
            if log_id:
                log_ch = self.bot.get_channel(int(log_id))
                if log_ch:
                    await log_ch.send(embed=embed)
        except Exception:
            pass  # avoid recursive error


# ======================================
# ✅ Setup
# ======================================
async def setup(bot):
    await bot.add_cog(ErrorHandler(bot))
    print("🧱 error_handler.py loaded successfully")
