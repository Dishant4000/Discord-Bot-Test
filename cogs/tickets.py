import discord
import json, asyncio, os
from discord.ext import commands
from datetime import datetime, timezone
from manage.database_manager import init_tickets_db, create_ticket, close_ticket
from manage.permissions import check_perm

# ---------- Load Configuration ----------
with open("config.json", "r", encoding="utf-8") as f:
    cfg = json.load(f)

bot_config = cfg["BOT"]
ticket_config = cfg["TICKET"]
bot_data_config = cfg["BOT_DATA"]

# ✅ Ensure database exists
init_tickets_db()

class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ---------- Helper: Generate Transcript ----------
    async def create_transcript(self, channel):
        """Generate a modern HTML transcript for the given ticket channel."""
         # Helper: ensure transcript folder exists
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        TRANSCRIPT_BASE = os.path.join(BASE_DIR, "data", "transcripts", "ticket-transcripts")
        os.makedirs(TRANSCRIPT_BASE, exist_ok=True)

        messages = [msg async for msg in channel.history(limit=None, oldest_first=True)]
        now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')

        # HTML START
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Transcript - {channel.name}</title>
<style>
    body {{
        background-color: #2b2d31;
        font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
        color: #dcddde;
        margin: 0;
        padding: 0;
    }}
    .header {{
        background: linear-gradient(90deg, #5865F2, #7289da);
        color: white;
        padding: 20px;
        text-align: center;
        box-shadow: 0 2px 10px rgba(0,0,0,0.3);
    }}
    .header h1 {{
        margin: 0;
        font-size: 28px;
    }}
    .meta {{
        font-size: 14px;
        color: #e0e0e0;
    }}
    .container {{
        max-width: 900px;
        margin: 30px auto;
        background-color: #313338;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 0 25px rgba(0,0,0,0.4);
    }}
    .message {{
        display: flex;
        margin-bottom: 15px;
        padding-bottom: 10px;
        border-bottom: 1px solid #202225;
    }}
    .avatar {{
        width: 48px;
        height: 48px;
        border-radius: 50%;
        margin-right: 12px;
    }}
    .msg-content {{
        flex: 1;
    }}
    .username {{
        font-weight: 600;
        font-size: 15px;
        color: #ffffff;
    }}
    .timestamp {{
        font-size: 12px;
        color: #b9bbbe;
        margin-left: 8px;
    }}
    .content {{
        margin-top: 4px;
        font-size: 15px;
        color: #dcddde;
        word-wrap: break-word;
    }}
    .attachment {{
        margin-top: 8px;
        border-radius: 8px;
        overflow: hidden;
    }}
    .attachment img {{
        max-width: 400px;
        border-radius: 8px;
    }}
    .embed {{
        background-color: #2f3136;
        border-left: 4px solid #5865F2;
        padding: 10px 14px;
        border-radius: 5px;
        margin-top: 8px;
    }}
    .footer {{
        text-align: center;
        font-size: 13px;
        color: #999;
        padding: 15px;
        border-top: 1px solid #202225;
        margin-top: 40px;
    }}
    .footer a {{
        color: #5865F2;
        text-decoration: none;
    }}
</style>
</head>
<body>
    <div class="header">
        <h1>📜 Ticket Transcript</h1>
        <div class="meta">
            Server: {channel.guild.name} • Channel: #{channel.name} • Generated: {now}
        </div>
    </div>

    <div class="container">
"""

        # Loop through messages
        for msg in messages:
            avatar = msg.author.display_avatar.url if msg.author.display_avatar else "https://cdn.discordapp.com/embed/avatars/0.png"
            timestamp = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
            content_html = msg.clean_content.replace("\n", "<br>")

            html += f"""
        <div class="message">
            <img class="avatar" src="{avatar}">
            <div class="msg-content">
                <div><span class="username">{msg.author}</span><span class="timestamp">{timestamp}</span></div>
                <div class="content">{content_html}</div>
            """

            # Attachments
            if msg.attachments:
                for att in msg.attachments:
                    if att.content_type and att.content_type.startswith("image/"):
                        html += f'<div class="attachment"><img src="{att.url}" alt="image"></div>'
                    else:
                        html += f'<div class="attachment"><a href="{att.url}" target="_blank">{att.filename}</a></div>'

            # Embeds
            for emb in msg.embeds:
                emb_title = emb.title or ""
                emb_desc = emb.description or ""
                html += f'<div class="embed"><b>{emb_title}</b><br>{emb_desc}</div>'

            html += "</div></div>"

        # END HTML
        html += f"""
    </div>
    <div class="footer">
        Generated by <strong>Ninja Official</strong> ⚙️ • <a href="#">Return to Server</a><br>
        <small>Created at {now}</small>
    </div>
</body>
</html>
"""

        filename = f"transcript_{channel.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        filepath = os.path.join(TRANSCRIPT_BASE, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)

        return filepath

    # ---------- View: Ticket Panel ----------
    class TicketPanel(discord.ui.View):
        def __init__(self, bot):
            super().__init__(timeout=None)
            self.bot = bot

        @discord.ui.button(label="🎫 Create Ticket", style=discord.ButtonStyle.green, custom_id="create_ticket_btn")
        async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
            guild = interaction.guild
            author = interaction.user

            category = discord.utils.get(guild.categories, id=ticket_config["ticket_open_category"])
            if not category:
                await interaction.response.send_message("⚠️ Ticket category not found. Check config.", ephemeral=True)
                return

            existing = discord.utils.get(guild.channels, name=f"ticket-{author.name.lower()}")
            if existing:
                await interaction.response.send_message(f"⚠️ You already have a ticket: {existing.mention}", ephemeral=True)
                return

            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                author: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True),
            }
            staff_role = discord.utils.get(guild.roles, name="Staff")
            if staff_role:
                overwrites[staff_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

            ticket_channel = await guild.create_text_channel(
                name=f"ticket-{author.name}",
                category=category,
                overwrites=overwrites,
                reason=f"Ticket opened by {author}",
            )

            # ✅ Save to database
            ticket_id = await create_ticket(author.id, ticket_channel.id)

            embed = discord.Embed(
                title="🎟️ Ticket Created",
                description=f"Hello {author.mention}, please describe your issue below.\nUse `.close_ticket` when done.",
                color=discord.Color.green(),
                timestamp=datetime.now(timezone.utc)
            )
            embed.set_footer(text=f"Ticket ID: {ticket_id}")
            await ticket_channel.send(embed=embed)
            await interaction.response.send_message(f"✅ Ticket created: {ticket_channel.mention}", ephemeral=True)

            log_ch = self.bot.get_channel(ticket_config["ticket_transcript_id"])
            if log_ch:
                await log_ch.send(f"🟢 Ticket opened: {ticket_channel.mention} by {author.mention}")

    # ---------- Command: Panel Setup ----------
    @commands.command()
    @check_perm("FULL_ACCESS")
    async def panel_setup(self, ctx):
        if ctx.author.id != bot_config["OWNER_ID"]:
            return await ctx.send("❌ Only the bot owner can use this command.")
        embed = discord.Embed(
            title="🎫 Ticket Panel",
            description="Click the button below to create a support ticket.",
            color=discord.Color.blurple()
        )
        view = self.TicketPanel(self.bot)
        await ctx.send(embed=embed, view=view)

    # ---------- Command: Close Ticket ----------
    @commands.command(name="close_ticket")
    @check_perm("FULL_ACCESS", "ADMIN")
    async def close_ticket_cmd(self, ctx):
        """Close the current ticket and save transcript."""
        channel = ctx.channel
        if not channel.name.startswith("ticket-"):
            return await ctx.send("❌ This isn’t a ticket channel.")

        await ctx.send("🕒 Generating transcript and closing ticket...", delete_after=3)

        # 🔍 Load DB to find matching ticket_id by channel_id
        from manage.database_manager import load_tickets_db
        db = load_tickets_db()
        ticket_id = None

        for tid, data in db["tickets"].items():
            if data.get("channel_id") == channel.id:
                ticket_id = tid
                break

        # ⚠️ If no ticket entry found, stop
        if not ticket_id:
            return await ctx.send("⚠️ This ticket wasn’t found in the database.", delete_after=6)

        # 🧾 Create transcript
        filepath = await self.create_transcript(channel)

        # 🗃️ Update database record properly
        await close_ticket(ticket_id)

        # 📨 Send transcript to logs
        log_ch = self.bot.get_channel(ticket_config["ticket_transcript_id"])
        if log_ch:
            with open(filepath, "rb") as f:
                await log_ch.send(
                    content=f"📥 Transcript for `{channel.name}` (Ticket ID: `{ticket_id}`)",
                    file=discord.File(f, filename=os.path.basename(filepath))
                )

        # ✅ Notify user and delete channel
        await ctx.send("✅ Ticket closed successfully. Transcript saved.", delete_after=4)
        await asyncio.sleep(3)
        await channel.delete(reason="Ticket closed")

# ---------- Setup ----------
async def setup(bot):
    await bot.add_cog(Tickets(bot))
    bot.add_view(Tickets.TicketPanel(bot))  # ✅ Button re-register
    print("🧱 tickets.py loaded successfully")
