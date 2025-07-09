import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import json
import random
import os
from flask import Flask
from threading import Thread
from dotenv import load_dotenv
from datetime import datetime, timedelta

# ====== CONFIG ======
load_dotenv()
TOKEN = os.getenv("TOKEN")
CONFESS_CHANNEL_ID = 1392370500914774136
MOD_ROLE_ID = 1389121338123485224
DATA_FILE = "/data/garden_data.json"  # Persistent for economy + plants

# ====== BOT SETUP ======
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ====== LOAD/SAVE DATA ======
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"balances": {}, "gardens": {}}

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

data = load_data()

def get_balance(user_id):
    return data["balances"].get(str(user_id), 0)

def set_balance(user_id, amount):
    data["balances"][str(user_id)] = amount
    save_data()

def get_garden(user_id):
    return data["gardens"].get(str(user_id), {})

def add_plant(user_id, plant_name):
    garden = get_garden(user_id)
    garden[plant_name] = garden.get(plant_name, 0) + 1
    data["gardens"][str(user_id)] = garden
    save_data()

def clear_garden(user_id):
    data["gardens"][str(user_id)] = {}
    save_data()

# ====== EVENTS ======
@bot.event
async def on_ready():
    await tree.sync()
    print(f"✅ Logged in as {bot.user}")

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

# ====== GARDEN COMMANDS ======
plants = ["🌻 Sunflower", "🥕 Carrot", "🍓 Strawberry", "🌾 Wheat", "🌹 Rose"]

@tree.command(name="plant", description="Plant a random seed in your garden")
async def plant(interaction: discord.Interaction):
    user_id = interaction.user.id
    cost = 10
    balance = get_balance(user_id)
    if balance < cost:
        await interaction.response.send_message("❌ Not enough coins. Planting costs 10 coins.")
        return
    plant_choice = random.choice(plants)
    set_balance(user_id, balance - cost)
    add_plant(user_id, plant_choice)
    await interaction.response.send_message(f"🌱 You planted a {plant_choice}!")

@tree.command(name="harvest", description="Harvest all plants in your garden for coins")
async def harvest(interaction: discord.Interaction):
    user_id = interaction.user.id
    garden = get_garden(user_id)
    if not garden:
        await interaction.response.send_message("❌ You don’t have any plants to harvest.")
        return
    total_reward = 0
    message = "🌾 You harvested:\n"
    for plant, count in garden.items():
        reward = random.randint(5, 15) * count
        total_reward += reward
        message += f"• {plant} x{count} → 💰 {reward} coins\n"
    set_balance(user_id, get_balance(user_id) + total_reward)
    clear_garden(user_id)
    message += f"\nTotal earned: **{total_reward} coins** 💸"
    await interaction.response.send_message(message)

@tree.command(name="inventory", description="View your garden inventory")
async def inventory(interaction: discord.Interaction):
    user_id = interaction.user.id
    garden = get_garden(user_id)
    if not garden:
        await interaction.response.send_message("🌱 Your garden is empty. Use `/plant` to grow something!")
        return
    message = "🌿 **Your Garden:**\n"
    for plant, count in garden.items():
        message += f"• {plant} x{count}\n"
    await interaction.response.send_message(message)

# ====== FLASK KEEPALIVE ======
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

# ====== START BOT ======
bot.run(TOKEN)
