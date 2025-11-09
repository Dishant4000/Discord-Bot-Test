import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import asyncio
import re
import json
import os

# --- Load Config ---
with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

OWNER_IDS = config["BOT"]["OWNER_ID"]
LOG_CHANNEL_ID = config["BOT_DATA"]["LOG_ID"]

INVITE_REGEX = re.compile(r"(?:discord\.gg/|discord\.com/invite/)", re.IGNORECASE)
MENTION_REGEX = re.compile(r"@everyone|@here")

ban_kick_tracker = defaultdict(list)
delete_tracker = defaultdict(list)
lock = asyncio.Lock()

class Security(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cleaner.start()

    def cog_unload(self):
        self.cleaner.cancel()

    # cleanup old logs every 15 min
    @tasks.loop(minutes=15)
    async def cleaner(self):
        now = datetime.now(timezone.utc)
        for tracker in (ban_kick_tracker, delete_tracker):
            for k in list(tracker.keys()):
                tracker[k] = [t for t in tracker[k] if now - t < timedelta(minutes=10)]

    def is_owner(self, user: discord.User):
        return user.id in OWNER_IDS

    async def log(self, guild, embed: discord.Embed):
        channel = guild.get_channel(LOG_CHANNEL_ID)
        if channel:
            await channel.send(embed=embed)

    # --- EVENT: Ban / Kick tracking ---
    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
            executor = entry.user
            if executor.bot or self.is_owner(executor):
                return
            await self.handle_violation(guild, executor, "ban")

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        # For kicks
        guild = member.guild
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.kick):
            executor = entry.user
            if executor.bot or self.is_owner(executor):
                return
            await self.handle_violation(guild, executor, "kick")

    # --- EVENT: Channel deletion tracking ---
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        guild = channel.guild
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
            executor = entry.user
            if executor.bot or self.is_owner(executor):
                return
            await self.handle_violation(guild, executor, "channel_delete")
            # optional: restore deleted channel
            await guild.create_text_channel(name=channel.name, category=channel.category)

    # --- EVENT: Block invite or mass mention ---
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or self.is_owner(message.author):
            return

        if INVITE_REGEX.search(message.content):
            await message.delete()
            await message.channel.send(
                f"🚫 {message.author.mention} you can't send invite links.",
                delete_after=6
            )
            await self.log_violation(message.guild, message.author, "Invite Link Blocked")

        elif MENTION_REGEX.search(message.content):
            await message.delete()
            await message.channel.send(
                f"🚫 {message.author.mention} mass mentions are not allowed.",
                delete_after=6
            )
            await self.log_violation(message.guild, message.author, "Mass Mention Blocked")

    # --- Handle violations ---
    async def handle_violation(self, guild, user, action):
        async with lock:
            now = datetime.now(timezone.utc)
            tracker = ban_kick_tracker if action in ("ban", "kick") else delete_tracker
            tracker[user.id].append(now)

            count = len([t for t in tracker[user.id] if now - t < timedelta(minutes=10)])
            limit = 1  # 1 action per 10 min

            if count > limit:
                try:
                    for role in user.roles[1:]:
                        await user.remove_roles(role, reason="Anti-nuke triggered")
                    await user.timeout(duration=timedelta(hours=1))
                except Exception:
                    pass

                embed = discord.Embed(
                    title="🚨 Anti-Nuke Triggered",
                    description=f"**User:** {user.mention}\n**Action:** {action}\n**Punishment:** Roles removed + Timeout 1 hr",
                    color=discord.Color.red(),
                    timestamp=now,
                )
                await self.log(guild, embed)

    async def log_violation(self, guild, user, reason):
        embed = discord.Embed(
            title="🚫 Security Violation",
            description=f"**User:** {user.mention}\n**Reason:** {reason}",
            color=discord.Color.orange(),
            timestamp=datetime.now(timezone.utc),
        )
        await self.log(guild, embed)


async def setup(bot):
    await bot.add_cog(Security(bot))
    print("🧱 security.py loaded successfully")
