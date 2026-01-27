import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View
import random
from datetime import datetime, timezone
from cogs.economy import get_balance, update_balance, can_afford

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
        self.word_len = random.randint(1, 5)
        self.target_word = ''.join(random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ') for _ in range(self.word_len))
        self.guesses = []
        self.max_guesses = 5
        self.game_over = False
        self.won = False

    def make_guess(self, guess):
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
        result = []
        target_letters = list(self.target_word)
        guess_letters = list(guess)
        for i in range(self.word_len):
            if guess_letters[i] == target_letters[i]:
                result.append("🟩")
                target_letters[i] = None
                guess_letters[i] = None
            else:
                result.append("⬜")
        for i in range(self.word_len):
            if guess_letters[i] is not None and guess_letters[i] in target_letters:
                result[i] = "🟨"
                target_letters[target_letters.index(guess_letters[i])] = None
        return "".join(result)

    def get_display_word(self):
        if self.game_over and not self.won:
            return self.target_word
        return "?" * self.word_len

    def get_guesses_display(self):
        if not self.guesses:
            return "No guesses yet"
        display = []
        for i, guess in enumerate(self.guesses):
            result = self.get_guess_result(guess)
            display.append(f"**{i+1}.** {guess} → {result}")
        return "\n".join(display)

    def get_letter_hints(self):
        if not self.guesses:
            return "No hints yet - make your first guess!"
        correct_letters = set()
        wrong_position_letters = set()
        all_guessed_letters = set()
        for guess in self.guesses:
            all_guessed_letters.update(guess)
            target_letters = list(self.target_word)
            guess_letters = list(guess)
            for i in range(self.word_len):
                if guess_letters[i] == target_letters[i]:
                    correct_letters.add(guess_letters[i])
                    target_letters[i] = None
                    guess_letters[i] = None
            for i in range(self.word_len):
                if guess_letters[i] is not None and guess_letters[i] in target_letters:
                    wrong_position_letters.add(guess_letters[i])
                    target_letters[target_letters.index(guess_letters[i])] = None
        wrong_letters = all_guessed_letters - correct_letters - wrong_position_letters
        hints = []
        if correct_letters:
            hints.append(f"🟩 **Correct position:** `{', '.join(sorted(list(correct_letters)))}`")
        if wrong_position_letters:
            hints.append(f"🟨 **Wrong position:** `{', '.join(sorted(list(wrong_position_letters)))}`")
        if wrong_letters:
            hints.append(f"⬜ **Not in word:** `{', '.join(sorted(list(wrong_letters)))}`")
        return "\n".join(hints) if hints else "No hints yet - make your first guess!"

    def new_word(self):
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
        suits = ['♠️', '♥️', '♣️', '♦️']
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        self.deck = [{'rank': rank, 'suit': suit} for suit in suits for rank in ranks]
        random.shuffle(self.deck)

    def deal_card(self):
        if len(self.deck) < 10:
            self.reset_deck()
        return self.deck.pop()

    def card_value(self, card):
        rank = card['rank']
        if rank in ['J', 'Q', 'K']: return 10
        if rank == 'A': return 11
        return int(rank)

    def calculate_hand(self, hand):
        total = sum(self.card_value(card) for card in hand)
        aces = sum(1 for card in hand if card['rank'] == 'A')
        while total > 21 and aces > 0:
            total -= 10
            aces -= 1
        return total

    def hand_to_string(self, hand, hide_first=False):
        if hide_first and len(hand) > 0:
            cards = ['🂠'] + [f"{card['rank']}{card['suit']}" for card in hand[1:]]
        else:
            cards = [f"{card['rank']}{card['suit']}" for card in hand]
        return ' '.join(cards)

    def start_game(self):
        self.player_hand = [self.deal_card(), self.deal_card()]
        self.dealer_hand = [self.deal_card(), self.deal_card()]

class BlackjackView(View):
    def __init__(self, game, user_id):
        super().__init__(timeout=120)
        self.game = game
        self.user_id = user_id
        self.game_over = False

    async def update_game(self, interaction, message):
        player_total = self.game.calculate_hand(self.game.player_hand)
        dealer_total = self.game.calculate_hand(self.game.dealer_hand)
        embed = discord.Embed(title="🎰 Blackjack", description=message, color=discord.Color.gold())
        embed.add_field(name="💰 Bet Amount", value=f"**${self.game.bet_amount:,}**", inline=True)
        embed.add_field(name="🎴 Your Hand", value=f"{self.game.hand_to_string(self.game.player_hand)}\n**Total: {player_total}**", inline=False)
        dealer_display = self.game.hand_to_string(self.game.dealer_hand, hide_first=not self.game_over)
        dealer_score = dealer_total if self.game_over else "?"
        embed.add_field(name="🎴 Dealer's Hand", value=f"{dealer_display}\n**Total: {dealer_score}**", inline=False)
        if self.game_over: self.clear_items()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Hit", style=discord.ButtonStyle.primary, emoji="👊")
    async def hit_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("This isn't your game!", ephemeral=True)
        self.game.player_hand.append(self.game.deal_card())
        if self.game.calculate_hand(self.game.player_hand) > 21:
            self.game_over = True
            await self.dealer_play(interaction)
        else:
            await self.update_game(interaction, "You hit! Do you want to Hit or Stand?")

    @discord.ui.button(label="Stand", style=discord.ButtonStyle.secondary, emoji="✋")
    async def stand_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("This isn't your game!", ephemeral=True)
        self.game_over = True
        await self.dealer_play(interaction)

    async def dealer_play(self, interaction: discord.Interaction):
        player_total = self.game.calculate_hand(self.game.player_hand)
        if player_total > 21:
            return await self.update_game(interaction, "💥 **Bust! You went over 21. Dealer wins!**")
        dealer_total = self.game.calculate_hand(self.game.dealer_hand)
        while dealer_total < 17:
            self.game.dealer_hand.append(self.game.deal_card())
            dealer_total = self.game.calculate_hand(self.game.dealer_hand)
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
            update_balance(self.user_id, self.game.bet_amount)
            message = f"🤝 **It's a tie! Your bet of ${self.game.bet_amount:,} was returned**"
        await self.update_game(interaction, message)

# --- Wordle UI ---
class WordleView(View):
    def __init__(self, game, user_id):
        super().__init__(timeout=300)
        self.game = game
        self.user_id = user_id
        self.waiting_for_guess = False

    async def update_display(self, interaction: discord.Interaction, message: str = None):
        embed = discord.Embed(
            title="🎯 Wordle Game",
            color=discord.Color.green() if self.game.won else discord.Color.blue() if self.game.game_over else discord.Color.orange(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.description = message or f"Guess a {self.game.word_len}-letter word! You have **{self.game.max_guesses - len(self.game.guesses)}** guesses left."
        embed.add_field(name="Status", value="🎉 **WON!**" if self.game.won else "💀 **GAME OVER**" if self.game.game_over else "🔄 **IN PROGRESS**", inline=True)
        embed.add_field(name="Target Word", value=f"`{self.game.get_display_word()}`", inline=True)
        embed.add_field(name="Your Guesses", value=self.game.get_guesses_display(), inline=False)
        embed.add_field(name="💡 Letter Hints", value=self.game.get_letter_hints(), inline=False)
        if not self.game.game_over:
            embed.add_field(name="How to Play", value="🟩 = Correct letter, correct position\n🟨 = Correct letter, wrong position\n⬜ = Letter not in word", inline=False)
        embed.set_footer(text=f"Playing as {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
        self.clear_items()
        if self.game.game_over:
            self.add_item(NewWordButton())
        elif not self.waiting_for_guess:
            self.add_item(GuessButton())
            self.add_item(NewWordButton())
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Make a Guess", style=discord.ButtonStyle.primary, emoji="💭")
    async def guess_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("This isn't your game!", ephemeral=True)
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
            return await interaction.response.send_message(f"❌ {message}", ephemeral=True)
        self.view.waiting_for_guess = False
        await self.view.update_display(interaction, message)

class NewWordButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="New Word", style=discord.ButtonStyle.secondary, emoji="🔄")
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.view.user_id:
            return await interaction.response.send_message("This isn't your game!", ephemeral=True)
        self.view.game.new_word()
        self.view.waiting_for_guess = False
        await self.view.update_display(interaction, "🎯 New word selected! Start guessing!")

class GuessButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Make a Guess", style=discord.ButtonStyle.primary, emoji="💭")
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.view.user_id:
            return await interaction.response.send_message("This isn't your game!", ephemeral=True)
        self.view.waiting_for_guess = True
        await interaction.response.send_modal(WordleGuessModal(self.view.game, self.view))

# --- Baccarat ---
class BaccaratGame:
    def __init__(self, user_id: int, bet: int, side: str):
        self.user_id, self.bet, self.side = user_id, bet, side
        self.shoe = self._build_shoe()
        self.player_hand, self.banker_hand = [], []
        self.finished, self.outcome, self.payout = False, None, 0
        self._deal_initial()
        self._resolve_naturals_or_draws()

    def _build_shoe(self):
        ranks = ['A'] + [str(i) for i in range(2, 10)] + ['10', 'J', 'Q', 'K']
        shoe = ranks * 4 * 6
        random.shuffle(shoe)
        return shoe

    def _value(self, card_rank: str) -> int:
        if card_rank == 'A': return 1
        if card_rank in ['10', 'J', 'Q', 'K']: return 0
        return int(card_rank)

    def _score(self, hand) -> int:
        return sum(self._value(r) for r in hand) % 10

    def _draw(self):
        if not self.shoe: self.shoe = self._build_shoe()
        return self.shoe.pop()

    def _deal_initial(self):
        self.player_hand = [self._draw(), self._draw()]
        self.banker_hand = [self._draw(), self._draw()]

    def _resolve_naturals_or_draws(self):
        p, b = self._score(self.player_hand), self._score(self.banker_hand)
        if p in (8, 9) or b in (8, 9):
            self._finalize()
            return
        third_player = None
        if p <= 5:
            third_player = self._draw()
            self.player_hand.append(third_player)
            p = self._score(self.player_hand)
        b_score = self._score(self.banker_hand)
        if third_player is None:
            if b_score <= 5: self.banker_hand.append(self._draw())
        else:
            tp_val = self._value(third_player)
            if b_score <= 2: self.banker_hand.append(self._draw())
            elif b_score == 3 and tp_val != 8: self.banker_hand.append(self._draw())
            elif b_score == 4 and tp_val in [2, 3, 4, 5, 6, 7]: self.banker_hand.append(self._draw())
            elif b_score == 5 and tp_val in [4, 5, 6, 7]: self.banker_hand.append(self._draw())
            elif b_score == 6 and tp_val in [6, 7]: self.banker_hand.append(self._draw())
        self._finalize()

    def _finalize(self):
        self.finished = True
        p, b = self._score(self.player_hand), self._score(self.banker_hand)
        if p > b: self.outcome = "player"
        elif b > p: self.outcome = "banker"
        else: self.outcome = "tie"
        self._calc_payout()

    def _calc_payout(self):
        if self.outcome == self.side:
            if self.side == "player": self.payout = self.bet * 2
            elif self.side == "banker": self.payout = int(self.bet * 1.95)
            else: self.payout = self.bet * 9
        else: self.payout = 0

    def hand_string(self, hand): return " ".join(hand)

    def board_embed(self):
        p_score, b_score = self._score(self.player_hand), self._score(self.banker_hand)
        color = discord.Color.green() if self.outcome == self.side else discord.Color.red() if self.outcome else discord.Color.blurple()
        embed = discord.Embed(title="Baccarat — Result" if self.finished else "Baccarat", color=color, timestamp=datetime.now(timezone.utc))
        embed.add_field(name="Player", value=f"{self.hand_string(self.player_hand)}\nTotal: **{p_score}**", inline=True)
        embed.add_field(name="Banker", value=f"{self.hand_string(self.banker_hand)}\nTotal: **{b_score}**", inline=True)
        embed.add_field(name="Your Bet", value=f"{self.side.capitalize()} — ${self.bet:,}", inline=False)
        if self.finished:
            result = "It’s a TIE!" if self.outcome == 'tie' else f"{self.outcome.upper()} wins"
            embed.description = f"🎴 {result}\n{'Payout: **$' + f'{self.payout:,}' + '**' if self.payout else 'Lost: **$' + f'{self.bet:,}' + '**'}"
        embed.set_footer(text="Baccarat • 6-deck shoe • Banker commission on wins")
        return embed

class BaccaratView(View):
    def __init__(self, game):
        super().__init__(timeout=120)
        self.game = game
        if game.finished: self.add_item(BaccaratNewRoundButton())

class BaccaratNewRoundButton(Button):
    def __init__(self):
        super().__init__(label="New Round", style=discord.ButtonStyle.secondary, emoji="🔄")
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("Use /baccarat to start a new round.", ephemeral=True)

# --- Mines ---
class MinesGame:
    def __init__(self, user_id, bet_amount, num_mines):
        self.user_id, self.bet_amount, self.num_mines = user_id, bet_amount, num_mines
        self.board_size, self.revealed, self.game_over, self.won, self.multiplier = 20, set(), False, False, 1.0
        self.mine_positions = set(random.sample(range(self.board_size), num_mines))

    def reveal_tile(self, position):
        if position in self.revealed or self.game_over: return False
        self.revealed.add(position)
        if position in self.mine_positions:
            self.game_over = True
            return False
        self.multiplier = 1.0 + (len(self.revealed) * (self.num_mines / (self.board_size - self.num_mines)) * 0.3)
        return True

    def cash_out(self):
        if not self.game_over and self.revealed:
            self.game_over, self.won = True, True
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
            return await interaction.response.send_message("No active game!", ephemeral=True)
        is_safe = game.reveal_tile(self.position)
        if self.position in game.mine_positions:
            self.label, self.style = "💣", discord.ButtonStyle.danger
        else:
            self.label, self.style = "💎", discord.ButtonStyle.success
        self.disabled = True
        if game.game_over:
            for item in self.view.children:
                if isinstance(item, MinesButton) and item.position in game.mine_positions:
                    item.label, item.style = "💣", discord.ButtonStyle.danger
                item.disabled = True
            if not is_safe:
                update_balance(interaction.user.id, -game.bet_amount)
                await interaction.response.edit_message(embed=discord.Embed(title="💣 BOOM!", description=f"Lost **${game.bet_amount:,}**", color=discord.Color.red()), view=self.view)
                del mines_games[interaction.user.id]
        else:
            potential = int(game.bet_amount * game.multiplier)
            embed = discord.Embed(title="💎 Mines", description=f"Bet: **${game.bet_amount:,}** | Mines: **{game.num_mines}**", color=discord.Color.green())
            embed.add_field(name="Multiplier", value=f"**{game.multiplier:.2f}x**", inline=True)
            embed.add_field(name="Potential Win", value=f"**${potential:,}**", inline=True)
            embed.add_field(name="Revealed", value=f"**{len(game.revealed)}** / {game.board_size - game.num_mines}", inline=True)
            await interaction.response.edit_message(embed=embed, view=self.view)

class MinesView(View):
    def __init__(self, game):
        super().__init__(timeout=300)
        self.game = game
        for i in range(20): self.add_item(MinesButton(i, i // 5))
        self.add_item(CashOutButton())
    async def on_timeout(self):
        if self.game.user_id in mines_games: del mines_games[self.game.user_id]

class CashOutButton(Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.success, label="💰 Cash Out", row=4)
    async def callback(self, interaction: discord.Interaction):
        game = mines_games.get(interaction.user.id)
        if not game: return await interaction.response.send_message("No active game!", ephemeral=True)
        if not game.revealed: return await interaction.response.send_message("Reveal at least one tile!", ephemeral=True)
        winnings = game.cash_out()
        profit = winnings - game.bet_amount
        update_balance(interaction.user.id, profit)
        for item in self.view.children: item.disabled = True
        embed = discord.Embed(title=" Cashed Out!", description=f"Won **${winnings:,}** (Profit: **${profit:,}**)", color=discord.Color.gold())
        embed.add_field(name="Final Multiplier", value=f"{game.multiplier:.2f}x", inline=True)
        await interaction.response.edit_message(embed=embed, view=self.view)
        del mines_games[interaction.user.id]

# --- Tower ---
class TowerGame:
    def __init__(self, user_id, bet):
        self.user_id, self.bet, self.level, self.max_levels, self.multiplier, self.game_over, self.bomb_position = user_id, bet, 1, 10, 1.0, False, None
    def next_level(self):
        self.level += 1
        self.multiplier += 0.5
    def reset_bomb(self): self.bomb_position = random.randint(1, 3)
    def is_bomb(self, choice): return choice == self.bomb_position
    def progress_bar(self):
        return "".join("⬛" if i < self.level else "🟩" if i == self.level else "⬜" for i in range(1, self.max_levels + 1))

tower_games = {}

class TowerButton(Button):
    def __init__(self, position):
        super().__init__(label=f"Tile {position}", style=discord.ButtonStyle.secondary)
        self.position = position
    async def callback(self, interaction: discord.Interaction):
        game = tower_games.get(interaction.user.id)
        if not game or game.game_over: return await interaction.response.send_message("No active Tower game!", ephemeral=True)
        if game.is_bomb(self.position):
            game.game_over = True
            update_balance(interaction.user.id, -game.bet)
            for item in self.view.children:
                if isinstance(item, TowerButton):
                    item.disabled, item.style = True, discord.ButtonStyle.danger if item.position == game.bomb_position else discord.ButtonStyle.success
            embed = discord.Embed(title="💣 BOOM!", description=f"Lost **${game.bet:,}**", color=discord.Color.red())
            embed.add_field(name="Progress", value=game.progress_bar(), inline=False)
            await interaction.response.edit_message(embed=embed, view=self.view)
            del tower_games[interaction.user.id]
        else:
            if game.level >= game.max_levels:
                winnings = int(game.bet * game.multiplier)
                update_balance(interaction.user.id, winnings - game.bet)
                game.game_over = True
                for item in self.view.children: item.disabled = True
                embed = discord.Embed(title=" Conquered the tower!", description=f"Won **${winnings:,}**", color=discord.Color.gold())
                embed.add_field(name="Progress", value=game.progress_bar(), inline=False)
                await interaction.response.edit_message(embed=embed, view=self.view)
                del tower_games[interaction.user.id]
            else:
                game.next_level()
                embed = discord.Embed(title=" Tower Game", description=f"Level: **{game.level} / {game.max_levels}**\nMultiplier: **{game.multiplier:.2f}x**", color=discord.Color.blue())
                embed.add_field(name="Progress", value=game.progress_bar(), inline=False)
                await interaction.response.edit_message(embed=embed, view=TowerView(game))

class CashOutTowerButton(Button):
    def __init__(self):
        super().__init__(label=" Cash Out", style=discord.ButtonStyle.success)
    async def callback(self, interaction: discord.Interaction):
        game = tower_games.get(interaction.user.id)
        if not game or game.game_over: return await interaction.response.send_message("No active game!", ephemeral=True)
        winnings = int(game.bet * game.multiplier)
        update_balance(interaction.user.id, winnings - game.bet)
        game.game_over = True
        for item in self.view.children: item.disabled = True
        embed = discord.Embed(title=" Cashed Out!", description=f"Won **${winnings:,}**", color=discord.Color.gold())
        embed.add_field(name="Progress", value=game.progress_bar(), inline=False)
        await interaction.response.edit_message(embed=embed, view=self.view)
        del tower_games[interaction.user.id]

class TowerView(View):
    def __init__(self, game):
        super().__init__(timeout=300)
        self.game = game
        self.game.reset_bomb()
        for i in range(1, 4): self.add_item(TowerButton(i))
        self.add_item(CashOutTowerButton())
    async def on_timeout(self):
        if self.game.user_id in tower_games: del tower_games[self.game.user_id]

class Games(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="blackjack", description="Play Blackjack with betting!")
    @app_commands.describe(bet="Amount to bet (min 100)")
    async def blackjack(self, interaction: discord.Interaction, bet: int = 100):
        if bet < 100: return await interaction.response.send_message("❌ Minimum bet is $100!", ephemeral=True)
        if bet > 10000: return await interaction.response.send_message("❌ Maximum bet is $10,000!", ephemeral=True)
        if not can_afford(interaction.user.id, bet):
            return await interaction.response.send_message(f"❌ Can't afford! Balance: ${get_balance(interaction.user.id):,}", ephemeral=True)
        update_balance(interaction.user.id, -bet)
        game = BlackjackGame(bet_amount=bet)
        game.start_game()
        player_total, dealer_total = game.calculate_hand(game.player_hand), game.calculate_hand(game.dealer_hand)
        if player_total == 21:
            if dealer_total == 21:
                update_balance(interaction.user.id, game.bet_amount)
                description = f"🤝 **Push! Both have Blackjack!**"
            else:
                winnings = int(game.bet_amount * 2.5)
                update_balance(interaction.user.id, winnings)
                description = f"🎉 **BLACKJACK! You win ${winnings:,}!**"
            embed = discord.Embed(title="🎰 Blackjack", description=description, color=discord.Color.gold())
            embed.add_field(name="💰 Bet", value=f"**${game.bet_amount:,}**", inline=True)
            embed.add_field(name="🎴 Your Hand", value=f"{game.hand_to_string(game.player_hand)}\n**Total: {player_total}**", inline=False)
            embed.add_field(name="🎴 Dealer's Hand", value=f"{game.hand_to_string(game.dealer_hand)}\n**Total: {dealer_total}**", inline=False)
            return await interaction.response.send_message(embed=embed)
        await interaction.response.send_message(embed=discord.Embed(title="🎰 Blackjack", description="Hit or Stand?").add_field(name="💰 Bet", value=f"${bet:,}").add_field(name="🎴 Your Hand", value=f"{game.hand_to_string(game.player_hand)}\n**Total: {player_total}**").add_field(name="🎴 Dealer's Hand", value=f"{game.hand_to_string(game.dealer_hand, hide_first=True)}"), view=BlackjackView(game, interaction.user.id))

    @app_commands.command(name="wordle", description="Play Wordle!")
    async def wordle(self, interaction: discord.Interaction):
        game = WordleGame()
        embed = discord.Embed(title=" Wordle Game", description=f"Guess a {game.word_len}-letter word!", color=discord.Color.orange(), timestamp=datetime.now(timezone.utc))
        embed.add_field(name="Status", value="🔄 **IN PROGRESS**", inline=True).add_field(name="Target Word", value=f"`{'?' * game.word_len}`", inline=True).add_field(name="Your Guesses", value="No guesses yet", inline=False).add_field(name="💡 Hints", value="No hints yet", inline=False)
        await interaction.response.send_message(embed=embed, view=WordleView(game, interaction.user.id))

    @app_commands.command(name="baccarat", description="Play Baccarat!")
    @app_commands.describe(bet="Amount to bet (min 100)", side="Choose your bet")
    @app_commands.choices(side=[app_commands.Choice(name="Player", value="player"), app_commands.Choice(name="Banker", value="banker"), app_commands.Choice(name="Tie", value="tie")])
    async def baccarat(self, interaction: discord.Interaction, bet: int, side: app_commands.Choice[str]):
        if bet < 100: return await interaction.response.send_message("❌ Minimum $100!", ephemeral=True)
        if not can_afford(interaction.user.id, bet): return await interaction.response.send_message("❌ Not enough money!", ephemeral=True)
        update_balance(interaction.user.id, -bet)
        game = BaccaratGame(interaction.user.id, bet, side.value)
        if game.payout: update_balance(interaction.user.id, game.payout)
        embed = game.board_embed()
        embed.insert_field_at(0, name="", value=f"{'🟩' if game.outcome == game.side else '🟥'} Bet: {side.name} • ${bet:,}", inline=False)
        await interaction.response.send_message(embed=embed, view=BaccaratView(game))

    @app_commands.command(name="mines", description="Play Mines!")
    @app_commands.describe(bet="Amount to bet", mines="Number of mines (1-10)")
    async def mines(self, interaction: discord.Interaction, bet: int, mines: int = 3):
        if not (1 <= mines <= 10): return await interaction.response.send_message("❌ Mines: 1-10!", ephemeral=True)
        if bet < 100: return await interaction.response.send_message("❌ Minimum $100!", ephemeral=True)
        if not can_afford(interaction.user.id, bet): return await interaction.response.send_message("❌ Not enough money!", ephemeral=True)
        if interaction.user.id in mines_games: return await interaction.response.send_message("❌ Finish active game!", ephemeral=True)
        game = MinesGame(interaction.user.id, bet, mines)
        mines_games[interaction.user.id] = game
        embed = discord.Embed(title=" Mines Game", description=f"Bet: **${bet:,}** | Mines: **{mines}**", color=discord.Color.blue())
        embed.add_field(name="Multiplier", value="**1.00x**", inline=True).add_field(name="Potential Win", value=f"**${bet:,}**", inline=True).add_field(name="Revealed", value=f"**0** / {20 - mines}", inline=True)
        await interaction.response.send_message(embed=embed, view=MinesView(game))

    @app_commands.command(name="clearmines", description="Clear stuck mines game")
    async def clearmines(self, interaction: discord.Interaction):
        if interaction.user.id in mines_games:
            del mines_games[interaction.user.id]
            await interaction.response.send_message("Mines cleared!", ephemeral=True)
        else: await interaction.response.send_message("No active game.", ephemeral=True)

    @app_commands.command(name="tower", description="Play Tower!")
    @app_commands.describe(bet="Amount to bet")
    async def tower(self, interaction: discord.Interaction, bet: int):
        if bet < 100: return await interaction.response.send_message("❌ Minimum $100!", ephemeral=True)
        if not can_afford(interaction.user.id, bet): return await interaction.response.send_message("❌ Not enough money!", ephemeral=True)
        if interaction.user.id in tower_games: return await interaction.response.send_message("❌ Finish active game!", ephemeral=True)
        game = TowerGame(interaction.user.id, bet)
        tower_games[interaction.user.id] = game
        embed = discord.Embed(title=" Tower Game", description=f"Level: **1 / 10**\nMultiplier: **1.00x**\nBet: **${bet:,}**", color=discord.Color.blurple())
        embed.add_field(name="Progress", value=game.progress_bar(), inline=False)
        await interaction.response.send_message(embed=embed, view=TowerView(game))

    @app_commands.command(name="cleartower", description="Clear stuck tower game")
    async def cleartower(self, interaction: discord.Interaction):
        if interaction.user.id in tower_games:
            del tower_games[interaction.user.id]
            await interaction.response.send_message("Tower cleared!", ephemeral=True)
        else: await interaction.response.send_message("No active game.", ephemeral=True)
            
async def setup(bot: commands.Bot):
    await bot.add_cog(Games(bot))
