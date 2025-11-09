import discord
import json
from discord.ext import commands
from datetime import datetime, timezone
from manage.permissions import check_perm
from manage.database_manager import add_embed_log, add_normal_log

# --- Load Config ---
with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

bot_data_config = config["BOT_DATA"]
bot_config = config["BOT"]

class Moderator(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ===========================
    # 👢 Kick Command
    # ===========================
    @commands.command(name="kick")
    @check_perm("FULL_ACCESS")
    async def kick_member(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        await ctx.message.delete()
        log_channel = self.bot.get_channel(bot_data_config["LOG_ID"])
        try:
            await member.kick(reason=reason)
            await ctx.send(f"✅ {member.mention} has been kicked. Reason: `{reason}`", delete_after=5)

            embed = discord.Embed(
                title="👢 Member Kicked",
                description=f"{member.mention} was kicked from the server.",
                color=discord.Color.red(),
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="👮 Moderator", value=f"{ctx.author.mention} (`{ctx.author.id}`)", inline=False)
            embed.add_field(name="💬 Reason", value=f"```{reason}```", inline=False)
            embed.set_footer(text=f"User ID: {member.id}", icon_url=ctx.author.display_avatar.url)
            
            add_embed_log(
                title="👢 Member Kicked",
                description=f"{member.mention} was kicked from the server.",
                fields=[
                    {"name": "👮 Moderator", "value": f"{ctx.author.mention} (`{ctx.author.id}`)", "inline": False},
                    {"name": "💬 Reason", "value": reason, "inline": False},
                ],
                footer_text=f"User ID: {member.id}",
                footer_icon=ctx.author.display_avatar.url
            )
            
            await log_channel.send(embed=embed)

        except Exception as e:
            await ctx.send(f"❌ Failed to kick member: `{e}`")

    # ===========================
    # 🔨 Ban Command
    # ===========================
    @commands.command(name="ban")
    @check_perm("FULL_ACCESS")
    async def ban_member(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        await ctx.message.delete()
        log_channel = self.bot.get_channel(bot_data_config["LOG_ID"])
        try:
            await member.ban(reason=reason)
            await ctx.send(f"🚫 {member.mention} has been banned. Reason: `{reason}`", delete_after=5)

            embed = discord.Embed(
                title="🚫 Member Banned",
                description=f"{member.mention} has been banned from the server.",
                color=discord.Color.dark_red(),
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="👮 Moderator", value=f"{ctx.author.mention} (`{ctx.author.id}`)", inline=False)
            embed.add_field(name="💬 Reason", value=f"```{reason}```", inline=False)
            embed.set_footer(text=f"User ID: {member.id}", icon_url=ctx.author.display_avatar.url)

            add_embed_log(
                title="🚫 Member Banned",
                description=f"{member.mention} has been banned from the server.",
                fields=[
                    {"name": "👮 Moderator", "value": f"{ctx.author.mention} (`{ctx.author.id}`)", "inline": False},
                    {"name": "💬 Reason", "value": reason, "inline": False},
                ],
                footer_text=f"User ID: {member.id}",
                footer_icon=ctx.author.display_avatar.url
            )

            await log_channel.send(embed=embed)

        except Exception as e:
            await ctx.send(f"❌ Failed to ban member: `{e}`")

    # ===========================
    # ♻️ Unban Command
    # ===========================
    @commands.command(name="unban")
    @check_perm("FULL_ACCESS")
    async def unban_member(self, ctx, user_id: int):
        await ctx.message.delete()
        log_channel = self.bot.get_channel(bot_data_config["LOG_ID"])
        try:
            user = await self.bot.fetch_user(user_id)
            await ctx.guild.unban(user)
            await ctx.send(f"✅ {user.mention} has been unbanned.", delete_after=5)

            embed = discord.Embed(
                title="♻️ Member Unbanned",
                description=f"{user.mention} has been unbanned.",
                color=discord.Color.green(),
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="👮 Moderator", value=f"{ctx.author.mention} (`{ctx.author.id}`)", inline=False)
            embed.add_field(name="🧾 Action", value="Manual Unban", inline=False)
            embed.set_footer(text=f"User ID: {user.id}", icon_url=ctx.author.display_avatar.url)

            add_embed_log(
                title="♻️ Member Unbanned",
                description=f"{user.mention} has been unbanned.",
                fields=[
                    {"name": "👮 Moderator", "value": f"{ctx.author.mention} (`{ctx.author.id}`)", "inline": False},
                    {"name": "🧾 Action", "value": "Manual Unban", "inline": False},
                ],
                footer_text=f"User ID: {user.id}",
                footer_icon=ctx.author.display_avatar.url
            )

            await log_channel.send(embed=embed)

        except Exception as e:
            await ctx.send(f"❌ Failed to unban: `{e}`")

    # ===========================
    # 🔇 Mute Command
    # ===========================
    @commands.command(name="mute")
    @check_perm("FULL_ACCESS", "ADMIN", "MODERATOR")
    async def mute_member(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        await ctx.message.delete()
        log_channel = self.bot.get_channel(bot_data_config["LOG_ID"])
        mute_role = discord.utils.get(ctx.guild.roles, name="Muted")

        if not mute_role:
            mute_role = await ctx.guild.create_role(name="Muted", reason="Auto-created mute role")
            for channel in ctx.guild.channels:
                await channel.set_permissions(mute_role, send_messages=False, speak=False)

        await member.add_roles(mute_role, reason=reason)
        await ctx.send(f"🔇 {member.mention} has been muted. Reason: `{reason}`", delete_after=5)

        embed = discord.Embed(
            title="🔇 Member Muted",
            description=f"{member.mention} has been muted.",
            color=discord.Color.orange(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="👮 Moderator", value=f"{ctx.author.mention} (`{ctx.author.id}`)", inline=False)
        embed.add_field(name="💬 Reason", value=f"```{reason}```", inline=False)
        embed.set_footer(text=f"User ID: {member.id}", icon_url=ctx.author.display_avatar.url)

        add_embed_log(
            title="🔇 Member Muted",
            description=f"{member.mention} has been muted.",
            fields=[
                {"name": "👮 Moderator", "value": f"{ctx.author.mention} (`{ctx.author.id}`)", "inline": False},
                {"name": "💬 Reason", "value": reason, "inline": False},
            ],
            footer_text=f"User ID: {member.id}",
            footer_icon=ctx.author.display_avatar.url
        )
        
        await log_channel.send(embed=embed)

    # ===========================
    # 🔊 Unmute Command
    # ===========================
    @commands.command(name="unmute")
    @check_perm("FULL_ACCESS", "ADMIN", "MODERATOR")
    async def unmute_member(self, ctx, member: discord.Member):
        await ctx.message.delete()
        log_channel = self.bot.get_channel(bot_data_config["LOG_ID"])
        mute_role = discord.utils.get(ctx.guild.roles, name="Muted")

        if mute_role in member.roles:
            await member.remove_roles(mute_role)
            await ctx.send(f"🔊 {member.mention} has been unmuted.", delete_after=5)

            embed = discord.Embed(
                title="🔊 Member Unmuted",
                description=f"{member.mention} has been unmuted.",
                color=discord.Color.green(),
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="👮 Moderator", value=f"{ctx.author.mention} (`{ctx.author.id}`)", inline=False)
            embed.set_footer(text=f"User ID: {member.id}", icon_url=ctx.author.display_avatar.url)

            add_embed_log(
                title="🔊 Member Unmuted",
                description=f"{member.mention} has been unmuted.",
                fields=[
                    {"name": "👮 Moderator", "value": f"{ctx.author.mention} (`{ctx.author.id}`)", "inline": False},
                ],
                footer_text=f"User ID: {member.id}",
                footer_icon=ctx.author.display_avatar.url
            )
            
            await log_channel.send(embed=embed)
        else:
            await ctx.send("⚠️ User is not muted.", delete_after=5)

    # ===========================
    # ⚠️ Warn Command
    # ===========================
    @commands.command(name="warn")
    @check_perm("FULL_ACCESS", "ADMIN", "MODERATOR")
    async def warn_member(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        await ctx.message.delete()
        log_channel = self.bot.get_channel(bot_data_config["LOG_ID"])

        await ctx.send(f"⚠️ {member.mention} has been warned. Reason: `{reason}`", delete_after=5)

        try:
            await member.send(f"⚠️ You have been warned in **{ctx.guild.name}**.\nReason: `{reason}`")
        except:
            pass

        embed = discord.Embed(
            title="⚠️ Member Warned",
            description=f"{member.mention} received a warning.",
            color=discord.Color.yellow(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="👮 Moderator", value=f"{ctx.author.mention} (`{ctx.author.id}`)", inline=False)
        embed.add_field(name="💬 Reason", value=f"```{reason}```", inline=False)
        embed.set_footer(text=f"User ID: {member.id}", icon_url=ctx.author.display_avatar.url)

        add_embed_log(
            title="⚠️ Member Warned",
            description=f"{member.mention} received a warning.",
            fields=[
                {"name": "👮 Moderator", "value": f"{ctx.author.mention} (`{ctx.author.id}`)", "inline": False},
                {"name": "💬 Reason", "value": reason, "inline": False},
            ],
            footer_text=f"User ID: {member.id}",
            footer_icon=ctx.author.display_avatar.url
        )

        await log_channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Moderator(bot))
    print("🧱 moderator.py loaded successfully")
