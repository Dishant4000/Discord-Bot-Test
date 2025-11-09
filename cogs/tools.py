import discord
import requests
import json
import asyncio
import os
import yt_dlp
from gpt4all import GPT4All
from discord.ext import commands
from datetime import datetime, timezone
from manage.permissions import check_perm

# Load config
with open("config.json", "r", encoding="utf-8") as f:
    cfg = json.load(f)

bot_config = cfg["BOT"]
ticket_config = cfg["TICKET"]
bot_data_config = cfg["BOT_DATA"]
payment_methods = cfg["PAYMENT_METHODS"]
LTC_ADDRESS = payment_methods["LTC"]
UPI_ID = payment_methods["UPI"]
YOUTUBE_API_KEY = None


def _format_duration(seconds: int) -> str:
    if seconds is None:
        return "N/A"
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h:d}:{m:02d}:{s:02d}"
    return f"{m:d}:{s:02d}"

class Tools(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.model = None
    
    # ===========================
    # 📺 YouTube
    # ===========================
    @commands.command(name="youtube", aliases=["yt", "yts"])
    async def youtube(self, ctx, *, query: str = None):
        """Search YouTube and return the top result.
        Usage: .youtube <search terms>
        """

        # ✅ initialize yt_dlp inside the cog
        self.ytdl_opts = {
            "format": "best",
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "extract_flat": "in_playlist",
            "youtube_include_dash_manifest": False,
        }
        self.ytdl = yt_dlp.YoutubeDL(self.ytdl_opts)

        try:
            await ctx.message.delete()
        except (discord.NotFound, discord.Forbidden):
            pass  # message already deleted or no permission
        except Exception as e:
            print(f"⚠️ Message delete failed: {e}", delete_after=5)
        
        if not query:
            return await ctx.send("⚠️ Usage: `.youtube <search query>`", delete_after=8)

        searching = await ctx.send(f"🔎 Searching YouTube for: `{query}`")

        try:
            # Use yt_dlp 'ytsearch1:' to find the top result without API key.
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(None, lambda: self.ytdl.extract_info(f"ytsearch1:{query}", download=False))

            if not info or "entries" not in info or len(info["entries"]) == 0:
                await searching.edit(content="❌ No results found.")
                return

            entry = info["entries"][0]

            title = entry.get("title") or "Unknown title"
            uploader = entry.get("uploader") or entry.get("channel") or "Unknown channel"
            url = entry.get("webpage_url") or entry.get("url")
            duration = _format_duration(entry.get("duration"))
            thumbnail = entry.get("thumbnail")
            view_count = entry.get("view_count")
            upload_date = entry.get("upload_date")  # format YYYYMMDD
            description = entry.get("description") or ""
            short_desc = (description[:500] + "…") if len(description) > 500 else description

            # Try to create a nice professional embed
            embed = discord.Embed(
                title=title,
                url=url,
                description=short_desc or None,
                color=discord.Color(0xFF0000),  # YouTube red
                timestamp=datetime.now(timezone.utc)
            )
            embed.set_author(name=uploader)
            if thumbnail:
                embed.set_thumbnail(url=thumbnail)

            field_lines = []
            field_lines.append(f"**Duration:** `{duration}`")
            if view_count is not None:
                field_lines.append(f"**Views:** `{view_count:,}`")
            if upload_date:
                # convert YYYYMMDD to readable
                try:
                    d = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
                    field_lines.append(f"**Uploaded:** `{d}`")
                except Exception:
                    pass

            embed.add_field(name="📊 Info", value="\n".join(field_lines), inline=False)
            embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)

            # Buttons (link to video and open channel)
            view = discord.ui.View()
            view.add_item(discord.ui.Button(label="▶️ Watch on YouTube", style=discord.ButtonStyle.link, url=url))
            channel_url = entry.get("channel_url")
            if channel_url:
                view.add_item(discord.ui.Button(label="📺 Channel", style=discord.ButtonStyle.link, url=channel_url))

            await searching.edit(content=None, embed=embed, view=view)

        except Exception as e:
            # If something fails, try to show a helpful message and log to console
            await searching.edit(content=f"❌ Error while searching: `{e}`")
            print(f"[youtube] Error searching for '{query}': {e}")
    
    @commands.command(name="ai")
    async def ai_command(self, ctx, *, prompt: str):
        """
        Use: .ai <question or message>
        Example: .ai What is the meaning of life?
        """

        # 🧠 Your OpenRouter API key
        OPENROUTER_API_KEY = bot_data_config["OPENROUTER_API_KEY"]
        # 🧩 API endpoint & model
        API_URL = "https://openrouter.ai/api/v1/chat/completions"
        MODEL_NAME = "openai/gpt-4o"

        await ctx.typing()
        try:
            def ask_openrouter():
                response = requests.post(
                    url=API_URL,
                    headers={
                        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://discord.com",
                        "X-Title": "Discord AI Bot",
                    },
                    data=json.dumps({
                        "model": MODEL_NAME,
                        "messages": [
                            {"role": "user", "content": prompt}
                        ]
                    })
                )

                # Raise exception if failed
                response.raise_for_status()
                data = response.json()
                if "choices" in data and len(data["choices"]) > 0:
                    return data["choices"][0]["message"]["content"]
                else:
                    return "⚠️ No response received or malformed API reply."

            reply = await asyncio.to_thread(ask_openrouter)

            embed = discord.Embed(
                title=f"🤖 OpenAI (Artificial Intelligence)",
                description=reply[:4000],
                color=discord.Color.blurple()
            )
            embed.add_field(name="Prompt", value=prompt[:1024], inline=False)
            embed.set_footer(text=f"Requested by {ctx.author} • Made by Dishant", icon_url=ctx.author.display_avatar.url)
            await ctx.reply(embed=embed)

        except requests.exceptions.HTTPError as e:
            await ctx.reply(f"❌ HTTP Error: `{e}`\nResponse: {e}")
        except Exception as e:
            await ctx.reply(f"❌ Error: `{e}`")

async def setup(bot):
    await bot.add_cog(Tools(bot))
    print("🧱 tools.py loaded successfully")