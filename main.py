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
        self.GUILD_ID = int(os.getenv("GUILD_ID", "868504571637547018"))
        self.GUILD_OBJECT = discord.Object(id=self.GUILD_ID)

    async def setup_hook(self):
        print("--- STARTING COG LOAD ---", flush=True)
        # Load all cogs for render uploading
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                try:
                    await self.load_extension(f'cogs.{filename[:-3]}')
                    print(f"✅ Loaded extension: {filename}", flush=True)
                except Exception as e:
                    print(f"❌ Failed to load extension {filename}: {e}", flush=True)
        print("--- COG LOAD COMPLETE ---", flush=True)

        # Sync commands
        if os.getenv("SYNC_COMMANDS", "true").lower() == "true":
            try:
                self.tree.copy_global_to(guild=self.GUILD_OBJECT)
                await self.tree.sync(guild=self.GUILD_OBJECT)
                print("⚡ Guild commands synced", flush=True)
            except Exception as e:
                print(f"❌ Sync failed: {e}", flush=True)

    async def on_ready(self):
        print(f"✅ VERSION {self.BOT_VERSION} active", flush=True)
        print(f"✅ Logged in as {self.user}", flush=True)
        await self.change_presence(activity=discord.Game(name="Casino Games | /balance"))

bot = MyBot()

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("ERROR: DISCORD_TOKEN not found in environment variables")
    else:
        bot.run(token)
