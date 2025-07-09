import discord
from discord.ext import commands
import json
import random
import os
from datetime import datetime, timedelta

# ====== CONFIG ======
TOKEN = os.getenv("TOKEN") or "YOUR_BOT_TOKEN"
MOD_ROLE_ID = 1389121338123485224
DATA_FILE = "garden_data.json"

# ====== BOT SETUP ======
intents = discord.Intents.all()
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
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash commands globally!")
    except Exception as e:
        print(f"❌ Sync failed: {e}")
    print(f"🌱 {bot.user} is online.")

# ====== SLASH COMMANDS ======
@bot.tree.command(name="help", description="Show all The Garden Bot commands")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🌿 The Garden Bot Help",
        description="Commands you can use:",
        color=discord.Color.green()
    )
    embed.add_field(name="Economy", value="/balance, /daily, /work, /beg", inline=False)
    embed.add_field(name="Moderation (Mods)", value="/addcoins, /removecoins", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="balance", description="Check your coin balance")
async def balance(interaction: discord.Interaction):
    bal = get_balance(interaction.user.id)
    await interaction.response.send_message(f"💰 {interaction.user.mention}, you have **{bal} coins**.")

@bot.tree.command(name="daily", description="Claim your daily reward")
async def daily(interaction: discord.Interaction):
    can_claim, wait = can_use(interaction.user.id, "daily", 86400)
    if not can_claim:
        await interaction.response.send_message(f"⏳ Claim again in {wait // 60}m {wait % 60}s.", ephemeral=True)
        return
    reward = random.randint(50, 150)
    set_balance(interaction.user.id, get_balance(interaction.user.id) + reward)
    await interaction.response.send_message(f"🎁 {interaction.user.mention}, you got **{reward} coins**!")

@bot.tree.command(name="work", description="Work and earn coins (1h cooldown)")
async def work(interaction: discord.Interaction):
    can_work, wait = can_use(interaction.user.id, "work", 3600)
    if not can_work:
        await interaction.response.send_message(f"⏳ Work again in {wait // 60}m {wait % 60}s.", ephemeral=True)
        return
    jobs = ["Gardener", "Botanist", "Farmer"]
    job = random.choice(jobs)
    pay = random.randint(20, 100)
    set_balance(interaction.user.id, get_balance(interaction.user.id) + pay)
    await interaction.response.send_message(f"👨‍🌾 {interaction.user.mention}, you worked as a {job} and earned **{pay} coins**!")

@bot.tree.command(name="beg", description="Beg for some coins (5m cooldown)")
async def beg(interaction: discord.Interaction):
    can_beg, wait = can_use(interaction.user.id, "beg", 300)
    if not can_beg:
        await interaction.response.send_message(f"⏳ Beg again in {wait}s.", ephemeral=True)
        return
    reward = random.randint(5, 30)
    set_balance(interaction.user.id, get_balance(interaction.user.id) + reward)
    await interaction.response.send_message(f"🙏 {interaction.user.mention}, you got **{reward} coins**!")

@bot.tree.command(name="addcoins", description="(Mods) Add coins to a user")
async def addcoins(interaction: discord.Interaction, user: discord.User, amount: int):
    if MOD_ROLE_ID not in [role.id for role in interaction.user.roles]:
        await interaction.response.send_message("❌ You don’t have permission.", ephemeral=True)
        return
    set_balance(user.id, get_balance(user.id) + amount)
    await interaction.response.send_message(f"✅ Added {amount} coins to {user.mention}.")

@bot.tree.command(name="removecoins", description="(Mods) Remove coins from a user")
async def removecoins(interaction: discord.Interaction, user: discord.User, amount: int):
    if MOD_ROLE_ID not in [role.id for role in interaction.user.roles]:
        await interaction.response.send_message("❌ You don’t have permission.", ephemeral=True)
        return
    current = get_balance(user.id)
    set_balance(user.id, max(0, current - amount))
    await interaction.response.send_message(f"✅ Removed {amount} coins from {user.mention}.")

# ====== START BOT ======
bot.run(TOKEN)
