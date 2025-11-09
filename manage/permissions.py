import discord
import json
import os
import asyncio
from discord.ext import commands
from datetime import datetime, timezone

CONFIG_PATH = "config.json"
CONFIG_LOCK = asyncio.Lock()

def read_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

async def write_config(new_cfg):
    async with CONFIG_LOCK:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(new_cfg, f, indent=4, ensure_ascii=False)

def _get_perm_list(cfg, key):
    perms = cfg.get("PERMISSIONS", {})
    return perms.get(key, [])

# ---------------------------
# Helper: permission check factory
# ---------------------------
def check_perm(*levels):
    """
    Returns a predicate usable with @commands.check(...)
    Accepts multiple permission levels, e.g.:
        @check_perm("FULL_ACCESS", "ADMIN")
    """
    levels = [lvl.upper() for lvl in levels]

    def predicate(ctx: commands.Context):
        try:
            cfg = read_config()
            perms = cfg.get("PERMISSIONS", {})

            # Always allow BOT owner and FULL_ACCESS
            owner_id = cfg.get("BOT", {}).get("OWNER_ID")
            if owner_id and ctx.author.id == owner_id:
                return True

            if ctx.author.id in perms.get("FULL_ACCESS", []):
                return True

            # Check if in any allowed level
            for lvl in levels:
                if ctx.author.id in perms.get(lvl, []):
                    return True

            return False
        except Exception:
            return False

    return commands.check(predicate)

# ---------------------------
# Cog: permission management
# ---------------------------
class PermissionManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # -------- helper (internal) ----------
    async def _modify_perm(self, ctx, list_name: str, member_id: int, add: bool):
        try:
            cfg = read_config()
            perms = cfg.setdefault("PERMISSIONS", {})
            # ensure lists exist
            perms.setdefault("FULL_ACCESS", [])
            perms.setdefault("ADMIN", [])
            perms.setdefault("MODERATOR", [])

            # do not allow editing FULL_ACCESS via commands
            if list_name == "FULL_ACCESS":
                return await ctx.send("❌ FULL_ACCESS cannot be modified via command. Edit `config.json` directly.")

            target_list = perms.get(list_name, [])

            if add:
                if member_id in target_list:
                    return await ctx.send(f"⚠️ ID `{member_id}` is already in `{list_name}`.")
                target_list.append(member_id)
                perms[list_name] = target_list
                await write_config(cfg)
                return await ctx.send(f"✅ Added `{member_id}` to `{list_name}`.")
            else:
                if member_id not in target_list:
                    return await ctx.send(f"⚠️ ID `{member_id}` not present in `{list_name}`.")
                target_list.remove(member_id)
                perms[list_name] = target_list
                await write_config(cfg)
                return await ctx.send(f"✅ Removed `{member_id}` from `{list_name}`.")
        except Exception as e:
            await ctx.send(f"❌ Error modifying permissions: `{e}`")

    # -------------------------
    # Management commands
    # Only FULL_ACCESS (or BOT OWNER) can run these
    # -------------------------
    @commands.group(name="perms", invoke_without_command=True)
    @check_perm("FULL_ACCESS")
    async def perms(self, ctx):
        """Permission utilities. Use subcommands: list / add / remove"""
        await ctx.send("⚙️ Use `.perms list` to view or `.perms add <ROLE> <id>` / `.perms remove <ROLE> <id>`.")

    @perms.command(name="list")
    @check_perm("FULL_ACCESS")
    async def perms_list(self, ctx):
        """Show current permission lists (FULL_ACCESS / ADMIN / MODERATOR)"""
        try:
            cfg = read_config()
            perms = cfg.get("PERMISSIONS", {})
            full = perms.get("FULL_ACCESS", [])
            admin = perms.get("ADMIN", [])
            mod = perms.get("MODERATOR", [])

            embed = discord.Embed(
                title="🔐 Permission Lists",
                color=discord.Color.blurple(),
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="👑 FULL_ACCESS (manual - config.json)", value="\n".join(f"`{i}`" for i in full) or "None", inline=False)
            embed.add_field(name="🛡️ ADMIN", value="\n".join(f"`{i}`" for i in admin) or "None", inline=False)
            embed.add_field(name="🔰 MODERATOR", value="\n".join(f"`{i}`" for i in mod) or "None", inline=False)
            embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)

            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ Error reading permissions: `{e}`")

    @perms.command(name="add")
    @check_perm("FULL_ACCESS")
    async def perms_add(self, ctx, role: str = None, member_id: str = None):
        """
        Add an ID to ADMIN or MODERATOR.
        Usage: .perms add ADMIN 123456789012345678
        (FULL_ACCESS cannot be added here)
        """
        if not role or not member_id:
            return await ctx.send("⚠️ Usage: `.perms add <ADMIN|MODERATOR> <user_id>`")

        # role = role.upper()
        if role not in ("ADMIN", "MODERATOR"):
            return await ctx.send("⚠️ Only `ADMIN` or `MODERATOR` can be modified via command.")

        if not member_id.isdigit():
            return await ctx.send("⚠️ Provide a valid numeric user ID.")

        await self._modify_perm(ctx, role, int(member_id), add=True)

    @perms.command(name="remove")
    @check_perm("FULL_ACCESS")
    async def perms_remove(self, ctx, role: str = None, member_id: str = None):
        """
        Remove an ID from ADMIN or MODERATOR.
        Usage: .perms remove MODERATOR 123456789012345678
        """
        if not role or not member_id:
            return await ctx.send("⚠️ Usage: `.perms remove <ADMIN|MODERATOR> <user_id>`")

        role = role.upper()
        if role not in ("ADMIN", "MODERATOR"):
            return await ctx.send("⚠️ Only `ADMIN` or `MODERATOR` can be modified via command.")

        if not member_id.isdigit():
            return await ctx.send("⚠️ Provide a valid numeric user ID.")

        await self._modify_perm(ctx, role, int(member_id), add=False)


async def setup(bot):
    await bot.add_cog(PermissionManager(bot))
    print("🧱 permissions.py loaded successfully")
