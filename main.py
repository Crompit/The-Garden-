import discord
from discord.ext import commands, tasks
from discord import app_commands
import random
import asyncio
from flask import Flask
import threading
import os

TOKEN = os.environ['TOKEN']  # Render token from environment

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Economy storage
user_balances = {}
user_plants = {}
current_weather = None
luck_multiplier = 1.0

# Weather events and their multipliers
weather_events = {
    "rain": 2,
    "thunderstorm": 100,
    "blizzard": 70,
    "heatwave": 30,
    "sandstorm": 1,
    "disco": 120,  # Admin only
    "dj_party": 180  # Admin only
}

# Plant rarities
plants = {
    "sunflower": 7,
    "rose": 23,
    "tulip": 30,
    "daisy": 40
}

# Flask keepalive
app = Flask('')

@app.route('/')
def home():
    return "The Garden Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = threading.Thread(target=run)
    t.start()

keep_alive()

# Auto weather every 10 mins
@tasks.loop(minutes=10)
async def auto_weather():
    global current_weather, luck_multiplier
    current_weather = random.choice(list(weather_events.keys()))
    luck_multiplier = weather_events[current_weather]
    print(f"🌦️ Auto weather: {current_weather} (x{luck_multiplier})")
    await asyncio.sleep(120)  # Event lasts 2 minutes
    current_weather = None
    luck_multiplier = 1.0
    print("⛅ Weather cleared.")

@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash commands")
    except Exception as e:
        print(e)
    auto_weather.start()
    print(f"🌱 The Garden Bot is online as {bot.user}")

# Economy commands
@bot.tree.command(name="balance", description="Check your balance")
async def balance(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    balance = user_balances.get(user_id, 0)
    await interaction.response.send_message(f"💰 You have {balance} coins.")

@bot.tree.command(name="daily", description="Claim daily coins")
async def daily(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    coins = random.randint(50, 100)
    user_balances[user_id] = user_balances.get(user_id, 0) + coins
    await interaction.response.send_message(f"🎁 You claimed your daily {coins} coins!")

@bot.tree.command(name="beg", description="Beg for some coins")
async def beg(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    coins = random.randint(5, 20)
    user_balances[user_id] = user_balances.get(user_id, 0) + coins
    await interaction.response.send_message(f"🙏 Someone gave you {coins} coins!")

@bot.tree.command(name="work", description="Work to earn coins")
async def work(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    jobs = ["Gardener", "Farmer", "Botanist", "Florist"]
    job = random.choice(jobs)
    coins = random.randint(20, 80)
    user_balances[user_id] = user_balances.get(user_id, 0) + coins
    await interaction.response.send_message(f"👨‍🌾 You worked as a {job} and earned {coins} coins.")

# Admin commands
@bot.tree.command(name="addcoins", description="Admin: Add coins to a user")
@app_commands.describe(user="User to add coins to", amount="Amount of coins")
async def addcoins(interaction: discord.Interaction, user: discord.User, amount: int):
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("🚫 You don't have permission.", ephemeral=True)
        return
    user_id = str(user.id)
    user_balances[user_id] = user_balances.get(user_id, 0) + amount
    await interaction.response.send_message(f"✅ Added {amount} coins to {user.mention}.")

@bot.tree.command(name="removecoins", description="Admin: Remove coins from a user")
@app_commands.describe(user="User to remove coins from", amount="Amount of coins")
async def removecoins(interaction: discord.Interaction, user: discord.User, amount: int):
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("🚫 You don't have permission.", ephemeral=True)
        return
    user_id = str(user.id)
    user_balances[user_id] = max(user_balances.get(user_id, 0) - amount, 0)
    await interaction.response.send_message(f"✅ Removed {amount} coins from {user.mention}.")

# Planting system
@bot.tree.command(name="plant", description="Plant seeds in your garden")
async def plant(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    cost = 20
    if user_balances.get(user_id, 0) < cost:
        await interaction.response.send_message("❌ You need 20 coins to plant.")
        return
    user_balances[user_id] -= cost
    chance = random.randint(1, 100)
    result = None
    for plant, rarity in plants.items():
        if chance <= rarity:
            result = plant
            break
    if not result:
        result = "common grass"
    user_plants[user_id] = user_plants.get(user_id, []) + [result]
    await interaction.response.send_message(f"🌱 You planted a seed and grew a **{result}**!")

@bot.tree.command(name="harvest", description="Harvest your plants")
async def harvest(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    if user_id not in user_plants or not user_plants[user_id]:
        await interaction.response.send_message("🌾 You have no plants to harvest.")
        return
    reward = random.randint(30, 100) * luck_multiplier
    reward = int(reward)
    user_balances[user_id] += reward
    harvested = len(user_plants[user_id])
    user_plants[user_id] = []
    await interaction.response.send_message(f"🌾 You harvested {harvested} plants and earned {reward} coins!")

# Spawn weather (admin only)
@bot.tree.command(name="spawnweather", description="Admin: Spawn a weather event")
@app_commands.describe(event="Name of the weather event")
async def spawnweather(interaction: discord.Interaction, event: str):
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("🚫 You don't have permission.", ephemeral=True)
        return
    if event not in weather_events:
        await interaction.response.send_message(f"⚠️ Invalid weather! Options: {', '.join(weather_events.keys())}", ephemeral=True)
        return
    global current_weather, luck_multiplier
    current_weather = event
    luck_multiplier = weather_events[event]
    await interaction.response.send_message(f"🌤️ Weather set to **{event}** with x{luck_multiplier} multiplier.")

bot.run(TOKEN)
