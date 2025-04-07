import discord
import os
import math
import json
from dotenv import load_dotenv

load_dotenv()

from discord.ext import commands
from discord import app_commands

db = {}

def retrieve_json(filename="snipes_data.json"):
  try:
    with open(filename, "rb") as f:
      return f
  except Exception as e:
    print(f"Error opening file {filename}: {e}")

# load saved db from json file into working db
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
  db[sniper_key]['pts'] -= points

  store_database()

# store entire working db into json file
def store_database(filename="snipes_data.json"):
  temp_dict = {}
  for key in db.keys():
    temp_dict[key] = db[key]
    
  try:
    with open(filename, "w") as f:
      json.dump(temp_dict, f)
  except Exception as e:
    print(f"Error writing to file {filename}: {e}")

# adds a single entry to the json file
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
  db[user_key]['pts'] += points

# get raw (pre multiplier) value for a snipe
def raw_snipe_value(out_count, in_count):
  #return 10 / (math.log10((0.5*in_count + 1.3) + (1 / (out_count + 1))))
  return (math.log(out_count + 2) / math.log(in_count + 2))*20
  #return 10 / math.log10((0.5 * in_count + 1.3) + (1 / math.sqrt(out_count + 1)))

# get raw (pre multiplier) value for a user
def get_raw_user_value(user: discord.Member):
  
  FLOOR_VALUE = 10
  
  user_key = db_get_user_key(user)
  db_row = db[user_key]
  raw_val = raw_snipe_value(db_row['out'], db_row['in'])
  return max(raw_val, FLOOR_VALUE)

# get hunting szn (role id, multiplier) in tuple 
def get_szn():
  if 'szn' not in db.keys():
    db['szn'] = {"role_id":-1, "mlt": 1}
  return (db['szn']["role_id"], db['szn']['mlt'])

# determines if member has szn target role
def is_szn_target(target: discord.Member):
  szn = (get_szn())[0]
  role_ids = [role.id for role in target.roles]
  if szn in role_ids:
    return True
  else:
    return False

# log snipe (update snipe stats after snipe)
def log_snipe(sniper: discord.Member, targets: list[discord.Member]):
  # set bonus for combo
  combo_bonus = get_combo_bonus(targets)
  # mark point total
  total = 0
  # collect all szn targets
  szn_targets = []
  for user in targets:
    value = get_raw_user_value(user)
    multiplier = 1
    if is_szn_target(user):
      multiplier = get_szn()[1]
      szn_targets.append(user)

    value = math.ceil(value * multiplier * combo_bonus)
    increment_out(sniper)
    increment_in(user)
    add_points(sniper, value)
    
    total += value
    
  # update values
  store_database()
    
  return total, szn_targets
  
# check if user is in database and initialize user in database if not
# returns key being used as user key for db
def db_get_user_key(user: discord.Member):
  # determine key here
  user_key = str(user.id)
  
  if user_key not in db.keys():
    db[user_key] = {"out": 0, "in": 0, "pts": 0}
  return user_key
    

# return database tuple for user
def check_user_stats(user: discord.Member):
  user_key = db_get_user_key(user)
  vals = db[user_key]
  return vals['in'], vals['out'],vals['pts']

# set hunting szn target and target multiplier
def set_hunting_szn(szn: discord.Role, multiplier: float):
  db['szn'] = {"role_id":szn.id, "mlt": multiplier}
  
  store_database()

# reset database values for user
def reset_values(user_id: discord.Member):
  user_key = db_get_user_key(user_id)
  
  db[user_key]['out'] = 0
  db[user_key]['in'] = 0
  db[user_key]['pts'] = 0
  
  store_database()

# return point leaders (greater than 0) sorted 
def get_leaderboard():
  leaderboard = []
  for key in db.keys():
    if key == 'szn':
      continue
    if db[key]['pts'] > 0:
      # retrieve nickname from user id
      leaderboard.append((key, db[key]['pts']))
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
    
  # converts maybe users into list of users
def parse_multi_snipes(*targets: list[discord.Member]) -> list[discord.Member]:
  res = [target for target in targets if target is not None]
  return res

def get_combo_bonus(targets: list[discord.Member]):
  vals = {1: 1, 2: 1.3, 3:1.4, 4: 1.45, 5: 1.5}
  return vals[len(targets)]

# returns a formatted string of user mentions from a list
def format_user_mentions(users: list[discord.Member]) -> str:
  # if only single person
  if len(users) == 1:
    return users[0].mention

  ret_msg = ''
  for u in users[:-1]:
    ret_msg += f'{u.mention} '
  ret_msg += f'and {users[-1].mention}'
  return ret_msg

def get_snipe_msg(targets: list[discord.Member]):
  if len(targets) == 1:
    return f':gun: Sniped {targets[0].mention}!'
  else:
    msg = f':gun: Wow! Sniped {format_user_mentions(targets)}! **{get_combo_bonus(targets)}x combo bonus** applied :fire:' 
    return msg

# create szn target message
def get_szn_target_msg(szn_targets):
  msg = ""
  szn_multi = (get_szn())[1]
  if len(szn_targets) == 1:
    msg = f":tada: You got a **hunting szn** target! **{szn_multi}x multiplier** applied! :tada:"
  elif len(szn_targets) > 1:
    szn_target_list = format_user_mentions(szn_targets)
    msg = f":tada: {szn_target_list} are **hunting szn** targets! **{szn_multi}x multiplier** applied to each! :tada:"
  return msg
  
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
                  description='Log a snipe for points! Up to five targets in one command.',
                  guild=GUILD_ID)
async def snipe(interaction: discord.Interaction, target: discord.Member, target2: discord.Member=None, target3: discord.Member=None, target4: discord.Member=None, target5:discord.Member=None):
  targets = parse_multi_snipes(target, target2, target3, target4, target5)
  points_earned, szn_targets = log_snipe(interaction.user, targets)
  # creates a hunting szn message if there were any targets
  szn_msg = get_szn_target_msg(szn_targets)
  target_msg = get_snipe_msg(targets)

  await interaction.response.send_message(f"{target_msg} \n{szn_msg} **+{points_earned}** points\nYou now have **{check_user_stats(interaction.user)[2]}** points! ")

  
  print(f"{interaction.user.display_name} used {interaction.command.name}")


# returns user stats
@bot.tree.command(name='stats', description='Check your snipe stats! Optionally, you can check someone else\'s stats', guild=GUILD_ID)
async def check_score(interaction: discord.Interaction, user: discord.Member=None):
  if user is None:
    user = interaction.user
  if type(user) is discord.Member:
    stats = check_user_stats(user)
    await interaction.response.send_message(f"**{user.display_name}'s Snipe Stats**\n:dart: Times targeted: **{stats[0]}**\n:gun: Snipes: **{stats[1]}**\n:moneybag: Points: **{stats[2]}**", ephemeral=True)
    print(f"{interaction.user.display_name} used {interaction.command.name}")
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
  print(f"{interaction.user.display_name} used {interaction.command.name}")
  
@bot.tree.command(name='snipes-help', 
                  description='Help menu for all sniping related commands!', 
                  guild=GUILD_ID)
async def help(interaction: discord.Interaction):
  em = discord.Embed(title="Help Menu", description="Here are all the commands for sniping and information")
  em.add_field(name="**:gun: /snipe** *@user*", value="Log a snipe for points! Point value of a target is determined by number of times they have been sniped as well as number of snipes that have achieved. If you snipe a group, add up to 5 people in one command for a bonus. Must send multiple commands if there are more than 5.", inline=False)
  em.add_field(name="**:chart_with_upwards_trend: /stats**", value="Check your snipe stats! Tells you your snipe count, your target count, and your total points.", inline=False)
  em.add_field(name="**:bar_chart: /leaderboard**", value="Check the leaderboard! This shows the top snipers in the server up to 10 who have any points", inline=False)
  em.add_field(name="**:question: /snipes-help**", value="Shows this menu lol", inline=False)
  await interaction.response.send_message(embed=em, ephemeral=True)
  print(f"{interaction.user.display_name} used {interaction.command.name}")

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
  print(f"{interaction.user.display_name} used {interaction.command.name}")

# set hunting szn
@bot.tree.command(name='set-szn',
                  description='Set the hunting szn role and optional multiplier (default 2x).',
                  guild=GUILD_ID)
@app_commands.default_permissions(administrator=True)
async def set_szn(interaction: discord.Interaction, szn: discord.Role, mult: float=2.0):
  await interaction.response.send_message(
      f":bangbang: Hunting Szn target is now {szn.mention}! :bangbang: \nAll {szn.name} are worth **{mult}x** points! You better hide! :index_pointing_at_the_viewer:")
  set_hunting_szn(szn, mult)
  print(f"{interaction.user.display_name} used {interaction.command.name}")

# reset user values
@bot.tree.command(name='reset-values', 
                  description='Reset values for user', 
                  guild=GUILD_ID)
@app_commands.default_permissions(administrator=True)
async def reset_user_values(interaction: discord.Interaction, user: discord.Member):
  if type(interaction.user) is discord.Member:
    reset_values(user)
    await interaction.response.send_message(f"Reset all values for {user.mention}")
    print(f"{interaction.user.display_name} used {interaction.command.name}")

# delete db values
@bot.tree.command(name='clear-db', description='Clears ALL database values. Really make sure you want to do this before you do it', guild=GUILD_ID)
@app_commands.default_permissions(administrator=True)
async def clear_db(interaction: discord.Interaction):
  cleardb()
  await interaction.response.send_message("Clearing database...")
  print(f"{interaction.user.display_name} used {interaction.command.name}")

# manually grant points to users
@bot.tree.command(name='give-points', description='manually add points to user', guild=GUILD_ID)
@app_commands.default_permissions(administrator=True)
async def give_points(interaction: discord.Interaction, user: discord.Member, points: int):
  if type(interaction.user) is discord.Member:
    add_points(user, points)
    await interaction.response.send_message(f"Gave {user.mention} {points} points. They now have {check_user_stats(user)[2]} points")
    print(f"{interaction.user.display_name} used {interaction.command.name}")

# store database into json
@bot.tree.command(name='store-db', description='store db into json file', guild=GUILD_ID)
@app_commands.default_permissions(administrator=True)
async def save_db(interaction: discord.Interaction):
  store_database()
  await interaction.response.send_message("Database saved!")
  print(f"{interaction.user.display_name} used {interaction.command.name}")

# erase snipe
@bot.tree.command(name='erase-snipe', description='erase a snipe if it was invalid', guild=GUILD_ID)
@app_commands.default_permissions(administrator=True)
async def erase_snipe(interaction: discord.Interaction, sniper: discord.Member, target: discord.Member, points: int):
  undo_snipe(sniper, target, points)
  await interaction.response.send_message(f"Erased {sniper.mention}'s snipe on {target.mention} for {points} points")
  print(f"{interaction.user.display_name} used {interaction.command.name}")

# send json db to discord
@bot.tree.command(name="get-json", description='send db json file', guild=GUILD_ID)
@app_commands.default_permissions(administrator=True)
async def get_json(interaction: discord.Interaction):
  file = retrieve_json()
  await interaction.response.send_message(file=discord.File('snipes_data.json'), ephemeral=True)

@bot.tree.command(name='kill-process', description='ends bot process', guild=GUILD_ID)
@app_commands.default_permissions(administrator=True)
async def kill_process(interaction: discord.Interaction):
  await interaction.response.send_message("Killing bot process!", ephemeral=True)
  exit(1)

# @bot.tree.command(name="upload-json", description='upload json file to set as db', guild=GUILD_ID)
# @app_commands.default_permissions(administrator=True)
# async def get_json(interaction: discord.Interaction, json: discord.File):
#   global db
#   db = json.load(json)
#   await interaction.response.send_message(file="DB uploaded", ephemeral=True)

@bot.tree.command(name='create-bounty', description='announce bounty on (whatever you want) for (however much you want)', guild=GUILD_ID)
@app_commands.default_permissions(administrator=True)
async def announce_bounty(interaction: discord.Interaction, item: str, value: int):
  await interaction.response.send_message(f":rotating_light: ** BOUNTY ALERT **:rotating_light:  \n\n :bangbang: @here First person to get a picture of **{item}** will receive **{value}** points :bangbang:", allowed_mentions=discord.AllowedMentions(everyone=True))

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
