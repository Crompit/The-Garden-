import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import random
import os
from flask import Flask
from threading import Thread

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True

TOKEN = os.getenv("TOKEN")
GUILD_ID = 1389063140989337630
CONFESS_CHANNEL_ID = 1392370500914774136
SHOP_CHANNEL_ID = 1392827882484535358
ADMIN_ROLE_ID = 1389121338123485224

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

user_data = {}
shop_items = []

# Flask keep-alive
app = Flask('')

@app.route('/')
def home():
    return "The Garden Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

keep_alive()

# Helper Functions
def is_admin(interaction):
    return any(role.id == ADMIN_ROLE_ID for role in interaction.user.roles)

def get_balance(user_id):
    return user_data.get(user_id, {}).get("coins", 0)

def add_coins(user_id, amount):
    user_data.setdefault(user_id, {"coins": 0, "plants": []})
    user_data[user_id]["coins"] += amount

def remove_coins(user_id, amount):
    user_data.setdefault(user_id, {"coins": 0, "plants": []})
    user_data[user_id]["coins"] = max(0, user_data[user_id]["coins"] - amount)

# Economy Commands
@tree.command(name="balance", description="Check your balance")
async def balance(interaction: discord.Interaction):
    coins = get_balance(interaction.user.id)
    await interaction.response.send_message(f"🌱 You have {coins} coins.", ephemeral=True)

@tree.command(name="daily", description="Claim your daily reward")
async def daily(interaction: discord.Interaction):
    add_coins(interaction.user.id, 100)
    await interaction.response.send_message("💰 You claimed 100 daily coins!", ephemeral=True)

@tree.command(name="beg", description="Beg for coins (5 min cooldown)")
async def beg(interaction: discord.Interaction):
    coins = random.randint(5, 25)
    add_coins(interaction.user.id, coins)
    await interaction.response.send_message(f"🙏 You received {coins} coins from begging.", ephemeral=True)

@tree.command(name="addcoins", description="Add coins to a user (Admin only)")
@app_commands.describe(user="User to add coins to", amount="Amount of coins")
async def addcoins(interaction: discord.Interaction, user: discord.Member, amount: int):
    if not is_admin(interaction):
        await interaction.response.send_message("❌ You don’t have permission.", ephemeral=True)
        return
    add_coins(user.id, amount)
    await interaction.response.send_message(f"✅ Added {amount} coins to {user.mention}.")

@tree.command(name="removecoins", description="Remove coins from a user (Admin only)")
@app_commands.describe(user="User to remove coins from", amount="Amount of coins")
async def removecoins(interaction: discord.Interaction, user: discord.Member, amount: int):
    if not is_admin(interaction):
        await interaction.response.send_message("❌ You don’t have permission.", ephemeral=True)
        return
    remove_coins(user.id, amount)
    await interaction.response.send_message(f"✅ Removed {amount} coins from {user.mention}.")

# Plant & Harvest
plants = {
    "Rose": 23,
    "Sunflower": 7,
    "Tulip": 15,
    "Lily": 10,
    "Orchid": 5
}

@tree.command(name="plant", description="Plant a random seed")
async def plant(interaction: discord.Interaction):
    chance = random.randint(1, 100)
    for plant, rarity in plants.items():
        if chance <= rarity:
            user_data.setdefault(interaction.user.id, {"coins": 0, "plants": []})
            user_data[interaction.user.id]["plants"].append(plant)
            await interaction.response.send_message(f"🌱 You planted a {plant}!")
            return
    await interaction.response.send_message("🌾 You planted, but nothing grew.")

@tree.command(name="harvest", description="Harvest your plants for coins")
async def harvest(interaction: discord.Interaction):
    plants_owned = user_data.get(interaction.user.id, {}).get("plants", [])
    if not plants_owned:
        await interaction.response.send_message("❌ You don’t have any plants to harvest.", ephemeral=True)
        return
    reward = len(plants_owned) * random.randint(50, 150)
    user_data[interaction.user.id]["plants"] = []
    add_coins(interaction.user.id, reward)
    await interaction.response.send_message(f"🌾 You harvested your plants and earned {reward} coins!")

# Confess
@tree.command(name="confess", description="Send an anonymous confession")
@app_commands.describe(message="Your confession")
async def confess(interaction: discord.Interaction, message: str):
    channel = bot.get_channel(CONFESS_CHANNEL_ID)
    if channel:
        await channel.send(f"💬 Anonymous Confession:\n{message}")
        await interaction.response.send_message("✅ Your confession was sent anonymously.", ephemeral=True)
    else:
        await interaction.response.send_message("❌ Confession channel not found.", ephemeral=True)

# Shop System
@tasks.loop(minutes=5)
async def restock_shop():
    global shop_items
    shop_items = random.sample(list(plants.keys()), k=3)
    stock_channel = bot.get_channel(SHOP_CHANNEL_ID)
    if stock_channel:
        items_list = "\n".join([f"🪴 {item}" for item in shop_items])
        await stock_channel.send(f"🛒 **Shop Restock!**\n{items_list}")

@tree.command(name="shop", description="View current shop items")
async def shop(interaction: discord.Interaction):
    if shop_items:
        items = "\n".join([f"🪴 {item}" for item in shop_items])
        await interaction.response.send_message(f"🛒 **Current Shop Stock:**\n{items}", ephemeral=True)
    else:
        await interaction.response.send_message("🛒 Shop is empty. Wait for restock.", ephemeral=True)

# Start Tasks
@bot.event
async def on_ready():
    await tree.sync(guild=discord.Object(id=GUILD_ID))
    restock_shop.start()
    print(f"✅ {bot.user} is online!")

bot.run(TOKEN)
