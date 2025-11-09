import discord
import io
import time
import qrcode
import requests
import aiohttp
import html
import psutil
import asyncio
import platform
import json, asyncio, os, sys
from discord.ext import commands
from discord import ui
from datetime import datetime, timezone, timedelta
from manage.permissions import check_perm
from manage.database_manager import init_receive_ltc_databases, add_receive_ltc, get_receive_ltc, update_receive_ltc_status, add_normal_log, add_embed_log

# --- Load Config ---
with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

bot_config = config["BOT"]
bot_data_config = config["BOT_DATA"]
ticket_config = config["TICKET"]
nowpayments_config = config["NOWPAYMENTS"]

# Test receive_ltc
NOWPAYMENTS_API_KEY = "PBFG6PX-CKKMVZE-HDGWVCS-7QSFJ41"
NOWPAYMENTS_LTC_WALLET = nowpayments_config["LTC_WALLET"]
NOWPAYMENTS_BASE_URL = "https://api-sandbox.nowpayments.io/v1/payment"
NOWPAYMENTS_STATUS_URL = "https://api-sandbox.nowpayments.io/v1/payment/"

# NOWPAYMENTS_API_KEY = nowpayments_config["API_KEY"]
# NOWPAYMENTS_LTC_WALLET = nowpayments_config["LTC_WALLET"]
# NOWPAYMENTS_BASE_URL = "https://api.nowpayments.io/v1/payment"
# NOWPAYMENTS_STATUS_URL = "https://api.nowpayments.io/v1/payment/"

init_receive_ltc_databases()

class PaymentsGateway(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    # -------------------------------------------
    # 🪙 Command: .receive_ltc <amount_in_usd>
    # -------------------------------------------
    @commands.command(name="receive_ltc")
    async def receive_ltc(self, ctx, amount: float):
        """Generate a Litecoin payment link using NowPayments"""
        # await ctx.message.delete()

        headers = {
            "x-api-key": NOWPAYMENTS_API_KEY,
            "Content-Type": "application/json"
        }

        order_id = f"ORDER_{ctx.author.id}_{int(datetime.now().timestamp())}"

        payload = {
            "price_amount": amount,
            "price_currency": "usd",
            "pay_currency": "ltc",
            "order_id": order_id,
            "order_description": f"LTC Payment by {ctx.author.name}",
            "ipn_callback_url": "https://nowpayments.io"  # optional
        }

        try:
            response = requests.post(NOWPAYMENTS_BASE_URL, headers=headers, json=payload)

            if response.status_code in (200, 201):
                data = response.json()
                payment_id = data.get("payment_id")
                pay_address = data.get("pay_address")
                pay_amount = data.get("pay_amount")
                purchase_id = data.get("purchase_id")

                # 💾 Save to database (status = waiting)
                await add_receive_ltc(
                    user_id=ctx.author.id,
                    purchase_id=purchase_id,
                    payment_id=payment_id,
                    amount_usd=amount,
                    ltc_amount=float(pay_amount),
                    address=pay_address,
                    status="waiting"
                )

                embed = discord.Embed(
                    title="💰 Litecoin Payment Request",
                    description="Please complete your LTC payment below 👇",
                    color=discord.Color.gold(),
                    timestamp=datetime.now(timezone.utc)
                )
                embed.add_field(name="💵 USD Amount", value=f"`{amount}`", inline=True)
                embed.add_field(name="🪙 LTC Amount", value=f"`{pay_amount}`", inline=True)
                embed.add_field(name="🏦 Pay to Address", value=f"```{pay_address}```", inline=False)
                embed.add_field(name="🆔 Payment ID", value=f"```{payment_id}```", inline=False)
                embed.set_thumbnail(url="https://cryptologos.cc/logos/litecoin-ltc-logo.png")
                embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)

                msg = await ctx.send(embed=embed)

                # ⏳ Check payment status in background
                await self.track_payment(ctx, payment_id, msg)

            else:
                print(f"❌ Failed to create payment (status {response.status_code})")
                print(response.text)
                await ctx.send("❌ Failed to create payment. Please try again later.")

        except Exception as e:
            print(f"❌ Exception while creating payment: {e}")
            await ctx.send(f"❌ Error: {e}")

    # -----------------------------------------------------
    # 🔍 Track Payment Status (auto-check until confirmed)
    # -----------------------------------------------------
    async def track_payment(self, ctx, payment_id: str, message: discord.Message):
        """Polls NowPayments API until payment is completed or times out."""
        headers = {"x-api-key": NOWPAYMENTS_API_KEY}
        max_attempts = 30  # ~5 minutes (10s interval)
        log_channel = self.bot.get_channel(bot_data_config["LOG_ID"])

        for attempt in range(max_attempts):
            try:
                response = requests.get(f"{NOWPAYMENTS_STATUS_URL}{payment_id}", headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    status = data.get("payment_status")

                    if status == "finished":
                        update_receive_ltc_status(payment_id, "finished")

                        embed = discord.Embed(
                            title="✅ LTC Payment Received",
                            description="Your payment was successfully confirmed on the blockchain.",
                            color=discord.Color.green(),
                            timestamp=datetime.now(timezone.utc)
                        )
                        embed.add_field(name="💸 Payment ID", value=f"`{payment_id}`", inline=False)
                        embed.add_field(name="🕒 Confirmation Time", value=f"<t:{int(datetime.now().timestamp())}:F>", inline=False)
                        embed.set_thumbnail(url="https://cryptologos.cc/logos/litecoin-ltc-logo.png")
                        embed.set_footer(text=f"Payment confirmed for {ctx.author}", icon_url=ctx.author.display_avatar.url)

                        add_embed_log(
                            title="✅ LTC Payment Received",
                            description="Your payment was successfully confirmed on the blockchain.",
                            fields=[
                                {"name": "💸 Payment ID", "value": payment_id, "inline": True},
                                {"name": "🕒 Confirmation Time", "value": datetime.now(timezone(timedelta(hours=5, minutes=30))).strftime("%A, %B %d, %Y %I:%M %p"), "inline": True}
                            ],
                            footer_text=f"Payment confirmed for {ctx.author}",
                            footer_icon=ctx.author.display_avatar.url
                        )

                        await ctx.author.send(embed=embed)
                        await log_channel.send(embed=embed)
                        await message.edit(content="✅ Payment confirmed successfully!", embed=None)
                        # print(f"✅ Payment confirmed: {payment_id}")
                        return

                    elif status == "failed":
                        update_receive_ltc_status(payment_id, "failed")
                        await ctx.send("❌ Payment failed. Please try again.")
                        print(f"❌ Payment failed: {payment_id}")
                        return

                await asyncio.sleep(10)

            except Exception as e:
                print(f"⚠️ Error checking payment: {e}")
                await asyncio.sleep(10)

        update_receive_ltc_status(payment_id, "timeout")
        await ctx.send("⌛ Payment verification timed out. If you paid, contact support.")

    # -----------------------------------------------------
    # 🧾 Command: .checkpayment <payment_id>
    # -----------------------------------------------------
    @commands.command(name="checkpayment")
    @check_perm("FULL_ACCESS", "ADMIN", "MODERATOR")
    async def check_payment_cmd(self, ctx, payment_id: str = None):
        """Check payment details from database."""
        if not payment_id:
            return await ctx.send("⚠️ Usage: `.checkpayment <payment_id>`")

        payment = get_receive_ltc(payment_id)
        if not payment:
            return await ctx.send("❌ No payment found with that ID.")

        embed = discord.Embed(
            title="📄 Payment Details",
            color=discord.Color.blurple(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="👤 User ID", value=f"`{payment['user_id']}`", inline=False)
        embed.add_field(name="💵 USD Amount", value=f"`{payment['amount_usd']}`", inline=True)
        embed.add_field(name="🪙 LTC Amount", value=f"`{payment['ltc_amount']}`", inline=True)
        embed.add_field(name="🏦 Address", value=f"```{payment['address']}```", inline=False)
        embed.add_field(name="📦 Status", value=f"`{payment['status']}`", inline=True)
        embed.add_field(name="🕒 Created", value=f"<t:{int(datetime.fromisoformat(payment['created_at']).timestamp())}:F>", inline=False)

        if "updated_at" in payment:
            embed.add_field(name="🔁 Updated", value=f"<t:{int(datetime.fromisoformat(payment['updated_at']).timestamp())}:F>", inline=False)

        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(PaymentsGateway(bot))
    print("🧱 payments_gateway.py loaded successfully")