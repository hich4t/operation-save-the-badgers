import webbrowser, time, os
from cfg import *

isTermux = "TERMUX" in os.environ

url = f"roblox://placeid={PLACE_ID}"

while True:
    if isTermux: os.system(f"xdg-open {url}")
    else: webbrowser.open(url)
    time.sleep(DELAY)