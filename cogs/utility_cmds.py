import discord
import io
import time
import qrcode
import math, re
import aiohttp
import requests
import html
import psutil
import platform
import importlib
import traceback
import json, asyncio, os, sys
from discord.ext import commands
from discord import ui
from datetime import datetime, timezone
from manage.permissions import check_perm
from manage.database_manager import add_embed_log, add_normal_log

# ---------- Load Configuration ----------
with open("config.json", "r") as f:
    cfg = json.load(f)

bot_config = cfg["BOT"]
ticket_config = cfg["TICKET"]
bot_data_config = cfg["BOT_DATA"]
payment_methods_config = cfg["PAYMENT_METHODS"]

class UtilityCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        bot.launch_time = time.time()
    
    @commands.command()
    @check_perm("FULL_ACCESS", "ADMIN", "MODERATOR")
    async def ping(self, ctx):
        """Check bot latency"""
        latency = round(self.bot.latency * 1000)  # Convert to ms
    
        # Choose color based on latency
        if latency < 100:
            color = discord.Color.green()
            status = "🟢 Excellent"
        elif latency < 250:
            color = discord.Color.yellow()
            status = "🟡 Good"
        else:
            color = discord.Color.red()
            status = "🔴 Poor"
    
        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"**Latency:** `{latency} ms`\n**Status:** {status}",
            color=color,
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
    
        # Optional: Add a small animation-like touch
        msg = await ctx.send(embed=embed)
        await asyncio.sleep(0.8)
        embed.description = f"**Latency:** `{latency} ms`\n**Status:** {status}\n**Gateway:** ✅ Online"
        await msg.edit(embed=embed)
    
    @commands.command()
    @check_perm("FULL_ACCESS", "ADMIN", "MODERATOR")
    async def status(self, ctx):
        """Show bot system status and stats"""
        current_time = time.time()
        uptime = int(current_time - self.bot.launch_time)
        hours, remainder = divmod(uptime, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{hours}h {minutes}m {seconds}s"
    
        # System info
        cpu_usage = psutil.cpu_percent(interval=1)
        ram_usage = psutil.virtual_memory().percent
        total_ram = round(psutil.virtual_memory().total / (1024 ** 3), 2)
        ping = round(self.bot.latency * 1000)
    
        # Host info
        python_version = platform.python_version()
        discord_version = discord.__version__
    
        embed = discord.Embed(
            title="📊 Bot System Status",
            color=discord.Color.blue(),
            timestamp=datetime.now(timezone.utc)
        )
    
        embed.add_field(name="🏓 Ping", value=f"`{ping} ms`", inline=True)
        embed.add_field(name="🕒 Uptime", value=f"`{uptime_str}`", inline=True)
        embed.add_field(name="⚙️ CPU Usage", value=f"`{cpu_usage}%`", inline=True)
    
        embed.add_field(name="💾 RAM Usage", value=f"`{ram_usage}% of {total_ram} GB`", inline=True)
        embed.add_field(name="🐍 Python Version", value=f"`{python_version}`", inline=True)
        embed.add_field(name="🤖 Discord.py", value=f"`{discord_version}`", inline=True)
    
        embed.add_field(name="📁 Active Guilds", value=f"`{len(self.bot.guilds)}`", inline=True)
        embed.add_field(name="👥 Total Members", value=f"`{sum(g.member_count for g in self.bot.guilds)}`", inline=True)
    
        embed.set_footer(
            text=f"Requested by {ctx.author} • Running on {platform.system()} {platform.release()}",
            icon_url=ctx.author.avatar.url if ctx.author.avatar else None
        )
    
        await ctx.send(embed=embed)
    
    @commands.command(name="uptime")
    @check_perm("FULL_ACCESS", "ADMIN", "MODERATOR")
    async def uptime(self, ctx):
        """Show bot uptime in a professional embed"""
        current_time = time.time()
        uptime_seconds = int(current_time - self.bot.launch_time)
    
        days, remainder = divmod(uptime_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
    
        uptime_str = (
            (f"{days}d " if days else "") +
            (f"{hours}h " if hours else "") +
            (f"{minutes}m " if minutes else "") +
            (f"{seconds}s" if seconds else "")
        )
    
        embed = discord.Embed(
            title="⏱️ Bot Uptime",
            description=f"**I've been running for:** `{uptime_str}`",
            color=discord.Color.green(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_footer(
            text=f"Requested by {ctx.author}",
            icon_url=ctx.author.display_avatar.url
        )
    
        await ctx.send(embed=embed)
    
    @commands.command(name="serverinfo")
    async def serverinfo(self, ctx):
        """
        Display stylish, full-size server info with a premium embed layout.
        """
    
        guild = ctx.guild
        if not guild:
            return await ctx.send("❌ This command can only be used inside a server.")
    
        owner = guild.owner or await self.bot.fetch_user(guild.owner_id)
        icon_url = guild.icon.url if guild.icon else None
        banner_url = guild.banner.url if guild.banner else None
    
        total_members = guild.member_count
        humans = len([m for m in guild.members if not m.bot])
        bots = total_members - humans
    
        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        categories = len(guild.categories)
        roles = len(guild.roles)
        emojis = len(guild.emojis)
        stickers = len(guild.stickers)
        boosts = guild.premium_subscription_count
        boost_tier = guild.premium_tier
        verification = str(guild.verification_level).title().replace("_", " ")
    
        # --- Time ---
        created_date = guild.created_at.strftime("%d %B %Y • %I:%M %p")
        created_relative = f"<t:{int(guild.created_at.timestamp())}:R>"
        now = datetime.now(timezone.utc)
        age_days = (now - guild.created_at).days
    
        # --- Embed base ---
        embed = discord.Embed(
            title=f"{guild.name}",
            description=(
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"**Owner:** {owner.mention}\n"
                f"**Server ID:** `{guild.id}`\n"
                f"**Created On:** {created_date} ({created_relative})\n"
                f"**Server Age:** `{age_days}` days\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=discord.Color.purple(),
            timestamp=datetime.now(timezone.utc)
        )
    
        if icon_url:
            embed.set_thumbnail(url=icon_url)
    
        # 🧩 Overview Section
        embed.add_field(
            name="👥 Members",
            value=(
                f"> 👤 **Total:** `{total_members}`\n"
                f"> 🧍 Humans: `{humans}`\n"
                f"> 🤖 Bots: `{bots}`"
            ),
            inline=True
        )
    
        embed.add_field(
            name="💬 Channels",
            value=(
                f"> 📝 Text: `{text_channels}`\n"
                f"> 🔊 Voice: `{voice_channels}`\n"
                f"> 📂 Categories: `{categories}`"
            ),
            inline=True
        )
    
        embed.add_field(
            name="🎭 Roles / Media",
            value=(
                f"> 🎭 Roles: `{roles}`\n"
                f"> 😄 Emojis: `{emojis}`\n"
                f"> 🎟️ Stickers: `{stickers}`"
            ),
            inline=True
        )
    
        embed.add_field(
            name="🚀 Boost Info",
            value=(
                f"> 💠 Level: `{boost_tier}`\n"
                f"> 💎 Boosts: `{boosts}`\n"
                f"> 🔒 Verification: `{verification}`"
            ),
            inline=False
        )
    
        if banner_url:
            embed.set_image(url=banner_url)
    
        embed.set_footer(
            text=f"Requested by {ctx.author} • {ctx.guild.name}",
            icon_url=ctx.author.display_avatar.url
        )
    
        # Buttons for quick access
        view = discord.ui.View()
        if icon_url:
            view.add_item(discord.ui.Button(label="🖼️ View Icon", url=icon_url))
        if banner_url:
            view.add_item(discord.ui.Button(label="🎨 View Banner", url=banner_url))
    
        await ctx.send(embed=embed, view=view)
    
    # ========== LOCK COMMAND ==========
    @commands.command(name="lock")
    @check_perm("FULL_ACCESS")
    async def lock(self, ctx, channel: discord.TextChannel = None):
        """
        🔒 Lock a text channel so members cannot send messages.
        Usage:
          .lock             -> locks the current channel
          .lock #channel    -> locks the mentioned channel
        """
        await ctx.message.delete()  # delete user’s command message
    
        channel = channel or ctx.channel
        overwrite = channel.overwrites_for(ctx.guild.default_role)
    
        if overwrite.send_messages is False:
            msg = await ctx.send("⚠️ This channel is already locked!")
            return await asyncio.sleep(5) or await msg.delete()
    
        overwrite.send_messages = False
        await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
    
        embed = discord.Embed(
            title="🔒 Channel Locked",
            description=f"{channel.mention} has been locked by {ctx.author.mention}.",
            color=discord.Color.red(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_footer(text=f"Moderator: {ctx.author}", icon_url=ctx.author.display_avatar.url)

        add_embed_log(
            title="🔒 Channel Locked",
            description=f"{channel.mention} has been locked by {ctx.author.mention}.",
            footer_text=f"Moderator: {ctx.author}",
            footer_icon=ctx.author.display_avatar.url
        )
    
        msg = await ctx.send(embed=embed)
        await asyncio.sleep(5)
        await msg.delete()
    
        # Log system
        log_id = bot_data_config["LOG_ID"]
        if log_id:
            log_channel = self.bot.get_channel(log_id)
            if log_channel:
                await log_channel.send(embed=embed)
    
    # ========== UNLOCK COMMAND ==========
    @commands.command(name="unlock")
    @check_perm("FULL_ACCESS")
    async def unlock(self, ctx, channel: discord.TextChannel = None):
        """
        🔓 Unlock a text channel so members can send messages again.
        Usage:
          .unlock             -> unlocks the current channel
          .unlock #channel    -> unlocks the mentioned channel
        """
        await ctx.message.delete()  # delete user’s command message
    
        channel = channel or ctx.channel
        overwrite = channel.overwrites_for(ctx.guild.default_role)
    
        if overwrite.send_messages is None or overwrite.send_messages is True:
            msg = await ctx.send("✅ This channel is already unlocked!")
            return await asyncio.sleep(5) or await msg.delete()
    
        overwrite.send_messages = True
        await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
    
        embed = discord.Embed(
            title="🔓 Channel Unlocked",
            description=f"{channel.mention} has been unlocked by {ctx.author.mention}.",
            color=discord.Color.green(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_footer(text=f"Moderator: {ctx.author}", icon_url=ctx.author.display_avatar.url)

        add_embed_log(
            title="🔓 Channel Unlocked",
            description=f"{channel.mention} has been unlocked by {ctx.author.mention}.",
            footer_text=f"Moderator: {ctx.author}",
            footer_icon=ctx.author.display_avatar.url
        )
    
        msg = await ctx.send(embed=embed)
        await asyncio.sleep(5)
        await msg.delete()
    
        # Log system
        log_id = bot_data_config["LOG_ID"]
        if log_id:
            log_channel = self.bot.get_channel(log_id)
            if log_channel:
                await log_channel.send(embed=embed)
    
    # Rename channel
    @commands.command(name="rename")
    @check_perm("FULL_ACCESS")
    async def rename(self, ctx, *, new_name: str = None):
        """
        ✏️ Rename the current channel.
        Usage:
          .rename <new-name>
        Example:
          .rename general-chat
        """
        await ctx.message.delete()  # instantly delete user message
    
        if not new_name:
            msg = await ctx.send("⚠️ Please provide a new name for this channel.\nExample: `.rename general-chat`")
            await asyncio.sleep(5)
            return await msg.delete()
    
        old_name = ctx.channel.name
    
        try:
            await ctx.channel.edit(name=new_name)
    
            embed = discord.Embed(
                title="✏️ Channel Renamed",
                description=f"**Old Name:** `{old_name}`\n**New Name:** `{new_name}`\n\nRenamed by: {ctx.author.mention}",
                color=discord.Color.gold(),
                timestamp=datetime.now(timezone.utc)
            )
            embed.set_footer(text=f"Moderator: {ctx.author}", icon_url=ctx.author.display_avatar.url)

            add_embed_log(
                title="✏️ Channel Renamed",
                description=f"Old Name: `{old_name}`\nNew Name: `{new_name}`\n\nRenamed by: {ctx.author.mention}",
                footer_text=f"Moderator: {ctx.author}",
                footer_icon=ctx.author.display_avatar.url
            )
    
            msg = await ctx.send(embed=embed)
            await asyncio.sleep(5)
            await msg.delete()
    
            # ✅ Send log update if LOG_ID exists
            log_id = bot_data_config.get("LOG_ID")
            if log_id:
                log_channel = self.bot.get_channel(log_id)
                if log_channel:
                    await log_channel.send(embed=embed)

        except discord.Forbidden:
            msg = await ctx.send("❌ I don't have permission to rename this channel.")
            await asyncio.sleep(5)
            await msg.delete()
        except Exception as e:
            msg = await ctx.send(f"⚠️ Error renaming channel: `{e}`")
            await asyncio.sleep(5)
            await msg.delete()
    
    @commands.command(name="add")
    @check_perm("FULL_ACCESS")
    async def add_user(self, ctx, target: str = None):
        """
        Add a mentioned user or user ID to the current channel.
        Usage:
          .add @user
          .add <user_id>
        """
        if not target:
            return await ctx.send("⚠️ Please mention a user or provide a valid user ID.")
    
        # Resolve user
        user = None
        if ctx.message.mentions:
            user = ctx.message.mentions[0]
        elif target.isdigit():
            try:
                user = await self.bot.fetch_user(int(target))
            except:
                return await ctx.send("❌ Couldn't find that user.")
        else:
            return await ctx.send("⚠️ Invalid input. Mention or use a user ID.")
    
        # Check channel type
        if not isinstance(ctx.channel, (discord.TextChannel, discord.VoiceChannel)):
            return await ctx.send("❌ This command only works in text or voice channels.")
    
        # Update permissions
        try:
            await ctx.channel.set_permissions(user, view_channel=True, send_messages=True)
            embed = discord.Embed(
                title="✅ User Added",
                description=f"{user.mention} has been added to {ctx.channel.mention}",
                color=discord.Color.green(),
                timestamp=datetime.now(timezone.utc)
            )
            embed.set_footer(
                text=f"Added by {ctx.author}",
                icon_url=ctx.author.display_avatar.url
            )

            add_embed_log(
                title="✅ User Added",
                description=f"{user.mention} has been added to {ctx.channel.mention}",
                footer_text=f"Added by {ctx.author}",
                footer_icon=ctx.author.display_avatar.url
            )

            await ctx.send(embed=embed)
    
        except Exception as e:
            await ctx.send(f"⚠️ Couldn't add user: `{e}`")
    
    @commands.command(name="userinfo")
    async def userinfo(self, ctx, target: str = None):
        """
        Show detailed user information for yourself, a mention, or any user ID.
        Usage:
          .userinfo
          .userinfo @user
          .userinfo <user_id>
        """
    
        # --- Resolve Target User ---
        member = None
        user = None
    
        if target is None:
            member = ctx.author if isinstance(ctx.author, discord.Member) else None
            user = ctx.author
        else:
            if ctx.message.mentions:
                member = ctx.message.mentions[0]
                user = member
            elif target.isdigit():
                try:
                    user = await self.bot.fetch_user(int(target))
                    member = ctx.guild.get_member(int(target)) if ctx.guild else None
                except Exception:
                    return await ctx.send("❌ Could not find that user.")
            else:
                return await ctx.send("⚠️ Please mention a user or provide a valid user ID.")
    
        # --- Fetch banner & accent color ---
        banner_url = None
        accent_color = None
        try:
            fetched_user = await self.bot.fetch_user(user.id)
            if fetched_user.banner:
                banner_url = fetched_user.banner.url
            if fetched_user.accent_color:
                accent_color = fetched_user.accent_color
        except:
            pass
    
        # --- Embed base ---
        embed_color = accent_color or discord.Color.blurple()
        embed = discord.Embed(
            title=f"👤 User Info — {user}",
            color=embed_color,
            timestamp=datetime.now(timezone.utc)
        )
    
        # --- Avatar ---
        avatar_url = user.display_avatar.url
        embed.set_thumbnail(url=avatar_url)
        embed.add_field(name="🆔 ID", value=f"`{user.id}`", inline=True)
        embed.add_field(name="📅 Account Created", value=f"<t:{int(user.created_at.timestamp())}:R>", inline=True)
    
        # --- Guild-specific info ---
        if member:
            if member.joined_at:
                embed.add_field(
                    name="📥 Joined Server",
                    value=f"<t:{int(member.joined_at.timestamp())}:R>",
                    inline=True
                )
            embed.add_field(name="🔰 Top Role", value=member.top_role.mention, inline=True)
    
            roles = [r.mention for r in member.roles if r.name != "@everyone"]
            role_text = ", ".join(roles[:15]) if roles else "No roles"
            if len(roles) > 15:
                role_text += f" and {len(roles) - 15} more..."
            embed.add_field(name=f"🎭 Roles ({len(roles)})", value=role_text, inline=False)
    
            # Voice channel
            voice = member.voice.channel.mention if member.voice and member.voice.channel else "Not in a voice channel"
            embed.add_field(name="🔊 Voice", value=voice, inline=False)
    
        else:
            embed.add_field(name="📥 Joined Server", value="Not in this server", inline=True)
    
        # --- Badges (flags) ---
        badges = []
        public_flags = getattr(user, "public_flags", None)
        if public_flags:
            # Staff / Partner / Programs
            if getattr(public_flags, "staff", False): badges.append("👔 Discord Staff")
            if getattr(public_flags, "partner", False): badges.append("🌟 Partner")
            if getattr(public_flags, "certified_moderator", False): badges.append("🛡️ Certified Moderator")
            if getattr(public_flags, "discord_certified_moderator", False): badges.append("🛡️ Certified Moderator (Legacy)")
        
            # HypeSquad Events & Houses
            if getattr(public_flags, "hypesquad", False): badges.append("🎪 HypeSquad Events")
            if getattr(public_flags, "hypesquad_bravery", False): badges.append("🦁 Bravery")
            if getattr(public_flags, "hypesquad_brilliance", False): badges.append("💎 Brilliance")
            if getattr(public_flags, "hypesquad_balance", False): badges.append("⚖️ Balance")
        
            # Bug Hunter
            if getattr(public_flags, "bug_hunter_level_1", False): badges.append("🐞 Bug Hunter Lvl 1")
            if getattr(public_flags, "bug_hunter_level_2", False): badges.append("🐛 Bug Hunter Lvl 2")
        
            # Early supporter / developer / bot / verified
            if getattr(public_flags, "early_supporter", False): badges.append("🎉 Early Supporter")
            if getattr(public_flags, "verified_bot", False): badges.append("🤖 Verified Bot")
            if getattr(public_flags, "verified_developer", False): badges.append("👨‍💻 Verified Developer")
            if getattr(public_flags, "bot_http_interactions", False): badges.append("🛰️ Application Command Bot")
            if getattr(public_flags, "active_developer", False): badges.append("⚙️ Active Developer")
        
            # Misc. older or hidden flags
            if getattr(public_flags, "team_user", False): badges.append("👥 Team User")
            if getattr(public_flags, "system", False): badges.append("🧠 Discord System")
            if getattr(public_flags, "spammer", False): badges.append("🚫 Spammer (Flagged)")
            if getattr(public_flags, "premium_discriminator", False): badges.append("💠 Nitro Discriminator")
        
        embed.add_field(
            name="🏅 Badges",
            value=", ".join(badges) if badges else "No public badges found",
            inline=False
        )
    
        # --- Banner Image (if available) ---
        if banner_url:
            embed.set_image(url=banner_url)
    
        embed.set_footer(
            text=f"Requested by {ctx.author}",
            icon_url=ctx.author.display_avatar.url
        )
    
        # --- Buttons ---
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Open Avatar", url=avatar_url))
        if banner_url:
            view.add_item(discord.ui.Button(label="Open Banner", url=banner_url))
    
        await ctx.send(embed=embed, view=view)
    
    @commands.command()
    @check_perm("FULL_ACCESS")
    async def clear(self, ctx, amount: str = None):
        """Clear messages with temporary confirmation and permanent log"""
        if amount is None:
            await ctx.send("⚠️ Please provide a number or type `.clear all` to delete everything.")
            return
    
        # Detect 'all' keyword
        if amount.lower() == "all":
            limit = None  # None = delete all possible messages
        else:
            try:
                amount = int(amount)
                if amount <= 0:
                    await ctx.send("⚠️ Please enter a positive number.")
                    return
                limit = amount + 1
            except ValueError:
                await ctx.send("❌ Invalid input. Use a number or 'all'. Example: `.clear 20` or `.clear all`")
                return
    
        moderator = ctx.author
        channel = ctx.channel
    
        # Delete messages
        deleted = await channel.purge(limit=limit)
    
        # Temporary confirmation embed (5 sec)
        confirm_embed = discord.Embed(
            title="🧹 Messages Cleared",
            description=f"Deleted `{len(deleted) - 1 if limit else 'all'}` messages by {moderator.mention}.",
            color=discord.Color.green(),
            timestamp=datetime.now(timezone.utc)
        )
        confirm_embed.add_field(name="Channel", value=channel.mention, inline=True)
        confirm_embed.set_footer(text=f"Requested by {moderator}", icon_url=moderator.avatar.url if moderator.avatar else None)
    
        confirmation = await ctx.send(embed=confirm_embed)
        await asyncio.sleep(5)
        await confirmation.delete()
    
        # Permanent log embed
        log_embed = discord.Embed(
            title="🧾 Message Clear Log",
            color=discord.Color.orange(),
            timestamp=datetime.now(timezone.utc)
        )
        log_embed.add_field(name="Moderator", value=f"{moderator.mention} (`{moderator}`)", inline=True)
        log_embed.add_field(name="Channel", value=channel.mention, inline=True)
        log_embed.add_field(name="Messages Deleted", value=f"{len(deleted) - 1 if limit else 'All'}", inline=True)
        log_embed.set_footer(text=f"Cleared at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")

        add_embed_log(
            title="🧾 Message Clear Log",
            fields=[
                {"name": "Moderator", "value": f"{moderator.mention} (`{moderator}`)", "inline": True},
                {"name": "Channel", "value": channel.mention, "inline": True},
                {"name": "Messages Deleted", "value": f"{len(deleted) - 1 if limit else 'All'}", "inline": True}
            ],
            footer_text=f"Cleared at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
            footer_icon=ctx.author.display_avatar.url
        )
    
        # Send log to configured channel
        log_channel_id = bot_data_config["LOG_ID"]
        if log_channel_id:
            log_channel = self.bot.get_channel(log_channel_id)
            if log_channel:
                await log_channel.send(embed=log_embed)
    
    @commands.command()
    async def qr(self, ctx, amount: float = None):
        """Generate your UPI QR code (optionally with an amount)"""
        upi_id = payment_methods_config["UPI"]
    
        if not upi_id:
            await ctx.send("⚠️ UPI ID is missing in config.json.")
            return
    
        # ✅ Build UPI Payment Link
        if amount:
            upi_link = f"upi://pay?pa={upi_id}&pn={ctx.author.name}&am={amount}&cu=INR"
            title = f"💰 Pay ₹{amount:.2f}"
            desc = f"Scan to pay ₹{amount:.2f} via UPI\n**UPI ID:** `{upi_id}`"
        else:
            upi_link = f"upi://pay?pa={upi_id}&pn={ctx.author.name}&cu=INR"
            title = "💳 UPI Payment QR"
            desc = f"Scan this QR to send payments securely.\n**UPI ID:** `{upi_id}`"
    
        # 🧾 Generate QR
        qr_img = qrcode.make(upi_link)
        img_bytes = io.BytesIO()
        qr_img.save(img_bytes, format="PNG")
        img_bytes.seek(0)
    
        # 🎨 Create Embed
        embed = discord.Embed(
            title=title,
            description=desc,
            color=discord.Color.blurple(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
    
        file = discord.File(img_bytes, filename="upi_qr.png")
        embed.set_image(url="attachment://upi_qr.png")
    
        # Send the QR Embed
        await ctx.send(embed=embed, file=file)
    
    # ===========================
    # 💌 DM Command
    # ===========================
    @commands.command(name="dm")
    @check_perm("FULL_ACCESS")
    async def dm_member(self, ctx, member: discord.Member = None, *, message: str = None):
        """Send a private DM to a user"""
        try:
            await ctx.message.delete()
        except (discord.NotFound, discord.Forbidden):
            pass  # message already deleted or no permission
        except Exception as e:
            print(f"⚠️ Message delete failed: {e}", delete_after=5)

        log_channel = self.bot.get_channel(bot_data_config["LOG_ID"])

        # Validation
        if not member or not message:
            return await ctx.send("⚠️ Usage: `.dm @user <message>`", delete_after=5)

        try:
            # 📩 Send DM to member
            embed_dm = discord.Embed(
                title=f"📩 Message from Server ({ctx.guild.name})",
                description=message,
                color=discord.Color.blurple(),
                timestamp=datetime.now(timezone.utc)
            )
            embed_dm.set_footer(text=f"Sent by {ctx.author}", icon_url=ctx.author.display_avatar.url)
            await member.send(embed=embed_dm)

            # ✅ Confirmation to command user
            await ctx.send(f"✅ Message successfully sent to {member.mention}", delete_after=5)

            # 🧾 Log the DM action
            embed_log = discord.Embed(
                title="📤 DM Sent to User",
                color=discord.Color.blue(),
                timestamp=datetime.now(timezone.utc)
            )
            embed_log.add_field(name="👤 Recipient", value=f"{member.mention} (`{member.id}`)", inline=False)
            embed_log.add_field(name="👮 Sent by", value=f"{ctx.author.mention} (`{ctx.author.id}`)", inline=False)
            embed_log.add_field(name="💬 Message", value=f"```{message}```", inline=False)
            embed_log.set_footer(text="Direct message sent", icon_url=ctx.author.display_avatar.url)

            add_embed_log(
                title="📤 DM Sent to User",
                fields=[
                    {"name": "👤 Recipient", "value": f"{member.mention} (`{member.id}`)", "inline": True},
                    {"name": "👮 Sent by", "value": f"{ctx.author.mention} (`{ctx.author.id}`)", "inline": True},
                    {"name": "💬 Message", "value": message, "inline": True}
                ],
                footer_text="Direct message sent",
                footer_icon=ctx.author.display_avatar.url
            )

            await log_channel.send(embed=embed_log)

        except discord.Forbidden:
            await ctx.send("❌ I can't send DM to that user (maybe DMs are closed).", delete_after=5)
        except Exception as e:
            await ctx.send(f"❌ Error sending DM: `{e}`", delete_after=5)
    
    @commands.command(name="calc", aliases=["calculator"])
    async def calc(self, ctx, *, expression: str):
        """Smart calculator that supports +, -, *, /, %, and parentheses"""
        try:
            await ctx.message.delete()
        except (discord.NotFound, discord.Forbidden):
            pass  # message already deleted or no permission
        except Exception as e:
            print(f"⚠️ Message delete failed: {e}", delete_after=5)

        # Clean expression
        expr = expression.replace(" ", "")

        # ✅ Handle percentages like "20+10%" or "100-25%"
        expr = re.sub(r'(\d+)([\+\-])(\d+)%', lambda m: f"{m.group(1)}{m.group(2)}({m.group(1)}*{float(m.group(3))/100})", expr)

        try:
            # ⚠️ Safe eval environment
            allowed_names = {k: v for k, v in math.__dict__.items() if not k.startswith("__")}
            result = eval(expr, {"__builtins__": {}}, allowed_names)

            embed = discord.Embed(
                title="🧮 Calculator",
                color=discord.Color.gold()
            )
            embed.add_field(name="📥 Expression", value=f"```{expression}```", inline=False)
            embed.add_field(name="📤 Result", value=f"```{result}```", inline=False)
            embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)

            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"❌ Error evaluating expression: `{e}`")
    
    @commands.command(name="market")
    @check_perm("FULL_ACCESS")
    async def market(self, ctx, symbol: str):
        """
        Get price of a crypto or fiat currency in INR and USD.
        Example:
        .price ltc
        .price btc
        .price usd
        .price inr
        """

        try:
            await ctx.message.delete()
        except (discord.NotFound, discord.Forbidden):
            pass  # message already deleted or no permission
        except Exception as e:
            print(f"⚠️ Message delete failed: {e}", delete_after=5)
        
        # log_channel = self.bot.get_channel(bot_data_config.get("LOG_ID"))

        # 🌍 Supported fiat currencies (for base rates)
        FIAT_CURRENCIES = ["usd", "inr", "eur", "gbp", "jpy", "aud", "cad", "rub", "cny", "krw", "brl"]
     
        # 🔄 Common crypto symbol-to-ID map (you can expand this anytime)
        COIN_MAP = {
            "btc": "bitcoin",
            "eth": "ethereum",
            "ltc": "litecoin",
            "bnb": "binancecoin",
            "xrp": "ripple",
            "doge": "dogecoin",
            "ada": "cardano",
            "sol": "solana",
            "trx": "tron",
            "dot": "polkadot",
            "bch": "bitcoin-cash",
            "matic": "polygon",
            "shib": "shiba-inu",
            "avax": "avalanche-2",
            "us": "usd",
        }

        symbol = symbol.lower()

        # 🔁 Auto map symbol → full name
        coin_id = COIN_MAP.get(symbol, symbol)

        try:
            # 🪙 Try fetching from CoinGecko API
            url = "https://api.coingecko.com/api/v3/simple/price"

            # Direct query (handles both fiat and crypto)
            params = {"ids": coin_id, "vs_currencies": "usd,inr"}
            response = requests.get(url, params=params, timeout=10)

            if response.status_code != 200:
                raise ValueError(f"API error ({response.status_code})")

            data = response.json()
            price_data = data.get(coin_id)

            if not price_data:
                # Check if it's fiat (like USD or INR)
                if symbol in FIAT_CURRENCIES:
                    fx_url = f"https://api.exchangerate.host/latest?base={symbol.upper()}&symbols=USD,INR"
                    fx_data = requests.get(fx_url, timeout=10).json()
                    price_data = {
                        "usd": fx_data["rates"].get("USD"),
                        "inr": fx_data["rates"].get("INR")
                    }
                else:
                    raise ValueError("❌ Invalid symbol or unsupported currency")

            price_usd = price_data.get("usd", "N/A")
            price_inr = price_data.get("inr", "N/A")

            # 🧾 Embed
            embed = discord.Embed(
                title=f"💰 {symbol.upper()} Price",
                color=discord.Color.gold(),
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="🇺🇸 USD", value=f"`{price_usd:,.2f}`", inline=True)
            embed.add_field(name="🇮🇳 INR", value=f"`{price_inr:,.2f}`", inline=True)
            embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)

            await ctx.send(embed=embed)

            # # 🪵 Optional log
            # if log_channel:
            #     log_embed = discord.Embed(
            #         title="📊 Price Checked",
            #         color=discord.Color.blurple(),
            #         timestamp=datetime.now(timezone.utc)
            #     )
            #     log_embed.add_field(name="User", value=f"{ctx.author.mention} (`{ctx.author.id}`)", inline=False)
            #     log_embed.add_field(name="Symbol", value=f"`{symbol.upper()}`", inline=True)
            #     log_embed.add_field(name="USD", value=f"`{price_usd:,.2f}`", inline=True)
            #     log_embed.add_field(name="INR", value=f"`{price_inr:,.2f}`", inline=True)
            #     await log_channel.send(embed=log_embed)

        except Exception as e:
            await ctx.send(f"❌ Error: {e}")
    
    @commands.command(name="resetlogs", aliases=["deletelogs", "reset_logs", "resetlog", "delete_log"])
    @check_perm("FULL_ACCESS")
    async def resetlogs(self, ctx):
        """Delete all logs from logs_database.json safely"""
        file_path = "data/database/logs_database.json"

        if not os.path.exists(file_path):
            await ctx.reply("⚠️ No logs file found to reset.")
            return

        try:
            # Optional: create backup before delete
            import shutil
            backup_path = file_path.replace(".json", "_backup.json")
            shutil.copy(file_path, backup_path)

            # Reset logs
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump({"global": []}, f, indent=2, ensure_ascii=False)

            # Success embed
            embed = discord.Embed(
                title="🧹 Logs Reset Successful",
                description=f"All logs have been cleared by **{ctx.author}**",
                color=discord.Color.red(),
                timestamp=datetime.now(timezone.utc)
            )
            embed.set_footer(text=f"Logs cleared by {ctx.author}", icon_url=ctx.author.display_avatar.url)
            await ctx.reply(embed=embed)

            # Save to logs_database.json for dashboard
            add_embed_log(
                title="🧹 Logs Reset",
                description=f"All logs were reset by {ctx.author} ({ctx.author.id})",
                footer_text=f"Cleared by {ctx.author}",
                footer_icon=ctx.author.display_avatar.url
            )

        except Exception as e:
            await ctx.reply(f"❌ Error while resetting logs: `{e}`")
    
# ---- Setup function for main.py ----
async def setup(bot):
    await bot.add_cog(UtilityCommands(bot))
    print("🧱 utility_cmds.py loaded successfully")