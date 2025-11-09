import discord, json, os
from datetime import datetime, timezone, timedelta
from discord.ext import commands
from manage.permissions import check_perm
from manage.database_manager import add_embed_log, add_normal_log

def india_time():
    return datetime.now(timezone(timedelta(hours=5, minutes=30)))

class Update(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="update_serverinfo")
    @check_perm("FULL_ACCESS", "ADMIN")
    async def update_serverinfo(self, ctx):
        """🔄 Update server info data into server_database.json"""
        await ctx.message.delete()
        servers_data = {}
        total_members = 0

        for guild in self.bot.guilds:
            total_members += guild.member_count
            servers_data[str(guild.id)] = {
                "name": guild.name,
                "id": str(guild.id),
                "owner": str(guild.owner),
                "owner_id": str(guild.owner.id) if guild.owner else None,
                "member_count": guild.member_count,
                "channels": len(guild.channels),
                "roles": len(guild.roles),
                "boost_level": guild.premium_tier,
                "boost_count": guild.premium_subscription_count,
                "created_at": guild.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "icon_url": guild.icon.url if guild.icon else None
            }

        db_path = "data/database/server_database.json"
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        # Load or create new JSON
        if os.path.exists(db_path):
            with open(db_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {"SERVERINFO": {}}

        data["SERVERINFO"] = {
            "total_servers": len(self.bot.guilds),
            "total_members": total_members,
            "servers": servers_data,
            "last_updated": india_time().strftime("%Y-%m-%d %H:%M:%S")
        }

        with open(db_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

        embed = discord.Embed(
            title="✅ Server Info Updated",
            description=(
                f"**Total Servers:** `{len(self.bot.guilds)}`\n"
                f"**Total Members:** `{total_members}`\n\n"
                f"📦 Data saved to `server_database.json`"
            ),
            color=discord.Color.green(),
            timestamp=india_time()
        )
        embed.set_footer(text=f"Updated by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Update(bot))
    print("🧱 update.py loaded successfully")
