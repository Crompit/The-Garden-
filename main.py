import discord
from discord.ext import commands, tasks
from discord import app_commands
import random
import asyncio
import json
from datetime import datetime, timedelta
from flask import Flask
from threading import Thread
import os

TOKEN = os.getenv("TOKEN")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

data_file = "data.json"
if not os.path.exists(data_file):
    with open(data_file, "w") as f:
        json.dump({}, f)

def save_data(data):
    with open(data_file, "w") as f:
        json.dump(data, f)

def load_data():
    with open(data_file, "r") as f:
        return json.load(f)

data = load_data()

# Weather Events
weather_events = {
    "Rain": 2,
    "Thunderstorm": 100,
    "Sunny": 1,
    "Wet": 2,
    "Sandstorm": 0.5,
    "Disco": 10,
    "DJ_Thai": 50
}
current_weather = None
luck_active = False
luck_end = None

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    weather_loop.start()

# Economy Commands
@bot.tree.command(name="balance", description="Check your coin balance")
async def balance(interaction: discord.Interaction):
    user = str(interaction.user.id)
    coins = data.get(user, {}).get("coins", 0)
    await interaction.response.send_message(f"💰 You have {coins} coins.", ephemeral=True)

@bot.tree.command(name="daily", description="Claim your daily coins")
async def daily(interaction: discord.Interaction):
    user = str(interaction.user.id)
    user_data = data.setdefault(user, {"coins": 0, "plants": {}, "last_daily": None})
    now = datetime.utcnow()
    last_daily = user_data.get("last_daily")
    if last_daily and now - datetime.fromisoformat(last_daily) < timedelta(hours=24):
        await interaction.response.send_message("⏳ You already claimed daily today. Come back later.", ephemeral=True)
    else:
        user_data["coins"] += 100
        user_data["last_daily"] = now.isoformat()
        save_data(data)
        await interaction.response.send_message("✅ You claimed 100 daily coins!", ephemeral=True)

@bot.tree.command(name="beg", description="Beg for some coins")
async def beg(interaction: discord.Interaction):
    user = str(interaction.user.id)
    amount = random.randint(5, 20)
    user_data = data.setdefault(user, {"coins": 0, "plants": {}, "last_daily": None})
    user_data["coins"] += amount
    save_data(data)
    await interaction.response.send_message(f"🙏 You received {amount} coins.", ephemeral=True)

# Admin Coin Controls
@bot.tree.command(name="addcoins", description="Add coins to a user (Admin only)")
@app_commands.describe(member="Member to add coins", amount="Amount to add")
async def addcoins(interaction: discord.Interaction, member: discord.Member, amount: int):
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("🚫 You don't have permission.", ephemeral=True)
        return
    user = str(member.id)
    user_data = data.setdefault(user, {"coins": 0, "plants": {}, "last_daily": None})
    user_data["coins"] += amount
    save_data(data)
    await interaction.response.send_message(f"✅ Added {amount} coins to {member.display_name}.")

@bot.tree.command(name="removecoins", description="Remove coins from a user (Admin only)")
@app_commands.describe(member="Member to remove coins", amount="Amount to remove")
async def removecoins(interaction: discord.Interaction, member: discord.Member, amount: int):
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("🚫 You don't have permission.", ephemeral=True)
        return
    user = str(member.id)
    user_data = data.setdefault(user, {"coins": 0, "plants": {}, "last_daily": None})
    user_data["coins"] = max(user_data["coins"] - amount, 0)
    save_data(data)
    await interaction.response.send_message(f"✅ Removed {amount} coins from {member.display_name}.")

# Planting & Harvesting
plants = [
    {"name": "Rose", "chance": 23, "value": 50},
    {"name": "Sunflower", "chance": 7, "value": 200},
    {"name": "Tulip", "chance": 30, "value": 30},
    {"name": "Daisy", "chance": 40, "value": 20}
]

@bot.tree.command(name="plant", description="Plant a seed")
async def plant(interaction: discord.Interaction):
    user = str(interaction.user.id)
    user_data = data.setdefault(user, {"coins": 0, "plants": {}, "last_daily": None})
    if user_data["coins"] < 50:
        await interaction.response.send_message("🚫 Not enough coins (50 needed).", ephemeral=True)
        return
    user_data["coins"] -= 50
    selected = random.choices(plants, weights=[p["chance"] for p in plants])[0]
    user_data["plants"][selected["name"]] = {"growth": 0, "value": selected["value"]}
    save_data(data)
    await interaction.response.send_message(f"🌱 You planted a {selected['name']}!")

@bot.tree.command(name="harvest", description="Harvest your plants")
async def harvest(interaction: discord.Interaction):
    user = str(interaction.user.id)
    user_data = data.get(user, {"coins": 0, "plants": {}, "last_daily": None})
    total = 0
    for plant, info in user_data["plants"].items():
        if info["growth"] >= 100:
            boost = weather_events.get(current_weather, 1)
            coins = int(info["value"] * boost)
            total += coins
    if total == 0:
        await interaction.response.send_message("🌱 No plants ready to harvest.", ephemeral=True)
        return
    user_data["coins"] += total
    user_data["plants"] = {}
    save_data(data)
    await interaction.response.send_message(f"🌾 You harvested all plants for {total} coins!")

@bot.tree.command(name="inventory", description="See your plants")
async def inventory(interaction: discord.Interaction):
    user = str(interaction.user.id)
    user_data = data.get(user, {"coins": 0, "plants": {}, "last_daily": None})
    if not user_data["plants"]:
        await interaction.response.send_message("🌱 Your garden is empty.", ephemeral=True)
        return
    msg = "🌿 **Your Plants:**\n"
    for plant, info in user_data["plants"].items():
        msg += f"- {plant}: {info['growth']}% grown\n"
    await interaction.response.send_message(msg, ephemeral=True)

# Luck and Weather
@bot.tree.command(name="luck", description="Boost luck for the server")
async def luck(interaction: discord.Interaction, duration: int = 5):
    global luck_active, luck_end
    if luck_active:
        await interaction.response.send_message("🍀 Luck is already active!", ephemeral=True)
        return
    luck_active = True
    luck_end = datetime.utcnow() + timedelta(minutes=duration)
    await interaction.response.send_message(f"🍀 Luck boost activated for {duration} minutes!")

@bot.tree.command(name="spawnweather", description="Admin: Spawn a weather event")
@app_commands.describe(event="Name of the weather event")
async def spawnweather(interaction: discord.Interaction, event: str):
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("🚫 You don't have permission.", ephemeral=True)
        return

    if event not in weather_events:
        await interaction.response.send_message(f"⚠️ Invalid weather! Options: {', '.join(weather_events.keys())}", ephemeral=True)
        return

    await interaction.response.send_message(f"🌤️ Setting weather to **{event}**...")
    global current_weather
    current_weather = event
    print(f"✅ Admin manually set weather to {event}")

@bot.tree.command(name="growall", description="Admin: Grow all plants instantly")
async def growall(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("🚫 You don't have permission.", ephemeral=True)
        return
    for user_data in data.values():
        for info in user_data["plants"].values():
            info["growth"] = 100
    save_data(data)
    await interaction.response.send_message("🌱 All plants are fully grown!")

# Background Weather Loop
@tasks.loop(minutes=10)
async def weather_loop():
    global current_weather, luck_active
    if luck_active and datetime.utcnow() > luck_end:
        luck_active = False
    current_weather = random.choice(list(weather_events.keys()))
    print(f"☁️ Weather changed to {current_weather}")

# Flask Server for Render
app = Flask('')

@app.route('/')
def home():
    return "The Garden Bot is alive!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

Thread(target=run_flask).start()

# Start Bot
bot.run(TOKEN)
