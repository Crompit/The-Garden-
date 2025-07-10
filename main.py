import discord
from discord.ext import commands, tasks
from discord import app_commands
import json, random, asyncio
from flask import Flask
from threading import Thread

TOKEN = "YOUR_BOT_TOKEN"  # Replace with your token
MOD_ROLE_ID = 123456789012345678  # Replace with your mod role ID
ADMIN_ROLE_ID = 987654321098765432  # Replace with your admin role ID
CONFESS_CHANNEL_ID = 123456789012345678  # Replace with your confession channel ID

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
    return "The Garden Bot is alive!"
def run():
    app.run(host='0.0.0.0', port=8080)
def keep_alive():
    t = Thread(target=run)
    t.start()

# ✅ /balance
@tree.command(name="balance", description="Check your coin balance")
async def balance(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    coins = data["coins"].get(user_id, 0)
    await interaction.response.send_message(f"💰 {interaction.user.mention} you have **{coins} coins**.")

# ✅ /daily
@tree.command(name="daily", description="Claim your daily reward")
async def daily(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    if "last_daily" not in data:
        data["last_daily"] = {}
    last = data["last_daily"].get(user_id, 0)
    now = discord.utils.utcnow().timestamp()
    if now - last < 86400:
        await interaction.response.send_message("⏳ You already claimed daily today. Try again later!")
    else:
        reward = random.randint(100, 300)
        reward *= active_event["multiplier"]
        data["coins"][user_id] = data["coins"].get(user_id, 0) + reward
        data["last_daily"][user_id] = now
        save_data()
        await interaction.response.send_message(f"🎁 You claimed your daily and got **{reward} coins**!")

# ✅ /addcoins (mods only)
@tree.command(name="addcoins", description="Add coins to a user (mods only)")
@app_commands.describe(member="User to add coins to", amount="Amount of coins")
@app_commands.checks.has_role(MOD_ROLE_ID)
async def addcoins(interaction: discord.Interaction, member: discord.Member, amount: int):
    user_id = str(member.id)
    data["coins"][user_id] = data["coins"].get(user_id, 0) + amount
    save_data()
    await interaction.response.send_message(f"✅ Added {amount} coins to {member.mention}.")

# ✅ /removecoins (mods only)
@tree.command(name="removecoins", description="Remove coins from a user (mods only)")
@app_commands.describe(member="User to remove coins from", amount="Amount of coins")
@app_commands.checks.has_role(MOD_ROLE_ID)
async def removecoins(interaction: discord.Interaction, member: discord.Member, amount: int):
    user_id = str(member.id)
    data["coins"][user_id] = max(data["coins"].get(user_id, 0) - amount, 0)
    save_data()
    await interaction.response.send_message(f"❌ Removed {amount} coins from {member.mention}.")

# 🌱 /plant
@tree.command(name="plant", description="Plant a random seed")
async def plant(interaction: discord.Interaction):
    chance = random.randint(1, 100)
    reward_plant = None
    for p in plants:
        if chance <= p["chance"]:
            reward_plant = p
            break
    if reward_plant:
        item = reward_plant["name"]
        data["inventory"].setdefault(str(interaction.user.id), []).append(item)
        save_data()
        await interaction.response.send_message(f"🌱 You planted and got a **{item}**!")
    else:
        await interaction.response.send_message("😢 Nothing grew this time.")

# 🌾 /harvest
@tree.command(name="harvest", description="Harvest your plants for coins")
async def harvest(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    inventory = data["inventory"].get(user_id, [])
    if not inventory:
        await interaction.response.send_message("🌾 You don’t have any plants to harvest.")
        return
    total = 0
    for plant_name in inventory:
        for p in plants:
            if p["name"] == plant_name:
                reward = random.randint(*p["reward"])
                total += reward
                break
    total *= active_event["multiplier"]
    data["coins"][user_id] = data["coins"].get(user_id, 0) + total
    data["inventory"][user_id] = []
    save_data()
    await interaction.response.send_message(f"🌾 You harvested and earned **{total} coins**!")

# 🌩 /spawnevent (admins only)
@tree.command(name="spawnevent", description="Admins can spawn special weather events")
@app_commands.describe(event_name="The name of the event")
@app_commands.choices(event_name=[app_commands.Choice(name=k, value=k) for k in events])
@app_commands.checks.has_role(ADMIN_ROLE_ID)
async def spawnevent(interaction: discord.Interaction, event_name: str):
    active_event["name"] = event_name
    active_event["multiplier"] = events[event_name]
    await interaction.response.send_message(f"🌟 Event **{event_name}** activated! Multiplier: x{events[event_name]}")
    await asyncio.sleep(120)
    active_event["name"] = None
    active_event["multiplier"] = 1
    await interaction.followup.send(f"⏳ Event **{event_name}** has ended.")

# Auto events every 10 mins
@tasks.loop(minutes=10)
async def auto_event():
    if random.randint(1, 10) <= 3:  # 30% chance to trigger
        event_name = random.choice(list(events.keys()))
        active_event["name"] = event_name
        active_event["multiplier"] = events[event_name]
        channel = bot.get_channel(CONFESS_CHANNEL_ID)
        await channel.send(f"⚡ Event **{event_name}** started! x{events[event_name]} multiplier for 2 mins!")
        await asyncio.sleep(120)
        active_event["name"] = None
        active_event["multiplier"] = 1
        await channel.send(f"⏳ Event **{event_name}** ended.")

@bot.event
async def on_ready():
    await tree.sync()
    auto_event.start()
    print(f"✅ Logged in as {bot.user}")

# Keep-alive for Render
keep_alive()
bot.run(TOKEN)
