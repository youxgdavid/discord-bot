import discord
from discord import app_commands
from discord.ext import commands
import json
import os
from datetime import datetime, timezone

CURRENCY_FILE = "player_balances.json"
STARTING_BALANCE = 10000

# In-memory cache for balances
_balances_cache = {}

def load_balances():
    """Load player balances from file"""
    global _balances_cache
    if _balances_cache:
        return _balances_cache
        
    try:
        if not os.path.exists(CURRENCY_FILE):
            _balances_cache = {}
            return _balances_cache
        with open(CURRENCY_FILE, 'r') as f:
            data = json.load(f)
            _balances_cache = data if isinstance(data, dict) else {}
            return _balances_cache
    except (FileNotFoundError, json.JSONDecodeError):
        _balances_cache = {}
        return _balances_cache

def save_balances(balances):
    """Save player balances to file"""
    global _balances_cache
    _balances_cache = balances
    with open(CURRENCY_FILE, 'w') as f:
        json.dump(balances, f, indent=2)

def get_balance(user_id):
    """Get player's balance, create if doesn't exist"""
    balances = load_balances()
    user_id_str = str(user_id)
    if user_id_str not in balances:
        balances[user_id_str] = STARTING_BALANCE
        save_balances(balances)
    return balances[user_id_str]

def update_balance(user_id, amount):
    """Update player's balance"""
    balances = load_balances()
    user_id_str = str(user_id)
    if user_id_str not in balances:
        balances[user_id_str] = STARTING_BALANCE
    balances[user_id_str] += amount
    save_balances(balances)
    return balances[user_id_str]

def can_afford(user_id, amount):
    """Check if player can afford the amount"""
    return get_balance(user_id) >= amount

class Economy(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="balance", description="Check your current balance")
    async def balance(self, interaction: discord.Interaction):
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

    @app_commands.command(name="leaderboard", description="View the top players by total balance")
    async def leaderboard(self, interaction: discord.Interaction):
        balances = load_balances()
        if not balances:
            await interaction.response.send_message("No player data yet!", ephemeral=True)
            return

        # Sort by balance descending
        sorted_players = sorted(balances.items(), key=lambda x: x[1], reverse=True)[:10]

        embed = discord.Embed(
            title=" Casino Leaderboard",
            description="Top 10 richest players across all games",
            color=discord.Color.gold(),
            timestamp=datetime.now(timezone.utc)
        )

        leaderboard_text = ""
        rank_emojis = ["🥇", "🥈", "🥉"] + ["🏅"] * 7

        for i, (user_id, balance) in enumerate(sorted_players):
            try:
                user = await self.bot.fetch_user(int(user_id))
                net_gain = balance - STARTING_BALANCE
                emoji = rank_emojis[i] if i < len(rank_emojis) else "🏅"
                sign = "+" if net_gain >= 0 else ""
                leaderboard_text += f"{emoji} **{user.name}** — 💰 ${balance:,}  (`{sign}{net_gain:,}`)\n"
            except Exception:
                pass

        embed.description = leaderboard_text or "No data yet!"
        embed.set_footer(text=f"Requested by {interaction.user}", icon_url=interaction.user.display_avatar.url)

        try:
            top_user = await self.bot.fetch_user(int(sorted_players[0][0]))
            embed.set_thumbnail(url=top_user.display_avatar.url)
        except Exception:
            pass

        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Economy(bot))
