# GameSir K1 on macOS (PCSX2 & other SDL apps)

Make the **GameSir K1 Kaleid** wired controller work on macOS in PCSX2 and other SDL3-based
apps (RetroArch, Dolphin, Steam games...). No driver needed.

> 🇧🇷 **Português:** o controle já funciona no Mac como gamepad HID, mas o SDL o ignora.
> Rode `./agent.sh install`, depois `python3 k1map.py`, feche e reabra o PCSX2.

## The problem

Plugged into a Mac, the K1 (VID `0x3537`, PID `0x1082`) does **not** use the Xbox GIP
protocol. It shows up as a plain HID gamepad and macOS loads its own HID driver for it. Even so:

1. **SDL skips it.** SDL believes Apple's GameController (MFi) framework will handle the
   device and leaves it out of its own IOKit backend. GameController never exposes it
   either, so the controller falls through the cracks and no SDL app sees it.
2. **No mapping.** SDL's controller DB only has a K1 entry for a different PID, and that
   entry is Linux-only. Without a Mac mapping the device is a raw joystick, not a gamepad.

## The fix

```sh
git clone https://github.com/Dansp-Lab/gamesir-k1-macos.git
cd gamesir-k1-macos
./agent.sh install     # 1. sets SDL_JOYSTICK_MFI=0 for apps opened from Finder/Dock, on every login
python3 k1map.py       # 2. press each button when asked; saves the mapping for PCSX2
```

Then quit PCSX2 (⌘Q) and reopen it. Go to **Settings → Controllers → Controller Port 1 →
Automatic Mapping** and pick **SDL-0: GameSir K1…**.

- `k1map.py` uses the SDL3 library inside `PCSX2.app`, so the GUID and button numbers are
  exactly what the emulator sees. PCSX2 ships an x86_64 build, so the script re-runs itself
  under Rosetta.
- The mapping is written to `~/Library/Application Support/PCSX2/game_controller_db.txt`,
  which PCSX2 reads instead of its bundled DB. On first run the bundled DB is copied there.
- `python3 k1map.py --monitor` prints which axes move, so you can check a mapping.
- For other SDL apps, copy the printed line into that app's controller DB, or set it in the
  `SDL_GAMECONTROLLERCONFIG` environment variable.

### Known mapping (K1, PID 0x1082, firmware 0x0163)

If your controller reports the same GUID, you can skip the mapper and add this line:

```
03001032373500008210000063010000,GameSir K1 (Mac),a:b0,b:b1,x:b3,y:b4,leftshoulder:b6,rightshoulder:b7,lefttrigger:a5,righttrigger:a4,back:b10,start:b11,guide:b12,leftstick:b13,rightstick:b14,dpup:h0.1,dpdown:h0.4,dpleft:h0.8,dpright:h0.2,leftx:a0,lefty:a1,rightx:a2,righty:a3,platform:Mac OS X,
```

LT/RT are analog axes (rest at -32768). The same mapping was proposed upstream in [mdqinc/SDL_GameControllerDB#996](https://github.com/mdqinc/SDL_GameControllerDB/pull/996).

## Uninstall

```sh
./agent.sh uninstall
rm ~/Library/Application\ Support/PCSX2/game_controller_db.txt   # PCSX2 falls back to its bundled DB
```

## Caveats

- `SDL_JOYSTICK_MFI=0` applies to every SDL app, and games that use only Apple's
  GameController framework (e.g. Apple Arcade) still won't see the K1.
- While the user DB exists, PCSX2 updates won't bring new mappings for *other* controllers.
  Delete it and run the mapper again to refresh.

## License

MIT
