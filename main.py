import discord
from discord import app_commands
from discord.ext import commands
import json
import os

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# File paths
TITLES_FILE = "titles.json"
RATINGS_FILE = "ratings.json"

# Load or initialize data files
def load_json(path):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {}

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=4)

titles = load_json(TITLES_FILE)  # dict with {title_name: True}
ratings = load_json(RATINGS_FILE)  # dict {title: {user_id: score}}

def get_media_list():
    return list(titles.keys())

# Autocomplete function for titles
async def title_autocomplete(interaction: discord.Interaction, current: str):
    return [
        app_commands.Choice(name=title, value=title)
        for title in get_media_list() if current.lower() in title.lower()
    ][:25]

# Check admin permissions helper
def is_admin(interaction: discord.Interaction):
    return interaction.user.guild_permissions.administrator

# Sync commands on ready
@bot.event
async def on_ready():
    await tree.sync()
    print(f"Logged in as {bot.user}!")

# Slash commands

@tree.command(name="addtitle", description="Add a new media title to rate")
@app_commands.describe(name="Name of the media title")
async def addtitle(interaction: discord.Interaction, name: str):
    if not is_admin(interaction):
        await interaction.response.send_message(
            "❌ You must be an admin to add titles.", ephemeral=True)
        return

    if name in titles:
        await interaction.response.send_message(
            f"⚠️ Title **{name}** already exists.", ephemeral=True)
        return

    titles[name] = True
    save_json(TITLES_FILE, titles)
    await interaction.response.send_message(f"✅ Added title **{name}**!")

@tree.command(name="deletetitle",
              description="Delete a media title and its ratings")
@app_commands.describe(name="Name of the media title to delete")
@app_commands.autocomplete(name=title_autocomplete)
async def deletetitle(interaction: discord.Interaction, name: str):
    if not is_admin(interaction):
        await interaction.response.send_message(
            "❌ You must be an admin to delete titles.", ephemeral=True)
        return

    if name not in titles:
        await interaction.response.send_message(
            f"❌ Title **{name}** not found.", ephemeral=True)
        return

    titles.pop(name)
    ratings.pop(name, None)
    save_json(TITLES_FILE, titles)
    save_json(RATINGS_FILE, ratings)
    await interaction.response.send_message(
        f"✅ Deleted title **{name}** and its ratings.")

@tree.command(name="listtitles", description="List all available media titles")
async def listtitles(interaction: discord.Interaction):
    if not titles:
        await interaction.response.send_message("No titles available yet.",
                                                ephemeral=True)
        return

    embed = discord.Embed(title="Available Titles", color=discord.Color.blue())
    embed.description = "\n".join(titles.keys())
    await interaction.response.send_message(embed=embed)

@tree.command(name="rate", description="Rate a media title")
@app_commands.describe(title="Title to rate", score="Score from 0 to 10")
@app_commands.autocomplete(title=title_autocomplete)
async def rate(interaction: discord.Interaction, title: str, score: float):
    if title not in titles:
        await interaction.response.send_message(
            f"❌ Title **{title}** not found.", ephemeral=True)
        return
    if score < 0 or score > 10:
        await interaction.response.send_message(
            "❌ Score must be between 0 and 10.", ephemeral=True)
        return

    user_id = str(interaction.user.id)
    if title not in ratings:
        ratings[title] = {}

    ratings[title][user_id] = score
    save_json(RATINGS_FILE, ratings)

    await interaction.response.send_message(
        f"✅ You rated **{title}** with {score}/10!")

@tree.command(name="ratings", description="See ratings for a title")
@app_commands.describe(title="Title to view ratings")
@app_commands.autocomplete(title=title_autocomplete)
async def ratings_cmd(interaction: discord.Interaction, title: str):
    if title not in titles:
        await interaction.response.send_message(
            f"❌ Title **{title}** not found.", ephemeral=True)
        return

    title_ratings = ratings.get(title, {})
    if not title_ratings:
        await interaction.response.send_message(
            f"No ratings yet for **{title}**.", ephemeral=True)
        return

    avg = sum(title_ratings.values()) / len(title_ratings)
    embed = discord.Embed(title=f"Ratings for {title}",
                          color=discord.Color.gold())
    embed.add_field(name="Average Score", value=f"{avg:.2f}/10", inline=False)

    # Show up to 10 user ratings
    lines = []
    for user_id, score in list(title_ratings.items())[:10]:
        user = await bot.fetch_user(int(user_id))
        lines.append(f"**{user.name}**: {score}/10")
    embed.add_field(name="User Ratings", value="\n".join(lines), inline=False)

    await interaction.response.send_message(embed=embed)

@tree.command(name="myratings", description="See all the media you have rated")
async def myratings(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    user_ratings = []

    for title, user_scores in ratings.items():
        if user_id in user_scores:
            user_ratings.append(f"**{title}**: {user_scores[user_id]}/10")

    if not user_ratings:
        await interaction.response.send_message(
            "You haven't rated any titles yet.", ephemeral=True)
        return

    embed = discord.Embed(title=f"{interaction.user.name}'s Ratings",
                          color=discord.Color.green())
    embed.description = "\n".join(user_ratings)
    await interaction.response.send_message(embed=embed)

@tree.command(name="toptitles",
              description="Show top 10 highest rated media titles")
async def toptitles(interaction: discord.Interaction):
    if not ratings:
        await interaction.response.send_message("No ratings available yet.",
                                                ephemeral=True)
        return

    avg_scores = []
    for title, user_scores in ratings.items():
        if user_scores:
            avg = sum(user_scores.values()) / len(user_scores)
            avg_scores.append((title, avg))

    avg_scores.sort(key=lambda x: x[1], reverse=True)
    top_10 = avg_scores[:10]

    embed = discord.Embed(title="Top 10 Rated Titles",
                          color=discord.Color.purple())
    for title, avg in top_10:
        embed.add_field(name=title, value=f"{avg:.2f}/10", inline=False)

    await interaction.response.send_message(embed=embed)

# Run the bot
TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)
