import discord
import random
import os, json
import asyncio
from discord.ext import commands
from datetime import datetime, timezone

# Load config
with open("config.json", "r", encoding="utf-8") as f:
    cfg = json.load(f)

bot_config = cfg["BOT"]
bot_data_config = cfg["BOT_DATA"]

WELCOME_CHANNEL_ID = bot_data_config["WELCOME_CHANNEL_ID"]
LEAVE_CHANNEL_ID = bot_data_config["LEAVE_CHANNEL_ID"]

BANNER_URL = "https://www.google.com/url?sa=i&url=https%3A%2F%2Fwww.freepik.com%2Fpremium-vector%2Fbanner-beautiful-rainforest-jungle-landscape-with-lush-foliage-green-colors-vector-illustration_70013490.htm&psig=AOvVaw0WjhYiAa1WUa7Vimvpe4ar&ust=1762446665980000&source=images&cd=vfe&opi=89978449&ved=0CBUQjRxqFwoTCIjiwM2325ADFQAAAAAdAAAAABBe"
BOT_LOGO_URL = "https://cdn.discordapp.com/attachments/your_logo.png"

INVITES_CACHE_PATH = "data/invites_cache.json"
os.makedirs(os.path.dirname(INVITES_CACHE_PATH), exist_ok=True)

WELCOME_MESSAGES = [
    "Welcome {member_mention}! 🎉 We're so glad to have you here at **{server_name}**!",
    "Hey {member_name}, welcome aboard! 🚀 Enjoy your stay in **{server_name}**.",
    "👋 {member_mention} just joined **{server_name}** — make some noise!",
]

LEAVE_MESSAGES = [
    "😢 {member_name} just left **{server_name}**. We'll miss you!",
    "👋 {member_name} has departed from **{server_name}**.",
]

# --------------------------
# COG
# --------------------------
class WelcomeLeave(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    async def update_count(self, guild: discord.Guild):
        """Helper function to update member count."""
        channel = guild.get_channel(1433009610301767753)
        if not channel:
            print(f"⚠️ Channel ID {1433009610301767753} not found in guild {guild.name}")
            return

        total_members = guild.member_count
        new_name = f"🔥・TOTAL: {total_members}"

        try:
            await channel.edit(name=new_name)
            # print(f"✅ Updated member count: {total_members}")
        except discord.Forbidden:
            print("❌ Missing 'Manage Channels' permission for bot.")
        except Exception as e:
            print(f"⚠️ Error updating member count: {e}")

    # --------------------------
    # 🟢 ON READY
    # --------------------------
    @commands.Cog.listener()
    async def on_ready(self):
        pass

    # --------------------------
    # 🟢 MEMBER JOIN
    # --------------------------
    @commands.Cog.listener()
    async def on_member_join(self, member):
        try:
            guild = member.guild
            channel = guild.get_channel(WELCOME_CHANNEL_ID)
            if not channel:
                return

            # prepare embed
            welcome_text = random.choice(WELCOME_MESSAGES).format(
                member_mention=member.mention,
                member_name=member.name,
                server_name=guild.name
            )

            embed = discord.Embed(
                title="🎉 Welcome to the Server!",
                description=welcome_text,
                color=discord.Color.green(),
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="👤 Member", value=f"{member}", inline=True)
            embed.add_field(name="🆔 ID", value=f"`{member.id}`", inline=True)
            embed.add_field(name="📅 Account Created", value=f"<t:{int(member.created_at.timestamp())}:R>", inline=True)
            embed.add_field(name="📈 Member Count", value=f"`{len(guild.members)}`", inline=True)

            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_image(url=BANNER_URL)
            embed.set_footer(text=f"Welcome to {guild.name}!", icon_url=BOT_LOGO_URL)

            await channel.send(embed=embed)
            await self.update_count(member.guild)

        except Exception as e:
            print(f"[ERROR] Welcome message failed: {e}")

    # --------------------------
    # 🔴 MEMBER LEAVE
    # --------------------------
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        try:
            guild = member.guild
            channel = guild.get_channel(LEAVE_CHANNEL_ID)
            if not channel:
                return

            leave_text = random.choice(LEAVE_MESSAGES).format(
                member_name=member.name,
                server_name=guild.name
            )

            embed = discord.Embed(
                title="👋 Member Left",
                description=leave_text,
                color=discord.Color.red(),
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="👤 Member", value=f"{member}", inline=True)
            embed.add_field(name="🆔 ID", value=f"`{member.id}`", inline=True)
            embed.add_field(name="📉 Members Left", value=f"`{len(guild.members)}` members remain", inline=True)
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_image(url=BANNER_URL)
            embed.set_footer(text=f"Goodbye from {guild.name}", icon_url=BOT_LOGO_URL)

            await channel.send(embed=embed)
            await self.update_count(member.guild)

        except Exception as e:
            print(f"[ERROR] Leave message failed: {e}")

async def setup(bot):
    await bot.add_cog(WelcomeLeave(bot))
    print("🧱 welcome_leave.py loaded successfully")
