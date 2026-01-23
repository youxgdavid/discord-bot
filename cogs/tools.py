import discord
from discord import app_commands
from discord.ext import commands
import io
import re
import aiohttp
from datetime import datetime, timezone, timedelta
from typing import List, Tuple, Dict, Optional

_emoji_avg_cache: Dict[int, Tuple[int,int,int]] = {}

_unicode_square_palette: List[Tuple[str, Tuple[int,int,int]]] = [
    ("🟥", (234, 67, 53)),
    ("🟧", (244, 180, 0)),
    ("🟨", (251, 188, 5)),
    ("🟩", (52, 168, 83)),
    ("🟦", (66, 133, 244)),
    ("🟪", (156, 39, 176)),
    ("⬛", (0, 0, 0)),
    ("⬜", (245, 245, 245)),
]

async def _fetch_bytes(url: str) -> bytes:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                raise RuntimeError(f"Failed to fetch {url} (HTTP {resp.status})")
            return await resp.read()

def _nearest_color(target: Tuple[int,int,int], palette: List[Tuple[Tuple[int,int,int], str]]) -> str:
    tr, tg, tb = target
    best, best_d = None, 1e18
    for (r,g,b), token in palette:
        dr, dg, db = tr - r, tg - g, tb - b
        d = dr*dr + dg*dg + db*db
        if d < best_d: best_d, best = d, token
    return best

def _emoji_token(e: discord.Emoji) -> str:
    return f"<a:{e.name}:{e.id}>" if e.animated else f"<:{e.name}:{e.id}>"

async def _compute_emoji_avg_color(e: discord.Emoji) -> Tuple[int,int,int]:
    if e.id in _emoji_avg_cache: return _emoji_avg_cache[e.id]
    try:
        data = await _fetch_bytes(e.url)
        from PIL import Image
        img = Image.open(io.BytesIO(data)).convert('RGB').resize((16,16))
        pixels = list(img.getdata())
        n = len(pixels)
        avg = (sum(p[0] for p in pixels) // n, sum(p[1] for p in pixels) // n, sum(p[2] for p in pixels) // n)
        _emoji_avg_cache[e.id] = avg
        return avg
    except:
        avg = (180,180,180)
        _emoji_avg_cache[e.id] = avg
        return avg

class Tools(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="clipthat", description="Clip last N seconds of chat into a clean log file")
    @app_commands.describe(title="Title for the clip", seconds="Duration (10-300s)", include_attachments="Include attachment URLs")
    async def clipthat(self, interaction: discord.Interaction, title: str, seconds: app_commands.Range[int, 10, 300] = 60, include_attachments: bool = True):
        if not isinstance(interaction.channel, (discord.TextChannel, discord.Thread)):
            return await interaction.response.send_message("Use in a text channel or thread.", ephemeral=True)
        await interaction.response.defer(thinking=True)
        window_start = datetime.now(timezone.utc) - timedelta(seconds=int(seconds))
        messages = []
        try:
            async for msg in interaction.channel.history(limit=1000, after=window_start, oldest_first=True):
                messages.append(msg)
        except Exception as e:
            return await interaction.followup.send(f"❌ Failed to read history: {e}", ephemeral=True)
        if not messages:
            return await interaction.followup.send("No messages in selected window.", ephemeral=True)
        
        safe_title = re.sub(r"[^A-Za-z0-9 _-]+", "", title).strip() or "clip"
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_title}_{ts}.txt"
        
        lines = [f"=== Clip: {title} ===\nChannel: #{interaction.channel.name}\nWindow: last {seconds}s\nGenerated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n=== Messages ===\n"]
        for m in messages:
            author = f"{m.author.display_name} (@{m.author.name})"
            lines.append(f"[{m.created_at.strftime('%H:%M:%S')} UTC] {author}: {m.clean_content}".rstrip())
            if m.reference and m.reference.resolved:
                ref = m.reference.resolved
                lines.append(f"  ↩ reply to {getattr(ref.author, 'display_name', 'unknown')}: {(ref.clean_content or '')[:80]}")
            if include_attachments and m.attachments:
                for a in m.attachments: lines.append(f"  📎 attachment: {a.filename} <{a.url}>")
        
        transcript = "\n".join(lines)
        file = discord.File(io.BytesIO(transcript.encode('utf-8')), filename=filename)
        embed = discord.Embed(title=f"🎬 Clip Saved: {title}", description="A transcript of recent messages has been attached.", color=discord.Color.blurple(), timestamp=datetime.now(timezone.utc))
        embed.add_field(name="Channel", value=interaction.channel.mention, inline=True).add_field(name="Duration", value=f"{seconds}s", inline=True).add_field(name="Messages", value=str(len(messages)), inline=True)
        await interaction.followup.send(embed=embed, file=file)

    @app_commands.command(name="emojimosaic", description="Convert an image into an emoji mosaic")
    @app_commands.describe(image="Source image", width="Columns (10-60)", theme="Emoji theme", preview="PNG preview")
    @app_commands.choices(theme=[app_commands.Choice(name="All", value="all"), app_commands.Choice(name="Static", value="static"), app_commands.Choice(name="Animated", value="animated")])
    async def emojimosaic(self, interaction: discord.Interaction, image: discord.Attachment, width: app_commands.Range[int, 10, 60] = 30, theme: app_commands.Choice[str] = None, preview: bool = True):
        await interaction.response.defer(thinking=True)
        if not image.content_type or not image.content_type.startswith('image/'):
            return await interaction.followup.send("❌ Attach valid image.", ephemeral=True)
        try: from PIL import Image, ImageDraw, ImageResampling
        except: return await interaction.followup.send("❌ Pillow not installed.", ephemeral=True)
        
        try:
            src = Image.open(io.BytesIO(await image.read())).convert('RGB')
            w, h = src.size
            tgt_w = int(width)
            tgt_h = min(60, int(round(tgt_w * (h / max(1, w)))))
            if tgt_h == 60: tgt_w = max(10, int(round(60 * (w / h))))
            
            small = src.resize((tgt_w, tgt_h), ImageResampling.BILINEAR)
            pixels = list(small.getdata())
            
            use_mode = (theme.value if theme else 'all')
            emoji_palette = []
            if interaction.guild:
                candidates = interaction.guild.emojis
                if use_mode == 'static': candidates = [e for e in candidates if not e.animated]
                elif use_mode == 'animated': candidates = [e for e in candidates if e.animated]
                for e in candidates[:150]:
                    emoji_palette.append((await _compute_emoji_avg_color(e), _emoji_token(e)))
            
            if not emoji_palette:
                for ch, rgb in _unicode_square_palette: emoji_palette.append((rgb, ch))
            
            lines = []
            for y in range(tgt_h):
                row = []
                for x in range(tgt_w):
                    row.append(_nearest_color(pixels[y * tgt_w + x], emoji_palette))
                lines.append(''.join(row))
            
            mosaic_text = "\n".join(lines)
            files, embed = [], discord.Embed(title=" Emoji Mosaic", color=discord.Color.purple(), timestamp=datetime.now(timezone.utc))
            embed.add_field(name="Size", value=f"{tgt_w}×{tgt_h}").add_field(name="Theme", value=use_mode)
            
            if len(mosaic_text) > 1500:
                files.append(discord.File(io.BytesIO(mosaic_text.encode('utf-8')), filename="mosaic.txt"))
                embed.add_field(name="Mosaic", value="Attached as mosaic.txt", inline=False)
            else: embed.description = f"```\n{mosaic_text}\n```" # Using code block for better alignment if small

            if preview:
                tile = 12
                prev = Image.new('RGB', (tgt_w*tile, tgt_h*tile))
                draw = ImageDraw.Draw(prev)
                for i, (r,g,b) in enumerate(pixels):
                    x, y = i % tgt_w, i // tgt_w
                    draw.rectangle([x*tile, y*tile, x*tile+tile, y*tile+tile], fill=(r,g,b))
                buf = io.BytesIO()
                prev.save(buf, format='PNG')
                buf.seek(0)
                files.append(discord.File(buf, filename='mosaic_preview.png'))
                embed.set_image(url="attachment://mosaic_preview.png")
            
            await interaction.followup.send(embed=embed, files=files)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed: {e}", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Tools(bot))
