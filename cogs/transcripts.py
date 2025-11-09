import discord
import io
import time
import qrcode
import aiohttp
import html
import psutil
import platform
import json, asyncio, os, sys
from discord.ext import commands
from discord import ui
from datetime import datetime, timezone
from manage.permissions import check_perm
from manage.database_manager import add_embed_log, add_normal_log

# --- Load Config ---
with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

bot_config = config["BOT"]
bot_data_config = config["BOT_DATA"]
ticket_config = config["TICKET"]

class Transcripts(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Helper: ensure transcript folder exists
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    TRANSCRIPT_BASE = os.path.join(BASE_DIR, "data", "transcripts", "other-transcripts")
    os.makedirs(TRANSCRIPT_BASE, exist_ok=True)
    
    def format_timestamp(self, dt):
        # return readable timestamp and unix for Discord-like formatting if needed
        if not dt:
            return ""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        unix = int(dt.timestamp())
        pretty = dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        return pretty, unix
    
    def escape(self, s: str):
        return html.escape(s) if s is not None else ""
    
    async def generate_transcript_html(self, channel):
        """
        Fetch messages and create an HTML file path (returns full path).
        Does NOT delete the channel. Caller handles sending/logging.
        """
        messages = []
        async for msg in channel.history(limit=None, oldest_first=True):
            messages.append(msg)
    
        # prepare html pieces
        title = f"Transcript — #{channel.name}"
        created = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
        safe_channel = "".join(c if c.isalnum() or c in "-_." else "_" for c in channel.name)
        filename = f"transcript_{safe_channel}_{created}.html"
        filepath = os.path.join(self.TRANSCRIPT_BASE, filename)
    
        # CSS (simple, professional)
        css = """
        body{font-family:Inter, Roboto, Arial, sans-serif;background:#0f1724;color:#e6eef8;margin:0;padding:0}
        .wrap{max-width:980px;margin:28px auto;padding:20px;background:linear-gradient(180deg,#081226 0%, #071423 100%);border-radius:12px;box-shadow:0 8px 30px rgba(2,6,23,.7)}
        h1{margin:0 0 8px 0;font-size:20px}
        .meta{color:#9fb0d4;margin-bottom:16px;font-size:13px}
        .msg{display:flex;gap:12px;padding:14px;border-radius:10px;margin-bottom:8px;background:linear-gradient(90deg, rgba(255,255,255,0.01), rgba(255,255,255,0.00));align-items:flex-start}
        .avatar{width:48px;height:48px;border-radius:10px;flex:0 0 48px;object-fit:cover}
        .content{flex:1}
        .author{font-weight:700;color:#dbeafe}
        .time{color:#8fa6cc;font-size:12px;margin-left:8px}
        .text{color:#e6eef8;margin-top:6px;white-space:pre-wrap}
        .embed{border-left:4px solid #2b6cb0;background:#071830;padding:10px;border-radius:8px;margin-top:8px;color:#bcd7f7}
        .attachment{margin-top:8px}
        .attachment a{color:#93c5fd}
        .footer{margin-top:18px;color:#9fb0d4;font-size:13px;border-top:1px solid rgba(255,255,255,0.02);padding-top:12px}
        """
    
        # Build HTML
        html_parts = []
        html_parts.append(f"<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>")
        html_parts.append(f"<title>{self.escape(title)}</title>")
        html_parts.append(f"<style>{css}</style></head><body><div class='wrap'>")
        html_parts.append(f"<h1>{self.escape(title)}</h1>")
        html_parts.append(f"<div class='meta'>Channel: #{self.escape(channel.name)} • Guild: {self.escape(channel.guild.name)} • Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</div>")
    
        for m in messages:
            # avatar and author
            author_name = f"{m.author.display_name}#{m.author.discriminator}" if getattr(m.author, "discriminator", None) else str(m.author)
            avatar_url = m.author.display_avatar.url if hasattr(m.author, "display_avatar") else ""
            ts_pretty, ts_unix = self.format_timestamp(m.created_at or datetime.now(timezone.utc))
            html_parts.append("<div class='msg'>")
            # avatar (linked to user's profile)
            html_parts.append(f"<div><img class='avatar' src='{self.escape(str(avatar_url))}' alt='avatar'></div>")
            # content
            html_parts.append("<div class='content'>")
            html_parts.append(f"<div><span class='author'>{self.escape(author_name)}</span><span class='time'> • {self.escape(ts_pretty)}</span></div>")
    
            # content text (escape)
            text = m.content or ""
            # convert mentions and channel mentions to readable form
            # simple replacements
            for user in m.mentions:
                text = text.replace(f"<@{user.id}>", f"@{user.display_name}")
                text = text.replace(f"<@!{user.id}>", f"@{user.display_name}")
            for role in m.role_mentions:
                text = text.replace(f"<@&{role.id}>", f"@{role.name}")
            for ch in m.channel_mentions:
                text = text.replace(f"<#{ch.id}>", f"#{ch.name}")
    
            if text.strip():
                html_parts.append(f"<div class='text'>{self.escape(text)}</div>")
    
            # embeds summary
            if m.embeds:
                for e in m.embeds:
                    # build a compact embed summary
                    title_e = e.title or ""
                    desc_e = e.description or ""
                    fields_e = ""
                    if getattr(e, "fields", None):
                        for f in e.fields:
                            fields_e += f"<div><strong>{self.escape(f.name)}:</strong> {self.escape(f.value)}</div>"
                    html_parts.append("<div class='embed'>")
                    if title_e: html_parts.append(f"<div><strong>{self.escape(title_e)}</strong></div>")
                    if desc_e: html_parts.append(f"<div>{self.escape(desc_e)}</div>")
                    if fields_e: html_parts.append(fields_e)
                    # include embed image as link/thumb
                    if getattr(e, "image", None) and getattr(e.image, "url", None):
                        html_parts.append(f"<div class='attachment'><a href='{self.escape(e.image.url)}' target='_blank'>Embed image</a></div>")
                    html_parts.append("</div>")
    
            # attachments
            if m.attachments:
                for a in m.attachments:
                    name = self.escape(a.filename)
                    url = self.escape(a.url)
                    # small image preview if image
                    if any(a.filename.lower().endswith(ext) for ext in ('.png','.jpg','.jpeg','.gif','.webp')):
                        html_parts.append(f"<div class='attachment'><a href='{url}' target='_blank'>{name}</a> — <a href='{url}' target='_blank'>preview</a></div>")
                    else:
                        html_parts.append(f"<div class='attachment'><a href='{url}' target='_blank'>{name}</a></div>")
    
            html_parts.append("</div>")  # end content
            html_parts.append("</div>")  # end msg
    
        # footer / summary
        html_parts.append(f"<div class='footer'>Transcript generated for <strong>#{self.escape(channel.name)}</strong> in <strong>{self.escape(channel.guild.name)}</strong> • Messages: {len(messages)}</div>")
        html_parts.append("</div></body></html>")
    
        # write file
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(html_parts))
    
        return filepath, filename
    
    @commands.command(name="transcript")
    @check_perm("FULL_ACCESS", "ADMIN")
    async def transcript_cmd(self, ctx):
        """
        Create an HTML transcript of the current channel, save locally, and send to log + requester.
        Usage:
          .transcript   -> run in the ticket/channel to export all messages
        """
        await ctx.message.delete()  # remove command tweet for privacy
    
        channel = ctx.channel
        generating_msg = await ctx.send("📤 Generating transcript, please wait...")
    
        try:
            filepath, filename = await self.generate_transcript_html(channel)
        except Exception as e:
            await generating_msg.edit(content=f"❌ Failed to generate transcript: {e}")
            return
    
        file_size = os.path.getsize(filepath)
        # send transcript to the user (DM) and to log channel if configured
        try:
            # # send to requester's DM
            # with open(filepath, "rb") as f:
            #     discord_file = discord.File(f, filename=filename)
            #     try:
            #         await ctx.author.send("📄 Here is your transcript (HTML):", file=discord_file)
            #     except Exception:
            #         # if DM fails, send to channel privately (ephemeral not supported in text command)
            #         await ctx.send("⚠️ Could not DM you the transcript. Sending here instead...", file=discord_file)
    
            # send to log channel if configured
            log_ch_id = ticket_config["ticket_transcript_id"] or bot_data_config["LOG_ID"]
            if log_ch_id:
                log_channel = self.bot.get_channel(int(log_ch_id))
                if log_channel:
                    with open(filepath, "rb") as lf:
                        await log_channel.send(
                            embed=discord.Embed(
                                title="📥 New Transcript Generated",
                                description=(
                                    f"Transcript for #{channel.name} ({channel.guild.name})"
                                    f"📁 **File:** `{filename}`\n"
                                    f"💾 **Size:** `{file_size//1024} KB`\n"
                                    ),
                                color=discord.Color.blue(),
                                timestamp=datetime.now(timezone.utc)
                            ).add_field(name="File", value=filename).set_footer(text=f"Requested by {ctx.author}"),
                            file=discord.File(lf, filename=filename)
                        )

                        add_embed_log(
                            title="📥 New Transcript Generated",
                            description=(
                                    f"Transcript for #{channel.name} ({channel.guild.name})"
                                    f"📁 File: `{filename}`\n"
                                    f"💾 Size: `{file_size//1024} KB`\n"
                                    ),
                            fields=[
                                {"name": "File", "value": filename},
                            ],
                            footer_text=f"Requested by {ctx.author}",
                            footer_icon=ctx.author.display_avatar.url
                        )
    
            embed = discord.Embed(
                title="✅ Transcript Generated Successfully",
                description=(
                    f"Your transcript for **#{channel.name}** has been created.\n\n"
                    f"📁 **File:** `{filename}`\n"
                    f"💾 **Size:** `{file_size//1024} KB`\n"
                    f"📬 **Delivered:** Sent to your DMs and logs."
                ),
                color=discord.Color.green(),
                timestamp=datetime.now(timezone.utc)
            )
            embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
            
            await generating_msg.edit(content=None, embed=embed, delete_after=5)
            # do not delete the transcript file automatically so you can keep a local copy; optional cleanup can be implemented
        except Exception as e:
            await generating_msg.edit(content=f"❌ Error while sending transcript: {e}")

async def setup(bot):
    await bot.add_cog(Transcripts(bot))
    print("🧱 transcripts.py loaded successfully")