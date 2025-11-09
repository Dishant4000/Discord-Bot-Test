import discord
import io
import time
import qrcode
import aiohttp
import html
import re
import psutil
import platform
import json, asyncio, os, sys
from discord.ext import commands
from discord import ui
from datetime import datetime, timezone
from manage.permissions import check_perm
from manage.database_manager import load_customers, save_customers

# --- Load Config ---
with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

bot_config = config["BOT"]
bot_data_config = config["BOT_DATA"]
ticket_config = config["TICKET"]

# ✅ Email validation regex
EMAIL_REGEX = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'

class Customers(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name="register")
    async def register(self, ctx, name: str = None, email: str = None):
        """Register yourself as a customer (email optional but must be valid)."""
        
        user = ctx.author

        # ⚠️ Require at least name
        if not name:
            return await ctx.reply("⚠️ Please provide your name.\n**Usage:** `.register <name> [email]`")

        # 🧠 Load data
        customers = load_customers()

        # 🚫 Check if already registered
        if str(user.id) in customers:
            existing = customers[str(user.id)]
            embed = discord.Embed(
                title="🪪 Already Registered",
                description=f"You're already registered as **{existing['name']}**.",
                color=discord.Color.gold()
            )
            embed.add_field(name="📅 Joined", value=f"`{existing['joined']}`", inline=False)
            embed.set_footer(text="You can only register once.")
            return await ctx.reply(embed=embed)

        # 🧾 Validate email if provided
        if email and not re.match(EMAIL_REGEX, email):
            embed = discord.Embed(
                title="❌ Invalid Email Address",
                description="The email you entered is not valid. Please provide a correct email format.\n\n**Example:** `example@gmail.com`",
                color=discord.Color.red()
            )
            return await ctx.reply(embed=embed)

        # ✅ Save registration
        customers[str(user.id)] = {
            "name": name,
            "email": email or "N/A",
            "joined": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "discord_tag": str(user),
            "discord_id": user.id
        }
        save_customers(customers)

        # 🎉 Confirmation embed
        embed = discord.Embed(
            title="✅ Registration Successful",
            description=f"Welcome, **{name}!** 👋 You’re now registered.",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        embed.add_field(name="🪪 Discord", value=user.mention, inline=True)
        embed.add_field(name="📧 Email", value=email or "N/A", inline=True)
        embed.add_field(name="📅 Joined", value=datetime.now().strftime("%B %d, %Y %I:%M %p"), inline=False)

        # 💡 Extra info note
        embed.add_field(
            name="💡 Next Step",
            value="You can view your full information anytime using `.myinfo` 🧾",
            inline=False
        )
        
        embed.set_footer(text=f"User ID: {user.id}", icon_url=user.display_avatar.url)
        await ctx.reply(embed=embed)

    # 👁️ View Info (with smart note)
    @commands.command(name="myinfo")
    async def myinfo(self, ctx):
        """View your registration info."""
        user = ctx.author
        customers = load_customers()
    
        if str(user.id) not in customers:
            return await ctx.reply("❌ You're not registered yet! Use `.register <name> [email]` to register.")
    
        c = customers[str(user.id)]
    
        embed = discord.Embed(
            title="👤 Your Registration Info",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        embed.add_field(name="🪪 Name", value=c['name'], inline=True)
        embed.add_field(name="📧 Email", value=c['email'], inline=True)
        embed.add_field(name="📅 Joined", value=c['joined'], inline=False)
        embed.add_field(name="🆔 Discord ID", value=str(user.id), inline=False)
        embed.set_thumbnail(url=user.display_avatar.url)
    
        # 💡 Smart Note System (depends on email status)
        if c['email'] == "N/A" or not c['email'].strip():
            # 🟥 No email set → Show full note with benefits
            note_text = (
                "💡 **Manage Your Info**\n"
                "You can update your information using these commands:\n"
                "• `.editname <new name>` — Change your name\n"
                "• `.editemail <new email>` — Add your email if not set\n\n"
                "📧 *Adding an email is optional, but recommended!*\n"
                "If you make a purchase, your delivery will be sent via **DM**, and "
                "if your email is added, it will be delivered to **both DM and email** ✅"
            )
        else:
            # 🟩 Email exists → Show short normal note
            note_text = (
                "💡 **Manage Your Info**\n"
                "You can update your information using these commands:\n"
                "• `.editname <new name>` — Change your name\n"
                "• `.editemail <new email>` — Update your email"
            )
    
        embed.add_field(name="🛠️ Account Settings", value=note_text, inline=False)
    
        await ctx.reply(embed=embed)

    # ✏️ Edit Name command
    @commands.command(name="editname")
    async def editname(self, ctx, *, new_name: str = None):
        """Edit your registered name."""
        user = ctx.author
        customers = load_customers()

        if str(user.id) not in customers:
            return await ctx.reply("❌ You are not registered yet! Use `.register <name> [email]` first.")

        if not new_name:
            return await ctx.reply("⚠️ Please provide a new name.\n**Example:** `.editname Dishant`")

        customers[str(user.id)]["name"] = new_name
        save_customers(customers)

        embed = discord.Embed(
            title="✏️ Name Updated Successfully",
            description=f"Your name has been changed to **{new_name}** ✅",
            color=discord.Color.blurple(),
            timestamp=datetime.now()
        )
        embed.set_footer(text=f"Updated by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        await ctx.reply(embed=embed)

    # 📧 Edit Email command
    @commands.command(name="editemail")
    async def editemail(self, ctx, email: str = None):
        """Edit your registered email (must be valid)."""
        user = ctx.author
        customers = load_customers()

        if str(user.id) not in customers:
            return await ctx.reply("❌ You are not registered yet! Use `.register <name> [email]` first.")

        if not email or not re.match(EMAIL_REGEX, email):
            return await ctx.reply("❌ Please provide a valid new email.\n**Example:** `.editemail example@gmail.com`")

        customers[str(user.id)]["email"] = email
        save_customers(customers)

        embed = discord.Embed(
            title="📧 Email Updated Successfully",
            description=f"Your email has been changed to **{email}** ✅",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        embed.set_footer(text=f"Updated by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        await ctx.reply(embed=embed)

async def setup(bot):
    await bot.add_cog(Customers(bot))
    print("🧱 customers.py loaded successfully")