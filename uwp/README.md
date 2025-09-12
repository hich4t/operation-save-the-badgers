# /uwp
Collection of useful scripts and macros.
```
.
└── operation-save-the-badgers/
    └── uwp/                    <- We are here
        ├── cfg.py
        ├── multiUWP.bat
        ├── multiUWP.ps1
        ├── uwpantiafk.ahk
        ├── uwpkill.py
        ├── uwplauncher.py
        └── uwpsingle.py
```

[![Download](https://img.shields.io/badge/DOWNLOAD-0077B6?style=for-the-badge&labelColor=black&color=0077B6&logo=github&logoColor=white)](https://github.com/hich4t/operation-save-the-badgers/releases/latest)

## [cfg.py](/cfg.py)
Configuration for [`uwplauncher.py`](#uwplauncherpy) and [`uwpsingle.py`](#uwpsinglepy)
```py
# Place ID for single instance (uwpsingle.py)
# IDs for popular hubs:
# 137685386779012
# 14553405542
# 107989209286390

PLACE_ID = 0

# Private Servers for multiple instances (uwplauncher.py)
PRIVATE_SERVERS = [
    "code=&type=server",
    "code=&type=server",
]

# Delay in seconds
DELAY = 6

# Roblox UWP Protocol Indexes
START_INDEX = 1
END_INDEX = 4

# Kills Edge
KILL_EDGE = True
```

## [multiUWP.bat](/multiUWP.bat)
> [!WARNING]  
> ⚠ Make sure to have "Developer Mode" turned on before usage.  
> ![Image](https://github.com/user-attachments/assets/31c83a32-e629-4a86-b714-ad8de1b08095)

Install multiple instances of Roblox from Microsoft Store  
Launches [`multiUWP.ps1`](#multiUWPps1)

## [multiUWP.ps1](/multiUWP.ps1)
Powershell script by [agauo](https://www.reddit.com/user/agauo/)  
Credits to [patyk73](https://github.com/Patrosi73) for method  
Modified by [ChatGPT](https://chat.openai.com/) to include protocol modification and ClientAppSettings.json (FFlags)  

## [uwpantiafk.ahk](/uwpantiafk.ahk)
> [!NOTE]  
> Make sure to have [`AutoHotKey`](https://www.autohotkey.com/) installed before usage.

Modified version of [AstrouxTheSecond/Anti-AFK](https://github.com/AstrouxTheSecond/Anti-AFK) to include `RobloxPlayerBeta.exe` and `ApplicationFrameHost.exe` (Roblox from Microsoft Store)

## [uwpkill.py](/uwpkill.py)
> [!NOTE]  
> Make sure to have [`Python`](https://www.python.org/) and [`psutil`](https://pypi.org/project/psutil/) installed before usage.  
> ```pip install psutil```  

Kills all instances of `ApplicationFrameHost.exe` (Roblox from Microsoft Store)

## [uwplauncher.py](/uwplauncher.py)
> [!NOTE]  
> Make sure to have [`Python`](https://www.python.org/) and [`psutil`](https://pypi.org/project/psutil/) installed and [configured](#cfgpy) before usage.  
> ```pip install psutil```

Launches multiple instances of Roblox from Microsoft Store using [`roblox://` protocol](https://github.com/bloxstraplabs/bloxstrap/wiki/A-deep-dive-on-how-the-Roblox-bootstrapper-works#protocoluri-handling)

## [uwpsingle.py](/uwpsingle.py)
> [!NOTE]  
> Make sure to have [`Python`](https://www.python.org/) installed and [configured](#cfgpy) before usage.  

Launches single instance of Roblox from Microsoft Store using [`roblox://` protocol](https://github.com/bloxstraplabs/bloxstrap/wiki/A-deep-dive-on-how-the-Roblox-bootstrapper-works#protocoluri-handling)


> [!TIP]  
> Use [badgers-macro](https://github.com/actuallyasmartname/badgers-macro) instead!
