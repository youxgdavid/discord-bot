import discord
from discord import app_commands
from discord.ext import commands
import os
from datetime import datetime, timezone
from typing import Optional, cast

class Utility(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"✅ Cog Utility active")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        try:
            joined_time = member.joined_at.strftime("%Y-%m-%d %H:%M UTC") if member.joined_at else "Just now"
            embed = discord.Embed(
                title="👋 Welcome to the Server!",
                description=(
                    f"Hey **{member.name}**!\n\n"
                    "We're glad to have you here 💙\n\n"
                    "✨ **What you can do:**\n"
                    "• Play casino games 🎰\n"
                    "• Check your balance with `/balance`\n"
                    "• Compete on the `/leaderboard`\n"
                    "• Try games like Blackjack, Mines, Tower & Wordle\n\n"
                    "📌 **Tip:** Start with `/balance` to see your starting money!"
                ),
                color=discord.Color.blurple(),
                timestamp=datetime.now(timezone.utc)
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.add_field(name="🕒 Joined At", value=f"`{joined_time}`", inline=False)
            embed.set_footer(text="Enjoy your stay 🚀")
            await member.send(embed=embed)
        except discord.Forbidden:
            pass

    @app_commands.command(name="check_setup", description="Verify if bot tokens and version are correctly loaded")
    async def check_setup(self, interaction: discord.Interaction):
        # These are accessed from the bot's environment or attributes if we pass them
        hf_token = os.getenv("HUGGINGFACE_TOKEN")
        # ELEVEN_LABS_API_KEY was mentioned in main.py line 271 but not defined in the snippet I saw at the top. 
        # I'll check main.py again for it if needed, but for now I'll use getenv.
        el_key = os.getenv("ELEVEN_LABS_API_KEY")
        
        hf_status = "✅ Loaded" if hf_token else "❌ Missing"
        el_status = "✅ Loaded" if el_key else "❌ Missing"
        
        embed = discord.Embed(title="Bot Setup Diagnostic", color=discord.Color.blue())
        # BOT_VERSION would need to be passed or hardcoded
        version = getattr(self.bot, 'BOT_VERSION', "Unknown")
        embed.add_field(name="Bot Version", value=f"`{version}`", inline=False)
        embed.add_field(name="HuggingFace Token", value=hf_status, inline=True)
        embed.add_field(name="ElevenLabs Key", value=el_status, inline=True)
        
        if el_key:
            key_preview = f"{el_key[:4]}...{el_key[-4:]}" if len(el_key) > 8 else "Too short!"
            embed.add_field(name="ElevenLabs Key Preview", value=f"`{key_preview}`", inline=False)
        
        embed.set_footer(text="If anything is 'Missing', check your Render environment variables.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="ping", description="Check the bot's latency and status")
    async def ping(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        if latency < 100:
            color, status = discord.Color.green(), "Excellent"
        elif latency < 200:
            color, status = discord.Color.gold(), "Good"
        else:
            color, status = discord.Color.red(), "High Latency"

        embed = discord.Embed(title="🏓 Pong!", color=color, timestamp=datetime.now(timezone.utc))
        embed.add_field(name="📡 Latency", value=f"**{latency}ms**", inline=True)
        embed.add_field(name="🔌 Status", value=f"**{status}**", inline=True)
        embed.set_footer(text=f"Requested by {interaction.user}", icon_url=interaction.user.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="userinfo", description="Show information about a user")
    @app_commands.guild_only()
    async def userinfo(self, interaction: discord.Interaction, member: Optional[discord.Member] = None):
        if member is None:
            member = cast(discord.Member, interaction.user)
        embed = discord.Embed(title=f"User Info - {member}", color=discord.Color.blurple(), timestamp=datetime.now(timezone.utc))
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="🪪 ID", value=member.id, inline=False)
        embed.add_field(name="📛 Username", value=member.name, inline=False)
        embed.add_field(name="🎨 Nickname", value=member.display_name, inline=False)
        embed.add_field(name="📅 Joined Server", value=member.joined_at.strftime("%Y-%m-%d %H:%M:%S") if member.joined_at else "Unknown", inline=False)
        embed.add_field(name="🕰️ Account Created", value=member.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=False)
        embed.add_field(name="🎭 Roles", value=" ".join([role.mention for role in member.roles[1:]]) or "No roles", inline=False)
        embed.set_footer(text=f"Requested by {interaction.user}", icon_url=interaction.user.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="resync", description="Force resync slash commands")
    @app_commands.guild_only()
    async def resync(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            # We need to access tree from interaction or bot
            # tree = self.bot.tree # this should work if using commands.Bot
            await self.bot.tree.sync(guild=interaction.guild)
            await interaction.followup.send("Slash commands have been fully re-synced for this server.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Sync failed: {e}", ephemeral=True)

    @app_commands.command(name="cleanupglobals", description="Admin: clear global slash commands and resync guild")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    async def cleanupglobals(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            self.bot.tree.clear_commands(guild=None)
            await self.bot.tree.sync(guild=None)
            if interaction.guild:
                await self.bot.tree.sync(guild=interaction.guild)
            await interaction.followup.send("Cleared global commands and re-synced guild commands.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Cleanup failed: {e}", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Utility(bot))
