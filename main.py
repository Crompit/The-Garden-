import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import random
import datetime
import json
import os
from flask import Flask
from threading import Thread

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

# Storage for coins and plants
data = {"coins": {}, "plants": {}, "mutations": {}, "server_luck": 1}

MOD_ROLE_ID = 1389121338123485224  # Mods
ADMIN_PERMS = discord.Permissions(administrator=True)

# Flask keepalive
app = Flask('')

@app.route('/')
def home():
    return "I'm alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

Thread(target=run).start()

# Save & Load
def save_data():
    with open("data.json", "w") as f:
        json.dump(data, f)

def load_data():
    global data
    try:
        with open("data.json", "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        save_data()

load_data()

# Cooldowns
cooldowns = {}

def check_cooldown(user_id, cmd, seconds):
    now = datetime.datetime.now().timestamp()
    if user_id in cooldowns and cmd in cooldowns[user_id]:
        if now - cooldowns[user_id][cmd] < seconds:
            return False, int(seconds - (now - cooldowns[user_id][cmd]))
    cooldowns.setdefault(user_id, {})[cmd] = now
    return True, 0

# Economy commands
@bot.tree.command(name="balance")
async def balance(interaction: discord.Interaction):
    user = interaction.user
    coins = data["coins"].get(str(user.id), 0)
    await interaction.response.send_message(f"💰 {user.mention}, you have {coins} coins.")

@bot.tree.command(name="daily")
async def daily(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    ok, wait = check_cooldown(user_id, "daily", 86400)
    if not ok:
        await interaction.response.send_message(f"⏳ Wait {wait}s for your next daily reward.")
        return
    data["coins"][user_id] = data["coins"].get(user_id, 0) + 100
    save_data()
    await interaction.response.send_message(f"✅ {interaction.user.mention}, you received 100 daily coins!")

@bot.tree.command(name="work")
async def work(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    ok, wait = check_cooldown(user_id, "work", 3600)
    if not ok:
        await interaction.response.send_message(f"⏳ Wait {wait}s to work again.")
        return
    earned = random.randint(50, 150)
    earned = int(earned * current_event["multiplier"])  # Weather boost
    data["coins"][user_id] = data["coins"].get(user_id, 0) + earned
    save_data()
    await interaction.response.send_message(f"💼 {interaction.user.mention}, you worked and earned {earned} coins!")

@bot.tree.command(name="beg")
async def beg(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    ok, wait = check_cooldown(user_id, "beg", 300)
    if not ok:
        await interaction.response.send_message(f"⏳ Wait {wait}s before begging again.")
        return
    earned = random.randint(10, 50)
    earned = int(earned * current_event["multiplier"])  # Weather boost
    data["coins"][user_id] = data["coins"].get(user_id, 0) + earned
    save_data()
    await interaction.response.send_message(f"🙇 {interaction.user.mention}, someone gave you {earned} coins.")

@bot.tree.command(name="addcoins")
@app_commands.checks.has_role(MOD_ROLE_ID)
async def addcoins(interaction: discord.Interaction, member: discord.Member, amount: int):
    user_id = str(member.id)
    data["coins"][user_id] = data["coins"].get(user_id, 0) + amount
    save_data()
    await interaction.response.send_message(f"✅ Added {amount} coins to {member.mention}.")

@bot.tree.command(name="removecoins")
@app_commands.checks.has_role(MOD_ROLE_ID)
async def removecoins(interaction: discord.Interaction, member: discord.Member, amount: int):
    user_id = str(member.id)
    data["coins"][user_id] = max(0, data["coins"].get(user_id, 0) - amount)
    save_data()
    await interaction.response.send_message(f"✅ Removed {amount} coins from {member.mention}.")

# Plant system
plants = {
    "Sunflower": 7,
    "Rose": 23,
    "Tulip": 30,
    "Daisy": 40
}

@bot.tree.command(name="plant")
async def plant(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    if data["coins"].get(user_id, 0) < 50:
        await interaction.response.send_message("❌ Not enough coins to plant (50 needed).")
        return
    data["coins"][user_id] -= 50
    roll = random.randint(1, 100)
    for plant, chance in plants.items():
        if roll <= chance:
            data["plants"][user_id] = data["plants"].get(user_id, []) + [plant]
            save_data()
            await interaction.response.send_message(f"🌱 You planted a {plant}!")
            return
    await interaction.response.send_message("😢 Your plant failed to grow.")

@bot.tree.command(name="inventory")
async def inventory(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    inventory = data["plants"].get(user_id, [])
    if not inventory:
        await interaction.response.send_message("🌿 Your garden is empty.")
    else:
        await interaction.response.send_message(f"🌿 Your plants: {', '.join(inventory)}")

# Weather events
weather_events = {
    "Rain": 2,
    "Thunderstorm": 3,
    "Sandstorm": 1.5,
    "Disco": 5,
    "DJ Jhai": 10  # Admin only
}

current_event = {"name": None, "multiplier": 1}

@tasks.loop(minutes=10)
async def auto_event():
    global current_event
    event = random.choice(list(weather_events.items()))
    current_event = {"name": event[0], "multiplier": event[1]}
    channel = discord.utils.get(bot.get_all_channels(), name="general")
    if channel:
        await channel.send(f"🌩️ **{event[0]}** has started! All rewards boosted x{event[1]} for 2 minutes.")
    await asyncio.sleep(120)
    current_event = {"name": None, "multiplier": 1}

@bot.tree.command(name="spawnevent")
@app_commands.checks.has_permissions(administrator=True)
async def spawnevent(interaction: discord.Interaction, event_name: str):
    if event_name not in weather_events:
        await interaction.response.send_message("❌ Invalid event name.")
        return
    global current_event
    current_event = {"name": event_name, "multiplier": weather_events[event_name]}
    await interaction.response.send_message(f"🌩️ **{event_name}** spawned by admin! All rewards boosted x{weather_events[event_name]} for 2 minutes.")
    await asyncio.sleep(120)
    current_event = {"name": None, "multiplier": 1}

# Start bot
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash commands.")
    except Exception as e:
        print(e)
    auto_event.start()

bot.run(os.getenv("TOKEN"))
