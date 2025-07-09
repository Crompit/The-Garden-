import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import json
import requests
import time
import os
from flask import Flask
from threading import Thread
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()
TOKEN = os.getenv("TOKEN")
REPL_URL = os.getenv("REPL_URL")
CONFESS_CHANNEL_ID = 1392370500914774136
MOD_ROLE_ID = 1389121338123485224
BALANCES_FILE = "balances.json"

# ====== BOT SETUP ======
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ====== BALANCE SYSTEM ======
def load_balances():
    if os.path.exists(BALANCES_FILE):
        with open(BALANCES_FILE, "r") as f:
            return json.load(f)
    return {}

def save_balances():
    with open(BALANCES_FILE, "w") as f:
        json.dump(user_balances, f)

user_balances = load_balances()

def get_balance(user_id):
    return user_balances.get(str(user_id), 0)

def set_balance(user_id, amount):
    user_balances[str(user_id)] = amount
    save_balances()

# ====== EVENTS ======
@bot.event
async def on_ready():
    await tree.sync()
    print(f"✅ Logged in as {bot.user}")
    print("🌱 The Garden Bot is ready!")

# ====== ECONOMY COMMANDS ======
@tree.command(name="balance", description="Check your coin balance")
async def balance(interaction: discord.Interaction):
    bal = get_balance(interaction.user.id)
    await interaction.response.send_message(f"💰 {interaction.user.mention}, you have **{bal} coins**.")

@tree.command(name="give", description="Give coins to another user")
@app_commands.describe(member="The user to give coins to", amount="Amount of coins")
async def give(interaction: discord.Interaction, member: discord.Member, amount: int):
    if amount <= 0:
        await interaction.response.send_message("❌ Amount must be positive.")
        return
    giver_balance = get_balance(interaction.user.id)
    if giver_balance < amount:
        await interaction.response.send_message("❌ You don’t have enough coins.")
        return
    set_balance(interaction.user.id, giver_balance - amount)
    set_balance(member.id, get_balance(member.id) + amount)
    await interaction.response.send_message(f"✅ Gave **{amount} coins** to {member.mention}!")

@tree.command(name="trade", description="Trade coins with another user")
@app_commands.describe(member="The user to trade with", amount="Amount of coins")
async def trade(interaction: discord.Interaction, member: discord.Member, amount: int):
    if amount <= 0:
        await interaction.response.send_message("❌ Amount must be positive.")
        return
    trader_balance = get_balance(interaction.user.id)
    if trader_balance < amount:
        await interaction.response.send_message("❌ You don’t have enough coins.")
        return
    set_balance(interaction.user.id, trader_balance - amount)
    set_balance(member.id, get_balance(member.id) + amount)
    await interaction.response.send_message(f"🔄 {interaction.user.mention} traded **{amount} coins** to {member.mention}.")

# ====== CONFESSION COMMAND ======
@tree.command(name="confess", description="Post an anonymous confession")
@app_commands.describe(message="Your confession message")
async def confess(interaction: discord.Interaction, message: str):
    channel = bot.get_channel(CONFESS_CHANNEL_ID)
    if channel:
        await channel.send(f"📢 **Anonymous Confession:**\n>>> {message}")
        await interaction.response.send_message("✅ Your confession has been sent anonymously.")
    else:
        await interaction.response.send_message("❌ Confession channel not found.")

# ====== MOD-ONLY COMMANDS ======
def is_mod(user):
    return any(role.id == MOD_ROLE_ID for role in user.roles)

@tree.command(name="addcoins", description="Add coins to a user (Mods only)")
@app_commands.describe(member="User to give coins to", amount="Amount of coins")
async def addcoins(interaction: discord.Interaction, member: discord.Member, amount: int):
    if is_mod(interaction.user):
        set_balance(member.id, get_balance(member.id) + amount)
        await interaction.response.send_message(f"✅ Added {amount} coins to {member.mention}.")
    else:
        await interaction.response.send_message("❌ You don’t have permission to use this command.", ephemeral=True)

@tree.command(name="removecoins", description="Remove coins from a user (Mods only)")
@app_commands.describe(member="User to remove coins from", amount="Amount of coins")
async def removecoins(interaction: discord.Interaction, member: discord.Member, amount: int):
    if is_mod(interaction.user):
        new_balance = max(get_balance(member.id) - amount, 0)
        set_balance(member.id, new_balance)
        await interaction.response.send_message(f"✅ Removed {amount} coins from {member.mention}.")
    else:
        await interaction.response.send_message("❌ You don’t have permission to use this command.", ephemeral=True)

# ====== DAILY COMMAND ======
last_claims = {}

@tree.command(name="daily", description="Claim your daily reward")
async def daily(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    now = datetime.utcnow()
    last_claim = last_claims.get(user_id)

    if last_claim and now - last_claim < timedelta(hours=24):
        next_claim = last_claim + timedelta(hours=24)
        remaining = next_claim - now
        hours, remainder = divmod(int(remaining.total_seconds()), 3600)
        minutes, _ = divmod(remainder, 60)
        await interaction.response.send_message(
            f"🕒 You’ve already claimed your daily. Come back in {hours}h {minutes}m!"
        )
        return

    reward = 50  # Daily reward amount
    set_balance(interaction.user.id, get_balance(interaction.user.id) + reward)
    last_claims[user_id] = now
    await interaction.response.send_message(f"✅ You claimed your daily **{reward} coins**!")

# ====== WORD-BASED COINS ======
user_word_cooldowns = {}

@bot.event
async def on_message(message):
    if message.author.bot or message.guild is None:
        return

    user_id = str(message.author.id)
    now = time.time()

    if user_id not in user_word_cooldowns or now - user_word_cooldowns[user_id] > 10:
        word_count = len(message.content.split())
        coins_earned = min(word_count, 10)  # Max 10 coins per message
        if coins_earned > 0:
            set_balance(message.author.id, get_balance(message.author.id) + coins_earned)
        user_word_cooldowns[user_id] = now

    await bot.process_commands(message)

# ====== KEEP ALIVE ======
app = Flask('')

@app.route('/')
def home():
    return "🌱 The Garden Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

keep_alive()

# ====== SELF-PING ======
def self_ping():
    while True:
        try:
            requests.get(REPL_URL)
            print("🔄 Self-ping successful.")
        except Exception as e:
            print("❌ Self-ping failed:", e)
        time.sleep(280)  # Every 4.5 minutes

Thread(target=self_ping).start()

# ====== START BOT ======
bot.run(TOKEN)
