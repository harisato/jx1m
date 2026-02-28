# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

JX1M (Võ Lâm Truyền Kỳ Mobile) is a mobile MMORPG built with a C# game server and a Unity client. The project is a rewrite of Võ Lâm Truyền Kỳ 1 for mobile devices. The codebase is primarily in Vietnamese.

## Repository Structure

```
jx1m/
├── server/
│   ├── src/              # Server source code (C# .NET Framework)
│   │   ├── GameServer/   # Main game server (KTGameServer)
│   │   ├── GameDBServer/ # Database proxy server (MySQL)
│   │   ├── LogDBServer/  # Logging database server
│   │   └── WEB/          # Web services (ASP.NET - SDK auth, server list, CDN)
│   ├── bin/              # Compiled server binaries and runtime configs
│   │   ├── GameServer/   # Game server executable + configs + Lua scripts
│   │   ├── GameDBServer/ # DB server executable
│   │   └── LogDBServer/  # Log server executable
│   └── db/               # Database files (gamedb.sql for MySQL, KiemTheDb.mdf for MSSQL)
├── client/
│   ├── src/              # Unity project root (Unity 2021.3.30f1)
│   │   ├── Assets/       # Game assets, scripts, scenes
│   │   ├── ProjectSettings/
│   │   └── Packages/
│   └── res/              # External game resources (sprites, animations, UI assets)
└── _/                    # Screenshot images for README
```

## Server Architecture

The server consists of three interconnected processes plus a web layer:

- **GameServer** (`server/src/GameServer/KTGameServer/GameServer/`) — Main game logic server. Entry point: `Program.cs`. Listens on TCP port 3001 by default. Uses MoonSharp (Lua) for scripting game logic (AI, NPCs, items, activities).
- **GameDBServer** (`server/src/GameServer/KTGameServer/KF.CenterServer.Remoting/` and `server/src/GameDBServer/`) — Database proxy between GameServer and MySQL. Listens on port 23001. Handles all persistent data operations.
- **LogDBServer** (`server/src/LogDBServer/`) — Logging database server on port 43001.
- **WEB** (`server/src/WEB/`) — ASP.NET web services for authentication (LoginSDK, RegisterSDK), server lists, gift codes, and payment.
- **Tmsk.Contract** (`server/src/GameServer/KTGameServer/Tmsk.Contract/`) — Shared interfaces, constants, and data contracts between server components.

### Server Key Subsystems

| Directory (under `GameServer/`) | Purpose |
|---|---|
| `VLTK/Network/KT_TCPHandler*.cs` | TCP protocol handlers (split by feature: Chat, Equip, Skill, Pet, Guild, etc.) |
| `VLTK/Core/` | Core game entities: Player, Monster, Skill, Buff, Pet, NPC, Item, Bot, Shop, Task, Trap |
| `VLTK/Logic/` | Game logic managers, global service manager |
| `VLTK/Entities/` | Entity data models (Player, Skill, Buff, Faction, Pet, etc.) |
| `VLTK/Activity/` | Activity/event systems (LuckyCircle, X2Exp, CardMonth, SevenDayLogin, etc.) |
| `VLTK/CopySceneEvents/` | Instanced dungeon events (MiJing, DynamicArena, ShenMiBaoKu, etc.) |
| `VLTK/GameEvents/` | World events |
| `VLTK/LuaSystem/` | Lua scripting bridge (KTLuaEnvironment) |
| `VLTK/GameDbController/` | Database command pool and queries |
| `VLTK/Utilities/` | Algorithms, crypto, timers, math |
| `Logic/` | GameManager, GameConfig, server events, sale system |
| `Server/` | TCP session management, command dispatch, cache |
| `TCPSOCKET/` | Low-level socket implementation (async event args, buffer management) |
| `Data/` | Protocol data structures for send/receive |
| `Protocol/` | Protocol definitions |

### Server Configuration Files (in `server/bin/GameServer/`)

- `AppConfig.xml` — Server connection settings (ports, DB server address, Lua config)
- `ServerConfig.xml` — Game tuning (exp rates, CCU limits, monster AI, threading, captcha)
- `MapConfig.xml` — Map definitions
- `GMList.xml` — GM account list
- `Config/` — Game data configs (items, skills, monsters, etc.)
- `LuaScripts/` — Lua game scripts (AI, NPC, items, activities, copy scenes)

### Server Database

- MySQL: `gamedb.sql` for game data, `logdb` for logging
- MSSQL: `KiemTheDb.mdf`/`.ldf` (legacy, can be attached with `restore.txt` instructions)
- Database credentials in AppConfig.xml are encrypted

## Client Architecture

Unity 2021.3.30f1 project. Single scene: `Assets/Scenes/MainGame.unity`.

### Client Key Subsystems

All game scripts are under `Assets/Scripts/FS/`:

| Directory | Purpose |
|---|---|
| `MainGame.cs` | Game entry point — singleton managing lifecycle, resource loading, frame rate |
| `GameEngine/Scene/GScene*.cs` | Scene management (loading, sprites, monsters, NPCs, pets, pathfinding, input) |
| `GameEngine/Sprite/GSprite*.cs` | Base sprite entity with actions, buffs, movement, UI |
| `GameEngine/Network/` | TCP client, session, protocol handler, ping |
| `GameEngine/Logic/` | Global settings, constants, enumerations, path utilities |
| `GameEngine/TimerManager/` | Dispatcher timer system |
| `VLTK/Control/` | Component controllers: Character, Monster, Bullet, Item, Effect, Map, Skill |
| `VLTK/Logic/PlayZone/` | Main gameplay controller (90+ partial class files split by feature) |
| `VLTK/Logic/AutoFight/` | Auto-combat system (targeting, buffs, pets, medicine, pickup, sell) |
| `VLTK/Logic/Global/KTGlobal*.cs` | Central utilities split by domain (audio, chat, items, maps, skills, UI) |
| `VLTK/Network/KT_TCPHandler*.cs` | Client-side protocol handlers (mirror server handlers) |
| `VLTK/Network/Data/` | Network data structures (100+ files for all protocol messages) |
| `VLTK/UI/` | UI screens: Login, ServerSelect, Loading, Main gameplay panels (299 files) |
| `VLTK/Entities/Config/` | XML config entity parsers (monsters, items, skills, buffs, maps, pets, etc.) |
| `VLTK/Loader/` | Resource loading system (per-entity-type loaders, download manager, version checker) |
| `VLTK/Factory/` | Object creation, animation management, object pooling, 2D rendering |
| `VLTK/Utilities/` | Pathfinding (A*, Dijkstra), crypto, timers, Unity components |
| `Server/Data/` | Server data classes (RoleData, MonsterData, server lists) |

### Client Resources (`client/res/`)

External sprite assets organized by type: `Npc/`, `Pet/`, `PlayerRes/` (Man/Woman/Horse), `SkillAnimation/`, `Effect/`, `UI/`.

### Client Plugins (`Assets/Plugins/`)

TextMesh Pro, Joystick Pack (mobile controls), SharpZipLib (compression), NSpeex (voice), SpriteGlow, MobilePostProcess.

## Communication Protocol

Client and server communicate via TCP using protobuf-net serialization. Protocol handlers on both sides follow the same naming convention (`KT_TCPHandler_<Feature>.cs`), making it straightforward to trace a feature's network flow between client and server.

## Lua Scripting (Server)

Game logic scripts in `server/bin/GameServer/LuaScripts/` use MoonSharp runtime. Directories: `AIScript/` (monster AI), `Activity/`, `CopyScene/` (dungeons), `Form/`, `GrowPoint/`, `Item/`, `NPC/`. Entry index: `ScriptIndex.xml`.
