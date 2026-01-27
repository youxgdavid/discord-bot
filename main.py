import discord
from discord.ext import commands
import os
import asyncio
from flask import Flask
from threading import Thread
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create Flask app for uptime
app = Flask(__name__)

@app.route('/')
def home():
    return "Discord bot is online!"

def run():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# Start the web server
keep_alive()

# Discord client and intents
BOT_VERSION = "2.3.2-AI-FIX"
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        self.BOT_VERSION = BOT_VERSION
        self.GUILD_ID = os.getenv("GUILD_ID")
        self.GUILD_OBJECT = discord.Object(id=int(self.GUILD_ID)) if self.GUILD_ID else None

    async def setup_hook(self):
        print("--- STARTING COG LOAD ---", flush=True)
        # Load all cogs
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py') and not filename.startswith('__'):
                try:
                    await self.load_extension(f'cogs.{filename[:-3]}')
                    print(f"✅ Loaded extension: {filename}", flush=True)
                except Exception as e:
                    print(f"❌ Failed to load extension {filename}: {e}", flush=True)
        print("--- COG LOAD COMPLETE ---", flush=True)

        # Robust Sync
        sync_mode = os.getenv("SYNC_COMMANDS", "true").lower()
        if sync_mode == "true":
            try:
                if self.GUILD_OBJECT:
                    print(f"⚡ Syncing commands to Guild: {self.GUILD_ID}...", flush=True)
                    self.tree.copy_global_to(guild=self.GUILD_OBJECT)
                    synced = await self.tree.sync(guild=self.GUILD_OBJECT)
                    print(f"✅ {len(synced)} Guild commands synced.", flush=True)
                else:
                    print("⚡ Syncing commands globally...", flush=True)
                    synced = await self.tree.sync()
                    print(f"✅ {len(synced)} Global commands synced (may take up to an hour to propagate).", flush=True)
            except Exception as e:
                print(f"❌ Sync failed: {e}", flush=True)

    @app_commands.command(name="sync", description="Manually sync application commands")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def sync_command(self, interaction: discord.Interaction, scope: str = "guild"):
        """Syncs commands. Scope can be 'guild' or 'global'."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            if scope == "guild":
                self.tree.copy_global_to(guild=interaction.guild)
                synced = await self.tree.sync(guild=interaction.guild)
                await interaction.followup.send(f"✅ Synced {len(synced)} commands to this guild.")
            else:
                synced = await self.tree.sync()
                await interaction.followup.send(f"✅ Synced {len(synced)} commands globally. Propagation may take time.")
        except Exception as e:
            await interaction.followup.send(f"❌ Sync failed: {e}")

    async def on_ready(self):
        print(f"✅ VERSION {self.BOT_VERSION} active", flush=True)
        print(f"✅ Logged in as {self.user}", flush=True)
        await self.change_presence(activity=discord.Game(name="Casino Games | /balance"))

bot = MyBot()

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("❌ ERROR: DISCORD_TOKEN not found in environment variables")
    else:
        bot.run(token)
