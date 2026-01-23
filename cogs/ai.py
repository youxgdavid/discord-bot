import discord
from discord import app_commands
from discord.ext import commands
import os
import io
import random
import tempfile
import asyncio
from huggingface_hub import InferenceClient

HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN")
HF_MODEL = "stabilityai/stable-diffusion-xl-base-1.0"

async def generate_image_bytes(scene: str):
    client_hf = InferenceClient(token=HUGGINGFACE_TOKEN)
    def generate():
        img = client_hf.text_to_image(scene, model=HF_MODEL)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    return await asyncio.get_event_loop().run_in_executor(None, generate)

class RecreateView(discord.ui.View):
    def __init__(self, scene: str, user_id: int):
        super().__init__(timeout=180)
        self.scene = scene
        self.user_id = user_id

    async def handle_regeneration(self, interaction: discord.Interaction, prompt: str):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Not your generation!", ephemeral=True)
        try: await interaction.response.defer(thinking=True)
        except: return
        try:
            img_data = await generate_image_bytes(prompt)
            tmp = os.path.join(tempfile.gettempdir(), f"recreate_{interaction.id}.png")
            with open(tmp, "wb") as f: f.write(img_data)
            file = discord.File(tmp, filename="recreate.png")
            embed = discord.Embed(title=" AI Generated Image", description=f"**Prompt:** {prompt}", color=discord.Color.blurple())
            embed.set_image(url="attachment://recreate.png")
            await interaction.followup.send(embed=embed, file=file, view=RecreateView(prompt, self.user_id))
        except Exception as e:
            await interaction.followup.send(f"❌ Failed: {str(e)[:100]}", ephemeral=True)

    @discord.ui.button(label="Retry", style=discord.ButtonStyle.grey, row=0)
    async def retry(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_regeneration(interaction, self.scene)

    @discord.ui.button(label="Retry in different styles", style=discord.ButtonStyle.grey, row=0)
    async def retry_styles(self, interaction: discord.Interaction, button: discord.ui.Button):
        styles = ["cyberpunk", "oil painting", "pencil sketch", "anime", "photorealistic", "origami", "pixel art"]
        await self.handle_regeneration(interaction, f"{self.scene}, {random.choice(styles)} style")

    @discord.ui.button(label="Variation", style=discord.ButtonStyle.grey, row=1)
    async def variation(self, interaction: discord.Interaction, button: discord.ui.Button):
        modifiers = ["different lighting", "slightly different perspective", "more contrast", "softer colors"]
        await self.handle_regeneration(interaction, f"{self.scene}, {random.choice(modifiers)}")

    @discord.ui.button(label="Upscale", style=discord.ButtonStyle.grey, row=1)
    async def upscale(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_regeneration(interaction, f"{self.scene}, 4k, 8k, highly detailed, sharp focus, masterpiece")

    @discord.ui.button(label="Download", style=discord.ButtonStyle.grey, row=1)
    async def download(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(" To download, right-click the image and select **'Save Image'**!", ephemeral=True)

class AI(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="recreate", description="Generate an image using AI")
    async def recreate(self, interaction: discord.Interaction, scene: str):
        try: await interaction.response.defer(thinking=True)
        except: return
        if not HUGGINGFACE_TOKEN:
            return await interaction.followup.send("❌ Missing HF Token.", ephemeral=True)
        try:
            img_data = await generate_image_bytes(scene)
            tmp = os.path.join(tempfile.gettempdir(), f"recreate_{interaction.id}.png")
            with open(tmp, "wb") as f: f.write(img_data)
            file = discord.File(tmp, filename="recreate.png")
            embed = discord.Embed(title=" AI Generated Image", description=f"**Prompt:** {scene}", color=discord.Color.blurple())
            embed.set_image(url="attachment://recreate.png")
            await interaction.followup.send(embed=embed, file=file, view=RecreateView(scene, interaction.user.id))
        except Exception as e:
            error_msg = str(e)
            if "401" in error_msg: await interaction.followup.send("❌ Invalid HF Token.")
            elif "402" in error_msg: await interaction.followup.send("❌ Paid limit reached.")
            elif "429" in error_msg: await interaction.followup.send("❌ Too many requests.")
            else: await interaction.followup.send(f"❌ Failed: {error_msg[:100]}")

async def setup(bot: commands.Bot):
    await bot.add_cog(AI(bot))
