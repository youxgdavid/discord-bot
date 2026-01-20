import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View
from datetime import datetime, timezone, timedelta
from typing import Optional, cast
import os
import random
import json
import asyncio
import aiohttp
from flask import Flask
from threading import Thread
import tempfile
import io
import re
from dotenv import load_dotenv
from huggingface_hub import InferenceClient

# Load environment variables
load_dotenv()

# Create Flask app for uptime (e.g., Render)
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

# Start the web server (optional for hosting providers that require an HTTP server)
keep_alive()

# Discord client and intents
BOT_VERSION = "2.2.8-MMS-FIX"
intents = discord.Intents.default()
intents.members = True  # Required for member info like roles/join date
intents.message_content = True # Required for auto-translation to read messages

client = commands.Bot(command_prefix="!", intents=intents)
tree = client.tree

# Scope all slash commands to a single guild for instant updates
GUILD_ID = int(os.getenv("GUILD_ID", "868504571637547018"))
GUILD_OBJECT = discord.Object(id=GUILD_ID)

# Command sync controls
# Set SYNC_COMMANDS=false to prevent automatic sync on startup (useful when running multiple instances)
SYNC_COMMANDS = os.getenv("SYNC_COMMANDS", "true").lower() == "true"
# Set GLOBAL_COMMAND_CLEANUP=true for a single run to clear previously created GLOBAL commands
# This helps remove duplicates if you used to register commands globally
GLOBAL_COMMAND_CLEANUP = os.getenv("GLOBAL_COMMAND_CLEANUP", "false").lower() == "true"

# --- Translation System ---
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

# List of common languages for the setup command
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

# --- Last.fm System ---
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

# --- Currency System ---
CURRENCY_FILE = "player_balances.json"
STARTING_BALANCE = 10000

def load_balances():
    """Load player balances from file"""
    try:
        with open(CURRENCY_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_balances(balances):
    """Save player balances to file"""
    with open(CURRENCY_FILE, 'w') as f:
        json.dump(balances, f, indent=2)

def get_balance(user_id):
    """Get player's balance, create if doesn't exist"""
    balances = load_balances()
    if str(user_id) not in balances:
        balances[str(user_id)] = STARTING_BALANCE
        save_balances(balances)
    return balances[str(user_id)]

def update_balance(user_id, amount):
    """Update player's balance"""
    balances = load_balances()
    if str(user_id) not in balances:
        balances[str(user_id)] = STARTING_BALANCE
    balances[str(user_id)] += amount
    save_balances(balances)
    return balances[str(user_id)]

def can_afford(user_id, amount):
    """Check if player can afford the amount"""
    return get_balance(user_id) >= amount


def make_mod_embed(title, color, *, user, moderator, reason=None, extra_fields=None):
    """Build a consistent moderation embed UI."""
    embed = discord.Embed(
        title=title,
        color=color,
        timestamp=datetime.now(timezone.utc)
    )
    try:
        embed.set_thumbnail(url=user.display_avatar.url)
    except Exception:
        pass
    embed.add_field(name="Member", value=f"{getattr(user, 'mention', str(user))} (`{user.id}`)", inline=False)
    embed.add_field(name="Moderator", value=f"{getattr(moderator, 'mention', str(moderator))}", inline=True)
    embed.add_field(name="Reason", value=reason or "No reason provided", inline=True)
    if extra_fields:
        for name, value, inline in extra_fields:
            embed.add_field(name=name, value=value, inline=inline)
    return embed


@client.event
async def on_ready():
    print(f"✅ VERSION {BOT_VERSION} active")
    print(f"✅ Logged in as {client.user}")
    if SYNC_COMMANDS:
        try:
            await tree.sync(guild=GUILD_OBJECT)
            print("⚡ Guild commands synced")
        except Exception as e:
            print(f"❌ Sync failed: {e}")
    await client.change_presence(activity=discord.Game(name="Casino Games | /balance"))

@client.event
async def on_message(message: discord.Message):
    # Debug: Check if any message is seen
    # print(f"Message received from {message.author}: {message.content}")
    
    # Ignore bot messages to prevent loops
    if message.author.bot:
        return

    # Process other commands if any (needed for message commands)
    await client.process_commands(message)

    configs = load_translate_configs()
    channel_id = str(message.channel.id)

    if channel_id in configs:
        config = configs[channel_id]
        target_lang = config["target_lang"]

        if not message.content.strip():
            return

        print(f"Translating message in {channel_id}: {message.content[:50]}...")

        try:
            loop = asyncio.get_event_loop()
            
            # Translate from 'auto' to target language
            translation = await loop.run_in_executor(
                None, 
                lambda: GoogleTranslator(source='auto', target=target_lang).translate(message.content)
            )

            # Only send if translation exists and is different from original message
            # This handles the case where it's already in the target language
            if translation and translation.strip().lower() != message.content.strip().lower():
                embed = discord.Embed(
                    description=translation,
                    color=discord.Color.blue()
                )
                embed.set_author(name=f"{message.author.display_name} (Translated to {config['target_name']})", icon_url=message.author.display_avatar.url)
                await message.channel.send(embed=embed)
        except Exception as e:
            print(f"Translation error in channel {channel_id}: {e}")


@client.event
async def on_member_join(member: discord.Member):
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

# --- /ping command ---
@tree.command(name="ping", description="Check the bot's latency and status")
async def ping(interaction: discord.Interaction):
    latency = round(client.latency * 1000)
    
    # Determine color and status based on latency
    if latency < 100:
        color = discord.Color.green()
        status = "Excellent"
    elif latency < 200:
        color = discord.Color.gold()
        status = "Good"
    else:
        color = discord.Color.red()
        status = "High Latency"

    embed = discord.Embed(
        title="🏓 Pong!",
        color=color,
        timestamp=datetime.now(timezone.utc)
    )
    
    embed.add_field(name="📡 Latency", value=f"**{latency}ms**", inline=True)
    embed.add_field(name="🔌 Status", value=f"**{status}**", inline=True)
    
    embed.set_footer(text=f"Requested by {interaction.user}", icon_url=interaction.user.display_avatar.url)
    
    await interaction.response.send_message(embed=embed)

# --- Translation Commands ---
@tree.command(name="translate_setup", description="Setup auto-translation for this channel")
@app_commands.describe(target_language="The language to translate all messages to", status="Enable or disable auto-translation")
@app_commands.choices(target_language=[
    app_commands.Choice(name=name, value=code) for name, code in LANGUAGES.items()
], status=[
    app_commands.Choice(name="Enable", value="enable"),
    app_commands.Choice(name="Disable", value="disable")
])
@app_commands.checks.has_permissions(manage_channels=True)
async def translate_setup(interaction: discord.Interaction, target_language: app_commands.Choice[str], status: app_commands.Choice[str]):
    await interaction.response.defer(ephemeral=True)
    configs = load_translate_configs()
    channel_id = str(interaction.channel_id)

    if status.value == "disable":
        if channel_id in configs:
            del configs[channel_id]
            save_translate_configs(configs)
            await interaction.followup.send("✅ Auto-translation disabled for this channel.")
        else:
            await interaction.followup.send("❌ Auto-translation was not enabled for this channel.")
        return

    configs[channel_id] = {
        "target_lang": target_language.value,
        "target_name": target_language.name
    }
    save_translate_configs(configs)

    await interaction.followup.send(
        f"✅ Auto-translation enabled! All messages in this channel will be translated to **{target_language.name}**."
    )

# --- Last.fm Commands ---
@tree.command(name="set_fm", description="Link your Last.fm account")
@app_commands.describe(username="Your Last.fm username")
async def set_fm(interaction: discord.Interaction, username: str):
    configs = load_lastfm_configs()
    configs[str(interaction.user.id)] = username
    save_lastfm_configs(configs)
    await interaction.response.send_message(f"✅ Last.fm account linked: **{username}**", ephemeral=True)

@tree.command(name="np", description="Show what you are currently listening to")
async def np(interaction: discord.Interaction, member: Optional[discord.Member] = None):
    target = member or interaction.user
    configs = load_lastfm_configs()
    username = configs.get(str(target.id))

    if not username:
        await interaction.response.send_message(
            f"❌ {'You' if target == interaction.user else f'{target.display_name}'} haven't linked a Last.fm account. Use `/set_fm [username]` to link.",
            ephemeral=True
        )
        return

    await interaction.response.defer()

    try:
        # Get recent tracks (current playing)
        recent_data = await fetch_lastfm_data("user.getrecenttracks", {"user": username, "limit": 1})
        if not recent_data or "recenttracks" not in recent_data or not recent_data["recenttracks"]["track"]:
            await interaction.followup.send(f"❌ Could not fetch data for **{username}**.")
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

# --- /userinfo command ---
@tree.command(name="userinfo", description="Show information about a user")
@app_commands.guild_only()
async def userinfo(interaction: discord.Interaction, member: Optional[discord.Member] = None):
    if member is None:
        # In guild context (enforced by @guild_only), interaction.user is always a Member
        member = cast(discord.Member, interaction.user)

    embed = discord.Embed(
        title=f"User Info - {member}",
        color=discord.Color.blurple(),
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="🪪 ID", value=member.id, inline=False)
    embed.add_field(name="📛 Username", value=member.name, inline=False)
    embed.add_field(name="🎨 Nickname", value=member.display_name, inline=False)
    embed.add_field(name="📅 Joined Server", value=member.joined_at.strftime("%Y-%m-%d %H:%M:%S") if member.joined_at else "Unknown", inline=False)
    embed.add_field(name="🕰️ Account Created", value=member.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=False)
    embed.add_field(
        name="🎭 Roles",
        value=" ".join([role.mention for role in member.roles[1:]]) or "No roles",
        inline=False
    )
    embed.set_footer(text=f"Requested by {interaction.user}", icon_url=interaction.user.display_avatar.url)

    await interaction.response.send_message(embed=embed)

# --- /balance command ---
@tree.command(name="balance", description="Check your current balance")
async def balance(interaction: discord.Interaction):
    user_balance = get_balance(interaction.user.id)

    embed = discord.Embed(
        title="💰 Your Balance",
        color=discord.Color.gold(),
        timestamp=datetime.now(timezone.utc)
    )

    embed.add_field(
        name="💵 Current Balance",
        value=f"**${user_balance:,}**",
        inline=False
    )

    if user_balance >= 50000:
        embed.add_field(name="🏆 Status", value="💰 **Snus money God**", inline=True)
    elif user_balance >= 25000:
        embed.add_field(name="🏆 Status", value="💎 **Could by bare snus**", inline=True)
    elif user_balance >= 10000:
        embed.add_field(name="🏆 Status", value="💵 **Chilling atm**", inline=True)
    elif user_balance >= 1000:
        embed.add_field(name="🏆 Status", value="💸 **Get your money up not your funny up**", inline=True)
    else:
        embed.add_field(name="🏆 Status", value="💀 **Brokie**", inline=True)

    embed.set_footer(text=f"Requested by {interaction.user}", icon_url=interaction.user.display_avatar.url)

    await interaction.response.send_message(embed=embed)

# --- Wordle Game Logic ---
class WordleGame:
    def __init__(self):
        # Common 5-letter words for Wordle (feel free to add any different words)
        self.word_list = [
            "ABOUT", "ABOVE", "ABUSE", "ACTOR", "ACUTE", "ADMIT", "ADOPT", "ADULT", "AFTER", "AGAIN",
            "AGENT", "AGREE", "AHEAD", "ALARM", "ALBUM", "ALERT", "ALIEN", "ALIGN", "ALIKE", "ALIVE",
            "ALLOW", "ALONE", "ALONG", "ALTER", "AMONG", "ANGER", "ANGLE", "ANGRY", "APART", "APPLE",
            "APPLY", "ARENA", "ARGUE", "ARISE", "ARRAY", "ASIDE", "ASSET", "AUDIO", "AUDIT", "AVOID",
            "AWAKE", "AWARD", "AWARE", "BADLY", "BAKER", "BASES", "BASIC", "BEACH", "BEGAN", "BEGIN",
            "BEING", "BELOW", "BENCH", "BILLY", "BIRTH", "BLACK", "BLAME", "BLANK", "BLIND", "BLOCK",
            "BLOOD", "BOARD", "BOOST", "BOOTH", "BOUND", "BRAIN", "BRAND", "BRASS", "BRAVE", "BREAD",
            "BREAK", "BREED", "BRIEF", "BRING", "BROAD", "BROKE", "BROWN", "BUILD", "BUILT", "BUYER",
            "CABLE", "CALIF", "CARRY", "CATCH", "CAUSE", "CHAIN", "CHAIR", "CHAOS", "CHARM", "CHART",
            "CHASE", "CHEAP", "CHECK", "CHEST", "CHIEF", "CHILD", "CHINA", "CHOSE", "CIVIL", "CLAIM",
            "CLASS", "CLEAN", "CLEAR", "CLICK", "CLIMB", "CLOCK", "CLOSE", "CLOUD", "COACH", "COAST",
            "COULD", "COUNT", "COURT", "COVER", "CRAFT", "CRASH", "CRAZY", "CREAM", "CRIME", "CROSS",
            "CROWD", "CROWN", "CRUDE", "CURVE", "CYCLE", "DAILY", "DANCE", "DATED", "DEALT", "DEATH",
            "DEBUT", "DELAY", "DEPTH", "DOING", "DOUBT", "DOZEN", "DRAFT", "DRAMA", "DRANK", "DRAWN",
            "DREAM", "DRESS", "DRILL", "DRINK", "DRIVE", "DROVE", "DYING", "EAGER", "EARLY", "EARTH",
            "EIGHT", "ELITE", "EMPTY", "ENEMY", "ENJOY", "ENTER", "ENTRY", "EQUAL", "ERROR", "EVENT",
            "EVERY", "EXACT", "EXIST", "EXTRA", "FAITH", "FALSE", "FAULT", "FIBER", "FIELD", "FIFTH",
            "FIFTY", "FIGHT", "FINAL", "FIRST", "FIXED", "FLASH", "FLEET", "FLOOR", "FLUID", "FOCUS",
            "FORCE", "FORTH", "FORTY", "FORUM", "FOUND", "FRAME", "FRANK", "FRAUD", "FRESH", "FRONT",
            "FROST", "FRUIT", "FULLY", "FUNNY", "GIANT", "GIVEN", "GLASS", "GLOBE", "GOING", "GRACE",
            "GRADE", "GRAND", "GRANT", "GRASS", "GRAVE", "GREAT", "GREEN", "GROSS", "GROUP", "GROWN",
            "GUARD", "GUESS", "GUEST", "GUIDE", "HAPPY", "HARRY", "HEART", "HEAVY", "HORSE", "HOTEL",
            "HOUSE", "HUMAN", "IDEAL", "IMAGE", "INDEX", "INNER", "INPUT", "ISSUE", "JAPAN", "JIMMY",
            "JOINT", "JONES", "JUDGE", "KNOWN", "LABEL", "LARGE", "LASER", "LATER", "LAUGH", "LAYER",
            "LEARN", "LEASE", "LEAST", "LEAVE", "LEGAL", "LEVEL", "LEWIS", "LIGHT", "LIMIT", "LINKS",
            "LIVES", "LOCAL", "LOOSE", "LOWER", "LUCKY", "LUNCH", "LYING", "MAGIC", "MAJOR", "MAKER",
            "MARCH", "MARIA", "MATCH", "MAYBE", "MAYOR", "MEANT", "MEDIA", "METAL", "MIGHT", "MINOR",
            "MINUS", "MIXED", "MODEL", "MONEY", "MONTH", "MORAL", "MOTOR", "MOUNT", "MOUSE", "MOUTH",
            "MOVED", "MOVIE", "MUSIC", "NEEDS", "NEVER", "NEWLY", "NIGHT", "NOISE", "NORTH", "NOTED",
            "NOVEL", "NURSE", "OCCUR", "OCEAN", "OFFER", "OFTEN", "ORDER", "OTHER", "OUGHT", "PAINT",
            "PANEL", "PAPER", "PARTY", "PEACE", "PETER", "PHASE", "PHONE", "PHOTO", "PIANO", "PIECE",
            "PILOT", "PITCH", "PLACE", "PLAIN", "PLANE", "PLANT", "PLATE", "PLAZA", "PLUS", "POINT",
            "POUND", "POWER", "PRESS", "PRICE", "PRIDE", "PRIME", "PRINT", "PRIOR", "PRIZE", "PROOF",
            "PROUD", "PROVE", "QUEEN", "QUICK", "QUIET", "QUITE", "RADIO", "RAISE", "RANGE", "RAPID",
            "RATIO", "REACH", "READY", "REALM", "REBEL", "REFER", "RELAX", "REPAY", "REPLY", "RIGHT",
            "RIGID", "RIVER", "ROBIN", "ROGER", "ROMAN", "ROUGH", "ROUND", "ROUTE", "ROYAL", "RURAL",
            "SCALE", "SCENE", "SCOPE", "SCORE", "SENSE", "SERVE", "SETUP", "SEVEN", "SHALL", "SHAPE",
            "SHARE", "SHARP", "SHEET", "SHELF", "SHELL", "SHIFT", "SHINE", "SHIRT", "SHOCK", "SHOOT",
            "SHORT", "SHOWN", "SIDED", "SIGHT", "SILLY", "SINCE", "SIXTY", "SIZED", "SKILL", "SLEEP",
            "SLIDE", "SMALL", "SMART", "SMILE", "SMITH", "SMOKE", "SNAKE", "SNOW", "SOLAR", "SOLID",
            "SOLVE", "SORRY", "SOUND", "SOUTH", "SPACE", "SPARE", "SPEAK", "SPEED", "SPEND", "SPENT",
            "SPLIT", "SPOKE", "SPORT", "STAFF", "STAGE", "STAKE", "STAND", "START", "STATE", "STEAM",
            "STEEL", "STEEP", "STEER", "STEPS", "STICK", "STILL", "STOCK", "STONE", "STOOD", "STORE",
            "STORM", "STORY", "STRIP", "STUCK", "STUDY", "STUFF", "STYLE", "SUGAR", "SUITE", "SUPER",
            "SWEET", "TABLE", "TAKEN", "TASTE", "TAXES", "TEACH", "TEETH", "TERRY", "TEXAS", "THANK",
            "THEFT", "THEIR", "THEME", "THERE", "THESE", "THICK", "THING", "THINK", "THIRD", "THOSE",
            "THREE", "THREW", "THROW", "THUMB", "TIGHT", "TIMER", "TIMES", "TITLE", "TODAY", "TOPIC",
            "TOTAL", "TOUCH", "TOUGH", "TOWER", "TRACK", "TRADE", "TRAIN", "TREAT", "TREND", "TRIAL",
            "TRIBE", "TRICK", "TRIED", "TRIES", "TRUCK", "TRULY", "TRUNK", "TRUST", "TRUTH", "TWICE",
            "TWIST", "TYLER", "UNDER", "UNDUE", "UNION", "UNITY", "UNTIL", "UPPER", "UPSET", "URBAN",
            "USAGE", "USUAL", "VALID", "VALUE", "VIDEO", "VIRUS", "VISIT", "VITAL", "VOCAL", "WASTE",
            "WATCH", "WATER", "WAVES", "WAYS", "WEIRD", "WELSH", "WHEEL", "WHERE", "WHICH", "WHILE",
            "WHITE", "WHOLE", "WHOSE", "WOMAN", "WOMEN", "WORLD", "WORRY", "WORSE", "WORST", "WORTH",
            "WOULD", "WRITE", "WRONG", "WROTE", "YOUNG", "YOUTH"
        ]
        self.word_len = random.randint(1, 5)
        self.target_word = ''.join(random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ') for _ in range(self.word_len))
        self.guesses = []
        self.max_guesses = 5
        self.game_over = False
        self.won = False

    def make_guess(self, guess):
        """Process a guess and return the result"""
        if len(guess) != self.word_len:
            return None, f"Guess must be exactly {self.word_len} letters!"

        if not guess.isalpha():
            return None, "Guess must contain only letters!"

        guess = guess.upper()

        if guess in self.guesses:
            return None, "You already guessed that word!"

        self.guesses.append(guess)

        if guess == self.target_word:
            self.game_over = True
            self.won = True
            return self.get_guess_result(guess), "🎉 Congratulations! You guessed it!"

        if len(self.guesses) >= self.max_guesses:
            self.game_over = True
            return self.get_guess_result(guess), f"Game over! The word was: **{self.target_word}**"

        return self.get_guess_result(guess), "Keep guessing!"

    def get_guess_result(self, guess):
        """Get the colored result for a guess"""
        result = []
        target_letters = list(self.target_word)
        guess_letters = list(guess)

        # First pass: mark exact matches (green)
        for i in range(self.word_len):
            if guess_letters[i] == target_letters[i]:
                result.append("🟩")  # Green for correct position
                target_letters[i] = None  # Mark as used
                guess_letters[i] = None
            else:
                result.append("⬜")  # Default to white

        # Second pass: mark partial matches (yellow)
        for i in range(self.word_len):
            if guess_letters[i] is not None and guess_letters[i] in target_letters:
                result[i] = "🟨"  # Yellow for wrong position
                target_letters[target_letters.index(guess_letters[i])] = None  # Mark as used

        return "".join(result)

    def get_display_word(self):
        """Get the display word with correct letters revealed"""
        if self.game_over and not self.won:
            return self.target_word
        return "?" * self.word_len

    def get_guesses_display(self):
        """Get formatted display of all guesses"""
        if not self.guesses:
            return "No guesses yet"

        display = []
        for i, guess in enumerate(self.guesses):
            result = self.get_guess_result(guess)
            display.append(f"**{i+1}.** {guess} → {result}")

        return "\n".join(display)

    def get_letter_hints(self):
        """Get hints about correct letters and their positions"""
        if not self.guesses:
            return "No hints yet - make your first guess!"

        # Track letter status
        correct_letters = set()  # Letters in correct position
        wrong_position_letters = set()  # Letters in wrong position
        wrong_letters = set()  # Letters not in word

        for guess in self.guesses:
            target_letters = list(self.target_word)
            guess_letters = list(guess)

            # First pass: find exact matches
            for i in range(self.word_len):
                if guess_letters[i] == target_letters[i]:
                    correct_letters.add(guess_letters[i])
                    target_letters[i] = None
                    guess_letters[i] = None

            # Second pass: find wrong position letters
            for i in range(self.word_len):
                if guess_letters[i] is not None and guess_letters[i] in target_letters:
                    wrong_position_letters.add(guess_letters[i])
                    target_letters[target_letters.index(guess_letters[i])] = None  # Mark as used

        # Find completely wrong letters
        all_guessed_letters = set()
        for guess in self.guesses:
            all_guessed_letters.update(guess)

        wrong_letters = all_guessed_letters - correct_letters - wrong_position_letters

        # Build hints display
        hints = []

        if correct_letters:
            correct_list = sorted(list(correct_letters))
            hints.append(f"🟩 **Correct position:** `{', '.join(correct_list)}`")

        if wrong_position_letters:
            wrong_pos_list = sorted(list(wrong_position_letters))
            hints.append(f"🟨 **Wrong position:** `{', '.join(wrong_pos_list)}`")

        if wrong_letters:
            wrong_list = sorted(list(wrong_letters))
            hints.append(f"⬜ **Not in word:** `{', '.join(wrong_list)}`")

        if not hints:
            return "No hints yet - make your first guess!"

        return "\n".join(hints)

    def new_word(self):
        """Start a new game with a different word"""
        self.word_len = random.randint(1, 5)
        self.target_word = ''.join(random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ') for _ in range(self.word_len))
        self.guesses = []
        self.game_over = False
        self.won = False

# --- Blackjack Game Logic ---
class BlackjackGame:
    def __init__(self, bet_amount=0):
        self.deck = []
        self.player_hand = []
        self.dealer_hand = []
        self.bet_amount = bet_amount
        self.reset_deck()

    def reset_deck(self):
        """Create a standard 52-card deck"""
        suits = ['♠️', '♥️', '♣️', '♦️']
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        self.deck = [{'rank': rank, 'suit': suit} for suit in suits for rank in ranks]
        random.shuffle(self.deck)

    def deal_card(self):
        """Deal a card from the deck"""
        if len(self.deck) < 10:
            self.reset_deck()
        return self.deck.pop()

    def card_value(self, card):
        """Get the numeric value of a card"""
        rank = card['rank']
        if rank in ['J', 'Q', 'K']:
            return 10
        elif rank == 'A':
            return 11
        else:
            return int(rank)

    def calculate_hand(self, hand):
        """Calculate the total value of a hand, accounting for Aces"""
        total = sum(self.card_value(card) for card in hand)
        aces = sum(1 for card in hand if card['rank'] == 'A')

        # Adjust for Aces if total is over 21
        while total > 21 and aces > 0:
            total -= 10
            aces -= 1

        return total

    def hand_to_string(self, hand, hide_first=False):
        """Convert hand to readable string"""
        if hide_first and len(hand) > 0:
            cards = ['🂠'] + [f"{card['rank']}{card['suit']}" for card in hand[1:]]
        else:
            cards = [f"{card['rank']}{card['suit']}" for card in hand]
        return ' '.join(cards)

    def start_game(self):
        """Start a new game"""
        self.player_hand = [self.deal_card(), self.deal_card()]
        self.dealer_hand = [self.deal_card(), self.deal_card()]

class BlackjackView(View):
    def __init__(self, game, user_id):
        super().__init__(timeout=180)
        self.game = game
        self.user_id = user_id
        self.game_over = False
        self.bet_placed = False

    async def update_game(self, interaction: discord.Interaction, message: str):
        """Update the game display"""
        player_total = self.game.calculate_hand(self.game.player_hand)
        dealer_total = self.game.calculate_hand(self.game.dealer_hand)

        embed = discord.Embed(
            title="🎰 Blackjack",
            description=message,
            color=discord.Color.gold()
        )

        # Add betting information
        if self.game.bet_amount > 0:
            embed.add_field(
                name="💰 Bet Amount",
                value=f"**${self.game.bet_amount:,}**",
                inline=True
            )

        if self.game_over:
            embed.add_field(
                name="🎴 Your Hand",
                value=f"{self.game.hand_to_string(self.game.player_hand)}\n**Total: {player_total}**",
                inline=False
            )
            embed.add_field(
                name="🎴 Dealer's Hand",
                value=f"{self.game.hand_to_string(self.game.dealer_hand)}\n**Total: {dealer_total}**",
                inline=False
            )
        else:
            embed.add_field(
                name="🎴 Your Hand",
                value=f"{self.game.hand_to_string(self.game.player_hand)}\n**Total: {player_total}**",
                inline=False
            )
            embed.add_field(
                name="🎴 Dealer's Hand",
                value=f"{self.game.hand_to_string(self.game.dealer_hand, hide_first=True)}\n**Total: ?**",
                inline=False
            )

        await interaction.response.edit_message(embed=embed, view=self if not self.game_over else None)

    @discord.ui.button(label="Hit", style=discord.ButtonStyle.primary, emoji="👆")
    async def hit_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't your game!", ephemeral=True)
            return

        # Deal a card to the player
        self.game.player_hand.append(self.game.deal_card())
        player_total = self.game.calculate_hand(self.game.player_hand)

        if player_total > 21:
            self.game_over = True
            await self.update_game(interaction, "💥 **Bust! You went over 21. Dealer wins!**")
        elif player_total == 21:
            self.game_over = True
            await self.dealer_play(interaction)
        else:
            await self.update_game(interaction, "You drew a card. Hit or Stand?")

    @discord.ui.button(label="Stand", style=discord.ButtonStyle.secondary, emoji="✋")
    async def stand_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't your game!", ephemeral=True)
            return

        self.game_over = True
        await self.dealer_play(interaction)

    async def dealer_play(self, interaction: discord.Interaction):
        """Dealer plays according to standard rules (hit until 17+)"""
        player_total = self.game.calculate_hand(self.game.player_hand)

        # If player already busted, dealer doesn't need to play and the game should end.
        if player_total > 21:
            message = "💥 **Bust! You went over 21. Dealer wins!**"
            await self.update_game(interaction, message)
            return

        dealer_total = self.game.calculate_hand(self.game.dealer_hand)

        # Dealer hits until 17 or higher
        while dealer_total < 17:
            self.game.dealer_hand.append(self.game.deal_card())
            dealer_total = self.game.calculate_hand(self.game.dealer_hand)

        # Determine winner and handle money with automatically updated /balance and /leaderboard system.
        if dealer_total > 21:
            winnings = self.game.bet_amount * 2
            update_balance(self.user_id, winnings)
            message = f"🎉 **Dealer busts! You win ${winnings:,}!**"
        elif player_total > dealer_total:
            winnings = self.game.bet_amount * 2
            update_balance(self.user_id, winnings)
            message = f"🎉 **You win ${winnings:,}!**"
        elif player_total < dealer_total:
            message = f"😔 **Dealer wins! You lost ${self.game.bet_amount:,}**"
        else:
            # Tie - return bet
            update_balance(self.user_id, self.game.bet_amount)
            message = f"🤝 **It's a tie! Your bet of ${self.game.bet_amount:,} was returned**"

        await self.update_game(interaction, message)

class WordleView(View):
    def __init__(self, game, user_id):
        super().__init__(timeout=300)  # 5 minute timeout
        self.game = game
        self.user_id = user_id
        self.waiting_for_guess = False

    async def update_display(self, interaction: discord.Interaction, message: str = None):
        """Update the Wordle game display"""
        embed = discord.Embed(
            title="🎯 Wordle Game",
            color=discord.Color.green() if self.game.won else discord.Color.blue() if self.game.game_over else discord.Color.orange(),
            timestamp=datetime.now(timezone.utc)
        )

        if message:
            embed.description = message
        else:
            embed.description = f"Guess a {self.game.word_len}-letter word! You have **{self.game.max_guesses - len(self.game.guesses)}** guesses left."

        # Add game status
        status = "🎉 **WON!**" if self.game.won else "💀 **GAME OVER**" if self.game.game_over else "🔄 **IN PROGRESS**"
        embed.add_field(name="Status", value=status, inline=True)

        # Add target word (revealed if game over)
        target_display = self.game.get_display_word()
        embed.add_field(name="Target Word", value=f"`{target_display}`", inline=True)

        # Add guesses
        guesses_display = self.game.get_guesses_display()
        embed.add_field(name="Your Guesses", value=guesses_display, inline=False)

        # Add letter hints (if guessing the correct letter correct)
        letter_hints = self.game.get_letter_hints()
        embed.add_field(name="💡 Letter Hints", value=letter_hints, inline=False)

        # Add instructions
        if not self.game.game_over:
            embed.add_field(
                name="How to Play",
                value="🟩 = Correct letter, correct position\n🟨 = Correct letter, wrong position\n⬜ = Letter not in word",
                inline=False
            )

        embed.set_footer(text=f"Playing as {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)

        # Update buttons based on game state
        if self.game.game_over:
            self.clear_items()
            self.add_item(NewWordButton())
        else:
            if not self.waiting_for_guess:
                self.clear_items()
                self.add_item(GuessButton())
                self.add_item(NewWordButton())

        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Make a Guess", style=discord.ButtonStyle.primary, emoji="💭")
    async def guess_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't your game!", ephemeral=True)
            return

        if self.game.game_over:
            await interaction.response.send_message("The game is over! Start a new game.", ephemeral=True)
            return

        self.waiting_for_guess = True
        await interaction.response.send_modal(WordleGuessModal(self.game, self))

class WordleGuessModal(discord.ui.Modal):
    def __init__(self, game, view):
        super().__init__(title="Make Your Wordle Guess")
        self.game = game
        self.view = view

        self.guess_input = discord.ui.TextInput(
            label=f"Enter your {self.game.word_len}-letter word guess",
            placeholder="Type your guess here...",
            min_length=self.game.word_len,
            max_length=self.game.word_len,
            style=discord.TextStyle.short
        )
        self.add_item(self.guess_input)

    async def on_submit(self, interaction: discord.Interaction):
        guess = self.guess_input.value.strip().upper()

        result, message = self.game.make_guess(guess)

        if result is None:
            await interaction.response.send_message(f"❌ {message}", ephemeral=True)
            return

        self.view.waiting_for_guess = False
        await self.view.update_display(interaction, message)

class NewWordButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="New Word", style=discord.ButtonStyle.secondary, emoji="🔄")

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if interaction.user.id != view.user_id:
            await interaction.response.send_message("This isn't your game!", ephemeral=True)
            return

        view.game.new_word()
        view.waiting_for_guess = False
        await view.update_display(interaction, "🎯 New word selected! Start guessing!")

class GuessButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Make a Guess", style=discord.ButtonStyle.primary, emoji="💭")

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.view.user_id:
            await interaction.response.send_message("This isn't your game!", ephemeral=True)
            return

        if self.view.game.game_over:
            await interaction.response.send_message("The game is over! Start a new game.", ephemeral=True)
            return

        self.view.waiting_for_guess = True
        await interaction.response.send_modal(WordleGuessModal(self.view.game, self.view))

# --- /blackjack command ---
@tree.command(name="blackjack", description="Play a game of Blackjack with betting!")
@app_commands.describe(bet="Amount to bet (minimum 100)")
async def blackjack(interaction: discord.Interaction, bet: int = 100):
    # Validate bet amount
    if bet < 100:
        await interaction.response.send_message("❌ Minimum bet is $100!", ephemeral=True)
        return

    if bet > 10000:
        await interaction.response.send_message("❌ Maximum bet is $10,000!", ephemeral=True)
        return

    # Check if player can afford / place the bet
    if not can_afford(interaction.user.id, bet):
        balance = get_balance(interaction.user.id)
        await interaction.response.send_message(f"❌ You can't afford that bet! Your balance: ${balance:,}", ephemeral=True)
        return

    # Deduct bet from balance
    update_balance(interaction.user.id, -bet)

    game = BlackjackGame(bet_amount=bet)
    game.start_game()

    player_total = game.calculate_hand(game.player_hand)
    dealer_total = game.calculate_hand(game.dealer_hand)

    # Check for natural blackjack
    if player_total == 21:
        # Determine outcome when player has blackjack
        if dealer_total == 21:
            # Push - return bet
            update_balance(interaction.user.id, game.bet_amount)
            description = f"🤝 **Push! Both you and the dealer have Blackjack! Your bet of ${game.bet_amount:,} was returned**"
        else:
            # Blackjack win - 2.5x payout
            winnings = int(game.bet_amount * 2.5)
            update_balance(interaction.user.id, winnings)
            description = f"🎉 **BLACKJACK! You got 21 and win ${winnings:,}!**"

        embed = discord.Embed(
            title="🎰 Blackjack",
            description=description,
            color=discord.Color.gold()
        )

        # Add bet information
        embed.add_field(
            name="💰 Bet Amount",
            value=f"**${game.bet_amount:,}**",
            inline=True
        )
        embed.add_field(
            name="🎴 Your Hand",
            value=f"{game.hand_to_string(game.player_hand)}\n**Total: {player_total}**",
            inline=False
        )
        embed.add_field(
            name="🎴 Dealer's Hand",
            value=f"{game.hand_to_string(game.dealer_hand)}\n**Total: {dealer_total}**",
            inline=False
        )
        await interaction.response.send_message(embed=embed)
    else:
        view = BlackjackView(game, interaction.user.id)

        embed = discord.Embed(
            title="🎰 Blackjack",
            description="Hit to draw a card, or Stand to hold your hand!",
            color=discord.Color.gold()
        )

        # Add bet information
        embed.add_field(
            name="💰 Bet Amount",
            value=f"**${game.bet_amount:,}**",
            inline=True
        )
        embed.add_field(
            name="🎴 Your Hand",
            value=f"{game.hand_to_string(game.player_hand)}\n**Total: {player_total}**",
            inline=False
        )
        embed.add_field(
            name="🎴 Dealer's Hand",
            value=f"{game.hand_to_string(game.dealer_hand, hide_first=True)}\n**Total: ?**",
            inline=False
        )

        await interaction.response.send_message(embed=embed, view=view)

# --- /wordle command ---
@tree.command(name="wordle", description="Play a game of Wordle! Guess a 1-5 letter word in 5 tries.")
async def wordle(interaction: discord.Interaction):
    game = WordleGame()
    view = WordleView(game, interaction.user.id)

    embed = discord.Embed(
        title="🎯 Wordle Game",
        description=f"Guess a {game.word_len}-letter word! You have **{game.max_guesses}** guesses to get it right!",
        color=discord.Color.orange(),
        timestamp=datetime.now(timezone.utc)
    )

    embed.add_field(name="Status", value="🔄 **IN PROGRESS**", inline=True)
    embed.add_field(name="Target Word", value=f"`{'?' * game.word_len}`", inline=True)
    embed.add_field(name="Your Guesses", value="No guesses yet", inline=False)
    embed.add_field(name="💡 Letter Hints", value="No hints yet - make your first guess!", inline=False)
    embed.add_field(
        name="How to Play",
        value="🟩 = Correct letter, correct position\n🟨 = Correct letter, wrong position\n⬜ = Letter not in word",
        inline=False
    )
    embed.set_footer(text=f"Playing as {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)

    await interaction.response.send_message(embed=embed, view=view)

# --- BACCARAT GAME ---
class BaccaratGame:
    def __init__(self, user_id: int, bet: int, side: str):
        # side in {"player", "banker", "tie"}
        self.user_id = user_id
        self.bet = bet
        self.side = side
        self.shoe = self._build_shoe()
        self.player_hand = []
        self.banker_hand = []
        self.finished = False
        self.outcome = None  # "player", "banker", "tie"
        self.payout = 0
        self._deal_initial()
        self._resolve_naturals_or_draws()

    def _build_shoe(self):
        # 6-deck shoe for better randomness; map ranks to Baccarat values
        ranks = ['A'] + [str(i) for i in range(2, 10)] + ['10', 'J', 'Q', 'K']
        deck = ranks * 4  # one deck
        shoe = deck * 6
        random.shuffle(shoe)
        return shoe

    def _value(self, card_rank: str) -> int:
        if card_rank == 'A':
            return 1
        if card_rank in ['10', 'J', 'Q', 'K']:
            return 0
        return int(card_rank)

    def _score(self, hand) -> int:
        return sum(self._value(r) for r in hand) % 10

    def _draw(self):
        if not self.shoe:
            self.shoe = self._build_shoe()
        return self.shoe.pop()

    def _deal_initial(self):
        self.player_hand = [self._draw(), self._draw()]
        self.banker_hand = [self._draw(), self._draw()]

    def _resolve_naturals_or_draws(self):
        p, b = self._score(self.player_hand), self._score(self.banker_hand)
        # Natural 8/9 stops draw
        if p in (8, 9) or b in (8, 9):
            self._finalize()
            return
        # Third-card rules
        third_player = None
        if p <= 5:
            third_player = self._draw()
            self.player_hand.append(third_player)
            p = self._score(self.player_hand)
        # Banker draw rules depend on player's third card
        b_score = self._score(self.banker_hand)
        if third_player is None:
            if b_score <= 5:
                self.banker_hand.append(self._draw())
        else:
            tp_val = self._value(third_player)
            # Banker drawing table
            if b_score <= 2:
                self.banker_hand.append(self._draw())
            elif b_score == 3 and tp_val != 8:
                self.banker_hand.append(self._draw())
            elif b_score == 4 and tp_val in [2, 3, 4, 5, 6, 7]:
                self.banker_hand.append(self._draw())
            elif b_score == 5 and tp_val in [4, 5, 6, 7]:
                self.banker_hand.append(self._draw())
            elif b_score == 6 and tp_val in [6, 7]:
                self.banker_hand.append(self._draw())
        self._finalize()

    def _finalize(self):
        self.finished = True
        p, b = self._score(self.player_hand), self._score(self.banker_hand)
        if p > b:
            self.outcome = "player"
        elif b > p:
            self.outcome = "banker"
        else:
            self.outcome = "tie"
        self._calc_payout()

    def _calc_payout(self):
        # Standard payouts: Player 1:1, Banker 0.95:1, Tie 8:1
        if self.outcome == self.side:
            if self.side == "player":
                self.payout = self.bet * 2  # return + profit
            elif self.side == "banker":
                win = int(self.bet * 1.95)
                self.payout = win  # includes original bet
            else:
                self.payout = self.bet * 9
        else:
            # If tie occurs but bet was player/banker, bet is lost (common rules)
            self.payout = 0

    def hand_string(self, hand):
        # Clean compact string like A 9 | J (total 0-9)
        return " ".join(hand)

    def board_embed(self):
        p_score, b_score = self._score(self.player_hand), self._score(self.banker_hand)
        color = discord.Color.green() if self.outcome == self.side else discord.Color.red() if self.outcome else discord.Color.blurple()
        title = "Baccarat — Result" if self.finished else "Baccarat"
        embed = discord.Embed(title=title, color=color, timestamp=datetime.now(timezone.utc))
        embed.add_field(name="Player", value=f"{self.hand_string(self.player_hand)}\nTotal: **{p_score}**", inline=True)
        embed.add_field(name="Banker", value=f"{self.hand_string(self.banker_hand)}\nTotal: **{b_score}**", inline=True)
        bet_label = self.side.capitalize()
        embed.add_field(name="Your Bet", value=f"{bet_label} — ${self.bet:,}", inline=False)
        # Fancy result banner
        if self.finished:
            if self.outcome == 'tie':
                result = "It’s a TIE!"
            else:
                result = f"{self.outcome.upper()} wins"
            payout_text = f"Payout: **${self.payout:,}**" if self.payout else f"Lost: **${self.bet:,}**"
            embed.description = f"🎴 {result}\n{payout_text}"
        embed.set_footer(text="Baccarat • 6-deck shoe • Banker commission on wins")
        return embed


class BaccaratView(View):
    def __init__(self, game: 'BaccaratGame'):
        super().__init__(timeout=120)
        self.game = game
        # Only a "New Round" button when finished, otherwise none (game resolves instantly)
        if game.finished:
            self.add_item(BaccaratNewRoundButton())

    async def on_timeout(self):
        pass


class BaccaratNewRoundButton(Button):
    def __init__(self):
        super().__init__(label="New Round", style=discord.ButtonStyle.secondary, emoji="🔄")

    async def callback(self, interaction: discord.Interaction):
        # No session persisted; just instruct the user to run /baccarat again
        await interaction.response.send_message("Use /baccarat to start a new round.", ephemeral=True)


@tree.command(name="baccarat", description="Play Baccarat: bet on Player, Banker, or Tie with a sleek UI")
@app_commands.describe(bet="Amount to bet (min 100)", side="Choose your bet: player, banker, or tie")
@app_commands.choices(side=[
    app_commands.Choice(name="Player", value="player"),
    app_commands.Choice(name="Banker", value="banker"),
    app_commands.Choice(name="Tie", value="tie"),
])
async def baccarat(interaction: discord.Interaction, bet: int, side: app_commands.Choice[str]):
    # Validate bet
    if bet < 100:
        await interaction.response.send_message("❌ Minimum bet is $100!", ephemeral=True)
        return
    if bet > 1000000:
        await interaction.response.send_message("❌ Maximum bet is $1,000,000!", ephemeral=True)
        return

    # Check balance
    if not can_afford(interaction.user.id, bet):
        bal = get_balance(interaction.user.id)
        await interaction.response.send_message(f"❌ You don't have enough money! Your balance: ${bal:,}", ephemeral=True)
        return

    # Deduct bet
    update_balance(interaction.user.id, -bet)

    game = BaccaratGame(interaction.user.id, bet, side.value)

    # Compute winnings and update balance if any
    if game.payout:
        profit = game.payout - bet
        update_balance(interaction.user.id, game.payout)  # since bet already deducted, add back full payout
        result_note = f"✅ You won ${profit:,}!" if profit > 0 else "🤝 Push"
    else:
        result_note = f"❌ You lost ${bet:,}."

    # Build slick UI with gradient-like feel via emojis and clean layout
    embed = game.board_embed()
    banner = "🟩" if game.outcome == game.side else "🟥"
    header = f"{banner} Bet: {side.name} • ${bet:,}"
    embed.insert_field_at(0, name="", value=header, inline=False)

    view = BaccaratView(game)
    await interaction.response.send_message(embed=embed, view=view)

# --- MINES GAME ---
class MinesGame:
    def __init__(self, user_id, bet_amount, num_mines):
        self.user_id = user_id
        self.bet_amount = bet_amount
        self.num_mines = num_mines
        self.board_size = 20  # 5x5 grid
        self.revealed = set()
        self.game_over = False
        self.won = False
        self.multiplier = 1.0

        # Place mines randomly
        all_positions = list(range(self.board_size))
        self.mine_positions = set(random.sample(all_positions, num_mines))

    def reveal_tile(self, position):
        if position in self.revealed or self.game_over:
            return False

        self.revealed.add(position)

        if position in self.mine_positions:
            self.game_over = True
            self.won = False
            return False
        else:
            # Calculate multiplier based on mines and revealed tiles
            safe_tiles = self.board_size - self.num_mines
            revealed_safe = len(self.revealed)
            self.multiplier = 1.0 + (revealed_safe * (self.num_mines / safe_tiles) * 0.3)
            return True

    def cash_out(self):
        if not self.game_over and len(self.revealed) > 0:
            self.game_over = True
            self.won = True
            return int(self.bet_amount * self.multiplier)
        return 0

mines_games = {}

class MinesButton(Button):
    def __init__(self, position, row):
        super().__init__(style=discord.ButtonStyle.secondary, label="?", row=row)
        self.position = position

    async def callback(self, interaction: discord.Interaction):
        game = mines_games.get(interaction.user.id)

        if not game or game.game_over:
            await interaction.response.send_message("No active game! Use `/mines` to start.", ephemeral=True)
            return

        # Reveal the tile
        is_safe = game.reveal_tile(self.position)

        # Update button appearance
        if self.position in game.mine_positions:
            self.label = "💣"
            self.style = discord.ButtonStyle.danger
        else:
            self.label = "💎"
            self.style = discord.ButtonStyle.success

        self.disabled = True

        # Update the view
        if game.game_over:
            # Game over - reveal all mines
            for item in self.view.children:
                if isinstance(item, MinesButton):
                    if item.position in game.mine_positions:
                        item.label = "💣"
                        item.style = discord.ButtonStyle.danger
                    item.disabled = True

            if is_safe:
                pass
            else:
                # Hit a mine
                update_balance(interaction.user.id, -game.bet_amount)
                embed = discord.Embed(
                    title="💣 BOOM! You hit a mine!",
                    description=f"You lost **${game.bet_amount:,}**",
                    color=discord.Color.red()
                )
                await interaction.response.edit_message(embed=embed, view=self.view)
                del mines_games[interaction.user.id]
        else:
            # Still playing
            potential_win = int(game.bet_amount * game.multiplier)
            embed = discord.Embed(
                title="💎 Mines Game",
                description=f"Bet: **${game.bet_amount:,}** | Mines: **{game.num_mines}**",
                color=discord.Color.green()
            )
            embed.add_field(
                name="Current Multiplier",
                value=f"**{game.multiplier:.2f}x**",
                inline=True
            )
            embed.add_field(
                name="Potential Win",
                value=f"**${potential_win:,}**",
                inline=True
            )
            embed.add_field(
                name="Revealed",
                value=f"**{len(game.revealed)}** / {game.board_size - game.num_mines}",
                inline=True
            )
            embed.set_footer(text="Click a tile to reveal it, or click Cash Out to collect your winnings!")

            await interaction.response.edit_message(embed=embed, view=self.view)

class MinesView(View):
    def __init__(self, game):
        super().__init__(timeout=300)
        self.game = game

        # Add 20 buttons in 4 rows
        for i in range(20):
            row = i // 5
            self.add_item(MinesButton(i, row))

        # Add cash out button
        self.add_item(CashOutButton())

    async def on_timeout(self):
        if self.game.user_id in mines_games:
            del mines_games[self.game.user_id]

class CashOutButton(Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.success, label="💰 Cash Out", row=4)

    async def callback(self, interaction: discord.Interaction):
        game = mines_games.get(interaction.user.id)

        if not game:
            await interaction.response.send_message("No active game!", ephemeral=True)
            return

        if len(game.revealed) == 0:
            await interaction.response.send_message("You need to reveal at least one tile first!", ephemeral=True)
            return

        winnings = game.cash_out()
        profit = winnings - game.bet_amount
        update_balance(interaction.user.id, profit)

        # Disable all buttons
        for item in self.view.children:
            item.disabled = True

        embed = discord.Embed(
            title="💰 Cashed Out!",
            description=f"You won **${winnings:,}** (Profit: **${profit:,}**)",
            color=discord.Color.gold()
        )
        embed.add_field(name="Final Multiplier", value=f"{game.multiplier:.2f}x", inline=True)
        embed.add_field(name="Tiles Revealed", value=f"{len(game.revealed)}", inline=True)

        await interaction.response.edit_message(embed=embed, view=self.view)
        del mines_games[interaction.user.id]

@tree.command(name="mines", description="Play a mines game - reveal tiles without hitting mines!")
@app_commands.describe(
    bet="Amount to bet",
    mines="Number of mines (1-10)"
)
async def mines(interaction: discord.Interaction, bet: int, mines: int = 3):
    # Validation
    if mines < 1 or mines > 10:
        await interaction.response.send_message("❌ Mines must be between 1 and 10!", ephemeral=True)
        return

    if bet < 100:
        await interaction.response.send_message("❌ Minimum bet is $100!", ephemeral=True)
        return

    if not can_afford(interaction.user.id, bet):
        user_balance = get_balance(interaction.user.id)
        await interaction.response.send_message(
            f"❌ You don't have enough money! Your balance: ${user_balance:,}",
            ephemeral=True
        )
        return

    # Check if user already has an active game
    if interaction.user.id in mines_games:
        await interaction.response.send_message("❌ You already have an active mines game! Finish it first.", ephemeral=True)
        return

    # Create new game
    game = MinesGame(interaction.user.id, bet, mines)
    mines_games[interaction.user.id] = game

    embed = discord.Embed(
        title="💎 Mines Game",
        description=f"Bet: **${bet:,}** | Mines: **{mines}**\nReveal tiles to increase your multiplier!",
        color=discord.Color.blue()
    )
    embed.add_field(name="Current Multiplier", value="**1.00x**", inline=True)
    embed.add_field(name="Potential Win", value=f"**${bet:,}**", inline=True)
    embed.add_field(name="Revealed", value=f"**0** / {20 - mines}", inline=True)
    embed.set_footer(text="Click a tile to reveal it! Avoid the mines!")

    view = MinesView(game)
    await interaction.response.send_message(embed=embed, view=view)

@tree.command(name="clearmines", description="Clear your stuck mines game")
async def clearmines(interaction: discord.Interaction):
    if interaction.user.id in mines_games:
        del mines_games[interaction.user.id]
        await interaction.response.send_message("Done! Your mines game has been cleared!", ephemeral=True)
    else:
        await interaction.response.send_message("You do not have an active mines game.", ephemeral=True)

# --- TOWER GAME (with visual progress bar) ---
class TowerGame:
    def __init__(self, user_id, bet):
        self.user_id = user_id
        self.bet = bet
        self.level = 1
        self.max_levels = 10
        self.multiplier = 1.0
        self.game_over = False
        self.bomb_position = None

    def next_level(self):
        self.level += 1
        self.multiplier += 0.5
        self.bomb_position = random.randint(1, 3)

    def reset_bomb(self):
        self.bomb_position = random.randint(1, 3)

    def is_bomb(self, choice):
        return choice == self.bomb_position

    def progress_bar(self):
        """Return a nice visual progress bar showing current climb"""
        bar = ""
        for i in range(1, self.max_levels + 1):
            if i < self.level:
                bar += "⬛"
            elif i == self.level:
                bar += "🟩"
            else:
                bar += "⬜"
        return bar


tower_games = {}


class TowerButton(Button):
    def __init__(self, position):
        super().__init__(label=f"Tile {position}", style=discord.ButtonStyle.secondary)
        self.position = position

    async def callback(self, interaction: discord.Interaction):
        game = tower_games.get(interaction.user.id)
        if not game or game.game_over:
            await interaction.response.send_message("No active Tower game! Use `/tower` to start.", ephemeral=True)
            return

        if game.is_bomb(self.position):
            game.game_over = True
            update_balance(interaction.user.id, -game.bet)

            for item in self.view.children:
                if isinstance(item, TowerButton):
                    item.disabled = True
                    item.style = (
                        discord.ButtonStyle.danger if item.position == game.bomb_position else discord.ButtonStyle.success
                    )

            embed = discord.Embed(
                title="💣 BOOM! You hit a bomb!",
                description=f"You lost **${game.bet:,}**",
                color=discord.Color.red(),
            )
            embed.add_field(name="Progress", value=game.progress_bar(), inline=False)
            await interaction.response.edit_message(embed=embed, view=self.view)
            del tower_games[interaction.user.id]

        else:
            if game.level >= game.max_levels:
                winnings = int(game.bet * game.multiplier)
                profit = winnings - game.bet
                update_balance(interaction.user.id, profit)
                game.game_over = True

                for item in self.view.children:
                    item.disabled = True

                embed = discord.Embed(
                    title="🏆 You conquered the tower!",
                    description=f"You reached the top and won **${winnings:,}** (Profit: **${profit:,}**)",
                    color=discord.Color.gold(),
                )
                embed.add_field(name="Progress", value=game.progress_bar(), inline=False)
                await interaction.response.edit_message(embed=embed, view=self.view)
                del tower_games[interaction.user.id]
                return

            # Advance to next level
            game.next_level()
            embed = discord.Embed(
                title="🧱 Tower Game",
                description=f"Level: **{game.level} / {game.max_levels}**\nMultiplier: **{game.multiplier:.2f}x**\nBet: **${game.bet:,}**",
                color=discord.Color.blue(),
            )
            embed.add_field(name="Progress", value=game.progress_bar(), inline=False)
            embed.set_footer(text="Pick a tile! Cash out anytime to secure your winnings.")
            view = TowerView(game)
            await interaction.response.edit_message(embed=embed, view=view)


class CashOutTowerButton(Button):
    def __init__(self):
        super().__init__(label="💰 Cash Out", style=discord.ButtonStyle.success)

    async def callback(self, interaction: discord.Interaction):
        game = tower_games.get(interaction.user.id)
        if not game or game.game_over:
            await interaction.response.send_message("No active Tower game!", ephemeral=True)
            return

        winnings = int(game.bet * game.multiplier)
        profit = winnings - game.bet
        update_balance(interaction.user.id, profit)
        game.game_over = True

        for item in self.view.children:
            item.disabled = True

        embed = discord.Embed(
            title="💰 Cashed Out!",
            description=f"You cashed out at Level **{game.level}** and won **${winnings:,}** (Profit: **${profit:,}**)",
            color=discord.Color.gold(),
        )
        embed.add_field(name="Progress", value=game.progress_bar(), inline=False)
        await interaction.response.edit_message(embed=embed, view=self.view)
        del tower_games[interaction.user.id]


class TowerView(View):
    def __init__(self, game):
        super().__init__(timeout=300)
        self.game = game
        self.game.reset_bomb()

        for i in range(1, 4):
            self.add_item(TowerButton(i))
        self.add_item(CashOutTowerButton())

    async def on_timeout(self):
        if self.game.user_id in tower_games:
            del tower_games[self.game.user_id]


@tree.command(name="tower", description="Play a Tower casino game - climb levels and avoid bombs!")
@app_commands.describe(bet="Amount to bet")
async def tower(interaction: discord.Interaction, bet: int):
    if bet < 100:
        await interaction.response.send_message("❌ Minimum bet is $100!", ephemeral=True)
        return
    if not can_afford(interaction.user.id, bet):
        bal = get_balance(interaction.user.id)
        await interaction.response.send_message(f"❌ You don't have enough money! Your balance: ${bal:,}", ephemeral=True)
        return
    if interaction.user.id in tower_games:
        await interaction.response.send_message("❌ You already have an active Tower game!", ephemeral=True)
        return

    game = TowerGame(interaction.user.id, bet)
    tower_games[interaction.user.id] = game
    game.reset_bomb()

    embed = discord.Embed(
        title="🧱 Tower Game",
        description=f"Level: **1 / {game.max_levels}**\nMultiplier: **{game.multiplier:.2f}x**\nBet: **${bet:,}**",
        color=discord.Color.blurple(),
    )
    embed.add_field(name="Progress", value=game.progress_bar(), inline=False)
    embed.set_footer(text="Pick a tile! Avoid the bomb to climb higher!")

    view = TowerView(game)
    await interaction.response.send_message(embed=embed, view=view)


@tree.command(name="cleartower", description="Clear your stuck tower game")
async def cleartower(interaction: discord.Interaction):
    if interaction.user.id in tower_games:
        del tower_games[interaction.user.id]
        await interaction.response.send_message("✅ Your Tower game has been cleared!", ephemeral=True)
    else:
        await interaction.response.send_message("You don't have an active Tower game.", ephemeral=True)

# --- LEADERBOARD COMMAND ---
@tree.command(name="leaderboard", description="View the top players by total balance")
async def leaderboard(interaction: discord.Interaction):
    balances = load_balances()
    if not balances:
        await interaction.response.send_message("No player data yet!", ephemeral=True)
        return

    # Sort by balance descending
    sorted_players = sorted(balances.items(), key=lambda x: x[1], reverse=True)[:10]

    embed = discord.Embed(
        title="🏆 Casino Leaderboard",
        description="Top 10 richest players across all games",
        color=discord.Color.gold(),
        timestamp=datetime.now(timezone.utc)
    )

    leaderboard_text = ""
    rank_emojis = ["🥇", "🥈", "🥉"] + ["🏅"] * 7

    for i, (user_id, balance) in enumerate(sorted_players):
        try:
            user = await client.fetch_user(int(user_id))
            net_gain = balance - STARTING_BALANCE
            emoji = rank_emojis[i] if i < len(rank_emojis) else "🏅"
            sign = "+" if net_gain >= 0 else ""
            leaderboard_text += f"{emoji} **{user.name}** — 💰 ${balance:,}  (`{sign}{net_gain:,}`)\n"
        except Exception:
            pass

    embed.description = leaderboard_text or "No data yet!"
    embed.set_footer(text=f"Requested by {interaction.user}", icon_url=interaction.user.display_avatar.url)

    # Add top player's avatar as thumbnail
    try:
        top_user = await client.fetch_user(int(sorted_players[0][0]))
        embed.set_thumbnail(url=top_user.display_avatar.url)
    except Exception:
        pass

    await interaction.response.send_message(embed=embed)

# --- Clip That (chat) ---
@tree.command(name="clipthat", description="Clip last N seconds of chat into a clean log file")
@app_commands.describe(
    title="Title for the clip",
    seconds="Duration to capture (10-300 seconds)",
    include_attachments="Include attachment URLs in the clip"
)
async def clipthat(
    interaction: discord.Interaction,
    title: str,
    seconds: app_commands.Range[int, 10, 300] = 60,
    include_attachments: bool = True,
):
    channel = interaction.channel
    if not isinstance(channel, (discord.TextChannel, discord.Thread)):
        await interaction.response.send_message("Use this command in a text channel or thread.", ephemeral=True)
        return

    await interaction.response.defer(thinking=True)

    window_start = datetime.now(timezone.utc) - timedelta(seconds=int(seconds))

    # Gather messages in the window in chronological order
    messages = []
    try:
        async for msg in channel.history(limit=1000, after=window_start, oldest_first=True):
            messages.append(msg)
    except Exception as e:
        await interaction.followup.send(f"❌ Failed to read history: {e}", ephemeral=True)
        return

    if not messages:
        await interaction.followup.send("No messages in the selected window.", ephemeral=True)
        return

    # Sanitize title for filename
    safe_title = re.sub(r"[^A-Za-z0-9 _-]+", "", title).strip() or "clip"
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"{safe_title}_{ts}.txt"

    # Build the transcript
    lines = []
    header = f"=== Clip: {title} ===\nChannel: #{channel.name if hasattr(channel, 'name') else channel.id}\nWindow: last {seconds}s (since {window_start.strftime('%Y-%m-%d %H:%M:%S UTC')})\nGenerated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n=== Messages ===\n"
    lines.append(header)

    for m in messages:
        time_str = m.created_at.strftime('%H:%M:%S') + " UTC"
        author = f"{m.author.display_name} (@{m.author.name})"
        base = f"[{time_str}] {author}: {m.clean_content}".rstrip()
        lines.append(base)
        if m.reference and m.reference.resolved:
            ref = m.reference.resolved
            ref_author = getattr(ref.author, 'display_name', 'unknown')
            excerpt = (ref.clean_content or '').replace('\n', ' ')
            if len(excerpt) > 80:
                excerpt = excerpt[:77] + '...'
            lines.append(f"  ↩ reply to {ref_author}: {excerpt}")
        if include_attachments and m.attachments:
            for a in m.attachments:
                lines.append(f"  📎 attachment: {a.filename} <{a.url}>")
        if m.stickers:
            for s in m.stickers:
                lines.append(f"  🩹 sticker: {s.name}")
        if m.embeds:
            lines.append(f"  🔗 embeds: {len(m.embeds)}")

    transcript = "\n".join(lines)

    # Create in-memory file
    data = io.BytesIO(transcript.encode('utf-8'))
    file = discord.File(data, filename=filename)

    # Build a slick summary embed
    embed = discord.Embed(
        title=f"🎬 Clip Saved: {title}",
        description="A clean transcript of recent messages has been attached.",
        color=discord.Color.blurple(),
        timestamp=datetime.now(timezone.utc)
    )
    embed.add_field(name="Channel", value=channel.mention if hasattr(channel, 'mention') else str(channel.id), inline=True)
    embed.add_field(name="Duration", value=f"{seconds}s", inline=True)
    embed.add_field(name="Messages", value=str(len(messages)), inline=True)
    embed.set_footer(text=f"Requested by {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)

    await interaction.followup.send(embed=embed, file=file)

# --- Emoji Mosaic (image -> emoji grid) ---
from typing import List, Tuple, Dict

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
    best = None
    best_d = 1e18
    for (r,g,b), token in palette:
        dr = tr - r; dg = tg - g; db = tb - b
        d = dr*dr + dg*dg + db*db
        if d < best_d:
            best_d = d; best = token
    return best

def _emoji_token(e: discord.Emoji) -> str:
    # Renders as <:name:id> or <a:name:id>
    return f"<a:{e.name}:{e.id}>" if e.animated else f"<:{e.name}:{e.id}>"

async def _compute_emoji_avg_color(e: discord.Emoji) -> Tuple[int,int,int]:
    if e.id in _emoji_avg_cache:
        return _emoji_avg_cache[e.id]
    try:
        data = await _fetch_bytes(e.url)
        try:
            from PIL import Image
        except Exception:
            # If Pillow not installed, fallback to a neutral color
            avg = (200, 200, 200)
            _emoji_avg_cache[e.id] = avg
            return avg
        img = Image.open(io.BytesIO(data))
        if img.mode != 'RGB':
            img = img.convert('RGB')
        img = img.resize((16,16))
        pixels = list(img.getdata())
        n = len(pixels)
        r = sum(p[0] for p in pixels) // n
        g = sum(p[1] for p in pixels) // n
        b = sum(p[2] for p in pixels) // n
        avg = (r,g,b)
        _emoji_avg_cache[e.id] = avg
        return avg
    except Exception:
        # On failure, use neutral gray
        avg = (180,180,180)
        _emoji_avg_cache[e.id] = avg
        return avg

@tree.command(name="emojimosaic", description="Convert an image into an emoji mosaic using this server's emojis")
@app_commands.describe(
    image="Attach the source image (PNG/JPEG)",
    width="Number of emoji columns (10-60)",
    theme="Use all, static, or animated emojis",
    preview="Attach a PNG color-grid preview (requires Pillow)"
)
@app_commands.choices(theme=[
    app_commands.Choice(name="All", value="all"),
    app_commands.Choice(name="Static", value="static"),
    app_commands.Choice(name="Animated", value="animated"),
])
async def emojimosaic(
    interaction: discord.Interaction,
    image: discord.Attachment,
    width: app_commands.Range[int, 10, 60] = 30,
    theme: app_commands.Choice[str] = None,
    preview: bool = True,
):
    await interaction.response.defer(thinking=True)

    # Validate attachment
    if not image.content_type or not image.content_type.startswith('image/'):
        await interaction.followup.send("❌ Please attach a valid image (PNG/JPEG).", ephemeral=True)
        return

    # Try to import Pillow lazily
    try:
        from PIL import Image, ImageDraw
    except Exception:
        await interaction.followup.send(
            "❌ This command requires Pillow. Add 'Pillow>=9.0.0' to your requirements and redeploy.",
            ephemeral=True
        )
        return

    # Download user image
    try:
        img_bytes = await image.read()
    except Exception as e:
        await interaction.followup.send(f"❌ Failed to read image: {e}", ephemeral=True)
        return

    try:
        src = Image.open(io.BytesIO(img_bytes))
        if src.mode != 'RGB':
            src = src.convert('RGB')
    except Exception as e:
        await interaction.followup.send(f"❌ Could not decode image: {e}", ephemeral=True)
        return

    # Determine target size
    w, h = src.size
    aspect = h / max(1, w)
    tgt_w = int(width)
    tgt_h = max(1, int(round(tgt_w * aspect)))
    # Limit rows to avoid massive messages
    if tgt_h > 60:
        scale = 60 / tgt_h
        tgt_w = max(10, int(round(tgt_w * scale)))
        tgt_h = 60

    # Resize to sampling grid
    small = src.resize((tgt_w, tgt_h), Image.Resampling.BILINEAR)
    pixels = list(small.getdata())  # row-major

    # Build emoji palette
    use_mode = (theme.value if theme else 'all')
    emoji_palette: List[Tuple[Tuple[int,int,int], str]] = []

    # Collect guild emojis
    try:
        if interaction.guild:
            candidates = [e for e in interaction.guild.emojis]
            if use_mode == 'static':
                candidates = [e for e in candidates if not e.animated]
            elif use_mode == 'animated':
                candidates = [e for e in candidates if e.animated]
            # Cap to avoid long first-time fetches
            candidates = candidates[:150]
            # Compute avg colors
            for e in candidates:
                avg = await _compute_emoji_avg_color(e)
                emoji_palette.append((avg, _emoji_token(e)))
    except Exception:
        pass

    # Fallback palette if no guild emojis
    if not emoji_palette:
        for ch, rgb in _unicode_square_palette:
            emoji_palette.append((rgb, ch))

    # Map pixels to emojis
    lines: List[str] = []
    idx = 0
    for y in range(tgt_h):
        row_tokens = []
        for x in range(tgt_w):
            r,g,b = pixels[idx]; idx += 1
            token = _nearest_color((r,g,b), emoji_palette)
            row_tokens.append(token)
        lines.append(''.join(row_tokens))

    mosaic_text = "\n".join(lines)

    # Prepare files/embeds
    files = []
    embed = discord.Embed(
        title="🧩 Emoji Mosaic",
        description=f"Size: **{tgt_w}×{tgt_h}**  |  Emojis used: **{len(emoji_palette)}**",
        color=discord.Color.purple(),
        timestamp=datetime.now(timezone.utc),
    )
    embed.add_field(name="Source", value=image.filename or "image", inline=True)
    embed.add_field(name="Theme", value=use_mode, inline=True)

    # If message likely too long, attach as file
    if len(mosaic_text) > 1500:
        data = io.BytesIO(mosaic_text.encode('utf-8'))
        files.append(discord.File(data, filename="mosaic.txt"))
        embed.add_field(name="Mosaic", value="Attached as mosaic.txt (too large to inline)", inline=False)
    else:
        embed.add_field(name="Mosaic", value=mosaic_text, inline=False)

    # Optional PNG preview (color blocks)
    if preview:
        try:
            tile = 12
            prev = Image.new('RGB', (tgt_w*tile, tgt_h*tile), (0,0,0))
            draw = ImageDraw.Draw(prev)
            idx = 0
            for y in range(tgt_h):
                for x in range(tgt_w):
                    r,g,b = pixels[idx]; idx += 1
                    draw.rectangle([x*tile, y*tile, x*tile+tile, y*tile+tile], fill=(r,g,b))
            buf = io.BytesIO()
            prev.save(buf, format='PNG')
            buf.seek(0)
            files.append(discord.File(buf, filename='mosaic_preview.png'))
            embed.set_image(url="attachment://mosaic_preview.png")
        except Exception:
            pass

    await interaction.followup.send(embed=embed, files=files)

# --- Image generation via Hugging Face Inference API ---
HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN")
ELEVEN_LABS_API_KEY = os.getenv("ELEVEN_LABS_API_KEY")

HF_MODEL = "stabilityai/stable-diffusion-3.5-large"
@tree.command(name="recreate", description="Generate an image using AI")
async def recreate(interaction: discord.Interaction, scene: str):
    try:
        await interaction.response.defer(thinking=True)
    except: return
    if not HUGGINGFACE_TOKEN:
        await interaction.followup.send("❌ Missing HF Token.", ephemeral=True)
        return
    try:
        client_hf = InferenceClient(api_key=HUGGINGFACE_TOKEN)
        img_bytes = await asyncio.get_event_loop().run_in_executor(None, lambda: client_hf.text_to_image(scene, model=HF_MODEL))
        tmp = os.path.join(tempfile.gettempdir(), f"recreate_{interaction.id}.png")
        with open(tmp, "wb") as f: f.write(img_bytes.read() if hasattr(img_bytes, 'read') else img_bytes)
        file = discord.File(tmp, filename="recreate.png")
        embed = discord.Embed(title="🖼️ AI Generated Image", description=f"**Prompt:** {scene}", color=discord.Color.blurple())
        embed.set_image(url="attachment://recreate.png")
        await interaction.followup.send(embed=embed, file=file)
    except Exception as e:
        await interaction.followup.send(f"❌ Failed: {str(e)[:100]}")

# --- AI Voices Feature ---
AI_VOICE_MODEL = "meta-llama/Llama-3.1-8B-Instruct"

PERSONAS = {
    "Donald Trump": "You are Donald Trump. Speak in his iconic style: use superlatives like 'tremendous', 'huge', 'disaster'. Mention building walls and winning.",
    "Gordon Ramsay": "You are Gordon Ramsay. You are extremely angry and critical. Use culinary insults like 'idiot sandwich', 'raw', 'disgrace'.",
    "Snoop Dogg": "You are Snoop Dogg. Speak in a very relaxed, laid-back manner. Use slang like 'fo shizzle', 'my nizzle'.",
    "Elon Musk": "You are Elon Musk. Talk about Mars, rockets, X, and the future. Use technical jargon and mention 'first principles'.",
    "Arnold Schwarzenegger": "You are Arnold Schwarzenegger. Speak like a tough action hero with catchphrases like 'I'll be back'.",
    "Morgan Freeman": "You are Morgan Freeman. Speak with a calm, wise, and authoritative voice. Use sophisticated language."
}

# Mapping personas to ElevenLabs Voice IDs
# You can find more voice IDs at https://elevenlabs.io/app/voice-lab
PERSONA_VOICES = {
    "Donald Trump": "cgSgS1p8qyau9n9Pym8r", # Marcus
    "Gordon Ramsay": "nPczCjzI2it9tZRW8uAV", # Brian
    "Snoop Dogg": "cgSgS1p8qyau9n9Pym8r", # Marcus
    "Elon Musk": "TX3LPaxmHKxFfWec9sWn", # Liam
    "Arnold Schwarzenegger": "cgSgS1p8qyau9n9Pym8r", # Marcus
    "Morgan Freeman": "cgSgS1p8qyau9n9Pym8r" # Marcus
}

@tree.command(name="ai_voice", description="Ask a famous person a question!")
@app_commands.describe(character="The famous person", question="The question")
@app_commands.choices(character=[app_commands.Choice(name=n, value=n) for n in PERSONAS.keys()])
async def ai_voice(interaction: discord.Interaction, character: app_commands.Choice[str], question: str):
    try:
        await interaction.response.defer(thinking=True)
    except: return
    if not HUGGINGFACE_TOKEN:
        await interaction.followup.send("❌ Missing HF Token.", ephemeral=True)
        return
    if not ELEVEN_LABS_API_KEY:
        await interaction.followup.send("❌ Missing ElevenLabs API Key. Add `ELEVEN_LABS_API_KEY` to your secrets.", ephemeral=True)
        return
    
    persona_prompt = PERSONAS[character.value]
    try:
        client_hf = InferenceClient(token=HUGGINGFACE_TOKEN)
        loop = asyncio.get_event_loop()
        
        def generate_text():
            try:
                messages = [{"role": "system", "content": persona_prompt}, {"role": "user", "content": question}]
                response = client_hf.chat_completion(messages=messages, model=AI_VOICE_MODEL, max_tokens=150, temperature=0.7)
                return response.choices[0].message.content.strip()
            except Exception as e: return f"Text Error: {str(e)}"
        
        ai_response = await loop.run_in_executor(None, generate_text)
        
        audio_file = None
        audio_status = "Audio pending..."
        
        if not ai_response.startswith("Text Error:"):
            tts_text = ai_response[:250].replace("*", "").replace("#", "").replace("`", "")
            voice_id = PERSONA_VOICES.get(character.value, "nPczCjzI2it9tZRW8uAV") # Default to Brian
            
            try:
                async with aiohttp.ClientSession() as session:
                    # ElevenLabs API
                    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
                    headers = {
                        "xi-api-key": ELEVEN_LABS_API_KEY,
                        "Content-Type": "application/json"
                    }
                    data = {
                        "text": tts_text,
                        "model_id": "eleven_monolingual_v1",
                        "voice_settings": {
                            "stability": 0.5,
                            "similarity_boost": 0.75
                        }
                    }
                    async with session.post(url, headers=headers, json=data, timeout=30) as resp:
                        if resp.status == 200:
                            audio_data = await resp.read()
                            if len(audio_data) > 100:
                                tmp = os.path.join(tempfile.gettempdir(), f"voice_{interaction.id}.mp3")
                                with open(tmp, "wb") as f:
                                    f.write(audio_data)
                                audio_file = discord.File(tmp, filename="voice.mp3")
                                audio_status = "Audio ready!"
                            else:
                                audio_status = "Audio failed (Empty result)"
                        else:
                            error_info = await resp.text()
                            print(f"DEBUG: ElevenLabs API error {resp.status}: {error_info}")
                            audio_status = f"Audio error ({resp.status})"
            except Exception as e:
                print(f"DEBUG: ElevenLabs Request exception: {e}")
                audio_status = f"Audio failed (Request Error)"

        embed = discord.Embed(
            title=f"🗣️ {character.value} Responds", 
            description=f"**Q:** {question}\n\n**A:** {ai_response}\n\n*Click the file below to hear the voice!*", 
            color=discord.Color.random(), 
            timestamp=datetime.now(timezone.utc)
        )
        footer = f"Requested by {interaction.user.display_name} • {audio_status}"
        embed.set_footer(text=footer, icon_url=interaction.user.display_avatar.url)

        if audio_file:
            msg = await interaction.followup.send(embed=embed, file=audio_file)
            try:
                await asyncio.sleep(1)
                msg = await interaction.followup.fetch_message(msg.id)
                if msg.attachments:
                    view = View()
                    view.add_item(Button(label="Download / Listen", url=msg.attachments[0].url, style=discord.ButtonStyle.link, emoji="📥"))
                    await msg.edit(view=view)
            except Exception as e: print(f"DEBUG: Button error: {e}")
        else:
            await interaction.followup.send(embed=embed)
            
    except Exception as e:
        print(f"DEBUG: Global error: {e}")
        await interaction.followup.send(f"❌ Error: {str(e)[:100]}")

# --- Force re-sync ---
@tree.command(name="resync", description="Force resync slash commands")
@app_commands.guild_only()
async def resync(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True, thinking=True)
    try:
        await tree.sync(guild=GUILD_OBJECT)
        await interaction.followup.send(
            "✅ Slash commands have been fully re-synced for this server.\nIf you don't see updates yet, restart Discord (Ctrl+R).",
            ephemeral=True,
        )
    except Exception as e:
        await interaction.followup.send(f"❌ Sync failed: {e}", ephemeral=True)


# Admin-only tool: clear global commands and re-sync the guild
@tree.command(name="cleanupglobals", description="Admin: clear global slash commands and resync guild")
@app_commands.guild_only()
@app_commands.default_permissions(administrator=True)
async def cleanupglobals(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True, thinking=True)
    try:
        tree.clear_commands(guild=None)
        await tree.sync(guild=None)
        await tree.sync(guild=GUILD_OBJECT)
        await interaction.followup.send(
            "✅ Cleared global commands and re-synced guild commands.",
            ephemeral=True,
        )
    except Exception as e:
        await interaction.followup.send(f"❌ Cleanup failed: {e}", ephemeral=True)


# --- Moderation Commands ---
@tree.command(name="ban", description="Ban a member from the server")
@app_commands.guild_only()
@app_commands.describe(member="Member to ban", reason="Reason for the ban", delete_days="Delete message history (0-7 days)")
@app_commands.checks.has_permissions(ban_members=True)
async def ban_member(
    interaction: discord.Interaction,
    member: discord.Member,
    reason: Optional[str] = None,
    delete_days: app_commands.Range[int, 0, 7] = 0,
):
    if member.id == interaction.user.id:
        await interaction.response.send_message("❌ You cannot ban yourself.", ephemeral=True)
        return
    if interaction.guild and interaction.guild.owner_id == member.id:
        await interaction.response.send_message("❌ You cannot ban the server owner.", ephemeral=True)
        return
    if interaction.guild and interaction.user != interaction.guild.owner and interaction.user.top_role <= member.top_role:
        await interaction.response.send_message("❌ You cannot ban a member with an equal or higher role.", ephemeral=True)
        return
    me = interaction.guild.me if interaction.guild else None
    if me and me.top_role <= member.top_role:
        await interaction.response.send_message("❌ I cannot ban that member due to role hierarchy.", ephemeral=True)
        return

    # Try DM first (before ban blocks DMs)
    dm_embed = make_mod_embed(
        title=f"You have been banned from {interaction.guild.name}",
        color=discord.Color.red(),
        user=member,
        moderator=interaction.user,
        reason=reason,
    )
    try:
        await member.send(embed=dm_embed)
    except discord.Forbidden:
        pass
    except Exception:
        pass

    try:
        await member.ban(reason=reason or f"Banned by {interaction.user}", delete_message_seconds=int(delete_days) * 86400)
        embed = make_mod_embed(
            title="🔨 Member Banned",
            color=discord.Color.red(),
            user=member,
            moderator=interaction.user,
            reason=reason,
            extra_fields=[("Deleted Messages", f"{delete_days} days", True)],
        )
        await interaction.response.send_message(embed=embed)
    except discord.Forbidden:
        await interaction.response.send_message("❌ I lack permission to ban this member.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Ban failed: {e}", ephemeral=True)


@tree.command(name="kick", description="Kick a member from the server")
@app_commands.guild_only()
@app_commands.describe(member="Member to kick", reason="Reason for the kick")
@app_commands.checks.has_permissions(kick_members=True)
async def kick_member(
    interaction: discord.Interaction,
    member: discord.Member,
    reason: Optional[str] = None,
):
    if member.id == interaction.user.id:
        await interaction.response.send_message("❌ You cannot kick yourself.", ephemeral=True)
        return
    if interaction.guild and interaction.guild.owner_id == member.id:
        await interaction.response.send_message("❌ You cannot kick the server owner.", ephemeral=True)
        return
    if interaction.guild and interaction.user != interaction.guild.owner and interaction.user.top_role <= member.top_role:
        await interaction.response.send_message("❌ You cannot kick a member with an equal or higher role.", ephemeral=True)
        return
    me = interaction.guild.me if interaction.guild else None
    if me and me.top_role <= member.top_role:
        await interaction.response.send_message("❌ I cannot kick that member due to role hierarchy.", ephemeral=True)
        return

    # DM prior to kick
    dm_embed = make_mod_embed(
        title=f"You have been kicked from {interaction.guild.name}",
        color=discord.Color.orange(),
        user=member,
        moderator=interaction.user,
        reason=reason,
    )
    try:
        await member.send(embed=dm_embed)
    except discord.Forbidden:
        pass
    except Exception:
        pass

    try:
        await member.kick(reason=reason or f"Kicked by {interaction.user}")
        embed = make_mod_embed(
            title="👢 Member Kicked",
            color=discord.Color.orange(),
            user=member,
            moderator=interaction.user,
            reason=reason,
        )
        await interaction.response.send_message(embed=embed)
    except discord.Forbidden:
        await interaction.response.send_message("❌ I lack permission to kick this member.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Kick failed: {e}", ephemeral=True)


@tree.command(name="timeout", description="Timeout a member for a duration (1-40320 minutes)")
@app_commands.guild_only()
@app_commands.describe(member="Member to timeout", minutes="Duration in minutes (1-40320)", reason="Reason for timeout")
@app_commands.checks.has_permissions(moderate_members=True)
async def timeout_member(
    interaction: discord.Interaction,
    member: discord.Member,
    minutes: app_commands.Range[int, 1, 40320],
    reason: Optional[str] = None,
):
    if member.id == interaction.user.id:
        await interaction.response.send_message("❌ You cannot timeout yourself.", ephemeral=True)
        return
    if interaction.guild and interaction.guild.owner_id == member.id:
        await interaction.response.send_message("❌ You cannot timeout the server owner.", ephemeral=True)
        return
    if interaction.guild and interaction.user != interaction.guild.owner and interaction.user.top_role <= member.top_role:
        await interaction.response.send_message("❌ You cannot timeout a member with an equal or higher role.", ephemeral=True)
        return
    me = interaction.guild.me if interaction.guild else None
    if me and me.top_role <= member.top_role:
        await interaction.response.send_message("❌ I cannot timeout that member due to role hierarchy.", ephemeral=True)
        return

    until = datetime.now(timezone.utc) + timedelta(minutes=int(minutes))

    # DM prior to timeout
    dm_embed = make_mod_embed(
        title=f"You have been timed out in {interaction.guild.name}",
        color=discord.Color.blurple(),
        user=member,
        moderator=interaction.user,
        reason=reason,
        extra_fields=[("Duration", f"{int(minutes)} minute(s)", True)],
    )
    try:
        await member.send(embed=dm_embed)
    except discord.Forbidden:
        pass
    except Exception:
        pass

    try:
        await member.timeout(until, reason=reason or f"Timed out by {interaction.user}")
        embed = make_mod_embed(
            title="⏳ Member Timed Out",
            color=discord.Color.blurple(),
            user=member,
            moderator=interaction.user,
            reason=reason,
            extra_fields=[("Duration", f"{int(minutes)} minute(s)", True)],
        )
        await interaction.response.send_message(embed=embed)
    except discord.Forbidden:
        await interaction.response.send_message("❌ I lack permission to timeout this member.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Timeout failed: {e}", ephemeral=True)


@tree.command(name="untimeout", description="Remove timeout from a member")
@app_commands.guild_only()
@app_commands.describe(member="Member to remove timeout", reason="Reason for removing timeout")
@app_commands.checks.has_permissions(moderate_members=True)
async def untimeout_member(
    interaction: discord.Interaction,
    member: discord.Member,
    reason: Optional[str] = None,
):
    # Role hierarchy checks
    if interaction.guild and interaction.user != interaction.guild.owner and interaction.user.top_role <= member.top_role:
        await interaction.response.send_message("❌ You cannot modify a member with an equal or higher role.", ephemeral=True)
        return
    me = interaction.guild.me if interaction.guild else None
    if me and me.top_role <= member.top_role:
        await interaction.response.send_message("❌ I cannot modify that member due to role hierarchy.", ephemeral=True)
        return

    # DM the user first
    dm_embed = make_mod_embed(
        title=f"Your timeout has been lifted in {interaction.guild.name}",
        color=discord.Color.green(),
        user=member,
        moderator=interaction.user,
        reason=reason,
    )
    try:
        await member.send(embed=dm_embed)
    except discord.Forbidden:
        pass
    except Exception:
        pass

    try:
        # Clear the timeout
        await member.timeout(None, reason=reason or f"Timeout cleared by {interaction.user}")
        embed = make_mod_embed(
            title="✅ Timeout Removed",
            color=discord.Color.green(),
            user=member,
            moderator=interaction.user,
            reason=reason,
        )
        await interaction.response.send_message(embed=embed)
    except discord.Forbidden:
        await interaction.response.send_message("❌ I lack permission to remove the timeout for this member.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Failed to remove timeout: {e}", ephemeral=True)


@tree.command(name="unban", description="Unban a user from the server")
@app_commands.guild_only()
@app_commands.describe(user="User to unban", reason="Reason for unban")
@app_commands.checks.has_permissions(ban_members=True)
async def unban_user(
    interaction: discord.Interaction,
    user: discord.User,
    reason: Optional[str] = None,
):
    # Attempt to DM before unban (may fail if DMs closed or no mutual guilds)
    dm_embed = make_mod_embed(
        title=f"You have been unbanned from {interaction.guild.name}",
        color=discord.Color.green(),
        user=user,
        moderator=interaction.user,
        reason=reason,
    )
    try:
        await user.send(embed=dm_embed)
    except Exception:
        pass

    try:
        await interaction.guild.unban(user, reason=reason or f"Unbanned by {interaction.user}")
        embed = make_mod_embed(
            title="✅ User Unbanned",
            color=discord.Color.green(),
            user=user,
            moderator=interaction.user,
            reason=reason,
        )
        await interaction.response.send_message(embed=embed)
    except discord.NotFound:
        await interaction.response.send_message("❌ That user is not currently banned.", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("❌ I lack permission to unban that user.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Unban failed: {e}", ephemeral=True)


@client.event
async def on_ready():
    try:
        print(f"✅ Logged in as {client.user} (ID: {client.user.id})")
    except Exception:
        print("✅ Logged in")

    # Set custom "Now Playing" status
    await client.change_presence(activity=discord.Game(name="Casino Games | /balance"))

    # Optional one-time global cleanup to remove any globally-registered commands
    if GLOBAL_COMMAND_CLEANUP:
        try:
            print("🧹 Clearing GLOBAL application commands...")
            tree.clear_commands(guild=None)
            await tree.sync(guild=None)
            print("✅ Global commands cleared.")
        except Exception as e:
            print(f"❌ Failed to clear global commands: {e}")

    # Conditionally sync guild commands to avoid duplicate syncing across multiple instances
    if SYNC_COMMANDS:
        try:
            await tree.sync()
            print("⚡ Global slash commands synced (propagation can take up to ~1 hour)")
            # Temporary dual-sync: also sync test guild for instant updates
            await tree.sync(guild=GUILD_OBJECT)
            print(f"⚡ Guild {GUILD_ID} slash commands synced instantly for testing")
        except Exception as e:
            print(f"❌ Sync failed: {e}")
    else:
        print("⏭️ Skipping guild sync because SYNC_COMMANDS=false")
        try:
            # Fetch existing guild commands so the bot can route interactions without altering remote state
            await tree.fetch_commands()
            print("🔎 Fetched existing global commands for routing.")
        except Exception as e:
            print(f"❌ Failed to fetch guild commands: {e}")


@tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandInvokeError) and "10062" in str(error): return
    print(f"❌ Command Error: {error}")
    try:
        msg = f"❌ Error: {str(error)[:100]}"
        if not interaction.response.is_done(): await interaction.response.send_message(msg, ephemeral=True)
        else: await interaction.followup.send(msg, ephemeral=True)
    except: pass

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN environment variable not set!")

client.run(TOKEN.strip())
