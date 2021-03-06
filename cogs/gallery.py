import discord
from discord.ext import commands
from .utils.dataIO import dataIO
import os
from __main__ import send_cmd_help
from .utils import checks
import re
import aiohttp
import json

__author__ = "Sebastian Winkler"
__version__ = "1.0.0"

class Gallery:
    """Cog for gallery channels"""

    def __init__(self, bot):
        self.bot = bot
        self.galleries_file_path = "data/gallery/galleries.json"
        self.galleries = dataIO.load_json(self.galleries_file_path)

    @commands.group(pass_context=True, no_pm=True, name="gallery")
    @checks.mod_or_permissions(administrator=True)
    async def _gallery(self, ctx):
        """Gallery managing"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @_gallery.command(pass_context=True, no_pm=True, name="add")
    @checks.mod_or_permissions(administrator=True)
    async def _add(self, ctx, source : discord.Channel, target : discord.Channel):
        """Adds a new channel to the gallery channel list"""
        author = ctx.message.author
        server = ctx.message.server

        if server.id not in self.galleries:
            self.galleries[server.id] = []

        galleryData = {"sourceChannelId": source.id, "targetChannelId": target.id}
        self.galleries[server.id].append(galleryData)

        dataIO.save_json(self.galleries_file_path, self.galleries)

        await self.bot.say("{0} Added gallery, from {1.mention} to {2.mention}! :ok_hand:".format(author.mention, source, target))

    @_gallery.command(pass_context=True, no_pm=True, name="list")
    @checks.mod_or_permissions(administrator=True)
    async def _list(self, ctx):
        """Shows all galleries"""
        author = ctx.message.author
        server = ctx.message.server

        if server.id not in self.galleries:
            await self.bot.say("{0} No galleries on this server! :warning:".format(author.mention))
            return

        listMessage = ""
        i = 0
        for galleryData in self.galleries[server.id]:
            sourceChannel = server.get_channel(galleryData["sourceChannelId"])
            targetChannel = server.get_channel(galleryData["targetChannelId"])
            listMessage += "`#{2}` posting from: {0.mention} to: {1.mention}\n".format(sourceChannel, targetChannel, i)
            i+= 1

        if listMessage == "":
            await self.bot.say("{0} No galleries on this server! :warning:".format(author.mention))
            return

        await self.bot.say("{0}\n{1}".format(author.mention, listMessage))

    @_gallery.command(pass_context=True, no_pm=True, name="del")
    @checks.mod_or_permissions(administrator=True)
    async def _del(self, ctx, galleryId : int):
        """Removes a gallery from the server"""
        author = ctx.message.author
        server = ctx.message.server

        if server.id not in self.galleries:
            await self.bot.say("{0} Unable to find gallery `#{1}` on this server! :warning:".format(author.mention, galleryId))
            return

        try:
            del(self.galleries[server.id][galleryId])
        except IndexError:
            await self.bot.say("{0} Unable to find gallery `#{1}` on this server! :warning:".format(author.mention, galleryId))
            return

        dataIO.save_json(self.galleries_file_path, self.galleries)

        await self.bot.say("{0} Successfully deleted gallery `#{1}` from this server! :ok_hand:".format(author.mention, galleryId))

    async def check_link(self, message):
        server = message.server
        author = message.author
        channel = message.channel

        if message.server is None:
            return

        if message.channel.is_private:
            return

        if author == self.bot.user:
            return

        if self._is_command(message.content):
            return

        if server.id not in self.galleries:
            return

        for galleryData in self.galleries[server.id]:
            if galleryData["sourceChannelId"] == channel.id:
                links = []
                if len(message.attachments) > 0:
                    for attachment in message.attachments:
                        links.append(attachment["url"])
                if len(message.content) > 0:
                    if "http" in message.content:
                        for item in message.content.split(" "):
                            linksFound = re.findall("(?P<url><?https?://[^\s]+>?)", item)
                            if linksFound != None:
                                for linkFound in linksFound:
                                    if not (linkFound[0] == "<" and linkFound[len(linkFound)-1] == ">"):
                                        if linkFound[0] == "<":
                                            links.append(linkFound[1:len(linkFound)])
                                        else:
                                            links.append(linkFound)
                if len(links) > 0:
                    sourceChannel = server.get_channel(galleryData["sourceChannelId"])
                    targetChannel = server.get_channel(galleryData["targetChannelId"])
                    for link in links:
                        await self._send_link_to_target(galleryData, link, author, sourceChannel, targetChannel)

    async def _send_link_to_target(self, galleryData, link, author, source, target):
        if "WEBHOOK_ID" not in galleryData or "WEBHOOK_TOKEN" not in galleryData or galleryData["WEBHOOK_ID"] == "" or galleryData["WEBHOOK_TOKEN"] == "":
            linkMessage = "**{1.name}** posted {0}".format(link, author, source, target)
            return await self.bot.send_message(target, linkMessage)
        else:
            linkMessage = "posted {0}".format(link, author, source, target)
            url = "https://discordapp.com/api/webhooks/{0[WEBHOOK_ID]}/{0[WEBHOOK_TOKEN]}".format(galleryData)
            headers = {"user-agent": "Red-cog-Gallery/"+__version__, "content-type": "application/json"}
            payload = {"username": author.name, "avatar_url": author.avatar_url, "content": linkMessage}
            conn = aiohttp.TCPConnector(verify_ssl=False)
            session = aiohttp.ClientSession(connector=conn)
            async with session.post(url, data=json.dumps(payload), headers=headers) as r:
                await r.text()
            session.close()
            return True

    def _is_command(self, msg):
        for p in self.bot.settings.prefixes:
            if msg.startswith(p):
                return True
        return False

def check_folder():
    if not os.path.exists("data/gallery"):
        print("Creating data/gallery folder...")
        os.makedirs("data/gallery")

def check_file():
    galleries = {}

    f = "data/gallery/galleries.json"
    if not dataIO.is_valid_json(f):
        print("Creating default gallery galleries.json...")
        dataIO.save_json(f, galleries)

def setup(bot):
    check_folder()
    check_file()
    n = Gallery(bot)
    bot.add_listener(n.check_link, "on_message")
    bot.add_cog(n)

