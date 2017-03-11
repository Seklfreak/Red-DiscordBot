import discord
from discord.ext import commands
from oauth2client.service_account import ServiceAccountCredentials
import random
import io
import aiohttp
from __main__ import send_cmd_help
from .utils.chat_formatting import pagify
import datetime
from .utils import checks
import asyncio
import math

__author__ = "Sebastian Winkler"
__version__ = "0.1"

class RandomPictures:
    """My custom cog that does RandomPictures!"""

    def __init__(self, bot, sleep):
        self.bot = bot
        self.sleep = sleep
        self.google_credentials_json = "data/randompictures/google_credentials.json"
        self.picture_download_base_url = "https://www.googleapis.com/drive/v3/files/{0}?alt=media"
        self.database = [
        {"folder_ids": ["0BwVumX-VvI_SQnpBU1NqbEcyLVk"], "labels": ["전소미", "Somi"]},
        {"folder_ids": ["0BwVumX-VvI_SWEZQMXNRc2phaFk"], "labels": ["김세정", "Sejeong"]},
        {"folder_ids": ["0BwVumX-VvI_SVG5HeEgzQ1lHNnc"], "labels": ["최유정", "Yoojung"]},
        {"folder_ids": ["0BwVumX-VvI_SNzNpTGtCYXVsU1E"], "labels": ["김청하", "Chungha"]},
        {"folder_ids": ["0BwVumX-VvI_SM3J0SWhJdzVLY28"], "labels": ["김소혜", "Sohye"]},
        {"folder_ids": ["0BwVumX-VvI_SMVNCTWZoaEpRZVk"], "labels": ["周洁琼", "Jieqiong"]},
        {"folder_ids": ["0BwVumX-VvI_SVktfVzM1ZFV6bE0"], "labels": ["정채연", "Chaeyeon"]},
        {"folder_ids": ["0BwVumX-VvI_SS2Y2NVB2V292R3c"], "labels": ["김도연", "Doyeon"]},
        {"folder_ids": ["0BwVumX-VvI_SSWdETXpCUTJNclk"], "labels": ["강미나", "Mina"]},
        {"folder_ids": ["0BwVumX-VvI_SaU1taDlXZmhZXzQ"], "labels": ["임나영", "Nayoung"]},
        {"folder_ids": ["0BwVumX-VvI_SZERaVXFPRUJWQWM"], "labels": ["유연정", "Yeonjung"]},
        {"folder_ids": ["0BwVumX-VvI_SaUQ2WW9NUkQ0bnc"], "labels": ["아이오아이", "I.O.I", "IOI", "OT11"]},
        {"folder_ids": ["0BwVumX-VvI_SaUQ2WW9NUkQ0bnc",
        "0BwVumX-VvI_SZERaVXFPRUJWQWM",
        "0BwVumX-VvI_SVktfVzM1ZFV6bE0",
        "0BwVumX-VvI_SWEZQMXNRc2phaFk",
        "0BwVumX-VvI_SM3J0SWhJdzVLY28",
        "0BwVumX-VvI_SS2Y2NVB2V292R3c",
        "0BwVumX-VvI_SVG5HeEgzQ1lHNnc",
        "0BwVumX-VvI_SQnpBU1NqbEcyLVk",
        "0BwVumX-VvI_SSWdETXpCUTJNclk",
        "0BwVumX-VvI_SNzNpTGtCYXVsU1E",
        "0BwVumX-VvI_SMVNCTWZoaEpRZVk",
        "0BwVumX-VvI_SaU1taDlXZmhZXzQ"],
        "labels": ["아이오아이-all", "I.O.I-all", "IOI-all"]},
        {"folder_ids": ["0ByR8toqsAlGreGdnMlFBRk5uRmc", "0ByR8toqsAlGrNmtQdlAxQ1V3TDA"], "post_to_channels": ["283145995020271617"]}
        ]
        self.aliases = [{}]
        self.settings = {"post_interval": 5400} # 1.5 hours
        self.picture_database = {}
        self.refresh_in_progress = False

    @commands.group(pass_context=True, no_pm=True, name="randompictures", aliases=["rapi", "pics", "pic"])
    async def _randompictures(self, context):
        """Get a random picture"""
        channel = context.message.channel
        server = context.message.server
        author = context.message.author

        if context.invoked_subcommand is None:
            for role in sorted(author.roles, key=lambda k: k.position, reverse=True):
                if await self._post_random_picture_by_alias(role.name, channel, verbose=False) == True:
                    return
            await self.bot.say("I couldn't find out your bias or pictures of your bias :thinking:")

    @_randompictures.command(pass_context=True, no_pm=True, name="stats")
    async def _randompictures_stats(self, context):
        """Lists google drive pictures in the cache"""
        if len(self.database) <= 0:
            await self.bot.say("No entries in the DB!")
            return

        message = ""
        for entry in self.database:
            num = self.database.index(entry)
            total_pictures = 0
            last_pictures_cache_refresh = "Never"
            label_text = ""
            if num in self.picture_database:
                if "last_pictures_cache_refresh" in self.picture_database[num]:
                    last_pictures_cache_refresh = self.picture_database[num]["last_pictures_cache_refresh"].strftime("%Y-%m-%d %H:%M UTC")
                if "pictures_cache" in self.picture_database[num]:
                    total_pictures = len(self.picture_database[num]["pictures_cache"])
            if "labels" in entry and len(entry["labels"]) > 0:
                label_text += " ("
                i = 0
                for label in entry["labels"]:
                    i += 1
                    label_text += "{0}{1}".format(label, "" if len(entry["labels"]) == i else ", ")
                label_text += ") "

            message += "`#{0}`{4}: `{2}` pictures in cache, last refresh: `{3}`, folder(s):\n".format(num, entry, total_pictures, last_pictures_cache_refresh, label_text)
            for folder_id in entry["folder_ids"]:
                message += "<https://drive.google.com/drive/folders/{0}>\n".format(folder_id)
            if "post_to_channels" in entry and entry["post_to_channels"] != "" and len(entry["post_to_channels"]) > 0:
                message += "posting to:\n"
                for channel_id in entry["post_to_channels"]:
                    channel = self.bot.get_channel(channel_id)
                    if channel != None:
                        message += "{0.server.name}/{0.mention}\n".format(channel)
                    else:
                        message += "`#{0}` (channel not found!)\n".format(channel_id)

        for page in pagify(message, delims=["\n"]):
            await self.bot.say(page)

    @_randompictures.command(pass_context=True, no_pm=True, name="refresh")
    @checks.mod_or_permissions(administrator=True)
    async def _randompictures_refresh(self, context, num: int):
        """Refreshes the picture DB from the google drive folder(s)"""

        self.picture_database[num] = {"pictures_cache": []}
        for folder_id in self.database[num]["folder_ids"]:
            await self._refresh_cache_num(num, folder_id)

        await self.bot.say("Found {0} pictures!".format(len(self.picture_database[num]["pictures_cache"])))

    @_randompictures.command(pass_context=True, no_pm=True, name="force")
    async def _randompictures_force(self, context, alias_search: str):
        """Posts a random picture from the specified folders"""
        channel = context.message.channel

        if alias_search != "":
            await self._post_random_picture_by_alias(alias_search, channel)
        else:
            await self.bot.say("Alias not found :thinking:")

    def _get_credentials(self):
        scopes = ['https://www.googleapis.com/auth/drive']
        credentials = ServiceAccountCredentials.from_json_keyfile_name(
            self.google_credentials_json, scopes=scopes)
        return credentials

    async def _post_random_picture_by_alias(self, alias_search, channel, verbose=True):
        if len(self.database) <= 0:
            if verbose == True:
                await self.bot.send_message(channel, "Entry not found in database")
            return False

        for entry in self.database:
            for alias in entry["labels"]:
                if alias.lower() in alias_search.lower():
                    num = self.database.index(entry)
                    if num not in self.picture_database:
                        self.picture_database[num] = {"pictures_cache": []}
                    elif "pictures_cache" not in self.picture_database[num]:
                        self.picture_database[num] = {"pictures_cache": []}

                    if len(self.picture_database[num]["pictures_cache"]) <= 0:
                        await self.bot.send_message(channel, "Refreshing database...")
                        if self.refresh_in_progress == False:
                            await self._randompictures_refresh.callback(self=self, context=context, num=num)
                        else:
                            if verbose == True:
                                await self.bot.send_message(channel, "Refreshing already in progress!")
                            return False

                    if len(self.picture_database[num]["pictures_cache"]) <= 0:
                        if verbose == True:
                            await self.bot.send_message(channel, "No pictures found in this entry")
                        return False

                    return await self._post_random_picture_by_id(num, channel)

        if verbose == True:
            await self.bot.send_message(channel, "Entry not found in database")
        return False

    async def _post_random_picture_by_id(self, num, channel):
        while True:
            random_choice = random.choice(self.picture_database[num]["pictures_cache"])
            if not "size" in random_choice or random_choice["size"] == "" or int(random_choice["size"]) >= 8e+6: # discord 8 mb file limit
                continue
            break

        random_picture_download_url = self.picture_download_base_url.format(random_choice["id"])

        credentials = self._get_credentials()

        conn = aiohttp.TCPConnector(verify_ssl=False)
        with aiohttp.ClientSession(connector=conn) as session:
            headers = {"user-agent": "Red-cog-RandomPictures/"+__version__, "Authorization": "Bearer {0.access_token}".format(credentials.get_access_token())}

            modified_time = datetime.datetime.strptime(random_choice["modifiedTime"], '%Y-%m-%dT%H:%M:%S.%fZ')
            taken_time = None
            camera_model = ""
            if "imageMediaMetadata" in random_choice and len(random_choice["imageMediaMetadata"]) > 0:
                if "time" in random_choice["imageMediaMetadata"] and random_choice["imageMediaMetadata"]["time"] != "":
                    print("picture taken at:", random_choice["imageMediaMetadata"]["time"])
                    taken_time = datetime.datetime.strptime(random_choice["imageMediaMetadata"]["time"], '%Y:%m:%d %H:%M:%S') # Convert timezone somehow
                if "cameraModel" in random_choice["imageMediaMetadata"] and random_choice["imageMediaMetadata"]["cameraModel"] != "":
                    camera_model = random_choice["imageMediaMetadata"]["cameraModel"]

            message = ""
            if taken_time != None:
                if camera_model != "":
                    camera_model = " (`{0}`)".format(camera_model)
                message += "taken at: `{0}`{1}, ".format(taken_time.replace(tzinfo=datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), camera_model)
            message += "uploaded on: `{0}`".format(modified_time.replace(tzinfo=datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))
            message += ", size: `{0}`".format(self.convert_size(int(random_choice["size"])))

            async with await session.get(random_picture_download_url, headers=headers) as resp:
                image = await resp.read()

                with io.BytesIO(image) as file_obj:
                    await self.bot.send_file(channel, file_obj, filename=random_choice["name"], content=message)
        return True

    # http://stackoverflow.com/a/14822210
    def convert_size(self, size_bytes):
       if (size_bytes == 0):
           return '0B'
       size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
       i = int(math.floor(math.log(size_bytes, 1024)))
       p = math.pow(1024, i)
       s = round(size_bytes/p, 2)
       return '%s %s' % (s, size_name[i])

    async def _refresh_cache_num(self, num, folder_id):
        self.refresh_in_progress = True
        conn = aiohttp.TCPConnector(verify_ssl=False)
        with aiohttp.ClientSession(connector=conn) as session:
            credentials = self._get_credentials()
            headers = {"user-agent": "Red-cog-RandomPictures/"+__version__, "Authorization": "Bearer {0.access_token}".format(credentials.get_access_token())}
            url = "https://www.googleapis.com/drive/v3/files"
            search_string = '"{0}" in parents and (mimeType = "image/gif" or mimeType = "image/jpeg" or mimeType = "image/png")'.format(folder_id)
            page_token = None
            while True:
                print("Executing:", search_string, ", page_token:", "Yes" if page_token != None else "No")
                param = {}
                if page_token:
                    param['pageToken'] = page_token
                param['q'] = search_string
                param['fields'] = 'nextPageToken, files(id, name, size, modifiedTime, imageMediaMetadata)'
                param['pageSize'] = 1000

                async with session.get(url, params=param, headers=headers) as r:
                    files = await r.json()

                    self.picture_database[num]["pictures_cache"].extend(files['files'])
                    page_token = files.get('nextPageToken')
                    if not page_token:
                        break
        self.picture_database[num]["last_pictures_cache_refresh"] = datetime.datetime.utcnow()
        self.refresh_in_progress = False

    async def refresh_cache_loop(self, sleep, loop):
        await self.bot.wait_until_ready()
        while self == self.bot.get_cog('RandomPictures'):
            print("[RandomPictures] refreshing picture caches...")
            for entry in self.database:
                num = self.database.index(entry)
                self.picture_database[num] = {"pictures_cache": []}
                for folder_id in self.database[num]["folder_ids"]:
                    if self.refresh_in_progress == False:
                        try:
                            print("[RandomPictures] refreshing picture cache (#{0}/{1})...".format(num, folder_id))
                            await self._refresh_cache_num(num, folder_id)
                        except Exception as e:
                            print("[RandomPictures] refreshing picture cache (#{0}/{1}) failed:".format(num, folder_id), e)
                    else:
                        print("[RandomPictures] refreshing picture cache (#{0}/{1}) failed:".format(num, folder_id), "refresh already in progress!")
            await loop.create_task(sleep(86400)) # one day

    async def post_pictures_loop(self, sleep, loop):
        await self.bot.wait_until_ready()
        if "post_interval" in self.settings and self.settings["post_interval"] != "":
            while self == self.bot.get_cog('RandomPictures'):
                await loop.create_task(sleep(int(self.settings["post_interval"]))) # sleep first (because of initial refresh)
                print("[RandomPictures] posting random pictures...")
                for entry in self.database:
                    num = self.database.index(entry)
                    if "post_to_channels" in entry and entry["post_to_channels"] != "" and len(entry["post_to_channels"]) > 0:
                        for channel_id in entry["post_to_channels"]:
                            channel = self.bot.get_channel(channel_id)
                            if channel != None:
                                await self._post_random_picture_by_id(num, channel)

def make_sleep():
    async def sleep(delay, result=None, *, loop=None):
        coro = asyncio.sleep(delay, result=result, loop=loop)
        task = asyncio.ensure_future(coro)
        sleep.tasks.add(task)
        try:
            return await task
        except asyncio.CancelledError:
            return result
        finally:
            sleep.tasks.remove(task)

    sleep.tasks = set()
    sleep.cancel_all = lambda: sum(task.cancel() for task in sleep.tasks)
    return sleep

def setup(bot):
    sleep = make_sleep()
    loop = asyncio.get_event_loop()
    n = RandomPictures(bot, sleep)
    bot.add_cog(n)
    bot.loop.create_task(n.refresh_cache_loop(sleep, loop))
    bot.loop.create_task(n.post_pictures_loop(sleep, loop))