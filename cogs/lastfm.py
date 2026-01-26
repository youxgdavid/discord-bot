import discord
from discord import app_commands
from discord.ext import commands
import os
import json
import aiohttp
from datetime import datetime, timezone
from typing import Optional

LAST_FM_API_KEY = os.getenv("LAST_FM_API_KEY")
LAST_FM_CONFIG_FILE = "lastfm_configs.json"

def load_lastfm_configs():
    try:
        with open(LAST_FM_CONFIG_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_lastfm_configs(configs):
    with open(LAST_FM_CONFIG_FILE, 'w') as f:
        json.dump(configs, f, indent=2)

async def fetch_lastfm_data(method, params):
    params.update({
        "method": method,
        "api_key": LAST_FM_API_KEY,
        "format": "json"
    })
    async with aiohttp.ClientSession() as session:
        async with session.get("http://ws.audioscrobbler.com/2.0/", params=params) as response:
            if response.status == 200:
                return await response.json()
            return None

class LastFM(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="set_fm", description="Link your Last.fm account")
    @app_commands.describe(username="Your Last.fm username")
    async def set_fm(self, interaction: discord.Interaction, username: str):
        configs = load_lastfm_configs()
        configs[str(interaction.user.id)] = username
        save_lastfm_configs(configs)
        await interaction.response.send_message(f"Last.fm account linked: **{username}**", ephemeral=True)

    @app_commands.command(name="np", description="Show what you are currently listening to")
    async def np(self, interaction: discord.Interaction, member: Optional[discord.Member] = None):
        target = member or interaction.user
        configs = load_lastfm_configs()
        username = configs.get(str(target.id))

        if not username:
            await interaction.response.send_message(
                f"{'You' if target == interaction.user else f'{target.display_name}'} haven't linked a Last.fm account. Use `/set_fm [username]` to link.",
                ephemeral=True
            )
            return

        await interaction.response.defer()

        try:
            # Get recent tracks (current playing)
            recent_data = await fetch_lastfm_data("user.getrecenttracks", {"user": username, "limit": 1})
            if not recent_data or "recenttracks" not in recent_data or not recent_data["recenttracks"]["track"]:
                await interaction.followup.send(f"Could not fetch data for **{username}**.")
                return

            track_data = recent_data["recenttracks"]["track"][0]
            artist = track_data["artist"]["#text"]
            track_name = track_data["name"]
            album = track_data["album"]["#text"]
            image_url = track_data["image"][-1]["#text"] # Large image
            
            # Check if currently playing
            now_playing = "@attr" in track_data and track_data["@attr"].get("nowplaying") == "true"
            status_text = "Now Playing" if now_playing else "Last Played"

            # Get track info for play count
            track_info = await fetch_lastfm_data("track.getInfo", {"user": username, "artist": artist, "track": track_name})
            user_playcount = "0"
            if track_info and "track" in track_info:
                user_playcount = track_info["track"].get("userplaycount", "0")

            # Get user info for total scrobbles
            user_info = await fetch_lastfm_data("user.getInfo", {"user": username})
            total_scrobbles = "0"
            if user_info and "user" in user_info:
                total_scrobbles = user_info["user"].get("playcount", "0")

            embed = discord.Embed(
                title=f"🎶 {status_text}",
                description=f"**[{track_name}](https://www.last.fm/music/{artist.replace(' ', '+')}/_/{track_name.replace(' ', '+')})**",
                color=discord.Color.red(),
                timestamp=datetime.now(timezone.utc)
            )
            embed.set_author(name=f"{target.display_name} ({username})", icon_url=target.display_avatar.url)
            embed.set_thumbnail(url=image_url)
            embed.add_field(name="👤 Artist", value=artist, inline=True)
            embed.add_field(name="💿 Album", value=album or "Unknown Album", inline=True)
            embed.set_footer(text=f"Plays: {user_playcount} | Total Scrobbles: {total_scrobbles}")

            await interaction.followup.send(embed=embed)

        except Exception as e:
            print(f"Last.fm error: {e}")
            await interaction.followup.send("❌ An error occurred while fetching Last.fm data.")

async def setup(bot: commands.Bot):
    await bot.add_cog(LastFM(bot))

