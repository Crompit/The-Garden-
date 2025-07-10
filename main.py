import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import random
import os
from flask import Flask
from threading import Thread

TOKEN = os.environ['TOKEN']
GUILD_ID = 1389063140989337630
ADMIN_ROLE_ID = 1389121338123485224
CONFESS_CHANNEL_ID = 1392370500914774136
SHOP_CHANNEL_ID = 1392827882484535358

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())
tree = bot.tree

user_balances = {}
shop_items = [
    {"name": "Golden Seed", "price": 1000, "rarity": "Legendary"},
    {"name": "Watering Can", "price": 200, "rarity": "Common"},
    {"name": "Fertilizer", "price": 500, "rarity": "Rare"}
]

# ---------------------- Flask anti-sleep ----------------------
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# ---------------------- Helper Functions ----------------------
def add_coins(user_id, amount):
    user_balances[user_id] = user_balances.get(user_id, 0) + amount

def remove_coins(user_id, amount):
    user_balances[user_id] = max(user_balances.get(user_id, 0) - amount, 0)

def is_admin(interaction):
    return any(role.id == ADMIN_ROLE_ID for role in interaction.user.roles)

# ---------------------- Economy Commands ----------------------
@tree.command(name="balance", description="Check your balance")
async def balance(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    coins = user_balances.get(interaction.user.id, 0)
    await interaction.followup.send(f"💰 You have {coins} coins.")

@tree.command(name="daily", description="Claim your daily coins")
async def daily(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    add_coins(interaction.user.id, 100)
    await interaction.followup.send("✅ You claimed 100 daily coins!")

@tree.command(name="addcoins", description="Add coins to a user (Admin only)")
@app_commands.describe(user="User to add coins to", amount="Amount of coins")
async def addcoins(interaction: discord.Interaction, user: discord.Member, amount: int):
    await interaction.response.defer(thinking=True)
    if not is_admin(interaction):
        await interaction.followup.send("❌ You don’t have permission.", ephemeral=True)
        return
    add_coins(user.id, amount)
    await interaction.followup.send(f"✅ Added {amount} coins to {user.mention}.")

@tree.command(name="removecoins", description="Remove coins from a user (Admin only)")
@app_commands.describe(user="User to remove coins from", amount="Amount of coins")
async def removecoins(interaction: discord.Interaction, user: discord.Member, amount: int):
    await interaction.response.defer(thinking=True)
    if not is_admin(interaction):
        await interaction.followup.send("❌ You don’t have permission.", ephemeral=True)
        return
    remove_coins(user.id, amount)
    await interaction.followup.send(f"✅ Removed {amount} coins from {user.mention}.")

# ---------------------- Shop Commands ----------------------
@tree.command(name="shop", description="View the shop")
async def shop(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    shop_text = "\n".join([f"**{item['name']}** - {item['price']} coins ({item['rarity']})" for item in shop_items])
    await interaction.followup.send(f"🛒 **Shop Items:**\n{shop_text}")

# ---------------------- Confession Command ----------------------
@tree.command(name="confess", description="Send an anonymous confession")
@app_commands.describe(message="Your confession")
async def confess(interaction: discord.Interaction, message: str):
    await interaction.response.defer(thinking=True, ephemeral=True)
    channel = bot.get_channel(CONFESS_CHANNEL_ID)
    if channel:
        await channel.send(f"💬 Anonymous Confession:\n{message}")
        await interaction.followup.send("✅ Your confession was sent anonymously.", ephemeral=True)
    else:
        await interaction.followup.send("❌ Confession channel not found.", ephemeral=True)

# ---------------------- Shop Auto-Updater ----------------------
@tasks.loop(minutes=5)
async def update_shop():
    channel = bot.get_channel(SHOP_CHANNEL_ID)
    if channel:
        stock_text = "\n".join([f"**{item['name']}** - {item['price']} coins ({item['rarity']})" for item in shop_items])
        await channel.send(f"🛒 **New Stock Available!**\n{stock_text}")

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    try:
        synced = await tree.sync(guild=discord.Object(id=GUILD_ID))
        print(f"🌐 Synced {len(synced)} commands.")
    except Exception as e:
        print(f"❌ Sync failed: {e}")
    update_shop.start()

# ---------------------- Start Everything ----------------------
keep_alive()
bot.run(TOKEN)
