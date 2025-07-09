import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import random
import json
from flask import Flask
from threading import Thread
import requests
import time
import os

# ===== CONFIG =====
TOKEN = "MTM5MjA4NDQyNzMxMTQxNTM0Nw.GjXvuO.t0xOlTieqk05RwibThDcsyXaAczYsLy3cokorE"  # 🔥 Replace this with your bot token
CONFESS_CHANNEL_ID = 1392370500914774136
MOD_ROLE_ID = 1389121338123485224
BALANCES_FILE = "balances.json"
REPL_URL = "https://0582873e-f1a7-4eb9-80d5-cc9ed694385e-00-mop5ggj5081x.pike.replit.dev"  # 🔥 Replace with your Replit web URL

# ===== DISCORD BOT =====
intents = discord.Intents.default()
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ===== LOAD & SAVE BALANCES =====
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

# ===== EVENTS =====
@bot.event
async def on_ready():
    await tree.sync()
    print(f"✅ Logged in as {bot.user}")
    print("🌱 The Garden Bot is ready!")

# ===== ECONOMY COMMANDS =====
@tree.command(name="ping", description="Check the bot's latency")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"🏓 Pong! Latency: {latency}ms")

@tree.command(name="balance", description="Check your coin balance")
async def balance(interaction: discord.Interaction):
    bal = get_balance(interaction.user.id)
    await interaction.response.send_message(f"💰 {interaction.user.mention}, you have **{bal} coins**.")

@tree.command(name="give", description="Give coins to another user")
@app_commands.describe(member="The user to give coins to", amount="Amount of coins")
async def give(interaction: discord.Interaction, member: discord.Member, amount: int):
    giver_id = interaction.user.id
    if amount <= 0:
        await interaction.response.send_message("❌ Amount must be positive.")
        return
    if get_balance(giver_id) < amount:
        await interaction.response.send_message("❌ You don’t have enough coins.")
        return
    set_balance(giver_id, get_balance(giver_id) - amount)
    set_balance(member.id, get_balance(member.id) + amount)
    await interaction.response.send_message(f"✅ Gave **{amount} coins** to {member.mention}!")

@tree.command(name="trade", description="Trade coins with another user")
@app_commands.describe(member="The user to trade with", amount="Amount of coins")
async def trade(interaction: discord.Interaction, member: discord.Member, amount: int):
    trader_id = interaction.user.id
    if amount <= 0:
        await interaction.response.send_message("❌ Amount must be positive.")
        return
    if get_balance(trader_id) < amount:
        await interaction.response.send_message("❌ You don’t have enough coins.")
        return
    set_balance(trader_id, get_balance(trader_id) - amount)
    set_balance(member.id, get_balance(member.id) + amount)
    await interaction.response.send_message(f"🔄 Trade: {interaction.user.mention} gave {amount} coins to {member.mention}.")

# ===== CONFESSION =====
@tree.command(name="confess", description="Post an anonymous confession")
@app_commands.describe(message="Your confession message")
async def confess(interaction: discord.Interaction, message: str):
    channel = bot.get_channel(CONFESS_CHANNEL_ID)
    if channel:
        await channel.send(f"📢 **Anonymous Confession:**\n>>> {message}")
        await interaction.response.send_message("✅ Your confession has been sent anonymously.")
    else:
        await interaction.response.send_message("❌ Confession channel not found.")

# ===== MOD ONLY COMMANDS =====
@tree.command(name="addcoins", description="Add coins to a user (Mods only)")
@app_commands.describe(member="User to give coins to", amount="Amount of coins")
async def addcoins(interaction: discord.Interaction, member: discord.Member, amount: int):
    if MOD_ROLE_ID in [role.id for role in interaction.user.roles]:
        set_balance(member.id, get_balance(member.id) + amount)
        await interaction.response.send_message(f"✅ Added {amount} coins to {member.mention}.")
    else:
        await interaction.response.send_message("❌ You don’t have permission to use this command.", ephemeral=True)

@tree.command(name="removecoins", description="Remove coins from a user (Mods only)")
@app_commands.describe(member="User to remove coins from", amount="Amount of coins")
async def removecoins(interaction: discord.Interaction, member: discord.Member, amount: int):
    if MOD_ROLE_ID in [role.id for role in interaction.user.roles]:
        new_balance = max(get_balance(member.id) - amount, 0)
        set_balance(member.id, new_balance)
        await interaction.response.send_message(f"✅ Removed {amount} coins from {member.mention}.")
    else:
        await interaction.response.send_message("❌ You don’t have permission to use this command.", ephemeral=True)

# ===== KEEP ALIVE =====
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

# ===== SELF PING =====
def self_ping():
    while True:
        try:
            requests.get(REPL_URL)
            print("🔄 Self-ping sent")
        except Exception as e:
            print("❌ Self-ping failed:", e)
        time.sleep(280)  # Ping every 4.5 min

Thread(target=self_ping).start()

# ===== RUN BOT =====
bot.run(TOKEN)