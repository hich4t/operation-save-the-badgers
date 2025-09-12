import webbrowser, threading, psutil, time
from cfg import *

roblox = "applicationframehost.exe"
msedge = "msedge.exe"

def killprocess(name):
    for proc in psutil.process_iter(['name']):
        if name.lower() in proc.info['name'].lower():
            try: proc.terminate()
            except: pass

def launch(roblox_index: int, ps_index):
    while True:
        webbrowser.open(f"roblox-uwp{roblox_index}://navigation/share_links?{PRIVATE_SERVERS[ps_index]}")
        time.sleep(DELAY)

def joiner():
    threads = []

    for ps_index, roblox_index in enumerate(range(START_INDEX, END_INDEX+1)):
        thread = threading.Thread(target=launch, args=(roblox_index, ps_index,))
        threads.append(thread)
        thread.start()

    for t in threads:
        t.join()

def killedge():
    while KILL_EDGE:
        killprocess(msedge)
        time.sleep(DELAY)

def main():
    threads = []

    for func in (joiner, killedge):
        thread = threading.Thread(target=func)
        threads.append(thread)
        thread.start()

    for t in threads:
        t.join()

if __name__ == "__main__": main()