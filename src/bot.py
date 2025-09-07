#                __  __    ____    U  ___ u   ____      _____   ____     
#      ___     U|' \/ '|uU|  _"\ u  \/"_ \/U |  _"\ u  |_ " _| / __"| u  
#     |_"_|    \| |\/| |/\| |_) |/  | | | | \| |_) |/    | |  <\___ \/   
#      | |      | |  | |  |  __/.-,_| |_| |  |  _ <     /| |\  u___) |   
#    U/| |\u    |_|  |_|  |_|    \_)-\___/   |_| \_\   u |_|U  |____/>>  
# .-,_|___|_,-.<<,-,,-.   ||>>_       \\     //   \\_  _// \\_  )(  (__) 
#  \_)-' '-(_/  (./  \.) (__)__)     (__)   (__)  (__)(__) (__)(__)      

import traceback, discord, asyncio, aiohttp, aiofiles, gspread, json, time, sys, re, os

from discord.ext import commands, tasks
import discord.ui as ui

from gspread_asyncio import AsyncioGspreadClientManager, AsyncioGspreadClient
from google.oauth2.service_account import Credentials

from cfg import *

#    _       U  ___ u    _      ____         ____     _____      _       _____  U _____ u 
#   |"|       \/"_ \/U  /"\  u |  _"\       / __"| u |_ " _| U  /"\  u  |_ " _| \| ___"|/ 
# U | | u     | | | | \/ _ \/ /| | | |     <\___ \/    | |    \/ _ \/     | |    |  _|"   
#  \| |/__.-,_| |_| | / ___ \ U| |_| |\     u___) |   /| |\   / ___ \    /| |\   | |___   
#   |_____|\_)-\___/ /_/   \_\ |____/ u     |____/>> u |_|U  /_/   \_\  u |_|U   |_____|  
#   //  \\      \\    \\    >>  |||_         )(  (__)_// \\_  \\    >>  _// \\_  <<   >>  
#  (_")("_)    (__)  (__)  (__)(__)_)       (__)    (__) (__)(__)  (__)(__) (__)(__) (__) 

if not os.path.exists("queue.csv"): 
    with open("queue.csv", "w") as file:
        file.write("\n")

if not os.path.exists("requesters.json"): 
    with open("requesters.json", "w") as file:
        file.write("{}")

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

async def get_universes(session: aiohttp.ClientSession, universes: list):
    request = await session.get(f"https://games.roblox.com/v1/games?universeIds={','.join(map(str, universes))}")
    request.raise_for_status()
    response = await request.json()
    return response.get("data")

async def get_universe_playability(session: aiohttp.ClientSession, universes: list):
    request = await session.get(f"https://games.roblox.com/v1/games/multiget-playability-status?universeIds={','.join(map(str, universes))}")
    request.raise_for_status()
    response = await request.json()
    return response

async def get_universe_maturity(session: aiohttp.ClientSession, universe_id):
    request = await session.post(
        "https://apis.roblox.com/experience-guidelines-api/experience-guidelines/get-age-recommendation",
        json={"universeId": str(universe_id)}    
    )
    request.raise_for_status()
    response = await request.json()
    return response.get("ageRecommendationDetails").get("summary").get("ageRecommendation")

async def get_places(session: aiohttp.ClientSession, places: list):
    params = "&".join([f"placeIds={place}" for place in places])
    request = await session.get(f"https://games.roblox.com/v1/games/multiget-place-details?{params}")
    request.raise_for_status()
    response = await request.json()
    return response

async def get_badges(session: aiohttp.ClientSession, universe_id):
    badges = []
    cursor = ""

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

async def resolve_share(session: aiohttp.ClientSession, url: str):
    request = await session.get(url)
    request.raise_for_status()
    html_content = await request.text()

    return html_content.split('''<meta name="roblox:start_place_id" content="''')[1].split('"')[0]

async def post_message(session: aiohttp.ClientSession, place_id):
    request = await session.post(
        f"https://apis.roblox.com/messaging-service/v1/universes/{HUB_ID}/topics/placeId",
        json={"message": place_id},
        headers={"x-api-key": API_KEY}
    )
    status = request.status
    response = {}
    if status != 200: response = await request.json()
    return status, response

async def change_datastore(session: aiohttp.ClientSession, place_id):
    request = await session.patch(
        f"https://apis.roblox.com/cloud/v2/universes/{HUB_ID}/data-stores/placeId/entries/placeId?allow_missing=true",
        json={"value": str(place_id)},
        headers={"x-api-key": API_KEY}
    )
    status = request.status
    response = {}
    if status != 200: response = await request.json()
    return status, response

async def get_latest(session: aiohttp.ClientSession):
    request = await session.get(
        f"https://apis.roblox.com/ordered-data-stores/v1/universes/{HUB_ID}/orderedDataStores/lastJoined/scopes/global/entries",
        params={"max_page_size": 10},
        headers={"x-api-key": API_KEY}
    )
    request.raise_for_status()

    response = await request.json()

    current = time.time()
    active = 1 if FARMING else 0
    for entry in response.get("entries"):
        if int(entry.get("value")) > current - ACTIVE_THRESHOLD: active += 1
    
    return active

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
session: aiohttp.ClientSession = None
agc: AsyncioGspreadClient = None

@tasks.loop(seconds=20)
async def checking_visits():
    global queue

    try:
        if not queue and agc: 
            spreadsheet = await agc.open_by_key(SPREADSHEET_ID)
            wip_sheet = await spreadsheet.get_worksheet(0)
            row = await wip_sheet.get(f'A20:E20')

            row = row[0]
            place_id = str(row[0].split("/")[-1])
            universe_id = str(row[1])
            queue.append((place_id, universe_id))
        
        if not queue: return
        universes = await get_universes(session, [queue[0][1]])

        universe = universes[0]
        universe_id = str(queue[0][1])
        place_id = str(queue[0][0])
        
        maturity = await get_universe_maturity(session, universe_id)

        if universe.get("visits") > 1000 or maturity.get("contentMaturity") != "unrated":
            queue.pop(0)

            await write_queue()
            await write_requesters()

            channel = client.get_channel(SAVED_CHANNEL)
            await channel.send(f"https://www.roblox.com/games/{place_id}")

            requester = requesters.get(universe_id)
            if requester:
                for user_id in requester:
                    try:
                        user = await client.fetch_user(user_id)

                        await user.send(f"farmed [{universe.get('name')}](<https://www.roblox.com/games/{universe.get('rootPlaceId')}>)")#, joins requested: {JOINS * RATIO}")
                    except Exception as e: print(e)

                requesters[universe_id] = None

            return await client.change_presence(status=discord.Status.idle)
        else:
            if HUB_ID: await asyncio.gather(*[post_message(session, place_id), change_datastore(session, place_id)])

        game = discord.Game(name=universe.get("name"))
        await client.change_presence(status=discord.Status.idle, activity=game)
    except Exception as e:
        traceback.print_exception(type(e), e, e.__traceback__, file=sys.stderr)

async def farm_visits():
    global JOINS
    while True:
        if not queue or not FARMING:
            await asyncio.sleep(5)
            continue

        if queue[0][0]: os.system(f"{FUNC} roblox://placeid={queue[0][0]}"); JOINS += 1
        await asyncio.sleep(DELAY)

def get_creds():
    """Returns the credentials from the service account key file."""
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    return Credentials.from_service_account_file(ACCOUNT_JSON, scopes=scopes)

@client.event
async def on_ready():
    global session
    global agc

    session = aiohttp.ClientSession(cookies={".ROBLOSECURITY": ROBLOSECURITY})

    checking_visits.start() 
    client.loop.create_task(farm_visits())

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

def create_spreadsheet_container(data):
    if not data: return ui.Container()

    widths = [max(len(str(item)) for item in col) for col in zip(*[row for row in data])]

    container_members = []
    message_limit = 3700
    current_length = 0

    header_string = "".join(str(item).ljust(widths[i] + 2) for i, item in enumerate(data[0]))
    container_members.append(ui.TextDisplay(content=header_string))
    current_length += len(header_string)

    for index, line in enumerate(data[1:11], 1):
        line_string = "".join(str(item).ljust(widths[i] + 2) for i, item in enumerate(line[:-1]))
        
        if current_length + len(line_string) > message_limit: break
        
        container_members.append(
            ui.Section(
                ui.TextDisplay(line_string),
                accessory=ui.Button(label="🔗", url=line[-1], style=discord.ButtonStyle.link),
            )
        )

        current_length += len(line_string) + len("Game link")

    container = ui.Container(*container_members)
    return container

class CustomPages(ui.View):
    def __init__(self, pages: list[ui.Container], timeout: int = 200, user: discord.User = None):
        super().__init__(timeout=timeout, disable_on_timeout=True)
        self.pages = pages

        self.len = len(self.pages)
        self.page = 0
        self.user = user
        self.disabled = False

        self.update_view()

    async def on_timeout(self):
        self.disabled = True
        await self.update_page()

    def create_buttons(self):
        container = ui.Container()

        buttons = [
            ("⏪", self.first, "", self.page == 0),
            ("◀", self.previous, "", self.page == 0),
            ("", self.indicator, f"{self.page+1}/{self.len}", self.len == 1),
            ("▶", self.next, "", self.page == self.len-1),
            ("⏩", self.last, "", self.page == self.len-1),
        ]

        for emoji, func, label, disabled in buttons:
            button = ui.Button(emoji=emoji if emoji else None, label=label, disabled=disabled)
            button.callback = func
            container.add_item(button)

        return container

    def update_view(self):
        self.clear_items()

        self.add_item(self.pages[self.page])
        if self.len != 1: self.add_item(self.create_buttons())

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
            
    async def interaction_check(self, ctx: discord.Interaction):
        if self.user and ctx.user.id != self.user.id:
            await ctx.response.send_message("This is not for you!", ephemeral=True)
            return False
        return True

    async def first(self, ctx: discord.Interaction):
        self.page = 0
        await self.update_page(ctx)

    async def previous(self, ctx: discord.Interaction):
        self.page -= 1
        await self.update_page(ctx)

    async def indicator(self, ctx: discord.Interaction):
        self.page = 0
        await ctx.response.send_modal(self.PageModal(view=self, title="Select Page"))

    async def next(self, ctx: discord.Interaction):
        self.page += 1
        await self.update_page(ctx)

    async def last(self, ctx: discord.Interaction):
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
            await self.view.update_page(ctx)

async def get_place_ids(content: str):
    url_pattern = r'https?://[^\s|"]+'
    urls = re.findall(url_pattern, content)
    place_ids = []

    for url in urls:
        if "roblox.com/share?code=" in url:
            place_id = await resolve_share(session, url)
            place_ids.append(str(place_id))
        elif "roblox.com/games/" in url:
            match = re.search(r'\d+', url)
            if match: place_ids.append(str(match.group(0)))

    return place_ids

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

    data = [["`🔳","# ", "Name", "Visits", "Link   `"]]
    visits_required = 0

    pages = []

    if queue:
        chunks = [queue[i:i + 10] for i in range(0, len(queue), 10)]
        botnet = await get_latest(session)

        for i_c, chunk in enumerate(chunks):
            universe_ids = [game[1] for game in chunk]
            universes = await get_universes(session, universe_ids)
            
            data = [["`🔳","# ", "Name", "Visits", "Link   `"]]
            visits_required = 0

            for i, universe in enumerate(universes, 1):
                data.append(["`🔲", i_c*10+i, universe.get('name'), str(universe.get('visits'))+"`", f"https://www.roblox.com/games/{universe.get('rootPlaceId')}"])
                
                visits_required += max(0, 1000 - universe.get("visits"))

            container = create_spreadsheet_container(data)
            container.add_text(f"\ngames in queue: `{len(queue)}`\nvisits required: `{visits_required}`\ncurrent online: `{botnet}`")

            pages.append(container)
    
    if not pages: pages = [create_spreadsheet_container(data)]
    view = CustomPages(pages=pages, user=ctx.author)
    return await ctx.edit(view=view)

async def add_queue_wrap(ctx: discord.ApplicationContext = None, message: discord.Message = ""):
    global queue
    global requesters

    if ctx: await ctx.defer()

    place_ids = await get_place_ids(message.content if message else ctx.message.content)

    if place_ids:
        chunks = [place_ids[i:i + 50] for i in range(0, len(place_ids), 50)]

        header = ["`🔳", "Name", "Visits", "# ", "Notes", "Link   `"]
        data = []

        for chunk in chunks:
            places = await get_places(session, chunk)

            universe_ids = [place.get("universeId") for place in places]

            universes = await get_universes(session, universe_ids)
            playabilities = await get_universe_playability(session, universe_ids)
            maturities = await asyncio.gather(*[get_universe_maturity(session, universe_id) for universe_id in universe_ids])

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
                
                if visits > 1000: data.append(["`❌", game_name, visits, "", "> 1k visits`", game_link]); continue
                if not place.get("isPlayable") and not playability.get("isPlayable"): data.append(["`❌", game_name, visits, "", "privated`", game_link]); continue

                game = (place_id, universe_id)

                if game in queue: data.append(["`❌", game_name, visits, "", "already in q`", game_link]); continue
                if maturity.get("contentMaturity") != "unrated": data.append(["`❌", game_name, visits, "", "already rated`", game_link]); continue

                queue.append(game)

                requester_ids = []
                if ctx:
                    requester_ids.append(ctx.author.id)
                if message and message.author.id not in requester_ids:
                    requester_ids.append(message.author.id)
                requesters[str(place.get("universeId"))] = requester_ids

                data.append(["`✅", game_name, visits, len(queue), "`", game_link])
            
        await write_queue()
        await write_requesters()

        pages = []
        chunks = [data[i:i + 10] for i in range(0, len(data), 10)]

        for chunk in chunks:
            lines = [header]
            lines.extend(chunk)

            pages.append(create_spreadsheet_container(lines))

        paginator = CustomPages(pages=pages, user=ctx.author if ctx else message.author)
        if ctx: await ctx.edit(view=paginator)
        else: return await message.reply(view=paginator)
    else:
        if ctx: return await ctx.respond("no games found 😔", ephemeral=True, delete_after=3)
        else: return await message.reply("no games found 😔", delete_after=3)

@client.message_command(name="add to queue")
async def add_queue(ctx: discord.ApplicationContext, message: discord.Message):
    return await add_queue_wrap(ctx=ctx, message=message)

@client.message_command(name="place info")
async def place_info(ctx: discord.ApplicationContext, message: discord.Message):
    await ctx.defer()

    place_ids = await get_place_ids(message.content)

    header = ["`🔳", "Name", "Visits", "Badges", "Link   `"]
    data = []
    
    chunks = [place_ids[i:i + 50] for i in range(0, len(place_ids), 50)]
    for chunk in chunks:
        places = await get_places(session, chunk)
        universe_ids = [place.get("universeId") for place in places]

        universes = await get_universes(session, universe_ids)

        async def universe_badges(universe):
            universe_id = universe.get("id")

            badges = await get_badges(session, universe_id)
            legacies = get_legacies(badges)
            
            return ["`   ", universe.get("name"), universe.get("visits"), len(legacies)+"`", f"https://www.roblox.com/games/{universe.get('rootPlaceId')}"]

        results = await asyncio.gather(*[universe_badges(universe) for universe in universes])
        data.extend(results)

    chunks = [data[i:i + 10] for i in range(0, len(data), 10)]
    pages = []
    for chunk in chunks:
        lines = [header]
        lines.extend(chunk)

        pages.append(create_spreadsheet_container(lines))

    paginator = CustomPages(pages=pages, user=ctx.author)
    return await ctx.respond(view=paginator)

@client.event
async def on_message(message: discord.Message):
    if (isinstance(message.channel, discord.TextChannel) and message.channel.id == PRIORITY_CHANNEL) or (isinstance(message.channel, discord.Thread) and message.channel.parent_id == PRIORITY_CHANNEL):
        if message.author.id == client.user.id: return
        return await add_queue_wrap(message=message)
    elif message.channel.id == SAVED_CHANNEL:
        place_ids = await get_place_ids(message.content)
        if not place_ids: return

        places = await get_places(session, place_ids)

        universe_ids = [place.get("universeId") for place in places]
        universes = await get_universes(session, universe_ids)

        spreadsheet = await agc.open_by_key(SPREADSHEET_ID)
        wip_sheet = await spreadsheet.get_worksheet(0)
        done_sheet = await spreadsheet.get_worksheet(1)

        response = await message.reply(f"processing 0/{len(places)}")

        for i, universe in enumerate(universes, 0):
            url = f"https://www.roblox.com/games/{universe.get('rootPlaceId')}"

            visits = universe.get("visits")
            maturity = await get_universe_maturity(session, universe.get("id"))

            if visits < 1000 and maturity.get("contentMaturity") == "unrated": await message.reply(f"{universe.get('rootPlaceId')}/{universe.get('name')} has not reached 1k visits yet", delete_after=3); continue

            cell = await wip_sheet.find(url)
            isdonebefore = await done_sheet.find(url)
            if isdonebefore: await message.reply(f"{universe.get('rootPlaceId')}/{universe.get('name')} is done in spreadsheet already", delete_after=3); continue

            if cell:
                row_index = cell.row

                row_data = await wip_sheet.row_values(row_index)
                await done_sheet.append_row(row_data)
                await wip_sheet.delete_rows(row_index)
            else:
                badges = await get_badges(session, universe.get("id"))
                legacies = get_legacies(badges)

                await done_sheet.append_row([url, universe.get("id"), len(legacies), visits])

            await response.edit(content=f"processing {i}/{len(places)}")
        
        await message.delete(reason=f"moved to spreadsheet")
        await response.delete()

client.run(BOT_TOKEN)