import discord
from discord import app_commands
from discord.ui import Button, View
from datetime import datetime, timezone
from typing import Optional, cast
import os
import random
import json
import asyncio
import aiohttp
from flask import Flask
from threading import Thread

# Create Flask app for Render
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

intents = discord.Intents.default()
intents.members = True  # Required for member info like roles/join date

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

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

# --- /ping command ---
@tree.command(name="ping", description="Check if the bot is working")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Pong! The bot is working.")

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
        # Common 5-letter words for Wordle
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
        self.target_word = random.choice(self.word_list)
        self.guesses = []
        self.max_guesses = 5
        self.game_over = False
        self.won = False
    
    def make_guess(self, guess):
        """Process a guess and return the result"""
        if len(guess) != 5:
            return None, "Guess must be exactly 5 letters!"
        
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
        for i in range(5):
            if guess_letters[i] == target_letters[i]:
                result.append("🟩")  # Green for correct position
                target_letters[i] = None  # Mark as used
                guess_letters[i] = None
            else:
                result.append("⬜")  # Default to white
        
        # Second pass: mark partial matches (yellow)
        for i in range(5):
            if guess_letters[i] is not None and guess_letters[i] in target_letters:
                result[i] = "🟨"  # Yellow for wrong position
                target_letters[target_letters.index(guess_letters[i])] = None  # Mark as used
        
        return "".join(result)
    
    def get_display_word(self):
        """Get the display word with correct letters revealed"""
        if self.game_over and not self.won:
            return self.target_word
        return "?????"
    
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
            for i in range(5):
                if guess_letters[i] == target_letters[i]:
                    correct_letters.add(guess_letters[i])
                    target_letters[i] = None
                    guess_letters[i] = None
            
            # Second pass: find wrong position letters
            for i in range(5):
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
        self.target_word = random.choice(self.word_list)
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
        
        # If player already busted, dealer doesn't need to play
        if player_total > 21:
            message = "💥 **Bust! You went over 21. Dealer wins!**"
            await self.update_game(interaction, message)
            return
        
        dealer_total = self.game.calculate_hand(self.game.dealer_hand)
        
        # Dealer hits until 17 or higher
        while dealer_total < 17:
            self.game.dealer_hand.append(self.game.deal_card())
            dealer_total = self.game.calculate_hand(self.game.dealer_hand)
        
        # Determine winner and handle money
        if dealer_total > 21:
            winnings = self.game.bet_amount * 2
            update_balance(self.user_id, winnings)
            record_win(self.user_id, winnings)
            message = f"🎉 **Dealer busts! You win ${winnings:,}!**"
        elif player_total > dealer_total:
            winnings = self.game.bet_amount * 2
            update_balance(self.user_id, winnings)
            record_win(self.user_id, winnings)
            message = f"🎉 **You win ${winnings:,}!**"
        elif player_total < dealer_total:
            record_loss(self.user_id, self.game.bet_amount)
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
            embed.description = f"Guess a 5-letter word! You have **{self.game.max_guesses - len(self.game.guesses)}** guesses left."
        
        # Add game status
        status = "🎉 **WON!**" if self.game.won else "💀 **GAME OVER**" if self.game.game_over else "🔄 **IN PROGRESS**"
        embed.add_field(name="Status", value=status, inline=True)
        
        # Add target word (revealed if game over)
        target_display = self.game.get_display_word()
        embed.add_field(name="Target Word", value=f"`{target_display}`", inline=True)
        
        # Add guesses
        guesses_display = self.game.get_guesses_display()
        embed.add_field(name="Your Guesses", value=guesses_display, inline=False)
        
        # Add letter hints
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
            label="Enter your 5-letter word guess",
            placeholder="Type your guess here...",
            min_length=5,
            max_length=5,
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
    
    # Check if player can afford the bet
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
@tree.command(name="wordle", description="Play a game of Wordle! Guess the 5-letter word in 5 tries.")
async def wordle(interaction: discord.Interaction):
    game = WordleGame()
    view = WordleView(game, interaction.user.id)
    
    embed = discord.Embed(
        title="🎯 Wordle Game",
        description=f"Guess a 5-letter word! You have **{game.max_guesses}** guesses to get it right!",
        color=discord.Color.orange(),
        timestamp=datetime.now(timezone.utc)
    )
    
    embed.add_field(name="Status", value="🔄 **IN PROGRESS**", inline=True)
    embed.add_field(name="Target Word", value="`?????`", inline=True)
    embed.add_field(name="Your Guesses", value="No guesses yet", inline=False)
    embed.add_field(name="💡 Letter Hints", value="No hints yet - make your first guess!", inline=False)
    embed.add_field(
        name="How to Play", 
        value="🟩 = Correct letter, correct position\n🟨 = Correct letter, wrong position\n⬜ = Letter not in word", 
        inline=False
    )
    embed.set_footer(text=f"Playing as {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
    
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
        import random
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
                # This shouldn't happen, but just in case
                pass
            else:
                # Hit a mine
                record_loss(interaction.user.id, game.bet_amount)
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
        record_win(interaction.user.id, profit)
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
  import discord
from discord import app_commands
from discord.ui import Button, View
import random

# Tower multipliers
TOWER_MULTIPLIERS = [1.2, 1.5, 2.0, 3.0, 5.0, 10.0]

# Active games
tower_games = {}

# ------------------------
# Dummy balance functions
# Replace with your real bot economy logic
# ------------------------
def can_afford(user_id, amount):
    return True

def get_balance(user_id):
    return 10000

def update_balance(user_id, amount):
    pass

# ------------------------
# Tower game logic
# ------------------------
class TowerGame:
    def __init__(self, user_id, bet_amount):
        self.user_id = user_id
        self.bet_amount = bet_amount
        self.levels = 6
        self.tiles_per_level = 3
        self.current_level = 0
        self.game_over = False
        self.won = False
        self.skull_positions = {level: random.randint(0, self.tiles_per_level - 1) for level in range(self.levels)}

    def select_tile(self, choice):
        if self.game_over:
            return None
        is_skull = self.skull_positions[self.current_level] == choice
        if is_skull:
            self.game_over = True
            self.won = False
            return False
        else:
            self.current_level += 1
            if self.current_level >= self.levels:
                self.game_over = True
                self.won = True
            return True

    def get_current_multiplier(self):
        if self.game_over and not self.won:
            return 0.0
        if self.current_level == 0:
            return 1.0
        return TOWER_MULTIPLIERS[self.current_level - 1]

    def cash_out(self):
        if self.game_over or self.current_level == 0:
            return 0
        self.game_over = True
        self.won = True
        return int(self.bet_amount * self.get_current_multiplier())

# ------------------------
# Tower buttons
# ------------------------
class TowerButton(Button):
    def __init__(self, level, choice):
        super().__init__(style=discord.ButtonStyle.secondary, label="❓", row=level)
        self.level = level
        self.choice = choice
        self.disabled = (level != 0)

    async def callback(self, interaction: discord.Interaction):
        game = tower_games.get(interaction.user.id)
        if not game:
            await interaction.response.send_message("This isn't your game!", ephemeral=True)
            return
        if game.game_over:
            await interaction.response.send_message("The game is already over.", ephemeral=True)
            return
        if self.level != game.current_level:
            await interaction.response.send_message("You must play the current level.", ephemeral=True)
            return

        is_safe = game.select_tile(self.choice)
        view = self.view

        if is_safe:
            self.style = discord.ButtonStyle.success
            self.label = "💎"
            # Disable all buttons on this level
            for child in view.children:
                if isinstance(child, TowerButton) and child.level == self.level:
                    child.disabled = True

            # Check if player won
            if game.game_over and game.won:
                winnings = int(game.bet_amount * TOWER_MULTIPLIERS[-1])
                profit = winnings - game.bet_amount
                update_balance(interaction.user.id, profit)
                embed = discord.Embed(
                    title="🎉 TOWER COMPLETE! 🎉",
                    description=f"You reached the top and won **${winnings:,}**!",
                    color=discord.Color.gold()
                )
                embed.add_field(name="Final Multiplier", value=f"{TOWER_MULTIPLIERS[-1]:.2f}x", inline=True)
                await interaction.response.edit_message(embed=embed, view=view)
                del tower_games[interaction.user.id]
                return

            # Enable next level buttons
            for child in view.children:
                if isinstance(child, TowerButton) and child.level == game.current_level:
                    child.disabled = False

            multiplier = game.get_current_multiplier()
            potential_win = int(game.bet_amount * multiplier)

            embed = discord.Embed(
                title="🗼 Tower Climb",
                description=f"You climbed to **Level {game.current_level}**!",
                color=discord.Color.green()
            )
            embed.add_field(name="Bet Amount", value=f"${game.bet_amount:,}", inline=True)
            embed.add_field(name="Multiplier", value=f"**{multiplier:.2f}x**", inline=True)
            embed.add_field(name="Potential Win", value=f"**${potential_win:,}**", inline=True)
            embed.set_footer(text="Pick a tile on the next level or cash out!")
            await interaction.response.edit_message(embed=embed, view=view)

        else:
            # Player hit a skull
            for child in view.children:
                if isinstance(child, TowerButton) and child.level == self.level:
                    child.disabled = True
                    if child.choice == game.skull_positions[self.level]:
                        child.style = discord.ButtonStyle.danger
                        child.label = "💀"
                    else:
                        child.style = discord.ButtonStyle.success
                        child.label = "💎"
            # Disable all buttons
            for child in view.children:
                child.disabled = True
            update_balance(interaction.user.id, -game.bet_amount)
            embed = discord.Embed(
                title="💀 BOOM! You hit a skull!",
                description=f"You lost your bet of **${game.bet_amount:,}**.",
                color=discord.Color.red()
            )
            await interaction.response.edit_message(embed=embed, view=view)
            del tower_games[interaction.user.id]

class TowerCashOutButton(Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.success, label="💰 Cash Out", row=4)

    async def callback(self, interaction: discord.Interaction):
        game = tower_games.get(interaction.user.id)
        if not game:
            await interaction.response.send_message("No active tower game! Use `/tower` to start.", ephemeral=True)
            return
        if game.current_level == 0:
            await interaction.response.send_message("Pick at least one tile before cashing out!", ephemeral=True)
            return
        winnings = game.cash_out()
        profit = winnings - game.bet_amount
        update_balance(interaction.user.id, profit)
        # Disable all buttons
        for item in self.view.children:
            item.disabled = True
        embed = discord.Embed(
            title="💰 Cashed Out!",
            description=f"You cashed out at **Level {game.current_level}** and won **${winnings:,}** (Profit: **${profit:,}**)",
            color=discord.Color.gold()
        )
        embed.add_field(name="Final Multiplier", value=f"{game.get_current_multiplier():.2f}x", inline=True)
        embed.add_field(name="Bet Amount", value=f"${game.bet_amount:,}", inline=True)
        await interaction.response.edit_message(embed=embed, view=self.view)
        del tower_games[interaction.user.id]

class TowerView(View):
    def __init__(self, game):
        super().__init__(timeout=300)
        self.game = game
        for level in range(game.levels):
            for choice in range(game.tiles_per_level):
                self.add_item(TowerButton(level, choice))
        self.add_item(TowerCashOutButton())

# ------------------------
# Tower command
# ------------------------
@tree.command(name="tower", description="Play Tower — pick safe tiles and climb to the top!")
@app_commands.describe(bet="Amount to bet (minimum 100)")
async def tower(interaction: discord.Interaction, bet: int = 100):
    # Validation errors → ephemeral
    if bet < 100:
        await interaction.response.send_message("❌ Minimum bet is $100!", ephemeral=True)
        return
    if bet > 1000000:
        await interaction.response.send_message("❌ Maximum bet is $1,000,000!", ephemeral=True)
        return
    if not can_afford(interaction.user.id, bet):
        balance = get_balance(interaction.user.id)
        await interaction.response.send_message(
            f"❌ You can't afford that bet! Your balance: ${balance:,}", ephemeral=True
        )
        return

    # Valid bet → defer response
    await interaction.response.defer(thinking=True)

    # Create game
    game = TowerGame(interaction.user.id, bet)
    tower_games[interaction.user.id] = game
    view = TowerView(game)

    # Send main game embed
    embed = discord.Embed(
        title="🗼 Tower — Pick a tile to climb!",
        description=f"Bet: **${bet:,}** — Pick a tile on Level 1. Avoid the skull!",
        color=discord.Color.blue()
    )
    embed.add_field(name="Current Multiplier", value="**1.00x**", inline=True)
    embed.add_field(name="Potential Top Win", value=f"**${int(bet * TOWER_MULTIPLIERS[-1]):,}**", inline=True)
    embed.set_footer(text="Pick one tile per level. Cash out anytime to keep your winnings.")

    await interaction.edit_original_response(embed=embed, view=view)


@tree.command(name="leaderboard", description="View the global casino leaderboard!")
async def leaderboard(interaction: discord.Interaction):
    stats = load_stats()
    if not stats:
        await interaction.response.send_message("No leaderboard data yet!", ephemeral=False)
        return

    # Sort by wins and losses
    top_wins = sorted(stats.items(), key=lambda x: x[1].get("wins", 0), reverse=True)[:10]
    top_losses = sorted(stats.items(), key=lambda x: x[1].get("losses", 0), reverse=True)[:10]

    embed = discord.Embed(
        title="🏆 Global Casino Leaderboard",
        color=discord.Color.gold(),
        timestamp=datetime.now(timezone.utc),
        description="Combined results from all casino games!"
    )

    # Winners
    win_lines = []
    for rank, (uid, data) in enumerate(top_wins, start=1):
        user = await client.fetch_user(int(uid))
        avatar = user.display_avatar.url
        win_lines.append(f"{rank}. [{user.display_name}]({avatar}) — **${data['wins']:,}**")

    # Losers
    lose_lines = []
    for rank, (uid, data) in enumerate(top_losses, start=1):
        user = await client.fetch_user(int(uid))
        avatar = user.display_avatar.url
        lose_lines.append(f"{rank}. [{user.display_name}]({avatar}) — **${data['losses']:,}**")

    embed.add_field(name="🥇 Top Winners", value="\n".join(win_lines) or "No winners yet.", inline=False)
    embed.add_field(name="💀 Biggest Losers", value="\n".join(lose_lines) or "No losses yet.", inline=False)
    embed.set_footer(text="Stats update automatically. Daily $1500 bonus for top 3 winners.")

    await interaction.response.send_message(embed=embed, ephemeral=False)

@client.event
async def on_ready():
    print(f"✅ Logged in as {client.user}")

    # Start daily bonus loop
    try:
        client.loop.create_task(award_daily_bonus())
    except Exception as e:
        print(f"[Leaderboard Bonus Task Error] {e}")

    # Sync commands (to your guild for instant updates)
    import os
    guild_id = os.getenv("GUILD_ID", "868504571637547018")
    try:
        if guild_id:
            guild = discord.Object(id=int(guild_id))
            tree.copy_global_to(guild=guild)
            await tree.sync(guild=guild)
            print(f"✅ Slash commands synced instantly to guild {868504571637547018}")
        else:
            await tree.sync()
            print("🌍 Synced slash commands globally (may take up to 1 hour)")
    except Exception as e:
        print(f"⚠️ Command sync error: {e}")

# --- Run the bot ---
TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise ValueError("❌ No token found! Add DISCORD_TOKEN in Render environment variables.")
print("Loaded token:", "✅ Found" if TOKEN else "❌ Missing")

client.run(TOKEN)

