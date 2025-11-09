import discord
import requests
import json
from discord.ext import commands
from datetime import datetime, timezone
from manage.permissions import check_perm

# Load config
with open("config.json", "r", encoding="utf-8") as f:
    cfg = json.load(f)

payment_methods = cfg["PAYMENT_METHODS"]
LTC_ADDRESS = payment_methods["LTC"]
UPI_ID = payment_methods["UPI"]

class PaymentMethods(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="bal")
    async def bal(self, ctx):
        # ---------- .bal Command ----------
        """Show LTC balance in LTC and USD."""
        if not LTC_ADDRESS:
            return await ctx.send("❌ LTC address not configured in config.")

        try:
            # --- Get Litecoin balance (BlockCypher API) ---
            url = f"https://api.blockcypher.com/v1/ltc/main/addrs/{LTC_ADDRESS}/balance"
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            balance_ltc = data.get("balance", 0) / 1e8
            unconfirmed = data.get("unconfirmed_balance", 0) / 1e8
            total_received = data.get("total_received", 0) / 1e8
            tx_count = data.get("n_tx", 0)
            # --- Convert to USD (CoinGecko API) ---
            rate_resp = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=litecoin&vs_currencies=usd", timeout=10)
            rate_resp.raise_for_status()
            rate = rate_resp.json().get("litecoin", {}).get("usd", 0)
            balance_usd = balance_ltc * rate
            # --- Embed formatting ---
            embed = discord.Embed(
                title="💰 Litecoin Wallet Balance",
                color=discord.Color.orange(),
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="📫 Address", value=f"`{LTC_ADDRESS}`", inline=False)
            embed.add_field(name="💎 Confirmed Balance", value=f"**{balance_ltc:.8f} LTC** (${balance_usd:,.2f})", inline=False)
            embed.add_field(name="🔄 Unconfirmed", value=f"{unconfirmed:.8f} LTC", inline=True)
            embed.add_field(name="📥 Total Received", value=f"{total_received:.8f} LTC", inline=True)
            embed.add_field(name="📊 Total Transactions", value=f"{tx_count}", inline=True)
            embed.set_footer(text="Powered by Ninja Official")
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ Error fetching balance:\n```{e}```")
    
    # ---------- .ltc Command ----------
    @commands.command(name="ltc")
    async def ltc(self, ctx):
        """💰 Show your Litecoin address with style."""
        if not LTC_ADDRESS:
            return await ctx.send("⚠️ LTC address not configured in config.json.")

        embed = discord.Embed(
            title="💎 Litecoin Payment Gateway",
            description="Use the address below to send Litecoin (LTC) payments securely.",
            color=discord.Color.from_rgb(191, 191, 191),
            timestamp=datetime.now(timezone.utc)
        )

        embed.add_field(
            name="📬 Your LTC Address",
            value=f"```{LTC_ADDRESS}```",
            inline=False
        )

        embed.add_field(
            name="⚡ Network",
            value="**Litecoin (LTC)** — Fast & Low Fees",
            inline=True
        )

        embed.add_field(
            name="🪙 Recommended Wallets",
            value="Exodus • Trust Wallet • Ledger • Binance",
            inline=True
        )

        embed.set_thumbnail(url="https://cryptologos.cc/logos/litecoin-ltc-logo.png?v=032")
        embed.set_footer(
            text="🔒 Secure blockchain transaction • Powered by Ninja Official",
            icon_url="https://cryptologos.cc/logos/litecoin-ltc-logo.png?v=032"
        )

        # Add a simple copy hint for users
        view = discord.ui.View()
        # view.add_item(discord.ui.Button(label="📋 Copy LTC Address", style=discord.ButtonStyle.grey, disabled=True))
        view.add_item(discord.ui.Button(label="🌐 View on Block Explorer", url=f"https://blockchair.com/litecoin/address/{LTC_ADDRESS}"))

        await ctx.send(embed=embed, view=view)

    # ----------------------- View -----------------------
    class UpiView(discord.ui.View):
        def __init__(self, upi_id):
            super().__init__(timeout=None)
            self.upi_id = upi_id

        @discord.ui.button(label="💰 View Payment Instructions", style=discord.ButtonStyle.secondary)
        async def show_help(self, interaction: discord.Interaction, button: discord.ui.Button):
            embed = discord.Embed(
                title="💳 How to Pay via UPI",
                description=(
                    "1️⃣ Copy the UPI ID.\n"
                    "2️⃣ Open your UPI app (Google Pay, Paytm, PhonePe).\n"
                    f"3️⃣ Paste `{self.upi_id}` in 'Send to UPI ID'.\n"
                    "4️⃣ Enter the amount & confirm payment ✅"
                ),
                color=discord.Color.blurple()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    # ----------------------- Command: .upi -----------------------
    @commands.command(name="upi")
    async def upi_cmd(self, ctx, target: str = None):
        """Show UPI payment info with professional embed."""

        member = None
        if ctx.message.mentions:
            member = ctx.message.mentions[0]
        elif target and target.isdigit():
            try:
                member = await self.bot.fetch_user(int(target))
            except Exception:
                member = None
        if member is None:
            member = ctx.author

        avatar_url = getattr(member.display_avatar, "url", None)

        embed = discord.Embed(
            title="💸 Pay via UPI",
            description=(
                f"Use the following **UPI ID** to send your payment securely:\n\n"
                f"🎯 **UPI: ```{UPI_ID}```**\n\n"
                "Click below to copy or get step-by-step payment instructions."
            ),
            color=discord.Color.green(),
            timestamp=datetime.now(timezone.utc)
        )

        if avatar_url:
            embed.set_thumbnail(url=avatar_url)
        embed.set_footer(text="Powered by Ninja Official ⚙️")

        view = self.UpiView(UPI_ID)
        await ctx.send(embed=embed, view=view)
    
    @commands.command(name="pm", aliases=["payment_methods"])
    async def payment_methods(self, ctx):
        """💳 Show all available payment methods (UPI + LTC)."""
        embed = discord.Embed(
            title="💰 Payment Methods",
            description="Here are all available payment options for your transactions:",
            color=discord.Color.gold(),
            timestamp=discord.utils.utcnow()
        )

        embed.add_field(
            name="🏦 UPI Payment",
            value=f"**UPI ID:** ```{UPI_ID}```\nUse any UPI app (Paytm, GPay, PhonePe) to send payment.",
            inline=False
        )

        embed.add_field(
            name="💎 Litecoin (LTC)",
            value=f"**LTC Address:** ```{LTC_ADDRESS}```\nUse a crypto wallet or exchange supporting Litecoin.",
            inline=False
        )

        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/2331/2331947.png")
        embed.set_footer(
            text=f"Requested by {ctx.author}",
            icon_url=ctx.author.display_avatar.url
        )

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(PaymentMethods(bot))
    print("🧱 payment_methods.py loaded successfully")