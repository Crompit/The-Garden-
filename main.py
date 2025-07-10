import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import random
import os
from flask import Flask
from threading import Thread

# Flask keep-alive server
app = Flask('')

@app.route('/')
def home():
    return "🌱 The Garden Bot is alive!"

def run():
    app.run(host="0.0.0.0", port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# Bot setup
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# Economy & Garden Data
user_balances = {}
user_gardens = {}

def get_balance(user_id):
    return user_balances.get(user_id, 0)

def update_balance(user_id, amount):
    user_balances[user_id] = get_balance(user_id) + amount

def get_garden(user_id):
    return user_gardens.get(user_id, {"plants": 0, "watered": False})

def update_garden(user_id, plants=None, watered=None):
    garden = get_garden(user_id)
    if plants is not None:
        garden["plants"] = plants
    if watered is not None:
        garden["watered"] = watered
    user_gardens[user_id] = garden

# Events
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    try:
        synced = await tree.sync()
        print(f"🌐 Synced {len(synced)} slash commands")
    except Exception as e:
        print(f"Error syncing commands: {e}")

# Slash Commands
@tree.command(name="balance", description="Check your coin balance 🌱")
async def balance(interaction: discord.Interaction):
    coins = get_balance(interaction.user.id)
    await interaction.response.send_message(f"💰 {interaction.user.mention}, you have **{coins} coins**.")

@tree.command(name="daily", description="Claim your daily coins 🌞")
async def daily(interaction: discord.Interaction):
    update_balance(interaction.user.id, 100)
    await interaction.response.send_message(f"✅ {interaction.user.mention}, you claimed **100 daily coins**!")

@tree.command(name="beg", description="Beg for coins 💸")
async def beg(interaction: discord.Interaction):
    update_balance(interaction.user.id, 10)
    await interaction.response.send_message(f"🪙 {interaction.user.mention}, someone gave you **10 coins**!")

@tree.command(name="addcoins", description="Mods only: Add coins to a user")
@app_commands.describe(user="User to add coins to", amount="Amount of coins")
async def addcoins(interaction: discord.Interaction, user: discord.Member, amount: int):
    if 1389121338123485224 in [role.id for role in interaction.user.roles]:
        update_balance(user.id, amount)
        await interaction.response.send_message(f"✅ Added **{amount} coins** to {user.mention}")
    else:
        await interaction.response.send_message("❌ You don't have permission.", ephemeral=True)

@tree.command(name="removecoins", description="Mods only: Remove coins from a user")
@app_commands.describe(user="User to remove coins from", amount="Amount of coins")
async def removecoins(interaction: discord.Interaction, user: discord.Member, amount: int):
    if 1389121338123485224 in [role.id for role in interaction.user.roles]:
        update_balance(user.id, -amount)
        await interaction.response.send_message(f"✅ Removed **{amount} coins** from {user.mention}")
    else:
        await interaction.response.send_message("❌ You don't have permission.", ephemeral=True)

# Garden Commands
@tree.command(name="plant", description="Plant a seed 🌱 (costs 50 coins)")
async def plant(interaction: discord.Interaction):
    if get_balance(interaction.user.id) < 50:
        await interaction.response.send_message("❌ Not enough coins! (50 required)")
        return
    update_balance(interaction.user.id, -50)
    garden = get_garden(interaction.user.id)
    update_garden(interaction.user.id, plants=garden["plants"] + 1, watered=False)
    await interaction.response.send_message(f"🌱 You planted a seed! You now have **{garden['plants'] + 1} plants**.")

@tree.command(name="water", description="Water your garden 💦")
async def water(interaction: discord.Interaction):
    garden = get_garden(interaction.user.id)
    if garden["plants"] == 0:
        await interaction.response.send_message("❌ You have no plants to water!")
        return
    if garden["watered"]:
        await interaction.response.send_message("💧 Your plants are already watered.")
        return
    update_garden(interaction.user.id, watered=True)
    await interaction.response.send_message("💦 You watered your garden! Next harvest will give a bonus.")

@tree.command(name="harvest", description="Harvest your plants 🍃 for coins")
async def harvest(interaction: discord.Interaction):
    garden = get_garden(interaction.user.id)
    if garden["plants"] == 0:
        await interaction.response.send_message("❌ You have no plants to harvest.")
        return
    base_reward = garden["plants"] * random.randint(20, 50)
    bonus = base_reward * 0.5 if garden["watered"] else 0
    total_reward = int(base_reward + bonus)
    update_balance(interaction.user.id, total_reward)
    update_garden(interaction.user.id, plants=0, watered=False)
    await interaction.response.send_message(
        f"🍃 You harvested your garden for **{total_reward} coins**! 🌱 (Bonus applied: {bonus > 0})"
    )

# Start Flask and bot
keep_alive()
bot.run(os.environ['TOKEN'])
