import discord
from discord.ext import commands, tasks
from discord import app_commands
import random
import asyncio
import json
import os

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

data_file = "economy.json"

# Load or initialize economy data
if os.path.exists(data_file):
    with open(data_file, "r") as f:
        economy = json.load(f)
else:
    economy = {}

def save_data():
    with open(data_file, "w") as f:
        json.dump(economy, f, indent=4)

def get_balance(user_id):
    return economy.get(str(user_id), {}).get("coins", 0)

def add_coins(user_id, amount):
    user_id = str(user_id)
    if user_id not in economy:
        economy[user_id] = {"coins": 0, "plants": 0}
    economy[user_id]["coins"] += amount
    save_data()

def remove_coins(user_id, amount):
    user_id = str(user_id)
    if user_id in economy:
        economy[user_id]["coins"] = max(economy[user_id]["coins"] - amount, 0)
        save_data()

def add_plant(user_id):
    user_id = str(user_id)
    if user_id not in economy:
        economy[user_id] = {"coins": 0, "plants": 0}
    economy[user_id]["plants"] += 1
    save_data()

# ===== Economy Commands =====

@bot.tree.command(name="balance")
async def balance(interaction: discord.Interaction):
    coins = get_balance(interaction.user.id)
    await interaction.response.send_message(f"🌱 {interaction.user.mention} has {coins} coins!")

@bot.tree.command(name="work")
async def work(interaction: discord.Interaction):
    earnings = random.randint(10, 50)
    add_coins(interaction.user.id, earnings)
    await interaction.response.send_message(f"💼 You worked hard and earned {earnings} coins!")

@bot.tree.command(name="beg")
async def beg(interaction: discord.Interaction):
    earnings = random.randint(1, 10)
    add_coins(interaction.user.id, earnings)
    await interaction.response.send_message(f"🙏 Someone gave you {earnings} coins!")

@bot.tree.command(name="daily")
async def daily(interaction: discord.Interaction):
    earnings = random.randint(50, 100)
    add_coins(interaction.user.id, earnings)
    await interaction.response.send_message(f"📅 You claimed your daily reward of {earnings} coins!")

@bot.tree.command(name="addcoins")
@app_commands.checks.has_role("Mods")
async def addcoins(interaction: discord.Interaction, member: discord.Member, amount: int):
    add_coins(member.id, amount)
    await interaction.response.send_message(f"✅ Added {amount} coins to {member.mention}")

@bot.tree.command(name="removecoins")
@app_commands.checks.has_role("Mods")
async def removecoins(interaction: discord.Interaction, member: discord.Member, amount: int):
    remove_coins(member.id, amount)
    await interaction.response.send_message(f"❌ Removed {amount} coins from {member.mention}")

# ===== Garden Features =====

@bot.tree.command(name="plant")
async def plant(interaction: discord.Interaction):
    cost = 20
    if get_balance(interaction.user.id) >= cost:
        remove_coins(interaction.user.id, cost)
        add_plant(interaction.user.id)
        await interaction.response.send_message(f"🌱 You planted a seed! (-{cost} coins)")
    else:
        await interaction.response.send_message("💸 Not enough coins to plant!")

@bot.tree.command(name="harvest")
async def harvest(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    if economy.get(user_id, {}).get("plants", 0) > 0:
        reward = random.randint(30, 70)
        add_coins(interaction.user.id, reward)
        economy[user_id]["plants"] -= 1
        save_data()
        await interaction.response.send_message(f"🌾 You harvested a plant and got {reward} coins!")
    else:
        await interaction.response.send_message("❌ You have no plants to harvest!")

@bot.tree.command(name="inventory")
async def inventory(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    plants = economy.get(user_id, {}).get("plants", 0)
    coins = get_balance(interaction.user.id)
    await interaction.response.send_message(f"🎒 You have {plants} plants and {coins} coins.")

# ===== Fun Games =====

@bot.tree.command(name="coinflip")
async def coinflip(interaction: discord.Interaction, bet: int, guess: str):
    guess = guess.lower()
    if guess not in ["heads", "tails"]:
        await interaction.response.send_message("❌ Guess must be 'heads' or 'tails'.")
        return
    if get_balance(interaction.user.id) < bet:
        await interaction.response.send_message("💸 Not enough coins!")
        return
    result = random.choice(["heads", "tails"])
    if result == guess:
        add_coins(interaction.user.id, bet)
        await interaction.response.send_message(f"🎉 It was {result}! You won {bet} coins!")
    else:
        remove_coins(interaction.user.id, bet)
        await interaction.response.send_message(f"😢 It was {result}! You lost {bet} coins.")

@bot.tree.command(name="slots")
async def slots(interaction: discord.Interaction, bet: int):
    if get_balance(interaction.user.id) < bet:
        await interaction.response.send_message("💸 Not enough coins!")
        return
    emojis = ["🍒", "🍋", "🔔", "⭐", "🍇"]
    result = [random.choice(emojis) for _ in range(3)]
    await interaction.response.send_message(f"🎰 {' '.join(result)}")
    if len(set(result)) == 1:
        winnings = bet * 5
        add_coins(interaction.user.id, winnings)
        await interaction.followup.send(f"🎉 JACKPOT! You won {winnings} coins!")
    else:
        remove_coins(interaction.user.id, bet)
        await interaction.followup.send(f"😢 You lost {bet} coins.")

# ===== Leaderboard =====

@bot.tree.command(name="top")
async def top(interaction: discord.Interaction):
    leaderboard = sorted(economy.items(), key=lambda x: x[1]["coins"], reverse=True)[:5]
    msg = "\n".join(
        [f"#{i+1} <@{uid}>: {data['coins']} coins" for i, (uid, data) in enumerate(leaderboard)]
    )
    await interaction.response.send_message(f"🏆 Top 5 Richest:\n{msg}")

# ===== On Ready =====

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Logged in as {bot.user}")

# ===== Run Bot =====

bot.run(os.environ["TOKEN"])
