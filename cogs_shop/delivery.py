import discord
import asyncio
import json
import requests
from datetime import datetime, timezone, timedelta
from discord.ext import commands
from manage.permissions import check_perm
from manage.database_manager import (
    load_orders_db, save_orders_db, get_all_products,
    load_receive_ltc_db, save_products_db, get_product, add_embed_log, add_normal_log
)

# --- Load Config ---
with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

bot_data_config = config["BOT_DATA"]
nowpayments_config = config["NOWPAYMENTS"]

NOWPAYMENTS_API_KEY = "PBFG6PX-CKKMVZE-HDGWVCS-7QSFJ41"
NOWPAYMENTS_STATUS_URL = "https://api-sandbox.nowpayments.io/v1/payment/"

# save in database table
save_pending_delivery_orders = "pending_delivery_orders"
save_pending_payment_orders = "pending_payment_orders"

# Indian Time Helper
def india_time():
    return datetime.now(timezone(timedelta(hours=5, minutes=30)))

class Delivery(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ============================================================
    # 📦 .delivery <user> <item_name> <delivery_details>
    # ============================================================
    @commands.command(name="delivery")
    @check_perm("FULL_ACCESS")
    async def deliver_item(self, ctx, member: discord.Member = None, item_name: str = None, *, delivery_details: str = None):
        """Manually deliver an order/item to a user via DM."""
        await ctx.message.delete()

        if not member or not item_name or not delivery_details:
            return await ctx.send("⚠️ Usage: `.delivery <user> <item_name> <details>`")

        # Delivery Embed
        embed = discord.Embed(
            title="📦 Your Order Has Been Delivered!",
            description="Thank you for shopping with us ❤️\n\n🕓 *Your order has been successfully delivered.*",
            color=discord.Color.green(),
            timestamp=india_time()
        )

        embed.add_field(name="📦 Product", value=f"`{item_name}`", inline=True)
        embed.add_field(name="📅 Date", value=f"`{india_time().strftime('%Y-%m-%d - %I:%M:%S%p')}`", inline=False)
        embed.add_field(name="🎁 Delivery Details", value=f"```{delivery_details}```", inline=False)
        embed.set_footer(text="Enjoy your product!", icon_url=ctx.author.display_avatar.url)

        try:
            await member.send(embed=embed)
            await ctx.send(f"✅ Successfully delivered **{item_name}** to {member.mention}.", delete_after=5)
        except Exception as e:
            await ctx.send(f"⚠️ Could not DM {member.mention}. They might have DMs disabled.\n`{e}`")

        # Log delivery
        log_channel = self.bot.get_channel(bot_data_config.get("LOG_ID"))
        if log_channel:
            log_embed = discord.Embed(
                title="📬 New Delivery Made",
                color=discord.Color.blurple(),
                timestamp=india_time()
            )
            log_embed.add_field(name="👤 Delivered To", value=f"{member} (`{member.id}`)", inline=False)
            log_embed.add_field(name="🎁 Item", value=f"`{item_name}`", inline=True)
            log_embed.add_field(name="📦 Delivered By", value=f"{ctx.author}", inline=True)
            log_embed.add_field(name="📝 Details", value=f"```{delivery_details}```", inline=False)
            log_embed.set_footer(text=f"Delivery logged at {india_time().strftime('%I:%M:%S %p')}")

            add_embed_log(
                title="📬 New Delivery Made",
                fields=[
                    {"name": "👤 Delivered To", "value": f"{member} (`{member.id}`)", "inline": True},
                    {"name": "🎁 Item", "value": f"{item_name}", "inline": True},
                    {"name": "📦 Delivered By", "value": f"{ctx.author}", "inline": True},
                    {"name": "📝 Details", "value": delivery_details, "inline": True}
                    ],
                footer_text=f"Delivery logged at {india_time().strftime('%I:%M:%S %p')}",
                footer_icon=ctx.author.display_avatar.url
            )
            
            await log_channel.send(embed=log_embed)
    
    # ============================================================
    # 📦 .pending_orders
    # ============================================================
    @commands.command(name="pending_orders", aliases=["pendingdelivery", "pdorders", "pdo", "deliverypending"])
    @check_perm("FULL_ACCESS")
    async def view_pending_delivery_orders(self, ctx):
        """View all pending delivery orders (admin only)."""
        await ctx.message.delete()

        db = load_orders_db()
        pending_orders = db.get("pending_delivery_orders", {})

        if not pending_orders:
            return await ctx.send("✅ There are no pending deliveries right now — everything's delivered!", delete_after=5)

        embed = discord.Embed(
            title="📦 Pending Deliveries",
            description="Below are all orders that have been **paid** but not **delivered** yet 🚚\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            color=discord.Color.gold(),
            timestamp=datetime.now(timezone(timedelta(hours=5, minutes=30)))
        )

        # Add each order with visual separation
        for order_id, order in pending_orders.items():
            user_mention = f"<@{order['user_id']}>"
            user_name = order.get("user_name", "Unknown User")
            item = order.get("item", "Unknown Item")
            amount = order.get("amount", 0.0)
            status = order.get("status", "Unknown")
            date = order.get("timestamp", "N/A")

            # Each order block
            order_block = (
                f"🆔 **Order ID:** `{order_id}` — **{status}**\n"
                f"👤 **User:** {user_mention} (`{user_name}`)\n"
                f"🎁 **Item:** `{item}`\n"
                f"💰 **Price:** `${amount}`\n"
                f"📅 **Date:** `{date}`\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            )

            embed.add_field(name="\u200b", value=order_block, inline=False)

        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)
    
    # ============================================================
    # ❌ .delete_pending_order <order_id>
    # ============================================================
    @commands.command(name="delete_pending_order", aliases=["delpending", "dpo", "delete_pendingorder", "deletependingorder", "dpendingorder", "delete_po"])
    @check_perm("FULL_ACCESS")
    async def delete_pending_order(self, ctx, order_id: str = None):
        """Delete a specific pending delivery order."""
        await ctx.message.delete()

        if not order_id:
            return await ctx.send("⚠️ Usage: `.delete_pending_order <order_id>`")

        db = load_orders_db()
        pending_orders = db.get("pending_delivery_orders", {})

        if order_id not in pending_orders:
            return await ctx.send(f"❌ Pending order `{order_id}` not found.")

        # Remove the order
        del pending_orders[order_id]
        db["pending_delivery_orders"] = pending_orders
        save_orders_db(db)

        # Confirmation embed
        embed = discord.Embed(
            title="🗑️ Pending Order Deleted",
            description=f"✅ Successfully removed order `{order_id}` from pending deliveries.",
            color=discord.Color.red(),
            timestamp=datetime.now(timezone(timedelta(hours=5, minutes=30)))
        )
        embed.set_footer(text=f"Deleted by {ctx.author}", icon_url=ctx.author.display_avatar.url)

        await ctx.send(embed=embed)

        # Optional logging
        log_channel = self.bot.get_channel(bot_data_config.get("LOG_ID"))
        if log_channel:
            log_embed = discord.Embed(
                title="📦 Pending Order Deleted (Log)",
                color=discord.Color.dark_red(),
                timestamp=datetime.now(timezone(timedelta(hours=5, minutes=30)))
            )
            log_embed.add_field(name="🧾 Order ID", value=f"`{order_id}`", inline=False)
            log_embed.add_field(name="🧑 Deleted By", value=f"{ctx.author} (`{ctx.author.id}`)", inline=False)
            log_embed.set_footer(text="Action logged automatically")
            await log_channel.send(embed=log_embed)

async def setup(bot):
    await bot.add_cog(Delivery(bot))
    print("🧱 delivery.py loaded successfully")
