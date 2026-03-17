import discord
from discord import app_commands
from discord.ext import commands
import os
import asyncio
from aiohttp import web
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Discord client and intents
BOT_VERSION = "2.3.2-AI-FIX"
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

class MyBot(commands.Bot):
    def __init__(self, proxy=None):
        super().__init__(command_prefix="!", intents=intents, proxy=proxy)
        self.BOT_VERSION = BOT_VERSION
        self.GUILD_ID = os.getenv("GUILD_ID")
        self.GUILD_OBJECT = discord.Object(id=int(self.GUILD_ID)) if self.GUILD_ID else None
        self.site = None

    async def setup_hook(self):
        # Start aiohttp server
        app = web.Application()
        app.router.add_get('/', lambda r: web.Response(text="Discord bot is online!"))
        runner = web.AppRunner(app)
        await runner.setup()
        port = int(os.environ.get('PORT', 8080))
        self.site = web.TCPSite(runner, '0.0.0.0', port)
        await self.site.start()
        print(f"✅ Health check server started on port {port}", flush=True)

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

        # Ensure the sync command itself is in the tree
        self.tree.add_command(self.sync_command)

        # Global Error Handler for App Commands
        @self.tree.error
        async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
            if isinstance(error, app_commands.CommandOnCooldown):
                await interaction.response.send_message(f"⏳ Command on cooldown. Try again in {error.retry_after:.2f}s.", ephemeral=True)
            elif isinstance(error, app_commands.MissingPermissions):
                await interaction.response.send_message(f"❌ You lack permissions: {', '.join(error.missing_permissions)}", ephemeral=True)
            else:
                print(f"❌ App Command Error: {error}", flush=True)
                try:
                    if not interaction.response.is_done():
                        await interaction.response.send_message(f"❌ An error occurred: {error}", ephemeral=True)
                    else:
                        await interaction.followup.send(f"❌ An error occurred: {error}", ephemeral=True)
                except Exception as e:
                    print(f"❌ Failed to send error message: {e}", flush=True)

        # Robust Sync
        sync_mode = os.getenv("SYNC_COMMANDS", "false").lower()
        if sync_mode == "true":
            try:
                if self.GUILD_OBJECT:
                    print(f"⚡ Syncing commands to Guild: {self.GUILD_ID}...", flush=True)
                    self.tree.copy_global_to(guild=self.GUILD_OBJECT)
                    synced = await self.tree.sync(guild=self.GUILD_OBJECT)
                    print(f"✅ {len(synced)} Guild commands synced to {self.GUILD_ID}.", flush=True)
                else:
                    print("⚡ Syncing commands globally...", flush=True)
                    synced = await self.tree.sync()
                    print(f"✅ {len(synced)} Global commands synced.", flush=True)
            except Exception as e:
                print(f"❌ Sync failed during setup_hook: {e}", flush=True)
        else:
            print(f"ℹ️ SYNC_COMMANDS is {sync_mode}. Skipping auto-sync. Use !sync or /sync.", flush=True)

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
                await interaction.followup.send(f"✅ Synced {len(synced)} commands globally.")
        except Exception as e:
            await interaction.followup.send(f"❌ Sync failed: {e}")

    async def on_ready(self):
        print(f"✅ VERSION {self.BOT_VERSION} active", flush=True)
        print(f"✅ Logged in as {self.user}", flush=True)
        await self.change_presence(activity=discord.Game(name="Casino Games | /balance"))

    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type == discord.InteractionType.application_command:
            print(f"📥 Received slash command: /{interaction.command.name if interaction.command else 'unknown'} from {interaction.user}", flush=True)
        await super().on_interaction(interaction)

async def main():
    token = os.getenv("DISCORD_TOKEN")
    proxy = os.getenv("DISCORD_PROXY")
    
    if not token:
        print("❌ ERROR: DISCORD_TOKEN not found in environment variables")
        return

    retry_count = 0
    max_retries = 10
    # faster retries
    wait_times = [5, 15, 30, 60, 120, 180, 180, 180, 180, 180]
    
    while retry_count < max_retries:
        bot = MyBot(proxy=proxy)
        try:
            print(f"🚀 Attempting login ({retry_count + 1}/{max_retries})...", flush=True)
            async with bot:
                await bot.start(token)
        except discord.errors.HTTPException as e:
            if e.status == 429:
                wait_time = wait_times[min(retry_count, len(wait_times) - 1)]
                print(f"⚠️ RATE LIMITED (429). Waiting {wait_time}s before retry...", flush=True)
                retry_count += 1
                await asyncio.sleep(wait_time)
            else:
                print(f"❌ HTTP Error: {e}", flush=True)
                break
        except Exception as e:
            print(f"❌ Unexpected error: {e}", flush=True)
            break
        finally:
            if not bot.is_closed():
                await bot.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
