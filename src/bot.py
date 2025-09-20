#                __  __    ____    U  ___ u   ____      _____   ____     
#      ___     U|' \/ '|uU|  _"\ u  \/"_ \/U |  _"\ u  |_ " _| / __"| u  
#     |_"_|    \| |\/| |/\| |_) |/  | | | | \| |_) |/    | |  <\___ \/   
#      | |      | |  | |  |  __/.-,_| |_| |  |  _ <     /| |\  u___) |   
#    U/| |\u    |_|  |_|  |_|    \_)-\___/   |_| \_\   u |_|U  |____/>>  
# .-,_|___|_,-.<<,-,,-.   ||>>_       \\     //   \\_  _// \\_  )(  (__) 
#  \_)-' '-(_/  (./  \.) (__)__)     (__)   (__)  (__)(__) (__)(__)      

import traceback, webbrowser, discord, asyncio, aiohttp, aiofiles, gspread, json, time, sys, re, os

from discord.ext import commands, tasks
import discord.ui as ui

from gspread_asyncio import AsyncioGspreadClientManager, AsyncioGspreadClient
from google.oauth2.service_account import Credentials

from rich import print
from cfg import *

#    _       U  ___ u    _      ____         ____     _____      _       _____  U _____ u 
#   |"|       \/"_ \/U  /"\  u |  _"\       / __"| u |_ " _| U  /"\  u  |_ " _| \| ___"|/ 
# U | | u     | | | | \/ _ \/ /| | | |     <\___ \/    | |    \/ _ \/     | |    |  _|"   
#  \| |/__.-,_| |_| | / ___ \ U| |_| |\     u___) |   /| |\   / ___ \    /| |\   | |___   
#   |_____|\_)-\___/ /_/   \_\ |____/ u     |____/>> u |_|U  /_/   \_\  u |_|U   |_____|  
#   //  \\      \\    \\    >>  |||_         )(  (__)_// \\_  \\    >>  _// \\_  <<   >>  
#  (_")("_)    (__)  (__)  (__)(__)_)       (__)    (__) (__)(__)  (__)(__) (__)(__) (__) 

cookies = {".ROBLOSECURITY": ROBLOSECURITY}

if not os.path.exists("queue.csv"): 
    with open("queue.csv", "w") as file:
        file.write("\n")

if not os.path.exists("requesters.json"): 
    with open("requesters.json", "w") as file:
        file.write("{}")

ignore = []
queue = []
with open("queue.csv", "r") as file:
    for line in open("queue.csv", "r").readlines():
        clear = line.strip()
        splitted = clear.split(",")
        if len(splitted) == 2: queue.append((splitted[0], splitted[1]))

requesters = {}
with open("requesters.json", "r") as file:
    content = file.read()
    requester = json.loads(content)

async def write_queue():
    async with aiofiles.open("queue.csv", "w") as file:
        for game in queue: 
            await file.write(f"{game[0]},{game[1]}\n")

async def write_requesters():
    async with aiofiles.open("requesters.json", "w") as file:
        await file.write(json.dumps(requesters))

#    ____    U _____ u  ___     _   _ U _____ u ____     _____   ____     
# U |  _"\ u \| ___"|/ / " \ U |"|u| |\| ___"|// __"| u |_ " _| / __"| u  
#  \| |_) |/  |  _|"  | |"| | \| |\| | |  _|" <\___ \/    | |  <\___ \/   
#   |  _ <    | |___ /| |_| |\ | |_| | | |___  u___) |   /| |\  u___) |   
#   |_| \_\   |_____|U \__\_\u<<\___/  |_____| |____/>> u |_|U  |____/>>  
#   //   \\_  <<   >>   \\// (__) )(   <<   >>  )(  (__)_// \\_  )(  (__) 
#  (__)  (__)(__) (__) (_(__)    (__) (__) (__)(__)    (__) (__)(__)      

async def get_universes(universes: list):
    async with aiohttp.ClientSession(cookies=cookies) as session:
        request = await session.get(f"https://games.roblox.com/v1/games?universeIds={','.join(map(str, universes))}")
        request.raise_for_status()
        response = await request.json()
        return response.get("data")

async def get_universe_playability(universes: list):
    async with aiohttp.ClientSession(cookies=cookies) as session:
        request = await session.get(f"https://games.roblox.com/v1/games/multiget-playability-status?universeIds={','.join(map(str, universes))}")
        request.raise_for_status()
        response = await request.json()
        return response

async def get_universe_maturity(universe_id):
    async with aiohttp.ClientSession(cookies=cookies) as session:
        request = await session.post(
            "https://apis.roblox.com/experience-guidelines-api/experience-guidelines/get-age-recommendation",
            json={"universeId": str(universe_id)}
        )
        request.raise_for_status()
        response = await request.json()
        return response.get("ageRecommendationDetails").get("summary").get("ageRecommendation")

async def get_places(places: list):
    params = "&".join([f"placeIds={place}" for place in places])
    async with aiohttp.ClientSession(cookies=cookies) as session:
        request = await session.get(f"https://games.roblox.com/v1/games/multiget-place-details?{params}")
        request.raise_for_status()
        response = await request.json()
        return response

async def get_badges(universe_id):
    badges = []
    cursor = ""
    async with aiohttp.ClientSession(cookies=cookies) as session:
        while cursor != None:
            request = await session.get(
                f"https://badges.roblox.com/v1/universes/{universe_id}/badges",
                params={
                    "limit": 100,
                    "cursor": cursor
                }
            )
            request.raise_for_status()
            response = await request.json()

            badges.extend(response.get("data"))
            cursor = response.get("nextPageCursor")
    
    return badges

def get_legacies(badges: list):
    return [badge for badge in badges if badge.get("id") <= 2124945818]

async def resolve_share(url: str):
    async with aiohttp.ClientSession(cookies=cookies) as session:
        request = await session.get(url)
        request.raise_for_status()
        html_content = await request.text()

    return html_content.split('''<meta name="roblox:start_place_id" content="''')[1].split('"')[0]

async def post_message(place_id):
    async with aiohttp.ClientSession(headers={"x-api-key": API_KEY}) as session:
        request = await session.post(
            f"https://apis.roblox.com/messaging-service/v1/universes/{HUB_ID}/topics/placeId",
            json={"message": place_id}
        )
        status = request.status
        response = {}
        if status != 200: response = await request.json()
        return status, response

async def change_datastore(place_id):
    async with aiohttp.ClientSession(headers={"x-api-key": API_KEY}) as session:
        request = await session.patch(
            f"https://apis.roblox.com/cloud/v2/universes/{HUB_ID}/data-stores/placeId/entries/placeId?allow_missing=true",
            json={"value": str(place_id)}
        )
        status = request.status
        response = {}
        if status != 200: response = await request.json()
        return status, response

async def get_datastore(datastore: str, max_page_size: int = 100, order_by: str = "desc", page_token: str = "") -> dict:
    async with aiohttp.ClientSession(headers={"x-api-key": API_KEY}) as session:
        request = await session.get(
            f"https://apis.roblox.com/ordered-data-stores/v1/universes/{HUB_ID}/orderedDataStores/{datastore}/scopes/global/entries",
            params={
                "max_page_size": max_page_size,
                "order_by": order_by,
                "page_token": page_token
            }
        )
        request.raise_for_status()

        response = await request.json()
        return response

async def get_latest(page_token: str = ""):
    datastore = await get_datastore(datastore="lastJoined", page_token=page_token)

    current = time.time()
    active = 1 if FARMING else 0

    for entry in datastore.get("entries"):
        user_time = int(entry.get("value"))
        limit = current - ACTIVE_THRESHOLD

        if user_time > limit: active += 1
    
    return active

async def get_users(user_ids: list):
    async with aiohttp.ClientSession(cookies=cookies) as session:
        request = await session.post(
            "https://users.roblox.com/v1/users",
            json={"userIds": user_ids, "excludeBannedUsers": False}
        )

        request.raise_for_status()

        response = await request.json()
        return response.get("data")

#    ____     U  ___ u _____        ____   U _____ u  _____    _   _   ____    
# U | __")u    \/"_ \/|_ " _|      / __"| u\| ___"|/ |_ " _|U |"|u| |U|  _"\ u 
#  \|  _ \/    | | | |  | |       <\___ \/  |  _|"     | |   \| |\| |\| |_) |/ 
#   | |_) |.-,_| |_| | /| |\       u___) |  | |___    /| |\   | |_| | |  __/   
#   |____/  \_)-\___/ u |_|U       |____/>> |_____|  u |_|U  <<\___/  |_|      
#  _|| \\_       \\   _// \\_       )(  (__)<<   >>  _// \\_(__) )(   ||>>_    
# (__) (__)     (__) (__) (__)     (__)    (__) (__)(__) (__)   (__) (__)__)   

client = discord.Bot(
    intents=discord.Intents.all(),
    allowed_mentions=discord.AllowedMentions.none(), 
    default_command_integration_types={
        discord.IntegrationType.user_install, 
        discord.IntegrationType.guild_install
    }
)

agc: AsyncioGspreadClient = None
emojis: dict[str: discord.AppEmoji] = None

@tasks.loop(seconds=20)
async def checking_visits():
    global queue
    global ignore
    global requesters

    try:
        if len(queue) < 10 and agc:
            spreadsheet = await agc.open_by_key(SPREADSHEET_ID)
            wip_sheet = await spreadsheet.get_worksheet(5)
            rows = await wip_sheet.get(f'A2:E{max(2, 12-len(queue))}')

            for row in rows:
                place_id = str(row[0].split("/")[-1])
                universe_id = str(row[1])
                game = (place_id, universe_id)
                # print(ignore, queue, game)

                # print(place_id not in ignore)
                # print(game not in queue)

                if place_id not in ignore and game not in queue: queue.append(game)

        if not queue: return

        chopped_queue = queue[:10]
        place_ids = [place_id for place_id, universe_id in chopped_queue]
        universe_ids = [universe_id for place_id, universe_id in chopped_queue]

        universes, places, maturities = await asyncio.gather(*[
            get_universes(universe_ids),
            get_places(place_ids),
            asyncio.gather(*[get_universe_maturity(universe_id) for universe_id in universe_ids]),
        ])

        saved = []

        for i, universe in enumerate(universes):
            #print(universe)
            universe_id = str(universe.get("id"))
            place_id = str(universe.get("rootPlaceId"))
            maturity = maturities[i]
            place = places[i]

            if universe.get("visits") > 1000 or maturity.get("contentMaturity") != "unrated" or not place.get("isPlayable"):
                ignore.append(place_id)
                index = queue.index((place_id, universe_id))
                queue.pop(index)

                url = f"https://www.roblox.com/games/{place_id}"
                saved.append(url)

                requester = requesters.get(universe_id)
                if not requester: continue

                for user_id in requester:
                    if "thread" in str(user_id):
                        thread = await client.fetch_channel(int(user_id.replace("thread", "")))
                        if not thread: continue

                        thread_requests = [temp_requester for temp_requesters in requesters for temp_requester in temp_requesters if "thread" in str(temp_requester)]
                        if len(thread_requests) > 1: continue

                        try:
                            forum: discord.ForumChannel = await client.fetch_channel(PRIORITY_CHANNEL)
                            tags = [tag for tag in thread.applied_tags if tag.id != WIP_TAG and tag.id != FINISHED_TAG]

                            tags.append(forum.get_tag(FINISHED_TAG))

                            await thread.edit(applied_tags=list(set(tags)))
                        except Exception as e: print(e)
                    else:
                        try:
                            user = await client.fetch_user(user_id)
                            if not user: continue

                            await user.send(f"farmed [{universe.get('name')}](<{url}>)")#, joins requested: {JOINS * RATIO}")
                        except Exception as e: print(e)

                requesters[universe_id] = None
        
        if saved:
            await write_queue()
            await write_requesters()

            channel = client.get_channel(SAVED_CHANNEL)
            await channel.send("\n".join(saved))

        if HUB_ID: await change_datastore(json.dumps([place_id for place_id, universe_id in queue[:10]])) #await asyncio.gather(*[post_message(place_id), change_datastore(place_id)])

        #game = discord.Game(name=universe.get("name"))
        #await client.change_presence(status=discord.Status.idle, activity=game)
    except Exception as e:
        traceback.print_exception(type(e), e, e.__traceback__, file=sys.stderr)

async def farm_visits():
    global JOINS
    while True:
        try:
            if not queue or not FARMING: await asyncio.sleep(5); continue

            if queue[0][0]:
                url = f"roblox://placeid={queue[0][0]}"
                if "TERMUX" in os.environ: os.system(f"xdg-open {url}")
                else: webbrowser.open(url)
                JOINS += 1
        except Exception as e: traceback.print_exception(type(e), e, e.__traceback__, file=sys.stderr)
        await asyncio.sleep(DELAY)

async def fetch_emojis():
    global emojis

    emotes = await client.fetch_emojis()
    emojis = {emote.name: f"<:{emote.name}:{emote.id}>" for emote in emotes}
    print(emojis)

def get_creds():
    """Returns the credentials from the service account key file."""
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    return Credentials.from_service_account_file(ACCOUNT_JSON, scopes=scopes)

@client.event
async def on_ready():
    global agc

    if not checking_visits.is_running(): checking_visits.start() 

    asyncio.create_task(farm_visits())
    asyncio.create_task(fetch_emojis())

    agcm = AsyncioGspreadClientManager(get_creds)
    agc = await agcm.authorize()

    print(f"logged in as {client.user.name}")

@client.event
async def on_application_command_error(ctx: discord.ApplicationContext, error: discord.DiscordException):
    try:
        text = f"meow meow something went VERY wrong >~<\n>>> ```{error}```"
        if ctx.interaction.response.is_done(): await ctx.edit(content=text) 
        else: await ctx.respond(text, ephemeral=True)
    except: pass

    traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

#               _   _     _____  U _____ u   ____        _        ____   _____             U  ___ u  _   _    ____     
#      ___     | \ |"|   |_ " _| \| ___"|/U |  _"\ u U  /"\  u U /"___| |_ " _|     ___     \/"_ \/ | \ |"|  / __"| u  
#     |_"_|   <|  \| |>    | |    |  _|"   \| |_) |/  \/ _ \/  \| | u     | |      |_"_|    | | | |<|  \| |><\___ \/   
#      | |    U| |\  |u   /| |\   | |___    |  _ <    / ___ \   | |/__   /| |\      | | .-,_| |_| |U| |\  |u u___) |   
#    U/| |\u   |_| \_|   u |_|U   |_____|   |_| \_\  /_/   \_\   \____| u |_|U    U/| |\u\_)-\___/  |_| \_|  |____/>>  
# .-,_|___|_,-.||   \\,-._// \\_  <<   >>   //   \\_  \\    >>  _// \\  _// \\_.-,_|___|_,-.  \\    ||   \\,-.)(  (__) 
#  \_)-' '-(_/ (_")  (_/(__) (__)(__) (__) (__)  (__)(__)  (__)(__)(__)(__) (__)\_)-' '-(_/  (__)   (_")  (_/(__)      

def whitelist_check(ctx: discord.ApplicationContext):
    if isinstance(ctx.author, discord.Member):
        has_role = discord.utils.get(ctx.author.roles, id=ROLE_ID) is not None
        if has_role or ctx.author.id in WHITELIST:
            return True
    else:
        if ctx.author.id in WHITELIST: return True
    
    return False

def create_spreadsheet_container(header, data, size: int = 10) -> list[ui.Container]:
    if not data: return None #[ui.Container(ui.TextDisplay(content="No data provided."))]

    pages = []
    chunks = [data[i:i + size] for i in range(0, len(data), size)]
    for chunk in chunks:
        lines = [header]
        lines.extend(chunk)

        widths = [max(len(str(item)) for item in col) for col in zip(*[row for row in lines])]

        container_members = []
        message_limit = 3700
        current_length = 0

        header_string = "".join(str(item).ljust(widths[i] + 2) for i, item in enumerate(lines[0]))
        container_members.append(ui.TextDisplay(content=header_string))
        current_length += len(header_string)

        for index, line in enumerate(lines[1:11], 1):
            line_string = "".join(str(item).ljust(widths[i] + 2) for i, item in enumerate(line[:-1]))
            
            if current_length + len(line_string) > message_limit: break
            
            container_members.append(
                ui.Section(
                    ui.TextDisplay(line_string),
                    accessory=ui.Button(label="🔗", url=line[-1], style=discord.ButtonStyle.link),
                )
            )

            current_length += len(line_string) + len("Game link")

        pages.append(ui.Container(*container_members))

    return pages

class CustomGroup:
    def __init__(self, label: str, description: str = "", emoji: discord.Emoji = None, pages: list[list[ui.Container]] = [], default: bool = False):
        self.label = label
        self.description = description
        self.emoji = emoji
        self.pages = pages
        self.default = default
        self._selected = False

class CustomPages(ui.View):
    def __init__(self, pages: list[ui.Container] = None, groups: list[CustomGroup] = None, timeout: int = 200, user: discord.User = None, interaction_callback = None, inf_pages: bool = False):
        super().__init__(timeout=timeout, disable_on_timeout=True)
        self.pages = pages
        self.page = 0
        self.group = 0

        self.groups = groups

        if groups:
            selected = False
            
            for i, group in enumerate(groups):
                if group.default: self.pages = group.pages; self.group = i; self.groups[i]._selected = True; selected = True; break

            if not selected: self.pages = groups[0].pages; self.groups[0]._selected = True

        self.user = user
        self.disabled = False

        self.inf_pages = inf_pages
        self.interaction_callback = interaction_callback

        self.update_view()

    @property
    def len(self):
        return len(self.pages)

    async def on_timeout(self):
        self.disabled = True
        await self.update_page()

    def create_buttons(self):
        container = ui.Container()

        if self.groups:
            selector = self.PageSelect(
                discord.ComponentType.string_select, 
                placeholder="Select your page group",
                required=True, 
                options=[discord.SelectOption(label=group.label, value=str(i), description=group.description, emoji=group.emoji, default=group._selected) for i, group in enumerate(self.groups)],
            )
            container.add_item(selector)

        if self.len != 1 or self.inf_pages:
            buttons = [
                ("⏪", self.first, "", self.page == 0),
                ("◀", self.previous, "", self.page == 0),
                ("", self.indicator, f"{self.page+1}/{self.len}{'' if not self.inf_pages else '..'}", self.len == 1),
                ("▶", self.next, "", self.page == self.len-1 and not self.inf_pages),
                ("⏩", self.last, "", self.page == self.len-1 and not self.inf_pages),
            ]

            for emoji, func, label, disabled in buttons:
                button = ui.Button(emoji=emoji if emoji else None, label=label, disabled=disabled)
                button.callback = func
                container.add_item(button)

        return container if container.items else None

    def update_view(self):
        self.clear_items()

        self.add_item(self.pages[self.page])

        menu = self.create_buttons()
        if menu: self.add_item(menu)

        if self.disabled:
            links = []
            for container in self.children[:self.len-1]:
                for item in container.items:
                    if isinstance(item, ui.Button):
                        if item.url: links.append(item)

            self.disable_all_items(exclusions=links)
    
    async def update_page(self, ctx: discord.Interaction = None):
        self.update_view()

        if ctx: await ctx.edit(view=self)
        elif self.parent and self.parent.message: await self.parent.edit(view=self)
        elif self.message: 
            try: await self.message.edit(view=self)
            except: pass
            
    async def interaction_check(self, ctx: discord.Interaction):
        if self.user and ctx.user.id != self.user.id:
            await ctx.response.send_message("This is not for you!", ephemeral=True)
            return False
        return True

    async def first(self, ctx: discord.Interaction):
        self.page = 0
        if self.interaction_callback: await self.interaction_callback(self, ctx, "first")
        await self.update_page(ctx)

    async def previous(self, ctx: discord.Interaction):
        self.page -= 1
        if self.interaction_callback: await self.interaction_callback(self, ctx, "previous")
        await self.update_page(ctx)

    async def indicator(self, ctx: discord.Interaction):
        self.page = 0
        await ctx.response.send_modal(self.PageModal(view=self, title="Select Page"))

    async def next(self, ctx: discord.Interaction):
        self.page += 1
        if self.interaction_callback: await self.interaction_callback(self, ctx, "next")
        await self.update_page(ctx)

    async def last(self, ctx: discord.Interaction):
        if self.interaction_callback: await self.interaction_callback(self, ctx, "last")
        self.page = self.len-1
        await self.update_page(ctx)

    class PageModal(ui.Modal):
        def __init__(self, view, *args, **kwargs):
            super().__init__(
                ui.InputText(
                    label="Page", 
                    placeholder=f"1-{len(view.pages)}"
                ),
                *args,
                **kwargs,
            )
            self.view = view
        
        async def callback(self, ctx: discord.Interaction):
            page = self.children[0].value
            if not page.isnumeric(): return await ctx.response.defer(invisible=True)
            page = int(page)

            if page < 1 or page > self.view.len: 
                return await ctx.response.defer(invisible=True)

            self.view.page = page-1
            if self.interaction_callback: await self.interaction_callback(self, ctx, "modal")
            await self.view.update_page(ctx)

    class PageSelect(ui.Select):
        def __init__(self, *args, **kwargs):
            super().__init__(
                *args,
                **kwargs,
            )
            #self.view = view
        
        async def callback(self, ctx: discord.Interaction):
            value = int(self.values[0])

            self.view.group = value
            self.view.page = 0
            self.view.pages = self.view.groups[value].pages

            for i, select in enumerate(self.view.groups): self.view.groups[i]._selected = i == value
            if self.view.interaction_callback: await self.view.interaction_callback(self.view, ctx, "select")
            await self.view.update_page(ctx)

async def get_place_ids(content: str):
    url_pattern = r'https?://[^\s|"]+'
    urls = re.findall(url_pattern, content)
    place_ids = []

    for url in urls:
        if "roblox.com/share?code=" in url:
            place_id = await resolve_share(url)
            place_ids.append(str(place_id))
        elif "roblox.com/games/" in url:
            match = re.search(r'\d+', url)
            if match: place_ids.append(str(match.group(0)))

    return list(set(place_ids))

@client.slash_command(name="toggle", description="toggle farm")
@commands.check(whitelist_check)
async def toggle_farm(ctx: discord.ApplicationContext):  
    global FARMING
    
    FARMING = not FARMING
    
    await ctx.respond(f"FARMING = {FARMING}")

@client.slash_command(name="delay", description="set delay")
@commands.check(whitelist_check)
async def set_delay(ctx: discord.ApplicationContext, delay: int = 1.5):  
    global DELAY
    
    DELAY = delay
    
    await ctx.respond(f"DELAY = {delay}")

@client.slash_command(name="load_queue", description="loads queue")
@commands.check(whitelist_check)
async def load_queue(ctx: discord.ApplicationContext, queue_file: discord.Attachment, requesters_file: discord.Attachment):
    await ctx.defer()
       
    global queue
    global requesters

    queue = []
    requesters = {}

    queue_content = await queue_file.read()
    queue_content = queue_content.decode('utf-8')
    
    for line in queue_content.splitlines():
        clear = line.strip()
        splitted = clear.split(",")
        if len(splitted) == 2: queue.append((splitted[0], splitted[1]))

    if requesters_file:
        requesters_content = await requesters_file.read()
        requesters_content = requesters_content.decode('utf-8')
    
        requesters = json.loads(requesters_content)

    await write_queue()
    await write_requesters()

    await ctx.respond("✅", ephemeral=True, delete_after=3)


@client.slash_command(name="purge_queue", description="purge queue")
@commands.check(whitelist_check)
async def purge_queue(ctx: discord.ApplicationContext):
    await ctx.defer()

    global queue
    global requesters
    
    queue_file = discord.File(fp="queue.csv")
    requesters_file = discord.File(fp="requesters.json")
    
    await ctx.respond(files=[queue_file, requesters_file])
    
    queue = []
    requesters = {}
    
    await write_queue()
    await write_requesters()

@client.slash_command(name="queue", description="place queue")
async def list_queue(ctx: discord.ApplicationContext):
    await ctx.defer()

    header = ["`🔳","# ", "Name", "Visits", "Link   `"]
    data = []
    visits_required = 0

    botnet = await get_latest()
    if queue:
        chunks = [queue[i:i + 50] for i in range(0, len(queue), 50)]

        for i_c, chunk in enumerate(chunks):
            universe_ids = [game[1] for game in chunk]
            universes = await get_universes(universe_ids)
            
            data = []
            visits_required = 0

            for i, universe in enumerate(universes, 1):
                data.append(["`🔲", i_c*10+i, universe.get('name'), str(universe.get('visits'))+"`", f"https://www.roblox.com/games/{universe.get('rootPlaceId')}"])
                
                visits_required += max(0, 1000 - universe.get("visits"))

    pages = create_spreadsheet_container(header, data)
    for page in pages:
        page.add_text(f"\ngames in queue: `{len(queue)}`\nvisits required: `{visits_required}`\ncurrent online: `{botnet}`")

    view = CustomPages(pages=pages, user=ctx.author)
    return await ctx.edit(view=view)

async def add_queue_wrap(ctx: discord.ApplicationContext = None, message: discord.Message = None):
    global queue
    global requesters

    if ctx: await ctx.defer()

    place_ids = await get_place_ids(message.content if message else ctx.message.content)

    if place_ids:
        chunks = [place_ids[i:i + 50] for i in range(0, len(place_ids), 50)]

        header = ["`🔳", "Name", "Visits", "# ", "Notes", "Link   `"]
        data = []

        for chunk in chunks:
            places = await get_places(chunk)

            universe_ids = [place.get("universeId") for place in places]

            universes, playabilities, maturities = await asyncio.gather(*[
                get_universes(universe_ids),
                get_universe_playability(universe_ids),
                asyncio.gather(*[get_universe_maturity(universe_id) for universe_id in universe_ids])
            ])

            for i in range(len(places)):
                place = places[i]
                place_id = str(place.get("placeId"))
                
                universe = universes[i]
                universe_id = str(place.get("universeId"))
                
                playability = playabilities[i]
                maturity = maturities[i]
                
                game_name = place.get('name')[:23]
                visits = universe.get("visits")
                
                game_link = f"https://www.roblox.com/games/{place_id}"
                
                if not place.get("isPlayable") and not playability.get("isPlayable"): data.append(["`❌", game_name, visits, "", "privated`", game_link]); continue
                if visits > 1000: data.append(["`❌", game_name, visits, "", "> 1k visits`", game_link]); continue

                game = (place_id, universe_id)

                if game in queue: data.append(["`❌", game_name, visits, "", "already in q`", game_link]); continue
                if maturity.get("contentMaturity") != "unrated": data.append(["`❌", game_name, visits, "", "already rated`", game_link]); continue

                queue.append(game)

                requester_ids = []
                if ctx:
                    requester_ids.append(ctx.author.id)
                if message and message.author.id not in requester_ids:
                    requester_ids.append(message.author.id)
                if isinstance(message.channel, discord.Thread):
                    requester_ids.append(f"thread{message.channel.id}")
                
                requesters[str(place.get("universeId"))] = requester_ids

                data.append(["`✅", game_name, visits, len(queue), "`", game_link])
            
        await write_queue()
        await write_requesters()

        pages = create_spreadsheet_container(header, data)

        paginator = CustomPages(pages=pages, user=ctx.author if ctx else message.author)

        if isinstance(message.channel, discord.Thread):
            thread = message.channel
            forum: discord.ForumChannel = await client.fetch_channel(PRIORITY_CHANNEL)

            tags = [tag for tag in thread.applied_tags if tag.id != FINISHED_TAG and tag.id != WIP_TAG]

            tags.append(forum.get_tag(WIP_TAG))

            await thread.edit(applied_tags=list(set(tags)))

        if ctx: await ctx.edit(view=paginator)
        else: return await message.reply(view=paginator)
    else:
        if ctx: return await ctx.respond("no games found 😔", ephemeral=True, delete_after=3)
        else: return

sort_bies = {"lastJoined": "Last joined", "joins": "Joins"}
sort_keys = [key for key, value in sort_bies.items()]
@client.slash_command()
@discord.option(name="sort_by", input_type=str, choices=[discord.OptionChoice(name=value, value=key) for key, value in sort_bies.items()], default="lastJoined")
async def get_contibutors(ctx: discord.ApplicationContext, sort_by: str):
    await ctx.defer()
    cursors = {key: "" for key, value in sort_bies.items()}

    groups = [
        CustomGroup("Last Joined", description="Sorts leaderboard by last joined", emoji="⏳", pages=[], default=sort_by=="lastJoined"),
        CustomGroup("Joins", description="Sorts leaderboard by joins", emoji="▶", pages=[], default=sort_by=="joins")
    ]

    async def get_pages(sort_by):
        data = await get_datastore(datastore=sort_by, page_token=cursors[sort_by], max_page_size=5)
        print(data)
        cursors[sort_by] = data.get("nextPageToken")
        print(cursors)
        entries = data.get("entries")
        if not entries: return None, await ctx.respond("no data provided 😔", ephemeral=True, delete_after=3)

        user_ids = [entry.get("id") for entry in entries]
        users = await get_users(user_ids)
        print(users)

        header = ["`🔳", "#", "User", sort_bies[sort_by], "Link   `"]
        lines = []

        for i, (entry, user) in enumerate(zip(entries, users), 1):
            lines.append(["`🔲", f"{i}", f'{user.get("displayName")}{" ☑" if user.get("hasVerifiedBadge") else ""} (@{user.get("name")})', f'{entry.get("value")}`' if sort_by == "joins" else f'`<t:{entry.get("value")}:R>', f'https://www.roblox.com/users/{entry.get("id")}/profile'])
        
        pages = create_spreadsheet_container(header, lines)
        return pages, None

    async def interaction_callback(view: CustomPages, ctx: discord.Interaction, action: str):
        #print(emojis['loading'])
        #inter = await ctx.respond(content=f"{emojis['loading']} loading...")

        if action in ["select", "next", "last"]:
            group_id = view.group
            sort_by = sort_keys[group_id]

            pages = []
            while pages != None:
                print(action)
                pages, _ = await get_pages(sort_by)
                view.groups[group_id].pages.extend(pages)
                if not action == "last": break

            print(cursors)
            print(sort_by)
            if cursors[sort_by] == None: view.inf_pages = False

        #await inter.delete_original_response()

    pages, _ = await get_pages(sort_by)
    groups[sort_keys.index(sort_by)].pages.extend(pages)
    for group in groups:
        print(group.pages)

    paginator = CustomPages(groups=groups, interaction_callback=interaction_callback, user=ctx.author, inf_pages=cursors[sort_by] != None)
    print(paginator)
    return await ctx.respond(view=paginator)

@client.message_command(name="add to queue")
async def add_queue(ctx: discord.ApplicationContext, message: discord.Message):
    return await add_queue_wrap(ctx=ctx, message=message)

@client.message_command(name="place info")
async def place_info(ctx: discord.ApplicationContext, message: discord.Message):
    await ctx.defer()

    place_ids = await get_place_ids(message.content)

    header = ["`Name", "Visits", "Badges", "Link   `"]
    data = []
    
    chunks = [place_ids[i:i + 50] for i in range(0, len(place_ids), 50)]
    for chunk in chunks:
        places = await get_places(chunk)
        universe_ids = [place.get("universeId") for place in places]

        universes = await get_universes(universe_ids)

        async def universe_badges(universe):
            universe_id = universe.get("id")

            badges = await get_badges(universe_id)
            legacies = get_legacies(badges)
            
            return [f"`{universe.get('name')}", universe.get("visits"), f"{len(legacies)}`", f"https://www.roblox.com/games/{universe.get('rootPlaceId')}"]

        results = await asyncio.gather(*[universe_badges(universe) for universe in universes])
        data.extend(results)

    pages = create_spreadsheet_container(header, data)

    paginator = CustomPages(pages=pages, user=ctx.author)
    return await ctx.respond(view=paginator)

@client.event
async def on_message(message: discord.Message):
    if (isinstance(message.channel, discord.TextChannel) and message.channel.id == PRIORITY_CHANNEL) or (isinstance(message.channel, discord.Thread) and message.channel.parent_id == PRIORITY_CHANNEL):
        if message.author.id == client.user.id: return
        return await add_queue_wrap(message=message)
    elif message.channel.id == SAVED_CHANNEL:
        global ignore
        place_ids = await get_place_ids(message.content)
        if not place_ids: return

        places = await get_places(place_ids)

        universe_ids = [place.get("universeId") for place in places]
        
        universes, maturities, badges = await asyncio.gather(*[
            get_universes(universe_ids),
            asyncio.gather(*[get_universe_maturity(universe_id) for universe_id in universe_ids]), 
            asyncio.gather(*[get_badges(universe_id) for universe_id in universe_ids])
        ])

        spreadsheet = await agc.open_by_key(SPREADSHEET_ID)
        wip_sheet = await spreadsheet.get_worksheet(5)
        done_sheet = await spreadsheet.get_worksheet(6)

        urls = [f"https://www.roblox.com/games/{place_id}" for place_id in place_ids]
        wips = await asyncio.gather(*[wip_sheet.find(url) for url in urls])
        dones = await asyncio.gather(*[done_sheet.find(url) for url in urls])

        header = ["`🔲", "Name", "Note", "Link   `"]
        data = []
        cells: list[gspread.Cell] = []
        dups: list[gspread.Cell] = []
        deleting = True
        
        for i, universe in enumerate(universes, 0):
            #universe_id = universe.get("id")
            place_id = str(universe.get("rootPlaceId"))

            url = urls[i] #f"https://www.roblox.com/games/{place_id}"

            name = universe.get("name")
            place = places[i]
            visits = universe.get("visits")
            maturity = maturities[i]
            legacies = len(get_legacies(badges[i]))

            cell = wips[i]
            isdonebefore = dones[i]

            if cell and not place.get("isPlayable"): data.append(["`⚠", name, "private`", url]); ignore.append(place_id); continue
            if visits < 1000 and maturity.get("contentMaturity") == "unrated": data.append(["`❌", name, "<1k visits`", url]); continue
            if isdonebefore and not cell: data.append(["`❌", name, "in table`", url]); ignore.append(place_id); continue
            if legacies == 0: data.append(["`❌", name, "no legacies`", url]); ignore.append(place_id); continue
            if cell and isdonebefore: data.append(["`⚠", name, "duplicate`", url]); dups.append(url); continue
            if not cell: data.append(["`⚠", name, "not in table`", url]); ignore.append(place_id); deleting = False; continue
            
            cells.append(url)
            data.append(["`✅", name, "`", url])
        
        async def move_cell(url: gspread.Cell, delete: bool = False):
            row = await wip_sheet.find(url)
            if not row: print(f"{url} not in wip"); return

            if not delete:
                row_data = await wip_sheet.row_values(row.row)
                print(row_data)
                await done_sheet.append_row(row_data, value_input_option='USER_ENTERED')
            await wip_sheet.delete_rows(row.row)

        for url in cells: await move_cell(url)
        for url in dups: await move_cell(url, delete=True)

        #await asyncio.gather(*[move_cell(cell) for cell in cells])
        #await asyncio.gather(*[wip_sheet.delete_rows(dupe.row) for dupe in dups])

        pages = create_spreadsheet_container(header, data)
        
        paginator = CustomPages(pages)
        
        try:
            await message.reply(view=paginator, delete_after=20 if deleting else None)
            await message.delete(reason=f"moved to spreadsheet")
        except Exception as e:
            print(f"{e}")

if __name__ == "__main__": client.run(BOT_TOKEN)