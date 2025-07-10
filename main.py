import discord
from discord.ext import commands, tasks
import random
import asyncio
import datetime

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="/", intents=intents)

# Economy data
user_balances = {}
user_plants = {}
current_event = {"name": None, "multiplier": 1, "end_time": None}
luck_boost = {"active": False, "multiplier": 1, "end_time": None}

# Events data
events = [
    {"name": "Thunderstorm", "multiplier": 100},
    {"name": "Wet", "multiplier": 2},
    {"name": "Heatwave", "multiplier": 0.5},
    {"name": "Rainbow", "multiplier": 10},
    {"name": "Butterfly Swarm", "multiplier": 3},
    {"name": "Bee Attack", "multiplier": 0.8},
    {"name": "Snowstorm", "multiplier": 1.2},
    {"name": "Wildfire", "multiplier": 0.3},
    {"name": "Bloom", "multiplier": 5},
    {"name": "Mushroom Growth", "multiplier": 4}
]

admin_only_events = [
    {"name": "DJ Jhai", "multiplier": 1000},
    {"name": "Disco", "multiplier": 500}
]

plant_rarity = [
    {"name": "Sunflower", "chance": 7, "coins": 200},
    {"name": "Rose", "chance": 23, "coins": 150},
    {"name": "Tulip", "chance": 30, "coins": 100},
    {"name": "Daisy", "chance": 40, "coins": 50}
]

# Auto event spawner
@tasks.loop(minutes=10)
async def spawn_event():
    event = random.choice(events)
    current_event.update({
        "name": event["name"],
        "multiplier": event["multiplier"],
        "end_time": datetime.datetime.utcnow() + datetime.timedelta(minutes=2)
    })
    print(f"🌱 Event started: {event['name']} x{event['multiplier']} for 2 minutes")
    await asyncio.sleep(120)
    current_event.update({"name": None, "multiplier": 1, "end_time": None})
    print("🌱 Event ended")

@bot.event
async def on_ready():
    print(f"{bot.user} is online!")
    spawn_event.start()

# Economy commands
@bot.slash_command(name="balance")
async def balance(ctx):
    coins = user_balances.get(ctx.author.id, 0)
    await ctx.respond(f"💰 You have {coins} coins.")

@bot.slash_command(name="plant")
async def plant(ctx):
    multiplier = current_event["multiplier"] * (luck_boost["multiplier"] if luck_boost["active"] else 1)
    rng = random.randint(1, 100)
    plant_got = None
    for plant in plant_rarity:
        if rng <= plant["chance"]:
            plant_got = plant
            break
    if not plant_got:
        plant_got = {"name": "Weed", "coins": 10}  # fallback

    reward = int(plant_got["coins"] * multiplier)
    user_balances[ctx.author.id] = user_balances.get(ctx.author.id, 0) + reward
    await ctx.respond(f"🌱 You planted and grew a **{plant_got['name']}** worth {reward} coins! (Event: {current_event['name'] or 'None'})")

@bot.slash_command(name="harvest")
async def harvest(ctx):
    multiplier = current_event["multiplier"] * (luck_boost["multiplier"] if luck_boost["active"] else 1)
    reward = int(random.randint(50, 200) * multiplier)
    user_balances[ctx.author.id] = user_balances.get(ctx.author.id, 0) + reward
    await ctx.respond(f"🌾 You harvested crops and earned {reward} coins! (Event: {current_event['name'] or 'None'})")

@bot.slash_command(name="luck")
@commands.has_permissions(administrator=True)
async def luck(ctx, minutes: int = 5):
    luck_boost.update({
        "active": True,
        "multiplier": 2,
        "end_time": datetime.datetime.utcnow() + datetime.timedelta(minutes=minutes)
    })
    await ctx.respond(f"🍀 Luck boost activated! All rewards x2 for {minutes} minutes.")
    await asyncio.sleep(minutes * 60)
    luck_boost.update({"active": False, "multiplier": 1, "end_time": None})
    await ctx.send("🍀 Luck boost has ended.")

@bot.slash_command(name="spawnevent")
@commands.has_permissions(administrator=True)
async def spawnevent(ctx, event_name: str):
    match = next((e for e in admin_only_events if e["name"].lower() == event_name.lower()), None)
    if match:
        current_event.update({
            "name": match["name"],
            "multiplier": match["multiplier"],
            "end_time": datetime.datetime.utcnow() + datetime.timedelta(minutes=2)
        })
        await ctx.respond(f"🎉 Admin spawned event: {match['name']} x{match['multiplier']} for 2 minutes!")
    else:
        await ctx.respond("❌ Event not found or not admin-only.")

@bot.slash_command(name="currentevent")
async def currentevent(ctx):
    if current_event["name"]:
        time_left = (current_event["end_time"] - datetime.datetime.utcnow()).seconds
        await ctx.respond(f"🌟 Current Event: {current_event['name']} x{current_event['multiplier']} (ends in {time_left}s)")
    else:
        await ctx.respond("🌿 No event active.")

bot.run("YOUR_BOT_TOKEN")
