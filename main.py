import discord
from discord.ext import commands, tasks
import random, asyncio, json
from datetime import datetime, timedelta
from flask import Flask
from threading import Thread

# Flask keep-alive
app = Flask('')

@app.route('/')
def home():
    return "🌱 The Garden Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# Bot setup
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="/", intents=intents)

# Economy storage
try:
    with open("economy.json", "r") as f:
        economy = json.load(f)
except FileNotFoundError:
    economy = {}

# Events & boosts
active_events = {}
event_boosts = {
    "thunderstorm": 100,
    "wet": 2,
    "sandstorm": 0.5,
    "sunshine": 1.5,
    "blizzard": 0.7,
    "heatwave": 1.2,
    "rainbow": 3,
    "drought": 0.3,
    "fertilizer": 2,
    "moonlight": 1.1,
    "dj": 5,
    "disco": 10
}

plants = {
    "Sunflower": 7,
    "Rose": 23,
    "Tulip": 30,
    "Lily": 25,
    "Orchid": 10,
    "Daisy": 5
}

cooldowns = {}

# Save data
def save_economy():
    with open("economy.json", "w") as f:
        json.dump(economy, f)

# Check & update balance
def get_balance(user_id):
    return economy.get(str(user_id), {}).get("coins", 0)

def update_balance(user_id, amount):
    economy.setdefault(str(user_id), {"coins": 0, "inventory": []})
    economy[str(user_id)]["coins"] += amount
    save_economy()

# Garden Commands
@bot.slash_command(name="balance")
async def balance(ctx):
    coins = get_balance(ctx.author.id)
    await ctx.respond(f"🌱 {ctx.author.mention}, you have **{coins} coins**.")

@bot.slash_command(name="daily")
async def daily(ctx):
    user = ctx.author
    now = datetime.utcnow()
    last = economy.get(str(user.id), {}).get("last_daily")

    if last and (now - datetime.fromisoformat(last)) < timedelta(days=1):
        await ctx.respond("⏳ You already claimed your daily reward today!")
        return

    update_balance(user.id, 100)
    economy[str(user.id)]["last_daily"] = now.isoformat()
    save_economy()
    await ctx.respond("✅ You claimed your daily 100 coins!")

@bot.slash_command(name="plant")
async def plant(ctx):
    user = ctx.author
    cost = 50
    if get_balance(user.id) < cost:
        await ctx.respond("💸 You need 50 coins to plant!")
        return

    update_balance(user.id, -cost)
    plant_choice = random.choices(list(plants.keys()), weights=plants.values())[0]
    economy[str(user.id)]["inventory"].append(plant_choice)
    save_economy()
    await ctx.respond(f"🌱 You planted a **{plant_choice}**!")

@bot.slash_command(name="harvest")
async def harvest(ctx):
    user = ctx.author
    inventory = economy.get(str(user.id), {}).get("inventory", [])
    if not inventory:
        await ctx.respond("🌾 You don’t have any plants to harvest!")
        return

    total_reward = 0
    for p in inventory:
        base_reward = random.randint(20, 50)
        boost = 1
        for event in active_events:
            boost *= event_boosts.get(event, 1)
        reward = int(base_reward * boost)
        total_reward += reward

    economy[str(user.id)]["inventory"] = []
    update_balance(user.id, total_reward)
    await ctx.respond(f"🌾 You harvested all plants for **{total_reward} coins**!")

# Mod-only commands
@bot.slash_command(name="addcoins")
@commands.has_role("Moderator")  # Replace with your Mod role name or ID
async def addcoins(ctx, member: discord.Member, amount: int):
    update_balance(member.id, amount)
    await ctx.respond(f"✅ Added {amount} coins to {member.mention}.")

@bot.slash_command(name="removecoins")
@commands.has_role("Moderator")
async def removecoins(ctx, member: discord.Member, amount: int):
    update_balance(member.id, -amount)
    await ctx.respond(f"✅ Removed {amount} coins from {member.mention}.")

# Luck boost
@bot.slash_command(name="luck")
@commands.has_role("Moderator")
async def luck(ctx, duration: int):
    active_events["luck"] = duration * 60
    await ctx.respond(f"🍀 Luck boost activated for {duration} minutes!")

# Admin-only event spawn
@bot.slash_command(name="spawnevent")
@commands.has_role("Admin")  # Replace with your Admin role name or ID
async def spawnevent(ctx, event: str):
    if event not in event_boosts:
        await ctx.respond("⚠️ Invalid event name!")
        return
    active_events[event] = 120  # Active for 2 minutes
    await ctx.respond(f"⚡ Event **{event}** has been spawned!")

# Automatic events
@tasks.loop(minutes=10)
async def spawn_random_event():
    event = random.choice(list(event_boosts.keys()))
    active_events[event] = 120
    print(f"🌟 Event {event} has started!")

@tasks.loop(seconds=60)
async def update_events():
    to_remove = []
    for event in active_events:
        active_events[event] -= 60
        if active_events[event] <= 0:
            to_remove.append(event)
    for event in to_remove:
        del active_events[event]
        print(f"❌ Event {event} has ended.")

# Start background tasks
spawn_random_event.start()
update_events.start()

# Start the bot
keep_alive()
bot.run("YOUR_BOT_TOKEN")
