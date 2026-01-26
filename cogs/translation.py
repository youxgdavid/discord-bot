import discord
from discord import app_commands
from discord.ext import commands
import json
import asyncio
from deep_translator import GoogleTranslator

TRANSLATE_CONFIG_FILE = "translate_configs.json"

def load_translate_configs():
    try:
        with open(TRANSLATE_CONFIG_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_translate_configs(configs):
    with open(TRANSLATE_CONFIG_FILE, 'w') as f:
        json.dump(configs, f, indent=2)

LANGUAGES = {
    "English": "en",
    "Spanish": "es",
    "French": "fr",
    "German": "de",
    "Italian": "it",
    "Portuguese": "pt",
    "Russian": "ru",
    "Chinese (Simplified)": "zh-cn",
    "Japanese": "ja",
    "Korean": "ko",
    "Arabic": "ar"
}

class Translation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        configs = load_translate_configs()
        channel_id = str(message.channel.id)

        if channel_id in configs:
            config = configs[channel_id]
            target_lang = config["target_lang"]

            if not message.content.strip():
                return

            try:
                loop = asyncio.get_event_loop()
                translation = await loop.run_in_executor(
                    None, 
                    lambda: GoogleTranslator(source='auto', target=target_lang).translate(message.content)
                )

                if translation and translation.strip().lower() != message.content.strip().lower():
                    embed = discord.Embed(
                        description=translation,
                        color=discord.Color.blue()
                    )
                    embed.set_author(name=f"{message.author.display_name} (Translated to {config['target_name']})", icon_url=message.author.display_avatar.url)
                    await message.channel.send(embed=embed)
            except Exception as e:
                print(f"Translation error in channel {channel_id}: {e}")

    @app_commands.command(name="translate_setup", description="Setup auto-translation for this channel")
    @app_commands.describe(target_language="The language to translate all messages to", status="Enable or disable auto-translation")
    @app_commands.choices(target_language=[
        app_commands.Choice(name=name, value=code) for name, code in LANGUAGES.items()
    ], status=[
        app_commands.Choice(name="Enable", value="enable"),
        app_commands.Choice(name="Disable", value="disable")
    ])
    @app_commands.checks.has_permissions(manage_channels=True)
    async def translate_setup(self, interaction: discord.Interaction, target_language: app_commands.Choice[str], status: app_commands.Choice[str]):
        await interaction.response.defer(ephemeral=True)
        configs = load_translate_configs()
        channel_id = str(interaction.channel_id)

        if status.value == "disable":
            if channel_id in configs:
                del configs[channel_id]
                save_translate_configs(configs)
                await interaction.followup.send("Auto-translation disabled for this channel.")
            else:
                await interaction.followup.send("Auto-translation was not enabled for this channel.")
            return

        configs[channel_id] = {
            "target_lang": target_language.value,
            "target_name": target_language.name
        }
        save_translate_configs(configs)

        await interaction.followup.send(
            f"Auto-translation enabled! All messages in this channel will be translated to **{target_language.name}**."
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(Translation(bot))

