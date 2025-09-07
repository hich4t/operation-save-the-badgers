import webbrowser, threading, psutil, time
from cfg import *

roblox = "applicationframehost.exe"
msedge = "msedge.exe"

def killprocess(name):
    for proc in psutil.process_iter(['name']):
        if name.lower() in proc.info['name'].lower():
            try: proc.terminate()
            except: pass

def launch(index: int):
    while True:
        webbrowser.open(f"roblox-uwp{index}://navigation/share_links?{PRIVATE_SERVERS[index-1]}")
        time.sleep(8)

def joiner():
    threads = []

    for i in range(START_INDEX, END_INDEX):
        thread = threading.Thread(target=launch, args=(i,))
        threads.append(thread)
        thread.start()

    for t in threads:
        t.join()

def killedge():
    while True:
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