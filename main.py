import discord
from discord.ext import commands
from discord import app_commands
import json
import random
import os
from datetime import datetime, timedelta

# ====== CONFIG ======
TOKEN = os.getenv("TOKEN")
CONFESS_CHANNEL_ID = 1392370500914774136
MOD_ROLE_ID = 1389121338123485224
TEST_SERVER_ID = 1389063140989337630  # Your server for instant testing
DATA_FILE = "/data/garden_data.json"

# ====== BOT SETUP ======
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ====== LOAD/SAVE DATA ======
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"balances": {}, "gardens": {}, "cooldowns": {}}

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
    try:
        # Force sync globally (takes 1 hour first time)
        synced = await tree.sync()
        print(f"✅ Globally synced {len(synced)} commands!")
        
        # ALSO sync instantly to your testing server
        await tree.sync(guild=discord.Object(id=TEST_SERVER_ID))
        print(f"⚡ Instant sync to server {TEST_SERVER_ID}!")
    except Exception as e:
        print(f"❌ Sync error: {e}")

# ====== ECONOMY COMMANDS ======
@tree.command(name="balance", description="Check your coin balance")
async def balance(interaction: discord.Interaction):
    bal = get_balance(interaction.user.id)
    await interaction.response.send_message(f"💰 {interaction.user.mention}, you have **{bal} coins**.")

@tree.command(name="daily", description="Claim your daily coins")
async def daily(interaction: discord.Interaction):
    can_claim, wait = can_use(interaction.user.id, "daily", 86400)
    if not can_claim:
        await interaction.response.send_message(f"⏳ You can claim again in {wait // 60}m {wait % 60}s.")
        return
    reward = random.randint(50, 150)
    set_balance(interaction.user.id, get_balance(interaction.user.id) + reward)
    await interaction.response.send_message(f"🎁 {interaction.user.mention}, you claimed **{reward} coins**!")

@tree.command(name="work", description="Do some work and earn coins")
async def work(interaction: discord.Interaction):
    can_work, wait = can_use(interaction.user.id, "work", 3600)
    if not can_work:
        await interaction.response.send_message(f"⏳ You can work again in {wait // 60}m {wait % 60}s.")
        return
    jobs = ["Gardener", "Farmer", "Botanist", "Market Seller"]
    job = random.choice(jobs)
    pay = random.randint(30, 100)
    set_balance(interaction.user.id, get_balance(interaction.user.id) + pay)
    await interaction.response.send_message(f"👨‍🌾 {interaction.user.mention}, you worked as a **{job}** and earned **{pay} coins**!")

@tree.command(name="beg", description="Beg for coins")
async def beg(interaction: discord.Interaction):
    can_beg, wait = can_use(interaction.user.id, "beg", 300)
    if not can_beg:
        await interaction.response.send_message(f"⏳ You can beg again in {wait}s.")
        return
    reward = random.randint(5, 30)
    set_balance(interaction.user.id, get_balance(interaction.user.id) + reward)
    await interaction.response.send_message(f"🙏 {interaction.user.mention}, someone gave you **{reward} coins**!")

@tree.command(name="addcoins", description="(Mods Only) Add coins to a user")
async def addcoins(interaction: discord.Interaction, member: discord.Member, amount: int):
    if MOD_ROLE_ID not in [role.id for role in interaction.user.roles]:
        await interaction.response.send_message("❌ You don’t have permission.")
        return
    set_balance(member.id, get_balance(member.id) + amount)
    await interaction.response.send_message(f"✅ Added **{amount} coins** to {member.mention}!")

@tree.command(name="removecoins", description="(Mods Only) Remove coins from a user")
async def removecoins(interaction: discord.Interaction, member: discord.Member, amount: int):
    if MOD_ROLE_ID not in [role.id for role in interaction.user.roles]:
        await interaction.response.send_message("❌ You don’t have permission.")
        return
    current = get_balance(member.id)
    set_balance(member.id, max(0, current - amount))
    await interaction.response.send_message(f"✅ Removed **{amount} coins** from {member.mention}.")

# ====== START BOT ======
bot.run(TOKEN)
