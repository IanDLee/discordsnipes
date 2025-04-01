import discord
import os
import math

from discord.ext import commands
from discord import app_commands
from replit import db
from replit.database import default_db

HUNTING_SZN_MULT = 2
ADMIN_ID = 1345151251037425694

# increment user out value
def increment_out(user: discord.Member):
  user_key = db_get_user_key(user)
  db[user_key]['out'] += 1

# increment user in value
def increment_in(user: discord.Member):
  user_key = db_get_user_key(user)
  db[user_key]['in'] += 1

# add points to user
def add_points(user: discord.Member, points: int):
  user_key = db_get_user_key(user)
  db[user_key]['points'] += points

# get raw (pre multiplier) value for a snipe
def raw_snipe_value(out_count, in_count):
  return 10 / (math.log10((in_count + 1) + (1 / (out_count + 1))))

# get raw (pre multiplier) value for a user
def get_raw_user_value(user: discord.Member):
  user_key = db_get_user_key(user)
  print(user_key)
  val = db[user_key]
  print(val)
  return raw_snipe_value(val['out'], val['in'])

# get the current hunting season
def get_szn():
  if 'szn' not in db.keys():
    db['szn'] = 0
  return db['szn']

def is_szn_target(target: discord.Member):
  szn = get_szn()
  role_ids = [role.id for role in target.roles]
  if szn in role_ids:
    return True
  else:
    return False

# log snipe (update snipe stats after snipe)
def log_snipe(sniper: discord.Member, target: discord.Member):
  value = get_raw_user_value(target)
  multiplier = 1
  if is_szn_target(target):
    multiplier = HUNTING_SZN_MULT

  value = math.ceil(value * multiplier)
  # update values
  add_points(sniper, value)
  increment_out(sniper)
  increment_in(target)

  return value
  
# check if user is in database and initialize user in database if not
# returns key being used as user key for db
def db_get_user_key(user: discord.Member):
  # determine key here
  user_key = str(user.id)
  
  if user_key not in db.keys():
    db[user_key] = {"out": 0, "in": 0, "points": 0}
  return user_key
    

# return database tuple for user
def check_user_stats(user: discord.Member):
  user_key = db_get_user_key(user)
  vals = db[user_key]
  return vals['in'], vals['out'],vals['points']

# set hunting szn target
def set_hunting_szn(szn: discord.Role):
  db['szn'] = szn.id

# reset database values for user
def reset_values(user_id: discord.Member):
  user_key = db_get_user_key(user_id)
  
  db[user_key]['out'] = 0
  db[user_key]['in'] = 0
  db[user_key]['points'] = 0

# return point leaders (greater than 0) sorted 
def get_leaderboard():
  leaderboard = []
  for key in db.keys():
    if key == 'szn':
      continue
    if db[key]['points'] > 0:
      # retrieve nickname from user id
      user = bot.get_user(key)
      if user is not None:
        leaderboard.append((user.display_name, db[key]['points']))
  leaderboard.sort(key=lambda x: x[1], reverse=True)
  return leaderboard[:10]

# delete all db values (including szn)
def cleardb():
  for key in db.keys():
    del db[key]

bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())


@bot.event
async def on_ready():
  print('Bot is running!')
  try:
    guild = discord.Object(id=1345135422094704731)
    synced = await bot.tree.sync(guild=guild)
    print(f'Synced {len(synced)} commands to guild {guild.id}')

  except Exception as e:
    print(f'Error syncing commands: {e}')


# Define a slash commands

GUILD_ID = discord.Object(id=1345135422094704731)


# registers snipe, updates user values
@bot.tree.command(name='snipe',
                  description='Log a snipe for points!',
                  guild=GUILD_ID)
async def snipe(interaction: discord.Interaction, user: discord.Member):
  if type(interaction.user) is discord.Member:
    points_earned = log_snipe(interaction.user, user)
    bonus = ""
    if is_szn_target(user):
      bonus = ":tada: You got a **hunting szn** target! **2x multiplier** applied! :tada:"
    await interaction.response.send_message(f":gun: Sniped {user.mention}! \n{bonus} **+{points_earned}** points\nYou now have **{check_user_stats(interaction.user)[2]}** points! ")


# returns user stats
@bot.tree.command(name='stats', description='Check your snipe stats!', guild=GUILD_ID)
async def check_score(interaction: discord.Interaction):
  if type(interaction.user) is discord.Member:
    stats = check_user_stats(interaction.user)
    await interaction.response.send_message(f":dart: Times targeted: **{stats[0]}**\n:gun: Snipes: **{stats[1]}**\n:moneybag: Points: **{stats[2]}**", ephemeral=True)
  else:
    await interaction.response.send_message("something broke")

# returns formatted leaderboard
@bot.tree.command(name='leaderboard', description='Check the leaderboard!', guild=GUILD_ID)
async def leaderboard(interaction: discord.Interaction):
  leader = get_leaderboard()
  em = discord.Embed(title="Leaderboard :star2:", description="These are the top snipers in the server! Do your best to get here")
  index = 1
  for person, score in leader:
    match index:
      case 1:
        num = ":first_place:"
      case 2:
        num = ":second_place:"
      case 3:
        num = ":third_place:"
      case _:
        num = index
      
    em.add_field(name=f"**{num}. {person}**", value=f'\t{score} pts', inline=False)
    index += 1

  await interaction.response.send_message(embed=em, ephemeral=True)
  
@bot.tree.command(name='snipes-help', 
                  description='Help menu for all sniping related commands!', 
                  guild=GUILD_ID)
async def help(interaction: discord.Interaction):
  em = discord.Embed(title="Help Menu", description="Here are all the commands for sniping and information")
  em.add_field(name="**:gun: /snipe** *@user*", value="Log a snipe for points! Point value of a target is determined by number of times they have been sniped as well as number of snipes that have achieved.", inline=False)
  em.add_field(name="**:chart_with_upwards_trend: /stats**", value="Check your snipe stats! Tells you your snipe count, your target count, and your total points.", inline=False)
  em.add_field(name="**:bar_chart: /leaderboard**", value="Check the leaderboard! This shows the top snipers in the server up to 10 who have any points", inline=False)
  em.add_field(name="**:question: /snipes-help**", value="Shows this menu lol", inline=False)
  await interaction.response.send_message(embed=em, ephemeral=True)

# admin commands
@bot.tree.command(name='admin-help', 
                  description='Help menu for admin commands!', 
                  guild=GUILD_ID)
@app_commands.default_permissions(administrator=True)
async def admin_help(interaction: discord.Interaction):
  em = discord.Embed(title="Admin Help Menu", description="Here are all the admin commands for sniping")
  
  em.add_field(name="**/set-hunting-szn** *@role*", value="Sets the hunting szn target role", inline=False)
  em.add_field(name="**/reset-values** *@user*", value="Resets all of a user's values to 0", inline=False)
  em.add_field(name="**/clear-db**", value="Clears all database values", inline=False)
  em.add_field(name="**/give-points** *@user* *points*", value="Gives a user points", inline=False)
  
  await interaction.response.send_message(embed=em, ephemeral=True)

# set hunting szn
@bot.tree.command(name='set-szn',
                  description='Set the hunting szn role!',
                  guild=GUILD_ID)
@app_commands.checks.has_permissions(administrator=True)
async def set_szn(interaction: discord.Interaction, szn: discord.Role):
  await interaction.response.send_message(
      f":bangbang: Hunting Szn target is now {szn.mention}! :bangbang: \nAll {szn.name} are worth **double** points! You better hide! :index_pointing_at_the_viewer:")
  set_hunting_szn(szn)

# reset user values
@bot.tree.command(name='reset-values', 
                  description='Reset values for user', 
                  guild=GUILD_ID)
@app_commands.checks.has_permissions(administrator=True)
async def reset_user_values(interaction: discord.Interaction, user: discord.Member):
  if type(interaction.user) is discord.Member:
    reset_values(user)
    await interaction.response.send_message(f"Reset all values for {user.mention}")

# delete db values
@bot.tree.command(name='clear-db', description='Clears ALL database values. Really make sure you want to do this before you do it', guild=GUILD_ID)
@app_commands.checks.has_permissions(administrator=True)
async def clear_db(interaction: discord.Interaction):
  cleardb()
  await interaction.response.send_message("Clearing database...")

# manually grand points to users
@bot.tree.command(name='give-points', description='manually add points to user', guild=GUILD_ID)
@app_commands.checks.has_permissions(administrator=True)
async def give_points(interaction: discord.Interaction, user: discord.Member, points: int):
  if type(interaction.user) is discord.Member:
    add_points(user, points)
    await interaction.response.send_message(f"Gave {user.mention} {points} points. They now have {check_user_stats(user)[2]} points")

# catch exceptions thrown during runtime
@bot.tree.error
async def on_tree_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("You need administrator permissions to use this command!", ephemeral=True)
    elif isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(f"This command is on cooldown. Try again in {error.retry_after:.2f} seconds.", ephemeral=True)
    elif isinstance(error, app_commands.MissingRole):
        await interaction.response.send_message("You're missing the required role to use this command!", ephemeral=True)
    else:
        await interaction.response.send_message(f"An error occurred: {str(error)}", ephemeral=True)
        print(f"Error: {str(error)}")

token = 0
try:
  token = os.getenv("DISCORD_BOT_TOKEN")
except Exception as e:
  print(f'DISCORD_BOT_TOKEN environment variable not found: {e}')
  exit(1)

bot.run(token)
