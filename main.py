"""   Imports  """
import discord, requests, sqlite3, json, random, operator
from bs4 import BeautifulSoup
from discord.ext import commands, tasks
from datetime import datetime

"""  Initialization  """
# function for log writing in the SQLite base, table `log`
def logwrite(string):
    cursor.executemany("INSERT into log values (?, ?)", [(datetime.now(), string)])
    connection.commit()

# function for prefix 
def get_prefix(client, message):
    with open('prefixes.json', 'r') as f: # getting all data
        prefixes = json.load(f)
    return [prefixes[str(message.guild.id)], prefixes[str(message.guild.id)].capitalize()] # getting prefix only for this guild and both in capitalize (for mobile users) and normal

# bot initialization
client = commands.Bot(command_prefix = get_prefix, help_command=commands.DefaultHelpCommand(no_category='Help'), owner_id=669893078961750027)
# client = commands.Bot(command_prefix = 'p.')

#SQLite3 connection to the database
connection = sqlite3.connect('discord.db')
cursor = connection.cursor()

# creating the tables if not already - not creating will result in errors
try:
    cursor.execute('create table coins (id text not NULL primary key, coins text)')
    cursor.execute('create table log (time text not NULL primary key, description text)')
    connection.commit()
except:
    pass

# initializing the dict `coins`
try:
    cursor.execute('select * from coins')
    a = cursor.fetchall() # getting all the data from the `coins` table
    coins = {}
    for i in a: # filling in dict `coins` if any are stored in the database
        coins[f'{i[0]}'] = int(i[1])
except:
    coins = {} # if something is wrong, resulting in an error, the dict will be empty
else:
    logwrite('Coins imported from discord.db.coins successfully!')

"""  Events + Loops  """
# function for `reactrole` cmd - add role
@client.event
async def on_raw_reaction_add(payload):
    if payload.member.bot:
        pass
    else:
        with open('reactrole.json') as react_file:
            data = json.load(react_file)
            for x in data:
                if x['emoji'] == payload.emoji.name:
                    role = discord.utils.get(client.get_guild(
                        payload.guild_id).roles, id=x['role_id'])
                    await payload.member.add_roles(role)

# function for `reactrole` cmd - remove role
@client.event
async def on_raw_reaction_remove(payload):
    with open('reactrole.json') as react_file:
        data = json.load(react_file)
        for x in data:
            if x['emoji'] == payload.emoji.name:
                role = discord.utils.get(client.get_guild(
                    payload.guild_id).roles, id=x['role_id'])
                await client.get_guild(payload.guild_id).get_member(payload.user_id).remove_roles(role)

# fucntion called every time a discord error occurs
@client.event
async def on_command_error(ctx, exc):
    if isinstance(exc, commands.CommandOnCooldown): # handler for when the user is on cooldown
        await ctx.send(f'Wait {round(exc.retry_after)} seconds ({round(round(exc.retry_after)/60, 2)} minutes) to do the command again!')

# function called whenever the bot goes online
@client.event
async def on_ready():
    await client.change_presence(activity=discord.Game(name="p.help | {} guilds".format(len(client.guilds)))) # change the bot's status to: 'Playing p.help | {} guilds'
    logwrite('Bot has been started successfully!')

# function called whenever the message is sent by anyone
@client.event
async def on_message(message):
    ''' Modmail '''
    empty_array = []
    if message.author == client.user:
        return
    if str(message.channel.type) == 'private':
        mod_channel = await client.fetch_channel(825038009229246494)
        a = ''
        if message.attachments != empty_array:
            files = message.attachments
            for file in files:
                a = a + str(file.url) + ' '
        if a:
            await mod_channel.send(f'[{message.author.id}] ' + message.content + '\n\nAttachments: ' + a)
        else:
            await mod_channel.send(f'[{message.author.id}] ' + message.content)
        logwrite(f'[{message.author.name}#{message.author.discriminator}] has wrote a message in DM\'s of [{message.content}]')
    elif message.channel.id == 825038009229246494 and message.content[:message.content.find(' ')].isdecimal():
        if 'owner' in message.author.top_role.name:
            role = '**(Owner) '
        elif 'mod' in message.author.top_role.name:
            role = '**(Moderator) '
        member_obj = await client.fetch_user(int(message.content[:message.content.find(' ')]))
        a = ''
        if message.attachments != empty_array:
            files = message.attachments
            for file in files:
                a = a + str(file.url) + ' '
        index = message.content.index(" ")
        string = message.content
        mod_message = string[index:]
        if a:
            await member_obj.send(role + str(message.author.name) + '**: ' + mod_message + '\n\nAttachments: ' + a)
        else:
            await member_obj.send(role + str(message.author.name) + '**: ' + mod_message)
        logwrite(f'[{message.author.name}#{message.author.discriminator}] with the role [{role[4:-2]}] has answered with [{mod_message}] to [{member_obj.name}#{member_obj.discriminator}]')
    await client.process_commands(message)

# function called whenever the bot joins the server
@client.event
async def on_guild_join(guild):
    # writing prefix
    with open('prefixes.json', 'r') as f:
        prefixes = json.load(f)
    prefixes[str(guild.id)] = "p."
    with open('prefixes.json', 'w') as f:
        json.dump(prefixes, f)
    # update status on join so the number of guilds update
    await client.change_presence(activity=discord.Game(name="p.help | {} guilds".format(len(client.guilds))))

# function for periodical coins writing to prevent loss of progress' users
@tasks.loop(minutes=1)
async def coins_table_write():
    cursor.execute('DROP TABLE coins')
    connection.commit()
    cursor.execute('create table coins (id text not NULL primary key, coins text)')
    data = [(str(i), str(coins[i])) for i in coins]
    cursor.executemany('INSERT into coins values (?, ?)', data)
    connection.commit()
    logwrite('Coins have been rewritten in the database!')

# function for periodical rank leadboards sending in #dashboard
@tasks.loop(minutes=30)
async def ranks_print():
    coinss = ''
    b = 0
    for i in sorted(coins.items(), key=operator.itemgetter(1), reverse=True): # sorting through the top players
        b += 1
        user = await client.fetch_user(int(i[0]))
        if user.bot:
            b -= 1
            continue
        coinss = coinss + '{} - {} coins\n'.format(str(user.name), i[1]) # printing: `{name} - {number_of_coins} coins`
        if b == 10: # limiting to only 10 users
            break
    channel = await client.fetch_channel(822119098640498748)
    await channel.send(coinss)

"""  Cogs + Commands """
class Moderation(commands.Cog): # Moderation Category of commands
    """ These commands are used to moderate the server. """
    
    # p.ban <member> [reason]
    @commands.has_permissions(ban_members=True)
    @commands.command(brief='Bans a member!', description='Requires the person to have the \'Ban Members\' permission.\nBans the member of the server mentioned in the message.\n\nSyntax usage:\nmember - mention a member you want to ban\nreason - optional - deafult=None - reason of why you ban the member')
    async def ban(self, ctx, member : discord.Member, *, reason=None):
        # await member.send(f'You were banned from [{ctx.guild.name}] for the reason of: [{reason}]') # sending to the member of ban to notify
        if type(member) == str:
            member = await client.fetch_user(int(member))
        emb = discord.Embed(title = 'You have been banned!', description = "You have been banned in **{}** server by **{}#{}**".format(ctx.guild.name, ctx.message.author.name, ctx.message.author.discriminator), color = discord.Colour.from_rgb(112, 216, 227))
        if reason:
            emb.description += "\n\n**A reason was provided:**\n{}".format(reason)
        else:
            emb.description += "\n\n**No reason was provided.**"
        emb.set_footer(text = "Rules are enforced according to their spirit, not to their words!")
        await member.send(embed = emb)
        await member.ban(reason = reason) # ban process
        await ctx.send(embed = discord.Embed(description = "**Banned:** {}#{} ({}, {})\n**Reason:** {}".format(member.name, member.discriminator, member.mention, member.id, reason), colour = discord.Colour.from_rgb(112, 216, 227)).set_footer(text = "Rules are enforced according to their spirit, not to their words!"))
        logwrite(f'[{ctx.message.author.name}#{ctx.message.author.discriminator}] has banned [{member.name}#{member.discriminator}] in [{ctx.message.guild}] for the reason of [{reason}]')

    # p.clear [amount]
    @commands.has_permissions(manage_messages=True)
    @commands.command(brief='Delete the messages!', description='Requiers the person to have the \'Manage Messages\' permission.\nClears specific amount of messages in the channel.\n\nSyntax usage:\namount - optional - default=2 - amount of messages you want to delete')
    async def clear(self, ctx, amount=2):
        await ctx.channel.purge(limit = amount)
        logwrite(f'[{ctx.message.author.name}#{ctx.message.author.discriminator}] has cleared [{amount}] messages in [{ctx.message.guild}] -> [{ctx.message.channel.name}]')

    # p.kick <member> [reason]
    @commands.has_permissions(kick_members=True)
    @commands.command(brief='Kicks a member!', description='Requires the person to have the \'Kick Members\' or \'Ban Members\' permission.\nKicks the member of the server mentioned in the message.\n\nSyntax usage:\nmember - mention a member you want to kick\nreason - optional - deafult=None - reason of why you kick the member')
    async def kick(self, ctx, member : discord.Member, *, reason=None):
        if type(member) == str:
            member = await client.fetch_user(int(member))
        emb = discord.Embed(title = 'You have been kicked!', description = "You have been kicked in **{}** server by **{}#{}**".format(ctx.guild.name, ctx.message.author.name, ctx.message.author.discriminator), color = discord.Colour.from_rgb(112, 216, 227))
        if reason:
            emb.description += "\n\n**A reason was provided:**\n{}".format(reason)
        else:
            emb.description += "\n\n**No reason was provided.**"
        emb.set_footer(text = "Rules are enforced according to their spirit, not to their words!")
        await member.send(embed = emb)
        await member.kick(reason=reason)
        await ctx.send(embed = discord.Embed(description = "**Kicked:** {}#{} ({}, {})\n**Reason:** {}".format(member.name, member.discriminator, member.mention, member.id, reason), colour = discord.Colour.from_rgb(112, 216, 227)).set_footer(text = "Rules are enforced according to their spirit, not to their words!"))
        logwrite(f'[{ctx.message.author.name}#{ctx.message.author.discriminator}] has kicked [{member.name}#{member.discriminator}] from [{ctx.message.guild}] for the reason of [{reason}]')

    # p.mute <member> [reason]
    # TODO: temp mute for period of time
    @commands.has_permissions(manage_messages=True)
    @commands.command(brief='Mutes a member!', description='Requires the person to have the \'Manage Messages\' permission.\nMutes the member mentioned in the message with a reason.\n\nSyntax usage:\nmember - mention of the person who you want to mute\nreason - optional - deafult=None - reason of why you mute the member')
    async def mute(self, ctx, member: discord.Member, *, reason=None):
        if type(member) == str:
            member = await client.fetch_user(int(member))
        emb = discord.Embed(title = 'You have been muted!', description = "You have been muted in **{}** server by **{}#{}**".format(ctx.guild.name, ctx.message.author.name, ctx.message.author.discriminator), color = discord.Colour.from_rgb(112, 216, 227))
        if reason:
            emb.description += "\n\n**A reason was provided:**\n{}".format(reason)
        else:
            emb.description += "\n\n**No reason was provided.**"
        emb.set_footer(text = "Rules are enforced according to their spirit, not to their words!")
        mutedRole = discord.utils.get(ctx.guild.roles, name="mute") # getting role `mute`
        if not mutedRole: # if not found, creating it
            mutedRole = await ctx.guild.create_role(name="mute")
            for channel in ctx.guild.channels:
                await channel.set_permissions(mutedRole, speak=False, send_messages=False, read_message_history=True, read_messages=True)
        await member.add_roles(mutedRole, reason = reason) # assigning it to member
        await ctx.send(embed = discord.Embed(description = "**Muted:** {}#{} ({}, {})\n**Reason:** {}".format(member.name, member.discriminator, member.mention, member.id, reason), colour = discord.Colour.from_rgb(112, 216, 227)).set_footer(text = "Rules are enforced according to their spirit, not to their words!"))
        await member.send(embed = emb) # messaging member of a mute
        logwrite(f'[{ctx.message.author.name}#{ctx.message.author.discriminator}] has muted [{member.name}#{member.discriminator}] for the reason of [{reason}]')

    # p.prefix [prefix]
    @commands.has_permissions(administrator=True)
    @commands.command(brief='Change the bot\'s prefix!', description='Requires the person to have \'Administrator\' permission.\nChanges the bot\'s prefix to a custom one.\nDefault prefix is: [p.]\n\nSyntax usage:\nprefix - optional - default=None - the prefix that you want the bot to have in your server\nIf \'prefix\' is \'None\', then the bot will say the server\'s current prefix.')
    async def prefix(self, ctx, prefix = None):
        with open('prefixes.json', 'r') as f: # loading prefixes
            prefixes = json.load(f)
        if prefix: # if `prefix` is passed, then change prefix
            oldp = prefixes[str(ctx.guild.id)]
            prefixes[str(ctx.guild.id)] = prefix
            with open("prefixes.json", 'w') as f:
                json.dump(prefixes, f)
            await ctx.send(f'The current server prefix was changed from `{oldp}`` to `{prefix}`!')
        else: # if not, print the current prefix
            await ctx.send(f'The current server prefix is: `{prefixes[str(ctx.guild.id)]}`!')
            logwrite(f'[{ctx.message.author.name}#{ctx.message.author.discriminator}] has checked the prefix of [{ctx.message.guild}] which was [{prefixes[str(ctx.guild.id)]}]')

    # p.give <member> <name> [reason]
    # TODO: expand on `member.send()`
    @commands.has_permissions(manage_roles=True)
    @commands.command(brief='Assigns the role!', description='Requires the person to have \'Manage Roles\' permission.\nAssigns a specific role to the member.\n\nSyntax usage:\nmember - mention of the user to assign the role to\nname - name of the role to assign\nreason - optional - default=None - the reason why you gave that role')
    async def give(self, ctx, member : discord.Member, name, *, reason=None):
        role = discord.utils.get(ctx.guild.roles, name=name)
        if not role:
            await ctx.send('The role \'{}\' does not exist.'.format(name))
            logwrite(f'[{ctx.message.author.name}#{ctx.message.author.discriminator}] tried to assign the role [{name}] in [{ctx.message.guild}] but it didn\'t exist')
        else: # giving the user a role if that exists
            await member.add_roles(role, reason=reason)
            await ctx.send(f'Gave {member.mention} role \'{name}\' for the reason of: {reason}')
            await member.send(f"You were given the role \'{name}\' in the server [{ctx.guild.name}] for the reason of: [{reason}].\nCongratulations!")
            logwrite(f'[{ctx.message.author.name}#{ctx.message.author.discriminator}] has given [{member.name}#{member.discriminator}] a role [{name}] in [{ctx.message.guild}] for the reason of [{reason}]')

    # p.remove <member> <name> [reason]
    # TODO: expand on `member.send()`
    @commands.has_permissions(manage_roles=True)
    @commands.command(brief='Unassigns the role!', description='Requires the person to have \'Manage Roles\' permission.\nUnassigns a specific role to the member given.\n\nSyntax usage:\nmember - mention of the user to unassign the role to\nname - name of the role to unassign\nreason - optional - default=None - the reason why you remove that role')
    async def remove(self, ctx, member : discord.Member, name, *, reason=None):
        role = discord.utils.get(ctx.guild.roles, name=name)
        if not role:
            await ctx.send('The role \'{}\' does not exist.'.format(name))
            logwrite(f'[{ctx.message.author.name}#{ctx.message.author.discriminator}] tried to remove the role [{name}] in [{ctx.message.guild}] but it didn\'t exist')
        else: # removing the role if that exists
            await member.remove_roles(role)
            await ctx.send(f"Removed the role '{name}' from {member.mention} for the reason of: {reason}")
            await member.send(f"You were removen the role '{name} in the server [{ctx.guild.name}] for the reason of: [{reason}].")
            logwrite(f'[{ctx.message.author.name}#{ctx.message.author.discriminator}] has removed [{member.name}#{member.discriminator}] a role [{name}] in [{ctx.message.guild}] for the reason of [{reason}]')

    # p.unban <member>
    # TODO: expand on `member.send()`
    @commands.has_permissions(ban_members=True)
    @commands.command(brief='Unbans a member!', description='Requires the person to have the \'Ban Members\' permission.\nUnbans the member written in the message.\n\nSyntax usage:\nmember - name and the discriminator of the person you want to unban splitted with \'#\'')
    async def unban(self, ctx, *, member):
        banned_users = await ctx.guild.bans() # getting all bans
        member_n, member_d = member.split('#') # preparing for search
        
        for ban_entry in banned_users:
            user = ban_entry.user
            if (user.name, user.discriminator) == (member_n, member_d): # if found such user in bans, unbanning
                await ctx.guild.unban(user)
                await ctx.send(f'Unbanned {user.name}#{user.discriminator}!')
                logwrite(f'[{ctx.message.author.name}#{ctx.message.author.discriminator}] has unbanned [{member_n}#{member_d}] in [{ctx.message.guild}]')

    # p.unmute <member>
    # TODO: expand on `member.send()`
    @commands.has_permissions(manage_messages=True)
    @commands.command(brief='Mutes a member!', description='Requires the person to have the \'Manage Messages\' permission.\nMutes the member mentioned in the message with a reason.\n\nSyntax usage:\nmember - mention of the person who you want to mute\nreason - optional - deafult=None - reason of why you mute the member')
    async def unmute(self, ctx, member: discord.Member):
        mutedRole = discord.utils.get(ctx.guild.roles, name="mute") # finding `mute` role
        await member.remove_roles(mutedRole) # removing it from user
        await ctx.send(f"Unmuted {member.mention}!")
        await member.send(f"You were unmuted in the server [{ctx.guild.name}]\n\nBe accurate and follow all the rules of the guild correctly!") # messaging user about unmute
        logwrite(f'[{ctx.message.author.name}#{ctx.message.author.discriminator}] has unmuted [{member.name}#{member.discriminator}] in [{ctx.message.guild}]')
    
    # p.reactrole <emoji> <role> <message>
    # TODO: improve embed
    @commands.command(brief='Add a reaction role message!', description='Requires the person to have the \'Manage Roles\' permission.\nThis command allows you to make an embed message with a reaction which if the member reacts to, will assign the role mentioned.\n\nSyntax usage:\nemoji - an emoji of the server/Discord\nrole - mention of the role you want to assign to users\nmessage - description of the embed')
    @commands.has_permissions(manage_roles=True)
    async def reactrole(self, ctx, emoji, role: discord.Role, *, message):
        emb = discord.Embed(description=message) # creating embed
        await ctx.channel.purge(limit=1) # purging the command message
        msg = await ctx.channel.send(embed=emb) # sending embed
        await msg.add_reaction(emoji) # adding reaction to embed
        with open('reactrole.json') as json_file: # sending the message to database
            data = json.load(json_file)
            new_react_role = {'role_name': role.name, 
            'role_id': role.id,
            'emoji': emoji,
            'message_id': msg.id}
            data.append(new_react_role)
        with open('reactrole.json', 'w') as f:
            json.dump(data, f, indent=4)
        logwrite(f'[{ctx.message.author.name}#{ctx.message.author.discriminator}] has created a reactrole message in [{ctx.guild.name}] with the role [{role.id}], emoji [{emoji}] and the message [{message}]')
    
    # p.editcmd <name> <message>
    @commands.command(brief='Add a custom command!', description='Requires the person to have the \'Manage Server\' permission.\nThis command allows you to create/edit your custom command to print out the text (can be formatted) given.\n\nSyntax usage:\nname - name of the command that you want to add\nmessage - text that you want the command to print when executed')
    @commands.has_permissions(manage_guild=True)
    async def editcmd(self, ctx, name, *, message):
        with open('commands.json', 'r') as f: # getting all commands
            data = json.load(f)
        if str(ctx.guild.id) in data: # parsing for specific guild
            guildcmds = data[str(ctx.guild.id)] # if found, getting its data
        else:
            guildcmds = {} # otherwise, creating new data for the guild
        guildcmds[name] = message
        data[str(ctx.guild.id)] = guildcmds
        with open('commands.json', 'w') as f: # applying the changes
            json.dump(data, f)
        await ctx.send('Your custom command was edited! You can use it by writing: `p.usecmd {}`.'.format(name)) # notifying of the command being added/edited
        logwrite(f'[{ctx.message.author.name}#{ctx.message.author.discriminator}] has created a custom command [{name}] in [{ctx.guild.name}] with the message [{message}]')

    # p.delcmd <name>
    @commands.command(brief='Delete a custom command!', description='Requires the person to have the \'Manage Server\' permission.\nThis command allows you to delete your custom command.\nSyntax usage:\nname - name of the command you want to remove')
    @commands.has_permissions(manage_guild=True)
    async def delcmd(self, ctx, name):
        if not name:
            await ctx.send('Not all the parameters were given. Please make sure you did, by looking at the syntax usage by typing `p.help delcmd`.')
        else:
            with open('commands.json', 'r') as f: # getting all data
                data = json.load(f)
            if str(ctx.guild.id) not in data: # parsing for specific guild's data
                await ctx.send('You do not have any commands so far. If you\'d like to make one, please see `p.help editcmd`.')
            else:
                guildcmds = data[str(ctx.guild.id)] # getting data only for this guild
                if name not in guildcmds:
                    await ctx.send('You do not have a command named \'{}\'. If you\'d like to make one, please see `p.help editcmd`.'.format(name))
                    return
                del guildcmds[name]
                data[str(ctx.guild.id)] = guildcmds
                with open('commands.json', 'w') as f: # applying data
                    json.dump(data, f)
                await ctx.send('Your custom command named \'{}\' was deleted.'.format(name))
                logwrite(f'[{ctx.message.author.name}#{ctx.message.author.discriminator}] has deleted a custom command [{name}] in [{ctx.guild.name}]')
    
    # p.usecmd <name>
    @commands.command(brief='Use your custom command!', description='Use your custom commands where ever on your server!\n\nSyntax usage:\nname - name of the command you want to use')
    async def usecmd(self, ctx, name):
        if not name:
            await ctx.send('Not all the parameters were given. Please make sure you did, by looking at the syntax usage by typing `p.help usecmd`.')
        else:
            with open('commands.json', 'r') as f: # getting all data
                data = json.load(f)
            if not data[str(ctx.guild.id)]:
                await ctx.send('You do not have any commands so far. If you\'d like to make one, please see `p.help editcmd`.')
            else:
                guildcmds = data[str(ctx.guild.id)] # getting data only for this guild
                if name not in guildcmds:
                    await ctx.send('You do not have a command named \'{}\'. If you\'d like to make one, please see `p.help editcmd`.'.format(name))
                    return
                await ctx.send(guildcmds[name])
                logwrite(f'[{ctx.message.author.name}#{ctx.message.author.discriminator}] has used a custom command [{name}] in [{ctx.guild.name}]')
    
    # p.poll <message>
    # TODO: improve embed
    @commands.has_permissions(manage_messages=True)
    @commands.cooldown(1, 30, commands.BucketType.guild)
    @commands.command(brief='Create a poll!', description='Requiers the person to have the \'Manage Messages\' permission.\nCreate a poll with two reactions!\n\nSyntax usage:\nmessage - your question for the poll; the answer to it must be either \'yes\' or \'no\'')
    async def poll(self, ctx, *, message):
        emb = discord.Embed(title='POLL', description=f'{message}') # creating embed
        await ctx.channel.purge(limit=1) # deleting the cmd message
        msg = await ctx.send(embed=emb) # sending
        await msg.add_reaction('👍') # adding reactions
        await msg.add_reaction('👎')
        logwrite(f'[{ctx.message.author.name}#{ctx.message.author.discriminator}] made a poll in [{ctx.message.guild}] with a question [{message}]')

class Fun(commands.Cog): # category Fun of all commands
    """ These commands are to have fun in the server. """

    # p.embed <params>
    @commands.command(brief='Create a custom embed!', description="Requiers the person to have the 'Manage Messages' permission.\nCreate an embed which is fully customizable - include colours, author, title, description, etc!\n\nSyntax usage:\nparams - a full example can be found here: https://i.imgur.com/NvQvCVp.png")
    @commands.has_permissions(manage_messages=True)
    async def embed(self, ctx, *, params):
        # Components of embed
        embed = discord.Embed()
        types = ['title=', 'description=', 'footer=', 'author=', 'colour=', 'timestamp=']
        # Converting `params` into a `dict` type
        dict = {}
        for i in types:
            if params.find(i) != -1:
                dict[i] = params.find(i)+len(i)
            else:
                dict[i] = params.find(i)
        allitems = sorted(dict.items(), key=operator.itemgetter(1))
        dict = {}
        for i in range(len(allitems)):
            if allitems[i][1] == -1:
                dict[allitems[i][0][:-1]] = ''
                continue
            if i == len(allitems) - 1:
                dict[allitems[i][0][:-1]] = params[allitems[i][1]:]
            else:    
                dict[allitems[i][0][:-1]] = params[allitems[i][1]:allitems[i+1][1]-len(allitems[i+1][0])-1]
        # Adding stuff to an embed
        if dict['title']: # embed title
            embed.title = dict['title']
        if dict['description']: # embed description
            embed.description = dict['description']
        if dict['footer']: # embed footer
            embed.set_footer(text=dict['footer'])
        if dict['colour']: # embed colour
            dict['colour'] = tuple([int(i) for i in dict['colour'].split(', ')])
            embed.colour = discord.Color.from_rgb(dict['colour'][0], dict['colour'][1], dict['colour'][2])
        if dict['author']: # embed author
            embed.set_author(name=dict['author'])
        if dict['timestamp']: # embed timestamp (unix format)
            embed.timestamp = datetime.strptime(dict['timestamp'], '%d.%m.%Y %H:%M %z')
        if len(embed) > 6000: # checking if the embed size is over the limit. if so, it cannot be sent, making an error. we inform the user about that.
            await ctx.send("Couldn't send an embed due to it being more that 6000 unicode characters. Please make it {} unicode characters shorter.".format(len(embed)-6000))
            return
        # otherwise just cotinuing to send it
        await ctx.channel.purge(limit=1) # clearing a message that triggered the embed creation
        await ctx.send(embed=embed) # sending an embed
        logwrite(f'[{ctx.message.author.name}#{ctx.message.author.discriminator}] has created an embed in [{ctx.guild.name}] with [{len(embed)}] UTF characters') # logging the command completion

    # p.balance [member]
    @commands.command(brief='Check your balance!', description='Check your balance or someone\'s else by mentioning them.\n\nSyntax usage:\nmember - optional - default=None - mention a member to get his/her balance')
    async def balance(self, ctx, member : discord.Member = None):
        if member: # if member is given, gets the balance of him/her
            await ctx.send('{} coins - {}\'s current balance!'.format(str(coins[str(member.id)]), member.mention))
            logwrite(f'[{ctx.message.author.name}#{ctx.message.author.discriminator}] checked [{member.name}#{member.discriminator}]\'s balance which was [{str(coins[str(member.id)])}] in [{ctx.message.guild}]')
        else: # otherwise, gets balance of yourself
            await ctx.send('{} coins - <@{}>\'s current balance!'.format(str(coins[str(ctx.message.author.id)]), ctx.message.author.id))
            logwrite(f'[{ctx.message.author.name}#{ctx.message.author.discriminator}] checked his own balance which was [{str(coins[str(member.id)])}] in [{ctx.message.guild}]')

    # p.coin
    @commands.command(brief='Free coins!', description='Chooses a random number 1-3 and applies this amount to your total amount.\n\nSyntax usage:')
    # async def coin(self, ctx, member : discord.Member = None):
    async def coin(self, ctx):
        b = random.randint(1, 3)
        if b == 1:
            coin_word = 'coin'
        else:
            coin_word = 'coins'
        '''
        if member:
            if str(member.id) in coins:
                a = coins[f'{member.id}'] + b
                coins[f'{member.id}'] = a
            else:
                coins[f'{member.id}'] = b
            await ctx.send('<@{}>\'s balance: {} coins (+{})'.format(str(member.id), coins[f'{member.id}'], b))
            logwrite(f'[{ctx.message.author.name}#{ctx.message.author.discriminator}] gave [{b}] {coin_word} to [{member.name}#{member.discriminator}] in [{ctx.message.guild}]')
        else:
        '''
        if str(ctx.message.author.id) in coins: # looking for that user in `coins` dict
            a = coins[f'{ctx.message.author.id}'] + b
            coins[f'{ctx.message.author.id}'] = a # applying the changes
        else:
            coins[f'{ctx.message.author.id}'] = b
        await ctx.send('<@{}>\'s balance: {} coins (+{})'.format(str(ctx.message.author.id), coins[f'{ctx.message.author.id}'], b))
        logwrite(f'[{ctx.message.author.name}#{ctx.message.author.discriminator}] gave [{b}] {coin_word} to himself in [{ctx.message.guild}]')

    '''
    # p.rob <member> [message]
    @commands.command(brief='Rob someone for coins!', description='Generates a random number from 1-10 and robs the mentioned person.\n\nSyntax usage:\nmember - mention a member who you want to rob\nmessage - optional - default=\'got robbed\'- custom message of \'got robbed\'')
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def rob(self, ctx, member : discord.Member, *, message='got robbed'):
        if member:
            if str(member.id) != str(ctx.message.author.id):
                if coins[str(ctx.message.author.id)] >= 10 and coins[str(member.id)] > 0:
                    if coins[str(member.id)] < 10:
                        b = coins[str(member.id)]
                        s = random.randint(1, b)
                        coins[str(member.id)] = b-s
                        a = coins[str(ctx.message.author.id)] + s
                        coins[str(ctx.message.author.id)] = a
                        await ctx.send('{} {} by <@{}>.\n{}\'s current balance: {} coins (-{})\n<@{}>\'s current balance: {} coins (+{})'.format(member.mention, message, ctx.message.author.id, member.mention, coins[f'{member.id}'], s, str(ctx.message.author.id), coins[str(ctx.message.author.id)], s))
                    else:
                        s = random.randint(1, 10)
                        a = coins[str(ctx.message.author.id)] + s
                        coins[str(ctx.message.author.id)] = a
                        b = coins[str(member.id)] - s
                        coins[str(member.id)] = b
                        if coins[str(member.id)] < 0:
                            coins[str(member.id)] = 0
                        await ctx.send('{} {} by <@{}>.\n{}\'s current balance: {} coins (-{})\n<@{}>\'s current balance: {} coins (+{})'.format(member.mention, message, ctx.message.author.id, member.mention, coins[f'{member.id}'], s, str(ctx.message.author.id), coins[str(ctx.message.author.id)], s))
                else:
                    await ctx.send('You need to have at least 10 coins to rob and the other player needs coins to be robbed!\nYou have {} coins. <@{}> has {} coins.'.format(coins[str(ctx.message.author.id)], member.id, coins[str(member.id)]))
            else:
                await ctx.send('You cannot rob yourself <@{}>!'.format(str(ctx.message.author.id)))
        else:
            await ctx.send('Mention someone to rob!')
    '''

    # p.rank
    @commands.command(brief='Check the world leaderboard!', description='Check your stats on the world leaderboard!\n\nSyntax usage:')
    async def rank(self, ctx):
        coinss = ''
        b = 0
        for i in sorted(coins.items(), key=operator.itemgetter(1), reverse=True): # going through the list of tuples sorted with the highest values first
            b += 1
            user = await client.fetch_user(int(i[0]))
            if user.bot: # if bot, then skipping
                b -= 1
                continue
            coinss = coinss + '{} - {} coins\n'.format(str(user.name), i[1])
            if b == 10: # limiting to only top 10 players
                break
        await ctx.channel.purge(limit=1)
        await ctx.send(coinss)
        logwrite(f'[{ctx.message.author.name}#{ctx.message.author.discriminator}] checked the leaderboard in [{ctx.message.guild}]')

class Info(commands.Cog): # category Info of commands
    """ These commands are to give you info about the bot. """

    # p.ping
    @commands.command(brief='Check the latency in ms!', description='Check how long does it take for the bot to respond to you!\n\nSyntax usage:')
    async def ping(self, ctx):
        await ctx.send(f'Ping: {round(client.latency * 1000)}ms') # sends latency in ms
        logwrite(f'[{ctx.message.author.name}#{ctx.message.author.discriminator}] checked the bot\'s ping in [{ctx.message.guild}]')

    # p.suggest
    @commands.command(brief='Suggest a command!', description="You can sugest a command for my bot by submiting a form via Google Forms.\n\nSyntax usage:")
    async def suggest(self, ctx):
        await ctx.send("Please follow the link to give your suggestions. Great to know that you want to help me improve the bot! https://forms.gle/GZBvLkqY6zAYH8gs7")
        logwrite(f'[{ctx.message.author.name}#{ctx.message.author.discriminator}] did \'p.suggest\' in [{ctx.message.guild}]')
    
    # p.bug
    @commands.command(brief='Report a bug!', description="If you found a bug, please report it through the Google Forms to me.\n\nSyntax usage:")
    async def bug(self, ctx):
        await ctx.send("Please follow the link here to report any bugs. Your cooperation is greatly appreciated! https://forms.gle/QFTdQfrhv578qJiw9")
        logwrite(f'[{ctx.message.author.name}#{ctx.message.author.discriminator}] did \'p.bug\' in [{ctx.message.guild}]')

    # p.author
    @commands.command(brief='Check the developer of the bot!', description='A one person project by the name of "pep\'s Bot" by @pep#7669 used to make your experience with Discord much better.\nUse \'p.help\' for more commands!\n\nSyntax usage:')
    async def author(self, ctx):
        await ctx.send('The developer of this bot is <@669893078961750027> (pep#7669)!')
        logwrite(f'[{ctx.message.author.name}#{ctx.message.author.discriminator}] has checked the developer of the bot in [{ctx.message.guild}]')

    # p.status
    @commands.cooldown(1, 300, commands.BucketType.guild)
    @commands.command(brief='Check the bot\'s status!', description='Check the bot\'s status right in Discord.\nMore about the bot\'s status on: https://pepbot.statuspage.io !\n\nSyntax usage:')
    async def status(self, ctx):
        page = requests.get('https://pepbot.statuspage.io')
        soup = BeautifulSoup(page.content, 'html.parser')
        result = soup.find('span', class_='status font-large')
        if not result:
            result = soup.find('a', class_='actual-title with-ellipsis')
        # creating an embed
        emb = discord.Embed(title='Bot Status', description=f'Current status of the bot is: {result.text.strip()}\nYou can find more on: https://pepbot.statuspage.io !')
        emb.set_footer(text='Check the status daily!')
        # sending it
        await ctx.send(embed=emb)
        logwrite(f'[{ctx.message.author.name}#{ctx.message.author.discriminator}] has checked the bot\'s status in [{ctx.message.guild}] which was [{result}]')
    
    # p.invite
    @commands.command(brief='Check the bot\'s links!', description="Sends the links in the channel for the official server, bot's invite link to your server and the bot's official status page.\n\nSyntax usage:")
    async def invite(self, ctx):
        await ctx.send("""The bot's current status/outages can be found here: <https://pepbot.statuspage.io>
The bot's invite link to the community server can be found here: <https://discord.com/invite/yktvrqxmYx>
The bot's invite link to your server can be found here: <https://shortest.link/pepbot>
The bot's page on top.gg can be found here: <https://top.gg/bot/789102405944868865>""")
        logwrite(f'[{ctx.message.author.name}#{ctx.message.author.discriminator}] did \'p.invite\' in [{ctx.message.guild}]')
    
    # p.contact [message]
    @commands.command(brief='Contact the owner/support!', description="Contact the support to get the help about this bot.\nNOTE: If the bot is unable to do a command properly, it might mean that it doesn't have the right permissions to do so in the channel. See the bot's settings as well as the channel ones to ensure they are correct.\n\nSyntax usage:\nmessage - optional - default=None - can be more than one word - if None, prints the guide on how to contact - if not None, sends this to the support of the bot")
    async def contact(self, ctx, *, message = None):
        if message: # if message passed, sends this message to #modmail
            mod_channel = await client.fetch_channel(825038009229246494)
            empty_array = []
            a = ''
            if ctx.message.attachments != empty_array: # attachments included
                files = ctx.message.attachments
                for file in files:
                    a = a + str(file.url) + ' '
            # sending
            if a:
                await mod_channel.send(f'[{ctx.message.author.id}] ' + message + '\n\nAttachments: ' + a)
            else:
                await mod_channel.send(f'[{ctx.message.author.id}] ' + message)
            logwrite(f'[{ctx.message.author.name}#{ctx.message.author.discriminator}] has wrote a message in the server [{ctx.message.guild}] of [{ctx.message.content}]')
        else: # else, prints guidelines on how to send
            await ctx.send("If you'd like to contact the support of the bot, please read below:\n\nNOTE: If the bot is unable to do a command properly, it might mean that it doesn't have the right permissions to do so in the channel. See the bot's settings as well as the channel ones to ensure they are correct.\n\nAlso, pleace notice that, if you break the Discord ToS while messaging the support team, you will not be responded with anything.\n\nIf you have any issues with the bot, please do the following:\n**1.** Join the following Discord: <https://discord.gg/yktvrqxmYx>\nThis is needed as for support to contact you through the bot's DM, needing to mention you.\n\n**2.** Contact the support.\nTo do so, you can either DM (Message) the bot or do `p.contact [message]`, where `[message]` is a message that you'd like to send for the support.")

# starting the loops
coins_table_write.start()
ranks_print.start()

# adding cogs
client.add_cog(Info())
client.add_cog(Fun())
client.add_cog(Moderation())

# starting the bot
client.run('TOKEN HERE')
