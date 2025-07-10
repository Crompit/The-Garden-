import discord
from discord.ext import commands, tasks
from discord.ext.commands import has_permissions
import json
import random
import asyncio
import os
from flask import Flask
from threading import Thread

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

# Flask for uptime
app = Flask('')

@app.route('/')
def home():
    return "The Garden Bot is alive!"

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

def keep_alive():
    t = Thread(target=run_flask)
    t.start()

keep_alive()

# Load economy data
if os.path.exists('economy.json'):
    with open('economy.json', 'r') as f:
        economy = json.load(f)
else:
    economy = {}

# Save data
def save_economy():
    with open('economy.json', 'w') as f:
        json.dump(economy, f, indent=4)

# Rare plants
plants = {
    "Rose": 0.23,
    "Sunflower": 0.07,
    "Tulip": 0.15,
    "Daisy": 0.2,
    "Orchid": 0.05,
    "Lily": 0.1,
    "Carnation": 0.2
}

# Event multipliers
active_event = {"name": None, "multiplier": 1}

events = {
    "Thunderstorm": 100,
    "Rain": 2,
    "Sunshine": 1.5,
    "Drought": 0.5,
    "Disco": 5,
    "DJ Jhai": 10
}

# Tasks
@tasks.loop(minutes=10)
async def random_event():
    global active_event
    active_event["name"] = random.choice(list(events.keys()))
    active_event["multiplier"] = events[active_event["name"]]
    print(f"🌱 Event started: {active_event['name']} x{active_event['multiplier']}")
    await asyncio.sleep(120)  # lasts 2 min
    active_event = {"name": None, "multiplier": 1}

@bot.event
async def on_ready():
    print(f"{bot.user} is online!")
    random_event.start()

# Commands
@bot.slash_command(description="Check your balance")
async def balance(ctx):
    user_id = str(ctx.author.id)
    coins = economy.get(user_id, 0)
    await ctx.respond(f"💰 You have {coins} coins.")

@bot.slash_command(description="Claim daily coins")
async def daily(ctx):
    user_id = str(ctx.author.id)
    economy[user_id] = economy.get(user_id, 0) + 100
    save_economy()
    await ctx.respond("🌱 You claimed your daily 100 coins!")

@bot.slash_command(description="Plant a random flower")
async def plant(ctx):
    user_id = str(ctx.author.id)
    if economy.get(user_id, 0) < 50:
        await ctx.respond("❌ Not enough coins to plant! (50 coins)")
        return
    economy[user_id] -= 50
    rarity_roll = random.random()
    multiplier = active_event["multiplier"]
    found_plant = None
    for plant, chance in plants.items():
        if rarity_roll <= chance * multiplier:
            found_plant = plant
            break
    if not found_plant:
        found_plant = "Weeds 😅"
    save_economy()
    await ctx.respond(f"🌸 You planted and grew: **{found_plant}**!")

@bot.slash_command(description="Harvest for random coins")
async def harvest(ctx):
    user_id = str(ctx.author.id)
    reward = random.randint(50, 150) * active_event["multiplier"]
    economy[user_id] = economy.get(user_id, 0) + int(reward)
    save_economy()
    await ctx.respond(f"🌾 You harvested and earned **{int(reward)} coins**!")

@bot.slash_command(description="Give coins to a user (Mods only)")
@has_permissions(manage_guild=True)
async def addcoins(ctx, member: discord.Member, amount: int):
    user_id = str(member.id)
    economy[user_id] = economy.get(user_id, 0) + amount
    save_economy()
    await ctx.respond(f"✅ Gave {amount} coins to {member.mention}")

@bot.slash_command(description="Remove coins from a user (Mods only)")
@has_permissions(manage_guild=True)
async def removecoins(ctx, member: discord.Member, amount: int):
    user_id = str(member.id)
    economy[user_id] = max(0, economy.get(user_id, 0) - amount)
    save_economy()
    await ctx.respond(f"✅ Removed {amount} coins from {member.mention}")

@bot.slash_command(description="Spawn a special event (Admins only)")
@has_permissions(administrator=True)
async def spawnevent(ctx, event_name: str):
    global active_event
    if event_name in events:
        active_event["name"] = event_name
        active_event["multiplier"] = events[event_name]
        await ctx.respond(f"🎉 Event **{event_name}** started! x{events[event_name]}")
    else:
        await ctx.respond("❌ Event not found.")

# Run bot
bot.run(os.environ["TOKEN"])
