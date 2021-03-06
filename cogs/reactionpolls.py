import discord
import os
from .utils.dataIO import dataIO
from discord.ext import commands
from __main__ import send_cmd_help
from random import choice as randchoice
from cogs.utils import checks
import asyncio
from discord import utils
import re

class ReactionPolls:
    """Create reaction polls!"""

    def __init__(self, bot):
        self.bot = bot
        self.polls_file_path = "data/reactionpolls/polls.json"
        self.polls = dataIO.load_json(self.polls_file_path)

    @commands.group(pass_context=True, no_pm=True, aliases=['rp', 'reactionpolls'])
    async def reactionpoll(self, ctx):
        """Manage reaction polls"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @checks.mod_or_permissions(administrator=True)
    @reactionpoll.command(pass_context=True, no_pm=True)
    async def attach(self, ctx, pollChannel : discord.Channel, messageId, maxReactions: int, *allowedEmojis: str):
        """Attaches a reaction poll to every message
        maxReactions: 0 = unlimited"""
        message = ctx.message
        author = message.author

        pollNumber = str(len(self.polls)+1)
        while True:
            if pollNumber in self.polls:
                pollNumber = str(int(pollNumber)+1)
            else:
                break

        if len(allowedEmojis) <= 0:
            await send_cmd_help(ctx)
            return

        pollMessage = await self.bot.get_message(pollChannel, messageId)
        if pollMessage == None:
            await self.bot.say("Unable to find message")
            return

        try:
            allCustomEmojis = list(self.bot.get_all_emojis())
            for emoji in allowedEmojis:
                customEmoji = self.getCustomEmoji(emoji, allCustomEmojis)
                if customEmoji == None:
                    await self.bot.add_reaction(pollMessage, emoji)
                else:
                    allowedEmojis = tuple(x for x in allowedEmojis if x != emoji)
                    allowedEmojis = allowedEmojis + (emoji,)
                    await self.bot.add_reaction(pollMessage, customEmoji)
        except discord.HTTPException as e:
            print(e)
            await self.bot.say("I need the `Embed links` permission "
                               "to send this or you send misformatted arguments")
            return
        self.polls[pollNumber] = {"messageId": pollMessage.id, "allowedEmojis": allowedEmojis, "status": "active", "createdBy": author.id, "maxReactions": maxReactions, "channelId": pollMessage.channel.id, "type": "attached"}
        dataIO.save_json(self.polls_file_path, self.polls)

        await self.bot.say("Done! :ok_hand:")

    @reactionpoll.command(pass_context=True, no_pm=True, aliases=['crt'])
    async def create(self, ctx, question: str, maxReactions: int, *allowedEmojis: str):
        """Create a new reaction poll
        maxReactions: 0 = unlimited"""
        message = ctx.message
        author = message.author

        pollNumber = str(len(self.polls)+1)
        while True:
            if pollNumber in self.polls:
                pollNumber = str(int(pollNumber)+1)
            else:
                break

        colour = ''.join([randchoice('0123456789ABCDEF') for x in range(6)])
        colour = int(colour, 16)

        if question == "" or len(allowedEmojis) <= 0:
            await send_cmd_help(ctx)
            return

        data = discord.Embed(
            description=str("Poll #{0}").format(pollNumber),
            colour=discord.Colour(value=colour))
        data.set_author(name=str(question))
        data.set_footer(text="Poll by {0}".format(author.name), icon_url=author.avatar_url)

        try:
            allCustomEmojis = list(self.bot.get_all_emojis())
            pollMessage = await self.bot.say(embed=data)
            for emoji in allowedEmojis:
                customEmoji = self.getCustomEmoji(emoji, allCustomEmojis)
                if customEmoji == None:
                    await self.bot.add_reaction(pollMessage, emoji)
                else:
                    allowedEmojis = tuple(x for x in allowedEmojis if x != emoji)
                    allowedEmojis = allowedEmojis + (emoji,)
                    await self.bot.add_reaction(pollMessage, customEmoji)
        except discord.HTTPException as e:
            print(e)
            await self.bot.say("I need the `Embed links` permission "
                               "to send this or you send misformatted arguments")
            return
        self.polls[pollNumber] = {"messageId": pollMessage.id, "allowedEmojis": allowedEmojis, "status": "active", "createdBy": author.id, "maxReactions": maxReactions, "channelId": message.channel.id, "type": "user"}
        dataIO.save_json(self.polls_file_path, self.polls)

    def getCustomEmoji(self, emojiStr, allCustomEmojis):
        for customEmoji in allCustomEmojis:
            if str(customEmoji) == emojiStr:
                return customEmoji
        return None

    @reactionpoll.command(pass_context=True, no_pm=True, aliases=['del'])
    async def delete(self, ctx, pollId: str):
        """Deletes a poll from the db (doesn't delete the chat message!)"""
        message = ctx.message
        author = message.author
        try:
            pollId = str(pollId.replace("#", ""))
            self.bot.say(pollId)
        except ValueError:
            await self.bot.say("You have to tell me the poll id... :thinking:")
            return

        if str(pollId) not in self.polls:
            await self.bot.say("Unable to find poll! :scream:")
            return

        poll = self.polls[str(pollId)]

        if poll["createdBy"] != author.id:# and not checks.mod_or_permissions(manage_messages=True):
            await self.bot.say("You are not allowed to delete this reaction poll... :warning:")
            return

        del self.polls[str(pollId)]
        dataIO.save_json(self.polls_file_path, self.polls)
        await self.bot.say("Poll deleted from database! :wave:")

    @reactionpoll.command(pass_context=True, no_pm=True, aliases=['frz'])
    async def freeze(self, ctx, pollId: str):
        """Toggles the state of a poll
        Nobody can add reactions to freezed polls (removal of reactions is still possible!)
        """
        message = ctx.message
        author = message.author
        try:
            pollId = str(pollId.replace("#", ""))
            self.bot.say(pollId)
        except ValueError:
            await self.bot.say("You have to tell me the poll id... :thinking:")
            return

        if str(pollId) not in self.polls:
            await self.bot.say("Unable to find poll! :scream:")
            return

        poll = self.polls[str(pollId)]

        if poll["createdBy"] != author.id:# and not checks.mod_or_permissions(manage_messages=True):
            await self.bot.say("You are not allowed to manage this reaction poll... :warning:")
            return

        if poll["status"] == "active":
            self.polls[str(pollId)]["status"] = "freezed"
            await self.bot.say("Poll freezed! :snowflake:")
        else:
            self.polls[str(pollId)]["status"] = "active"
            await self.bot.say("Poll unfreezed! :zap:")

    @reactionpoll.command(pass_context=True, no_pm=True, aliases=['clr'])
    async def clear(self, ctx, pollId: str):
        """Clears all reactions from a poll"""
        message = ctx.message
        author = message.author
        try:
            pollId = str(pollId.replace("#", ""))
            self.bot.say(pollId)
        except ValueError:
            await self.bot.say("You have to tell me the poll id... :thinking:")
            return

        if str(pollId) not in self.polls:
            await self.bot.say("Unable to find poll! :scream:")
            return

        poll = self.polls[str(pollId)]

        if poll["createdBy"] != author.id:# and not checks.mod_or_permissions(manage_messages=True):
            await self.bot.say("You are not allowed to manage this reaction poll... :warning:")
            return

        if poll["status"] != "active":
            await self.bot.say("This poll is freezed, you have to unfreeze it before clearing it... :warning:")
            return

        try:
            pollChannel = self.bot.get_channel(poll["channelId"])
            pollMessage = await self.bot.get_message(pollChannel, poll["messageId"])
        except Exception as e:
            print(e)
            await self.bot.say("Unable to find poll! :warning:")
            return

        await self.bot.clear_reactions(pollMessage)

        allCustomEmojis = list(self.bot.get_all_emojis())
        for emoji in poll["allowedEmojis"]:
            customEmoji = self.getCustomEmoji(emoji, allCustomEmojis)
            if customEmoji == None:
                await self.bot.add_reaction(pollMessage, emoji)
            else:
                await self.bot.add_reaction(pollMessage, customEmoji)
        await self.bot.say("Poll cleared! :cloud_tornado:")


    async def cache_loop(self):
        await self.bot.wait_until_ready()
        while self == self.bot.get_cog('ReactionPolls'):
            await self.cache()
            #await self._update_description()
            await asyncio.sleep(300)

    async def cache(self):
        for key in self.polls:
            poll = self.polls[key]
            if not utils.find(lambda m: m.id == poll["messageId"], self.bot.messages):
                pollChannel = self.bot.get_channel(poll["channelId"])
                if pollChannel == None:
                    print("Caching failed: message #{0}, channel not found".format(poll["messageId"]))
                else:
                    try:
                        pollMessage = await self.bot.get_message(pollChannel, poll["messageId"])
                        self.bot.messages.append(pollMessage)
                        #print("Cached: message #{0.id}".format(pollMessage))
                    except Exception as e:
                        print("Caching failed: message #{0}, error: {1}".format(poll["messageId"], e))

    async def _count_all_reactions(self, message):
        n = 0
        for reaction in message.reactions:
            n += reaction.count
        return n

    async def numberOfReactionsByUserOnMessage(self, message, user):
        i = 0
        for reaction in message.reactions:
            reactionUsers = await self.bot.get_reaction_users(reaction)
            # todo: pagifying for more than 100 reactions
            if user in reactionUsers:
                i += 1
        return i

    async def check_reaction(self, reaction, user):
        for key in self.polls:
            poll = self.polls[key]
            if poll["messageId"] == reaction.message.id:
                allCustomEmojis = list(self.bot.get_all_emojis())
                emoji = self.getCustomEmoji(reaction.emoji, allCustomEmojis)
                if emoji == None:
                    emoji = reaction.emoji
                if user != self.bot.user and (poll["status"] != "active" or str(emoji) not in poll["allowedEmojis"] or (poll["maxReactions"] != 0 and await self.numberOfReactionsByUserOnMessage(reaction.message, user) > poll["maxReactions"])):
                    try:
                        await self.bot.remove_reaction(reaction.message, reaction.emoji, user)
                    except Exception as e:
                        print(e)
                else:
                    pollType = "user"
                    if "type" in poll and poll["type"] != "":
                        pollType = poll["type"]
                    if pollType == "user":
                        if len(reaction.message.embeds) > 0:
                            embed = reaction.message.embeds[0]
                            numberOfReactions = await self._count_all_reactions(reaction.message)-len(poll["allowedEmojis"])
                            newDescription = "Poll #{0}, total votes: {1}".format(key, numberOfReactions)
                            if embed["description"] != newDescription:
                                data = discord.Embed(
                                    description=newDescription,
                                    colour=embed["color"])
                                data.set_author(name=embed["author"]["name"])
                                data.set_footer(text=embed["footer"]["text"], icon_url=embed["footer"]["icon_url"])
                                await self.bot.edit_message(reaction.message, embed=data)
                                #print("Updated: user poll #{0.id}".format(reaction.message))
                    if pollType == "attached":
                        if reaction.message.author == self.bot.user:
                            pollMessageContent = reaction.message.content
                            if "votes" in pollMessageContent.lower() or "replies" in pollMessageContent.lower():
                                numberOfReactions = await self._count_all_reactions(reaction.message)-len(poll["allowedEmojis"])
                                pollMessageContent = re.sub("(votes(:)?)\ (-)?[0-9]+", "\g<1> {0}".format(numberOfReactions), pollMessageContent, flags=re.IGNORECASE)
                                pollMessageContent = re.sub("(replies(:)?)\ (-)?[0-9]+", "\g<1> {0}".format(numberOfReactions), pollMessageContent, flags=re.IGNORECASE)

                            if pollMessageContent != reaction.message.content:
                                await self.bot.edit_message(reaction.message, pollMessageContent)
                                #print("Updated: attached poll #{0.id}".format(reaction.message))

    async def check_reaction_removal(self, reaction, user):
        for key in self.polls:
            poll = self.polls[key]
            if poll["messageId"] == reaction.message.id:
                pollType = "user"
                if "type" in poll and poll["type"] != "":
                    pollType = poll["type"]
                if pollType == "user":
                    if len(reaction.message.embeds) > 0:
                        embed = reaction.message.embeds[0]
                        numberOfReactions = await self._count_all_reactions(reaction.message)-len(poll["allowedEmojis"])
                        newDescription = "Poll #{0}, total votes: {1}".format(key, numberOfReactions)
                        if embed["description"] != newDescription:
                            data = discord.Embed(
                                description=newDescription,
                                colour=embed["color"])
                            data.set_author(name=embed["author"]["name"])
                            data.set_footer(text=embed["footer"]["text"], icon_url=embed["footer"]["icon_url"])
                            await self.bot.edit_message(reaction.message, embed=data)
                            #print("Updated: user poll #{0.id}".format(reaction.message))
                if pollType == "attached":
                    if reaction.message.author == self.bot.user:
                        pollMessageContent = reaction.message.content
                        if "votes" in pollMessageContent.lower() or "replies" in pollMessageContent.lower():
                            numberOfReactions = await self._count_all_reactions(reaction.message)-len(poll["allowedEmojis"])
                            pollMessageContent = re.sub("(votes(:)?)\ (-)?[0-9]+", "\g<1> {0}".format(numberOfReactions), pollMessageContent, flags=re.IGNORECASE)
                            pollMessageContent = re.sub("(replies(:)?)\ (-)?[0-9]+", "\g<1> {0}".format(numberOfReactions), pollMessageContent, flags=re.IGNORECASE)

                        if pollMessageContent != reaction.message.content:
                            await self.bot.edit_message(reaction.message, pollMessageContent)
                            #print("Updated: attached poll #{0.id}".format(reaction.message))


def check_folder():
    if not os.path.exists("data/reactionpolls"):
        print("Creating data/reactionpolls folder...")
        os.makedirs("data/reactionpolls")


def check_file():
    polls = {}

    f = "data/reactionpolls/polls.json"
    if not dataIO.is_valid_json(f):
        print("Creating default reactionpolls polls.json...")
        dataIO.save_json(f, polls)


def setup(bot):
    check_folder()
    check_file()
    n = ReactionPolls(bot)
    bot.add_listener(n.check_reaction, "on_reaction_add")
    bot.add_listener(n.check_reaction_removal, "on_reaction_remove")
    bot.loop.create_task(n.cache_loop())
    bot.add_cog(n)
