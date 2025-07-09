import discord
from discord.ext import commands
import json
import random
import os
from datetime import datetime, timedelta

# ====== CONFIG ======
TOKEN = os.getenv("TOKEN") or "YOUR-TOKEN-HERE"  # Replace with token if no env
CONFESS_CHANNEL_ID = 1392370500914774136
MOD_ROLE_ID = 1389121338123485224
DATA_FILE = "/data/garden_data.json"

# ====== BOT SETUP ======
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ====== LOAD/SAVE DATA ======
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"balances": {}, "cooldowns": {}}

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

data = load_data()

def get_balance(user_id):
    return data["balances"].get(str(user_id), 0)

def set_balance(user_id, amount):
    data["balances"][str(user_id)] = amount
    save_data()

def can_use(user_id, command, cooldown):
    now = datetime.utcnow()
    user_cooldowns = data["cooldowns"].get(str(user_id), {})
    last_used = user_cooldowns.get(command)
    if last_used and (now - datetime.fromisoformat(last_used)) < timedelta(seconds=cooldown):
        return False, cooldown - (now - datetime.fromisoformat(last_used)).seconds
    user_cooldowns[command] = now.isoformat()
    data["cooldowns"][str(user_id)] = user_cooldowns
    save_data()
    return True, 0

# ====== EVENTS ======
@bot.event
async def on_ready():
    print(f"✅ {bot.user} is online!")

# ====== ECONOMY COMMANDS ======
@bot.command()
async def balance(ctx):
    bal = get_balance(ctx.author.id)
    await ctx.send(f"💰 {ctx.author.mention}, you have **{bal} coins**.")

@bot.command()
async def daily(ctx):
    can_claim, wait = can_use(ctx.author.id, "daily", 86400)
    if not can_claim:
        await ctx.send(f"⏳ You can claim again in {wait // 60}m {wait % 60}s.")
        return
    reward = random.randint(50, 150)
    set_balance(ctx.author.id, get_balance(ctx.author.id) + reward)
    await ctx.send(f"🎁 {ctx.author.mention}, you claimed **{reward} coins**!")

@bot.command()
async def work(ctx):
    can_work, wait = can_use(ctx.author.id, "work", 3600)
    if not can_work:
        await ctx.send(f"⏳ You can work again in {wait // 60}m {wait % 60}s.")
        return
    jobs = ["Gardener", "Farmer", "Botanist", "Market Seller"]
    job = random.choice(jobs)
    pay = random.randint(30, 100)
    set_balance(ctx.author.id, get_balance(ctx.author.id) + pay)
    await ctx.send(f"👨‍🌾 {ctx.author.mention}, you worked as a **{job}** and earned **{pay} coins**!")

@bot.command()
async def beg(ctx):
    can_beg, wait = can_use(ctx.author.id, "beg", 300)
    if not can_beg:
        await ctx.send(f"⏳ You can beg again in {wait}s.")
        return
    reward = random.randint(5, 30)
    set_balance(ctx.author.id, get_balance(ctx.author.id) + reward)
    await ctx.send(f"🙏 {ctx.author.mention}, someone gave you **{reward} coins**!")

@bot.command()
async def addcoins(ctx, member: discord.Member, amount: int):
    if MOD_ROLE_ID not in [role.id for role in ctx.author.roles]:
        await ctx.send("❌ You don’t have permission.")
        return
    set_balance(member.id, get_balance(member.id) + amount)
    await ctx.send(f"✅ Added **{amount} coins** to {member.mention}.")

@bot.command()
async def removecoins(ctx, member: discord.Member, amount: int):
    if MOD_ROLE_ID not in [role.id for role in ctx.author.roles]:
        await ctx.send("❌ You don’t have permission.")
        return
    current = get_balance(member.id)
    set_balance(member.id, max(0, current - amount))
    await ctx.send(f"✅ Removed **{amount} coins** from {member.mention}.")

# ====== START BOT ======
bot.run(TOKEN)
