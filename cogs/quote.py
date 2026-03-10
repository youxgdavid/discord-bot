import discord
from discord import app_commands
from discord.ext import commands
import io
import aiohttp
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
from typing import Optional, List, Tuple
import textwrap
from datetime import datetime, timezone

class QuoteGenerator:
    def __init__(self, font_dir: str = "assets/fonts"):
        self.font_dir = font_dir
        self.fonts = {
            "Roboto": "Roboto-Bold.ttf",
            "Montserrat": "Montserrat-SemiBold.ttf",
            "Bebas": "BebasNeue-Regular.ttf"
        }

    def get_font_path(self, font_name: str) -> str:
        filename = self.fonts.get(font_name, "Roboto-Bold.ttf")
        return os.path.join(self.font_dir, filename)

    def create_quote(
        self,
        content: str,
        author_name: str,
        author_handle: str,
        avatar_bytes: bytes,
        font_name: str = "Montserrat",
        brightness: float = 1.0,
        blur: bool = False,
        bg_color: Tuple[int, int, int] = (15, 15, 15)
    ) -> io.BytesIO:
        # Image settings
        width, height = 1000, 500
        # Create background with gradient
        base = Image.new('RGB', (width, height), bg_color)
        draw = ImageDraw.Draw(base)
        
        # Add subtle gradient from left to right
        for i in range(width):
            r = max(0, bg_color[0] + (i // 20))
            g = max(0, bg_color[1] + (i // 20))
            b = max(0, bg_color[2] + (i // 20))
            draw.line([(i, 0), (i, height)], fill=(min(r, 40), min(g, 40), min(b, 40)))

        # Process Avatar
        avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
        avatar = avatar.resize((350, 350), Image.Resampling.LANCZOS)
        
        # Create circular mask for avatar
        mask = Image.new('L', (350, 350), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, 350, 350), fill=255)
        
        # Apply mask and paste
        avatar_final = Image.new('RGBA', (350, 350), (0, 0, 0, 0))
        avatar_final.paste(avatar, (0, 0), mask)
        
        # Paste avatar on the left
        base.paste(avatar_final, (50, 75), avatar_final)

        # Draw Text
        font_path = self.get_font_path(font_name)
        
        # Content Font
        content_font_size = 50
        content_font = ImageFont.truetype(font_path, content_font_size)
        
        # Author Name Font
        author_font = ImageFont.truetype(font_path, 40)
        handle_font = ImageFont.truetype(font_path, 25)

        # Wrap content
        wrapped_text = textwrap.fill(content, width=30)
        
        # Draw wrapped text
        draw.multiline_text((450, 150), wrapped_text, font=content_font, fill=(255, 255, 255), align="left", spacing=10)

        # Draw Author Info
        y_pos = 150 + (len(wrapped_text.split('\n')) * (content_font_size + 10)) + 20
        draw.text((450, y_pos), f"- {author_name}", font=author_font, fill=(255, 255, 255))
        draw.text((450, y_pos + 50), f"@{author_handle}", font=handle_font, fill=(180, 180, 180))

        # Apply Brightness
        if brightness != 1.0:
            from PIL import ImageEnhance
            enhancer = ImageEnhance.Brightness(base)
            base = enhancer.enhance(brightness)

        # Apply Blur
        if blur:
            base = base.filter(ImageFilter.GaussianBlur(radius=2))

        # Save to buffer
        buf = io.BytesIO()
        base.save(buf, format='PNG')
        buf.seek(0)
        return buf

class QuoteView(discord.ui.View):
    def __init__(self, bot, generator, original_msg, author_name, author_handle, avatar_bytes):
        super().__init__(timeout=180)
        self.bot = bot
        self.generator = generator
        self.original_msg = original_msg
        self.author_name = author_name
        self.author_handle = author_handle
        self.avatar_bytes = avatar_bytes
        
        # Current State
        self.font = "Montserrat"
        self.brightness = 1.0
        self.blur = False
        self.bg_color = (15, 15, 15)

    async def update_message(self, interaction: discord.Interaction):
        await interaction.response.defer()
        buf = self.generator.create_quote(
            self.original_msg.clean_content,
            self.author_name,
            self.author_handle,
            self.avatar_bytes,
            font_name=self.font,
            brightness=self.brightness,
            blur=self.blur,
            bg_color=self.bg_color
        )
        file = discord.File(buf, filename="quote.png")
        await interaction.edit_original_response(attachments=[file], view=self)

    @discord.ui.button(label="☀️", style=discord.ButtonStyle.gray)
    async def brightness_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.brightness = 1.5 if self.brightness == 1.0 else 1.0
        await self.update_message(interaction)

    @discord.ui.button(label="🎨", style=discord.ButtonStyle.gray)
    async def color_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Cycle through some basic dark colors
        colors = [(15, 15, 15), (25, 10, 10), (10, 25, 10), (10, 10, 25)]
        idx = colors.index(self.bg_color)
        self.bg_color = colors[(idx + 1) % len(colors)]
        await self.update_message(interaction)

    @discord.ui.button(label="💧", style=discord.ButtonStyle.gray)
    async def blur_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.blur = not self.blur
        await self.update_message(interaction)

    @discord.ui.button(label="🗑️", style=discord.ButtonStyle.red)
    async def delete_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.delete()

    @discord.ui.select(placeholder="Select a font", options=[
        discord.SelectOption(label="Montserrat", value="Montserrat", default=True),
        discord.SelectOption(label="Roboto", value="Roboto"),
        discord.SelectOption(label="Bebas Neue", value="Bebas")
    ])
    async def font_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.font = select.values[0]
        # Update default state in options
        for option in select.options:
            option.default = (option.value == self.font)
        await self.update_message(interaction)

class Quote(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.generator = QuoteGenerator()
        self.ctx_menu = app_commands.ContextMenu(
            name='Quote',
            callback=self.quote_context_menu,
        )
        self.bot.tree.add_command(self.ctx_menu)

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(self.ctx_menu.name, type=self.ctx_menu.type)

    async def _fetch_avatar(self, user: discord.User) -> bytes:
        avatar_url = user.display_avatar.with_format("png").with_size(512).url
        async with aiohttp.ClientSession() as session:
            async with session.get(avatar_url) as resp:
                if resp.status == 200:
                    return await resp.read()
                raise RuntimeError("Failed to fetch avatar")

    async def quote_context_menu(self, interaction: discord.Interaction, message: discord.Message):
        await interaction.response.defer(thinking=True)
        try:
            avatar_bytes = await self._fetch_avatar(message.author)
            buf = self.generator.create_quote(
                message.clean_content,
                message.author.display_name,
                message.author.name,
                avatar_bytes
            )
            file = discord.File(buf, filename="quote.png")
            view = QuoteView(
                self.bot, 
                self.generator, 
                message, 
                message.author.display_name, 
                message.author.name, 
                avatar_bytes
            )
            await interaction.followup.send(file=file, view=view)
        except Exception as e:
            await interaction.followup.send(f"❌ Error generating quote: {e}", ephemeral=True)

    @app_commands.command(name="quote", description="Quote a message by ID or URL")
    @app_commands.describe(message_id_or_url="The ID or URL of the message to quote")
    async def quote_slash(self, interaction: discord.Interaction, message_id_or_url: Optional[str] = None):
        await interaction.response.defer(thinking=True)
        
        target_message = None
        if message_id_or_url:
            # Try parsing URL
            if "discord.com/channels/" in message_id_or_url:
                try:
                    parts = message_id_or_url.split('/')
                    # URL format: .../channels/guild_id/channel_id/message_id
                    m_id = int(parts[-1])
                    c_id = int(parts[-2])
                    channel = self.bot.get_channel(c_id) or await self.bot.fetch_channel(c_id)
                    if isinstance(channel, discord.abc.Messageable):
                        target_message = await channel.fetch_message(m_id)
                except:
                    pass
            else:
                # Try parsing ID in current channel
                try:
                    target_message = await interaction.channel.fetch_message(int(message_id_or_url))
                except:
                    pass
        
        if not target_message:
            # Try fetching the message being replied to
            if interaction.message and interaction.message.reference:
                target_message = interaction.message.reference.resolved
            else:
                # Get last message in channel (excluding the interaction itself if possible)
                async for msg in interaction.channel.history(limit=2):
                    if msg.author.id != self.bot.user.id:
                        target_message = msg
                        break

        if not target_message:
            return await interaction.followup.send("❌ Could not find message to quote.", ephemeral=True)

        try:
            avatar_bytes = await self._fetch_avatar(target_message.author)
            buf = self.generator.create_quote(
                target_message.clean_content or "[No text content]",
                target_message.author.display_name,
                target_message.author.name,
                avatar_bytes
            )
            file = discord.File(buf, filename="quote.png")
            view = QuoteView(
                self.bot, 
                self.generator, 
                target_message, 
                target_message.author.display_name, 
                target_message.author.name, 
                avatar_bytes
            )
            await interaction.followup.send(file=file, view=view)
        except Exception as e:
            await interaction.followup.send(f"❌ Error generating quote: {e}", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Quote(bot))
