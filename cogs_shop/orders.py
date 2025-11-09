import discord
import asyncio
import json
import requests
from datetime import datetime, timezone, timedelta
from discord.ext import commands
from manage.permissions import check_perm
from manage.database_manager import (
    load_orders_db, save_orders_db, get_all_products,
    load_receive_ltc_db, save_products_db, get_product, add_normal_log, add_embed_log, load_customers
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


class Orders(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ============================================================
    # 🛒 .buy <product_name>
    # ============================================================
    @commands.command(name="buy", aliases=["purchase"])
    async def buy_product(self, ctx, *, product_name: str = None):
        """Buy a product from the shop and generate LTC payment."""

        if not product_name:
            return await ctx.reply("🛒 Please specify the item you want to buy.\nExample: `.buy Nitro`")
        
        customers = load_customers()

        # ✅ Check registration
        if str(ctx.author.id) not in customers:
            embed = discord.Embed(
                title="⚠️ Registration Required",
                description=(
                    "Before making a purchase, you need to **register your account.**\n\n"
                    "📝 Use this command to register:\n"
                    "```bash\n.register <name> [email]\n```\n"
                    "📧 *Email is optional, but if you add it, your purchased item will be delivered to both "
                    "**DM and your email**.*"
                ),
                color=discord.Color.gold(),
                timestamp=datetime.now()
            )
            embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
            embed.set_footer(text="You must register before buying.")
            return await ctx.reply(embed=embed)
        
        await ctx.message.delete()
        
        products = get_all_products()
        product = products.get(product_name)

        if not product:
            return await ctx.send("❌ Product not found. Use `.products` to view available items.")

        if product["stock"] <= 0:
            return await ctx.send(f"⚠️ `{product_name}` is out of stock.")

        # Load orders DB
        db = load_orders_db()

        # Ensure keys exist
        if save_pending_payment_orders not in db:
            db[save_pending_payment_orders] = {}
        if save_pending_delivery_orders not in db:
            db[save_pending_delivery_orders] = {}

        order_id = str(len(db[save_pending_payment_orders]) + len(db[save_pending_delivery_orders]) + 1).zfill(4)
        price = float(product["price"])

        # Create new order
        db[save_pending_payment_orders][order_id] = {
            "order_id": order_id,
            "user_id": ctx.author.id,
            "user_name": str(ctx.author),
            "item": product_name,
            "amount": price,
            "status": "Pending Payment",
            "timestamp": india_time().strftime("%Y-%m-%d - %I:%M:%S%p")
        }
        save_orders_db(db)

        # Initial embed
        embed = discord.Embed(
            title="🛍️ Order Created",
            description=f"**Item:** `{product_name}`\n💰 **Amount:** `${price}`\n\nPlease wait while we generate your payment link...",
            color=discord.Color.orange(),
            timestamp=india_time()
        )
        embed.set_footer(text=f"Ordered by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        msg = await ctx.send(embed=embed)

        # Payment system
        payment_cog = self.bot.get_cog("PaymentsGateway")
        if not payment_cog:
            return await msg.edit(content="❌ Payments system not loaded. Contact admin.", embed=None)

        await payment_cog.receive_ltc(ctx, price)

        # Update order to "Waiting for Payment"
        db[save_pending_payment_orders][order_id]["status"] = "Waiting for Payment"
        save_orders_db(db)

        # Track payment for this order
        await self.track_order_payment(ctx, order_id, price, product_name)

    # ============================================================
    # 💰 Track payment for specific order
    # ============================================================
    async def track_order_payment(self, ctx, order_id, price, product_name):
        """Track a single order's payment until it completes."""
        headers = {"x-api-key": NOWPAYMENTS_API_KEY}
        db_payments = load_receive_ltc_db()

        # Try to find latest payment made by this user with matching amount
        payment_id = None
        for pid, data in db_payments.get("payments", {}).items():
            if data["user_id"] == ctx.author.id and float(data["amount_usd"]) == float(price):
                payment_id = pid
                break

        if not payment_id:
            await ctx.send("⚠️ Could not locate payment in database. Try again or contact admin.")
            return

        # 🕒 Wait for payment confirmation
        await ctx.send("⌛ Waiting for Litecoin payment confirmation (this may take a few minutes)...")

        for _ in range(30):  # ~5 minutes max (10s interval)
            try:
                response = requests.get(f"{NOWPAYMENTS_STATUS_URL}{payment_id}", headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    status = data.get("payment_status")

                    if status == "finished":
                        # ✅ Payment confirmed — complete order
                        self.complete_order(ctx, order_id, product_name, price, payment_id)
                        return

                    elif status == "failed":
                        db = load_orders_db()
                        db[save_pending_payment_orders][order_id]["status"] = "Failed"
                        save_orders_db(db)
                        await ctx.send("❌ Payment failed. Order canceled.")
                        return

                await asyncio.sleep(10)

            except Exception as e:
                print(f"⚠️ Error checking payment: {e}")
                await asyncio.sleep(10)

        await ctx.send("⌛ Payment verification timed out. If you paid, contact support.")

    # ============================================================
    # 🎁 Complete order & move to pending_delivery_orders
    # ============================================================
    def complete_order(self, ctx, order_id, product_name, price, payment_id):
        """Mark order as complete and move it to pending_delivery_orders."""
        db_orders = load_orders_db()
        db_products = get_all_products()
        product = db_products.get(product_name)

        # Ensure both sections exist
        if save_pending_payment_orders not in db_orders:
            db_orders[save_pending_payment_orders] = {}
        if save_pending_delivery_orders not in db_orders:
            db_orders[save_pending_delivery_orders] = {}

        # Move from "orders" → "pending_delivery_orders"
        order_data = db_orders[save_pending_payment_orders].pop(order_id)
        order_data["status"] = "Completed"
        order_data["payment_id"] = payment_id
        order_data["timestamp"] = india_time().strftime("%Y-%m-%d - %I:%M:%S%p")
        db_orders[save_pending_delivery_orders][order_id] = order_data
        save_orders_db(db_orders)

        # Decrease stock
        if product:
            product["stock"] = max(product.get("stock", 0) - 1, 0)
            db_products[product_name] = product
            asyncio.create_task(save_products_db({"products": db_products}))

        # Send DM to user (Embed Format)
        embed = discord.Embed(
            title="✅ Payment Confirmed!",
            description="Thank you for your purchase! ❤️\n\n🕓 *Your order will be delivered very soon.*",
            color=discord.Color.green(),
            timestamp=india_time()
        )

        embed.add_field(name="🧾 Order ID", value=f"`{order_id}`", inline=True)
        embed.add_field(name="📦 Product", value=f"`{product_name}`", inline=True)
        embed.add_field(name="💰 Amount Paid", value=f"`{price} USD`", inline=True)
        embed.add_field(
            name="📅 Date",
            value=f"`{india_time().strftime('%Y-%m-%d - %I:%M:%S%p')}`",
            inline=False
        )

        if product and "description" in product:
            embed.add_field(
                name="📝 Product Info",
                value=product.get("description", "No Description"),
                inline=False
            )

        embed.set_footer(text="Sit tight! Delivery in progress 🚚")

        try:
            asyncio.create_task(ctx.author.send(embed=embed))
        except Exception:
            pass

        asyncio.create_task(ctx.send(f"✅ Order `{order_id}` completed! Check your DMs."))

async def setup(bot):
    await bot.add_cog(Orders(bot))
    print("🧱 orders.py loaded successfully")
