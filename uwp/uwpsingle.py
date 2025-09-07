import os, time
from cfg import *

FUNC = "start" if os.name == "nt" else "xdg-open"

while True:
    os.system(f"{FUNC} roblox://placeid={PLACE_ID}")
    time.sleep(DELAY)