import discord
import os
import math
import json
from dotenv import load_dotenv

load_dotenv()

from discord.ext import commands
from discord import app_commands

db = {}

def load_db(filename="snipes_data.json"):
  global db
  try:
    with open(filename, "r") as f:
      db = json.load(f)
      print("Snipe data successfully loaded")
  except (FileNotFoundError, json.JSONDecodeError):
    print("No snipes data loaded")
    db = {} 

# undoes a snipe if it was invalid
def undo_snipe(sniper: discord.Member, target: discord.Member, points: int):
  sniper_key = db_get_user_key(sniper)
  target_key = db_get_user_key(target)
  db[sniper_key]['out'] -= 1
  db[target_key]['in'] -= 1
  db[sniper_key]['points'] -= points

  store_database()

# store entire replit db into json file
def store_database(filename="snipes_data.json"):
  temp_dict = {}
  for key in db.keys():
    temp_dict[key] = db[key]
    
  try:
    with open(filename, "w") as f:
      json.dump(temp_dict, f)
  except Exception as e:
    print(f"Error writing to file {filename}: {e}")

def add_entry_to_file(key, value, filename="snipes_data.json"):
  try:
      with open(filename, "r") as file:
          kv_db = json.load(file)  # Load existing data
  except (FileNotFoundError, json.JSONDecodeError):
      kv_db = {}  # Start fresh if file doesn't exist or is empty

  kv_db[key] = value  # Update the dictionary

  with open(filename, "w") as file:
      json.dump(kv_db, file, indent=4)  # Rewrite the file with the new entry

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
  val = db[user_key]
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
  HUNTING_SZN_MULT = 2
  value = get_raw_user_value(target)
  multiplier = 1
  if is_szn_target(target):
    multiplier = HUNTING_SZN_MULT

  value = math.ceil(value * multiplier)
  # update values
  add_points(sniper, value)
  increment_out(sniper)
  increment_in(target)

  store_database()
    
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
      print(key)
      # retrieve nickname from user id
      leaderboard.append((key, db[key]['points']))
  leaderboard.sort(key=lambda x: x[1], reverse=True)
  return leaderboard[:10]

# delete all db values (including szn)
def cleardb(filename="snipes_data.json"):
  global db
  db = {}
  
  try:
    with open(filename, "w") as f:
      json.dump(db, f)
  except Exception as e:
    print(f"Error writing to file {filename}: {e}")

bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())

# bot startup code
@bot.event
async def on_ready():
  print('Bot is running!')
  load_db()
  id = os.getenv('SERVER_ID')
  if id is None:
    print('Missing SERVER_ID environment variable.')
    exit(1)
  try:
    guild = discord.Object(id=id)
    synced = await bot.tree.sync(guild=guild)
    print(f'Synced {len(synced)} commands to guild')

  except Exception as e:
    print(f'Error syncing commands: {e}')


# Define a slash commands
id = os.getenv('SERVER_ID')
if id is None:
  print('Missing SERVER_ID environment variable.')
  exit(1)
GUILD_ID = discord.Object(id=id)


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

  # for matching id to guild username
  guild = interaction.guild
  if guild is None:
    print("Error: Guild not found.")
    exit()
  
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

    # get member from id
    member = guild.get_member(int(person))
    if member is None:
      print(f"Error: Member with ID {person} not found.")
      exit()
      
    em.add_field(name=f"**{num}. {member.display_name}**", value=f'\t{score} pts', inline=False)
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
  em.add_field(name="**/store-db**", value="Manually store current instance database into json file", inline=False)
  em.add_field(name="**/erase-snipe** *@sniper* *@target* *points", value="Removes points from sniper and resets internal in/out values", inline=False)
  
  await interaction.response.send_message(embed=em, ephemeral=True)

# set hunting szn
@bot.tree.command(name='set-szn',
                  description='Set the hunting szn role!',
                  guild=GUILD_ID)
@app_commands.default_permissions(administrator=True)
async def set_szn(interaction: discord.Interaction, szn: discord.Role):
  await interaction.response.send_message(
      f":bangbang: Hunting Szn target is now {szn.mention}! :bangbang: \nAll {szn.name} are worth **double** points! You better hide! :index_pointing_at_the_viewer:")
  set_hunting_szn(szn)

# reset user values
@bot.tree.command(name='reset-values', 
                  description='Reset values for user', 
                  guild=GUILD_ID)
@app_commands.default_permissions(administrator=True)
async def reset_user_values(interaction: discord.Interaction, user: discord.Member):
  if type(interaction.user) is discord.Member:
    reset_values(user)
    await interaction.response.send_message(f"Reset all values for {user.mention}")

# delete db values
@bot.tree.command(name='clear-db', description='Clears ALL database values. Really make sure you want to do this before you do it', guild=GUILD_ID)
@app_commands.default_permissions(administrator=True)
async def clear_db(interaction: discord.Interaction):
  cleardb()
  await interaction.response.send_message("Clearing database...")

# manually grant points to users
@bot.tree.command(name='give-points', description='manually add points to user', guild=GUILD_ID)
@app_commands.default_permissions(administrator=True)
async def give_points(interaction: discord.Interaction, user: discord.Member, points: int):
  if type(interaction.user) is discord.Member:
    add_points(user, points)
    await interaction.response.send_message(f"Gave {user.mention} {points} points. They now have {check_user_stats(user)[2]} points")

# store database into json
@bot.tree.command(name='store-db', description='store db into json file', guild=GUILD_ID)
@app_commands.default_permissions(administrator=True)
async def save_db(interaction: discord.Interaction):
  store_database()
  await interaction.response.send_message("Database saved!")

# erase snipe
@bot.tree.command(name='erase-snipe', description='erase a snipe if it was invalid', guild=GUILD_ID)
@app_commands.default_permissions(administrator=True)
async def erase_snipe(interaction: discord.Interaction, sniper: discord.Member, target: discord.Member, points: int):
  undo_snipe(sniper, target, points)
  await interaction.response.send_message(f"Erased {sniper.mention}'s snipe on {target.mention} for {points} points")

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

token = os.getenv("DISCORD_BOT_TOKEN")
if token is None:
  print('DISCORD_BOT_TOKEN environment variable not found')
  exit(1)

bot.run(token)
