# 🎮 My Discord Bot

![Bot Demo](https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExOHoxZ28xa2RlaHBra3NrOWRyZjQ3NWtjc3gycmdmbHR4YW1kbWNrZiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/Kb3VjUXG7pHLPsTUbK/giphy.gif)

A fun and interactive Discord bot with games, utilities, and a balance system.  
Currently in **development** ⚠️ — please bear with any bugs!  

---

# 🤖 Discord Casino & Game Bot

Your all-in-one **Discord entertainment bot** — complete with casino-style games, Wordle, a global economy system, and now **AI image generation** using **Hugging Face Stable Diffusion** 🎨

---

## 🌐 Bot Status
![Discord Status](https://img.shields.io/badge/✔-Online-brightgreen) |
![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)
![Discord.py](https://img.shields.io/badge/Discord.py-2.3+-5865F2?logo=discord)
![License](https://img.shields.io/badge/License-MIT-green)

## 💬 Connect with Me

[![Discord](https://img.shields.io/badge/Discord-Message%20Me-7289DA?logo=discord&logoColor=white)](https://discord.com/users/868504267927986197)

> 🕒 *Bot runs 24/7 on Render hosting with built-in Flask keep-alive.*

---

## 🌟 Features

### 🎲 Games & Casino

| Game | Description | Status |
|------|--------------|--------|
| 🃏 **Blackjack** | Bet and play against the dealer | ![Status](https://img.shields.io/badge/✔-Available-brightgreen) |
| 🧩 **Wordle** | Guess the 5-letter word in 5 tries | ![Status](https://img.shields.io/badge/✔-Available-brightgreen) |
| 💣 **Mines** | Reveal tiles, avoid mines to increase multiplier | ![Status](https://img.shields.io/badge/✔-Available-brightgreen) |
| 🧱 **Tower Game** | Climb levels, avoid bombs, and cash out | ![Status](https://img.shields.io/badge/✔-Available-brightgreen) |
| 🧱 **Baccarat** | Bet and play against the dealer | ![Status](https://img.shields.io/badge/✔-Available-brightgreen) |

---

### ⚙️ Utility & Fun Commands

| Command | Description |
|---------|-------------|
| `/ping` | Check bot latency |
| `/userinfo` | Display information about a user |
| `/balance` | Show your current balance |
| `/leaderboard` | View the richest players and total profits |
| `/blackjack` | Play Blackjack and bet coins |
| `/wordle` | Start a new Wordle game |
| `/mines` | Play Mines (Minesweeper betting) |
| `/clearmines` | Clear any stuck Mines game |
| `/tower` | Play the Tower casino game |
| `/cleartower` | Clear any stuck Tower game |
| `/recreate` | Generate an AI image from text (powered by Hugging Face 🎨) |
| `/Ban` | Bans user from server |
| `/Kick` |Kicks user from server |
| `/Timeout` | time out user for a specific amount of time |

---

### 💰 Economy System

- 💵 **Integrated currency system** shared across all games  
- 💎 Start with `$10,000` in your balance  
- 📈 Win or lose depending on your game results  
- 🏦 Persistent balances saved in `player_balances.json`  
- 🏆 Global `/leaderboard` ranking shows the top players  

---

### 🧠 AI Image Generation

| Feature | Description |
|----------|--------------|
| `/recreate scene:<text>` | Generate stunning images with text prompts using **Hugging Face Stable Diffusion XL** |
| Example | `/recreate scene: draw my minecraft base as an ancient ruin` |
| API | Uses the free Hugging Face inference API (`stabilityai/stable-diffusion-xl-base-1.0`) |
| Env Variable | `HUGGINGFACE_TOKEN` required for authentication |

---

## 🛠️ Setup & Hosting

### 1️⃣ Requirements
- Python 3.11+
- `discord.py`, `aiohttp`, `flask`, `openpyxl`, `python-dotenv`

### 2️⃣ Environment Variables
| Variable | Description |
|-----------|--------------|
| `DISCORD_TOKEN` | Your Discord bot token |
| `HUGGINGFACE_TOKEN` | Your Hugging Face API token |
| `PORT` | Required for Flask keep-alive on Render |

### 3️⃣ Run
```bash
python main.py


---

## 🛠 Setup

1. Set environment variables:
```bash
DISCORD_TOKEN=<your_bot_token>
GUILD_ID=<your_guild_id>  # optional for faster command sync















