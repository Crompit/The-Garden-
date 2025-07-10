import discord
from discord.ext import commands, tasks
from discord import app_commands
import json, random, asyncio, os
from flask import Flask
from threading import Thread

# Get token from Render environment
TOKEN = os.getenv("TOKEN")
MOD_ROLE_ID = 1389121338123485224  # Replace with mod role ID
ADMIN_ROLE_ID = 1389121338123485224  # Replace with admin role ID
CONFESS_CHANNEL_ID = 123456789012345678  # Replace with confession channel ID

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

data_file = "data.json"

# Load & save functions
def load_data():
    try:
        with open(data_file, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"coins": {}, "inventory": {}, "events": {}, "boost": 1}

def save_data():
    with open(data_file, "w") as f:
        json.dump(data, f, indent=4)

data = load_data()

# 🌱 Plant rarities
plants = [
    {"name": "Sunflower", "chance": 7, "reward": (150, 300)},
    {"name": "Rose", "chance": 23, "reward": (50, 150)},
    {"name": "Blueberry", "chance": 30, "reward": (30, 100)},
    {"name": "Burning Bud", "chance": 10, "reward": (200, 400)}
]

# 🌤 Events with multipliers
events = {
    "Rain": 2,
    "Thunderstorm": 100,
    "Sandstorm": 3,
    "Disco": 10,
    "DJ Thai": 50
}

active_event = {"name": None, "multiplier": 1}

# Flask app for uptime
app = Flask('')
@app.route('/')
def home():
    return "🌱 The Garden Bot is alive!"
def run():
    app.run(host='0.0.0.0', port=8080)
def keep_alive():
    t = Thread(target=run)
    t.start()

# 🪙 Economy commands
@tree.command(name="balance", description="Check your coin balance")
async def balance(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    coins = data["coins"].get(user_id, 0)
    await interaction.response.send_message(f"💰 You have {coins} coins.", ephemeral=True)

@tree.command(name="daily", description="Claim your daily coins")
async def daily(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    reward = random.randint(50, 100) * active_event["multiplier"]
    data["coins"][user_id] = data["coins"].get(user_id, 0) + reward
    save_data()
    await interaction.response.send_message(f"🌞 Daily reward: {reward} coins! Event Boost: x{active_event['multiplier']}")

# 🌱 Planting & harvesting
@tree.command(name="plant", description="Plant a random seed")
async def plant(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    choice = random.choices(plants, weights=[p['chance'] for p in plants], k=1)[0]
    name = choice['name']
    data["inventory"].setdefault(user_id, []).append(name)
    save_data()
    await interaction.response.send_message(f"🌱 You planted a **{name}**!")

@tree.command(name="harvest", description="Harvest your plants for coins")
async def harvest(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    plants_owned = data["inventory"].get(user_id, [])
    if not plants_owned:
        await interaction.response.send_message("❌ You have no plants to harvest.")
        return
    total_reward = sum(random.randint(*next(p['reward'] for p in plants if p['name'] == plant)) for plant in plants_owned)
    total_reward *= active_event["multiplier"]
    data["coins"][user_id] += total_reward
    data["inventory"][user_id] = []
    save_data()
    await interaction.response.send_message(f"🌾 You harvested your garden and earned **{total_reward} coins**!")

# 🌩️ Admin-only spawn events
@tree.command(name="spawn_event", description="Spawn a weather event (admin only)")
@app_commands.describe(event_name="Name of the event")
async def spawn_event(interaction: discord.Interaction, event_name: str):
    if not any(role.id == ADMIN_ROLE_ID for role in interaction.user.roles):
        await interaction.response.send_message("❌ You don't have permission.", ephemeral=True)
        return
    if event_name in events:
        active_event["name"] = event_name
        active_event["multiplier"] = events[event_name]
        await interaction.response.send_message(f"⚡ Admin spawned **{event_name}** (x{events[event_name]} boost)!")
    else:
        await interaction.response.send_message("❌ Unknown event name.", ephemeral=True)

# 🌐 Start Flask + bot
keep_alive()
bot.run(TOKEN)
