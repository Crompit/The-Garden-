import discord
from discord.ext import commands
from discord import app_commands
import random
import os
from flask import Flask
from threading import Thread
from datetime import datetime, timedelta

# Flask keep-alive
app = Flask('')

@app.route('/')
def home():
    return "🌱 The Garden Bot is alive with RARITIES & LUCK BOOST!"

def run():
    app.run(host="0.0.0.0", port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# Bot setup
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# Data storage
user_balances = {}
user_gardens = {}
user_daily_timers = {}
server_luck = {}

def get_balance(user_id):
    return user_balances.get(user_id, 0)

def update_balance(user_id, amount):
    user_balances[user_id] = get_balance(user_id) + amount

def get_garden(user_id):
    return user_gardens.get(user_id, {"plants": [], "watered": False})

def update_garden(user_id, plants=None, watered=None):
    garden = get_garden(user_id)
    if plants is not None:
        garden["plants"] = plants
    if watered is not None:
        garden["watered"] = watered
    user_gardens[user_id] = garden

def get_luck(guild_id):
    return server_luck.get(guild_id, {"active": False, "ends_at": None})

def set_luck(guild_id, active, duration_minutes=0):
    ends_at = datetime.utcnow() + timedelta(minutes=duration_minutes) if active else None
    server_luck[guild_id] = {"active": active, "ends_at": ends_at}

# Events
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    try:
        synced = await tree.sync()
        print(f"🌐 Synced {len(synced)} slash commands")
    except Exception as e:
        print(f"Error syncing commands: {e}")

# Economy Commands
@tree.command(name="balance", description="Check your coin balance 🌱")
async def balance(interaction: discord.Interaction):
    coins = get_balance(interaction.user.id)
    await interaction.response.send_message(f"💰 {interaction.user.mention}, you have **{coins} coins**.")

@tree.command(name="daily", description="Claim your daily coins 🌞")
async def daily(interaction: discord.Interaction):
    now = datetime.utcnow()
    user_id = interaction.user.id

    if user_id in user_daily_timers:
        next_claim_time = user_daily_timers[user_id]
        if now < next_claim_time:
            remaining = next_claim_time - now
            hours, remainder = divmod(int(remaining.total_seconds()), 3600)
            minutes, _ = divmod(remainder, 60)
            await interaction.response.send_message(
                f"⏳ You already claimed your daily! Come back in {hours}h {minutes}m.",
                ephemeral=True
            )
            return

    update_balance(user_id, 100)
    user_daily_timers[user_id] = now + timedelta(hours=24)
    await interaction.response.send_message(
        f"✅ {interaction.user.mention}, you claimed **100 daily coins**! Come back tomorrow 🌞"
    )

@tree.command(name="beg", description="Beg for coins 💸")
async def beg(interaction: discord.Interaction):
    reward = random.randint(5, 15)
    update_balance(interaction.user.id, reward)
    await interaction.response.send_message(f"🪙 {interaction.user.mention}, someone gave you **{reward} coins**!")

# Mods only
@tree.command(name="addcoins", description="Mods only: Add coins to a user")
@app_commands.describe(user="User to add coins to", amount="Amount of coins")
async def addcoins(interaction: discord.Interaction, user: discord.Member, amount: int):
    if 1389121338123485224 in [role.id for role in interaction.user.roles]:
        update_balance(user.id, amount)
        await interaction.response.send_message(f"✅ Added **{amount} coins** to {user.mention}")
    else:
        await interaction.response.send_message("❌ You don't have permission.", ephemeral=True)

@tree.command(name="removecoins", description="Mods only: Remove coins from a user")
@app_commands.describe(user="User to remove coins from", amount="Amount of coins")
async def removecoins(interaction: discord.Interaction, user: discord.Member, amount: int):
    if 1389121338123485224 in [role.id for role in interaction.user.roles]:
        update_balance(user.id, -amount)
        await interaction.response.send_message(f"✅ Removed **{amount} coins** from {user.mention}")
    else:
        await interaction.response.send_message("❌ You don't have permission.", ephemeral=True)

# Luck Command
@tree.command(name="luck", description="Mods only: Activate server luck boost 🍀")
@app_commands.describe(duration="Minutes of luck boost")
async def luck(interaction: discord.Interaction, duration: int):
    if 1389121338123485224 in [role.id for role in interaction.user.roles]:
        set_luck(interaction.guild.id, True, duration)
        await interaction.response.send_message(f"🍀 Server-wide luck boost activated for **{duration} minutes**!")
    else:
        await interaction.response.send_message("❌ You don't have permission.", ephemeral=True)

# Garden Commands
RARITY_TABLE = [
    ("🌻 Sunflower", 7),
    ("🌹 Rose", 23),
    ("🍀 Clover", 50),
    ("🪴 Common Plant", 100)
]

def pick_plant(guild_id):
    luck = get_luck(guild_id)
    multiplier = 2 if luck["active"] and datetime.utcnow() < luck["ends_at"] else 1
    roll = random.uniform(0, 100)
    for plant, chance in RARITY_TABLE:
        if roll <= chance * multiplier:
            return plant
        roll -= chance
    return "🪴 Common Plant"

@tree.command(name="plant", description="Plant a seed 🌱 (costs 50 coins)")
async def plant(interaction: discord.Interaction):
    if get_balance(interaction.user.id) < 50:
        await interaction.response.send_message("❌ Not enough coins! (50 required)")
        return
    update_balance(interaction.user.id, -50)
    new_plant = pick_plant(interaction.guild.id)
    garden = get_garden(interaction.user.id)
    garden["plants"].append(new_plant)
    update_garden(interaction.user.id, plants=garden["plants"])
    await interaction.response.send_message(f"🌱 You planted a seed and got **{new_plant}**!")

@tree.command(name="water", description="Water your garden 💦")
async def water(interaction: discord.Interaction):
    garden = get_garden(interaction.user.id)
    if not garden["plants"]:
        await interaction.response.send_message("❌ You have no plants to water!")
        return
    if garden["watered"]:
        await interaction.response.send_message("💧 Your plants are already watered.")
        return
    update_garden(interaction.user.id, watered=True)
    await interaction.response.send_message("💦 You watered your garden! Next harvest will give a bonus.")

@tree.command(name="harvest", description="Harvest your plants 🍃 for coins")
async def harvest(interaction: discord.Interaction):
    garden = get_garden(interaction.user.id)
    if not garden["plants"]:
        await interaction.response.send_message("❌ You have no plants to harvest.")
        return
    total_reward = 0
    for plant in garden["plants"]:
        base = random.randint(20, 50)
        total_reward += base
    bonus = total_reward * 0.5 if garden["watered"] else 0
    total_reward = int(total_reward + bonus)
    update_balance(interaction.user.id, total_reward)
    update_garden(interaction.user.id, plants=[], watered=False)
    await interaction.response.send_message(
        f"🍃 You harvested your garden for **{total_reward} coins**!\n(Bonus applied: {bonus > 0})"
    )

# Start bot
keep_alive()
bot.run(os.environ['TOKEN'])
