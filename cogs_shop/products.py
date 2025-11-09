import discord
from discord.ext import commands
from datetime import datetime, timezone
from manage.permissions import check_perm
from manage.database_manager import (
    init_products_db,
    add_product,
    remove_product,
    get_all_products,
    load_products_db,
    save_products_db
)

# Initialize the products database when cog loads
init_products_db()

class Products(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --------------------------------------------------
    # 🛒 Add Product
    # --------------------------------------------------
    @commands.command(name="addproduct")
    @check_perm("FULL_ACCESS", "ADMIN")
    async def add_product_cmd(self, ctx, name: str = None, price: float = None, *, description: str = None):
        """Add a new product to the shop."""
        await ctx.message.delete()

        if not name or price is None or not description:
            return await ctx.send("⚠️ Usage: `.addproduct <name> <price> <description>`")

        await add_product(name=name, price=price, description=description, stock=0)

        embed = discord.Embed(
            title="🆕 Product Added Successfully",
            description=f"**{name}** has been added to the shop.",
            color=discord.Color.green(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="💰 Price", value=f"`{price}` USD", inline=True)
        embed.add_field(name="📦 Stock", value="`0`", inline=True)
        embed.add_field(name="📝 Description", value=description, inline=False)
        embed.set_footer(text=f"Added by {ctx.author}", icon_url=ctx.author.display_avatar.url)

        await ctx.send(embed=embed)

    # --------------------------------------------------
    # ❌ Delete Product
    # --------------------------------------------------
    @commands.command(name="delproduct")
    @check_perm("FULL_ACCESS", "ADMIN")
    async def del_product_cmd(self, ctx, *, name: str = None):
        """Delete a product from the shop."""
        await ctx.message.delete()
        if not name:
            return await ctx.send("⚠️ Usage: `.delproduct <name>`")

        result = await remove_product(name)
        if result:
            embed = discord.Embed(
                title="🗑️ Product Removed",
                description=f"Product **{name}** has been deleted.",
                color=discord.Color.red(),
                timestamp=datetime.now(timezone.utc)
            )
            embed.set_footer(text=f"Removed by {ctx.author}", icon_url=ctx.author.display_avatar.url)
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"❌ Product `{name}` not found.")

    # --------------------------------------------------
    # 💰 Edit Product Price
    # --------------------------------------------------
    @commands.command(name="editprice")
    @check_perm("FULL_ACCESS", "ADMIN")
    async def edit_price_cmd(self, ctx, name: str = None, new_price: float = None):
        """Edit the price of a product."""
        await ctx.message.delete()
        if not name or new_price is None:
            return await ctx.send("⚠️ Usage: `.editprice <product_name> <new_price>`")

        db = load_products_db()
        if name not in db["products"]:
            return await ctx.send(f"❌ Product `{name}` not found.")

        db["products"][name]["price"] = float(new_price)
        await save_products_db(db)

        embed = discord.Embed(
            title="💲 Price Updated",
            description=f"Price of **{name}** updated to `${new_price}`",
            color=discord.Color.gold(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_footer(text=f"Edited by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    # --------------------------------------------------
    # 📦 Edit Product Stock
    # --------------------------------------------------
    @commands.command(name="stock")
    @check_perm("FULL_ACCESS", "ADMIN", "MODERATOR")
    async def edit_stock_cmd(self, ctx, name: str = None, amount: int = None):
        """Update the stock of a product."""
        await ctx.message.delete()
        if not name or amount is None:
            return await ctx.send("⚠️ Usage: `.stock <product_name> <amount>`")

        db = load_products_db()
        if name not in db["products"]:
            return await ctx.send(f"❌ Product `{name}` not found.")

        db["products"][name]["stock"] = int(amount)
        await save_products_db(db)

        embed = discord.Embed(
            title="📦 Stock Updated",
            description=f"Stock for **{name}** updated to `{amount}` units.",
            color=discord.Color.blue(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_footer(text=f"Updated by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    # --------------------------------------------------
    # 🧾 List All Products
    # --------------------------------------------------
    @commands.command(name="products")
    async def list_products(self, ctx):
        """List all products in the shop with better visual spacing"""
        await ctx.message.delete()

        products = get_all_products()
        if not products:
            return await ctx.send("❌ No products available in the store right now.")

        embed = discord.Embed(
            title="🛒 Product Catalog",
            description="✨ **Explore our available products below!** ✨",
            color=discord.Color.blurple(),
            timestamp=datetime.now(timezone.utc)
        )

        for name, info in products.items():
            price = info.get("price", "N/A")
            stock = info.get("stock", 0)
            desc = info.get("description", "No Description")
            added = info.get("added_at", "Unknown")

            # Beautiful product "card"
            product_block = (
                f"**📦 {name}**\n"
                f"💰 **Price:** `${price}`\n"
                f"📦 **Stock:** `{stock}`\n"
                f"📝 **Description:** {desc}\n"
                f"🕒 **Added:** `{added}`\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            )

            embed.add_field(name="\u200b", value=product_block, inline=False)

        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Products(bot))
    print("🧱 products.py loaded successfully")
