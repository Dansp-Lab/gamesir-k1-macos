#!/usr/bin/env python3
"""Interactive SDL gamepad mapper for controllers SDL sees as plain joysticks on macOS
(e.g. GameSir K1 Kaleid). Uses the SDL3 library bundled with PCSX2, so the GUID and
button/axis numbering match exactly what the emulator sees.

  python3 k1map.py              map buttons, save to PCSX2's user game_controller_db.txt
  python3 k1map.py --monitor    print axes that move (to verify a mapping)
  python3 k1map.py --sdl PATH   use a specific libSDL3 dylib
"""
import argparse, ctypes as C, glob, os, platform, shutil, subprocess, sys, time

PCSX2_DATA = os.path.expanduser("~/Library/Application Support/PCSX2")


def classify_axis(i, v, rest, stick):
    """SDL mapping token for axis i at value v, or None if it barely moved."""
    if abs(v - rest) < 20000:
        return None
    if stick:
        return f"a{i}" if v > rest else f"a{i}~"
    if rest < -16000:  # trigger resting at -32768, full range
        return f"a{i}"
    return f"+a{i}" if v > 0 else f"-a{i}"  # half-range trigger resting at 0


def find_pcsx2():
    apps = subprocess.run(["mdfind", "kMDItemCFBundleIdentifier == 'net.pcsx2.pcsx2'"],
                          capture_output=True, text=True).stdout.split("\n")
    apps += glob.glob("/Applications/PCSX2*.app") + glob.glob(os.path.expanduser("~/Downloads/PCSX2*.app"))
    for app in filter(None, apps):
        libs = glob.glob(f"{app}/Contents/Frameworks/libSDL3*.dylib")
        if libs:
            return app, libs[0]
    sys.exit("PCSX2.app not found; pass --sdl /path/to/libSDL3.dylib")


def load_sdl(lib):
    # The dylib must match this process's arch (PCSX2 ships x86_64 -> re-run under Rosetta).
    archs = subprocess.run(["lipo", "-archs", lib], capture_output=True, text=True).stdout.split()
    if archs and platform.machine() not in archs:
        os.execvp("arch", ["arch", f"-{archs[0]}", "/usr/bin/python3", *sys.argv])
    sdl = C.CDLL(lib)

    class GUID(C.Structure):
        _fields_ = [("data", C.c_uint8 * 16)]
    sdl.SDL_Init.restype = C.c_bool
    sdl.SDL_GetJoysticks.restype = C.POINTER(C.c_uint32)
    sdl.SDL_GetJoystickNameForID.restype = C.c_char_p
    sdl.SDL_GetJoystickGUIDForID.restype = GUID
    sdl.SDL_GUIDToString.argtypes = [GUID, C.c_char_p, C.c_int]
    sdl.SDL_OpenJoystick.restype = C.c_void_p
    for f, r in (("SDL_GetJoystickAxis", C.c_int16), ("SDL_GetJoystickButton", C.c_bool),
                 ("SDL_GetJoystickHat", C.c_uint8)):
        getattr(sdl, f).argtypes = [C.c_void_p, C.c_int]
        getattr(sdl, f).restype = r
    for f in ("SDL_GetNumJoystickAxes", "SDL_GetNumJoystickButtons", "SDL_GetNumJoystickHats"):
        getattr(sdl, f).argtypes = [C.c_void_p]
    return sdl


def open_joystick(sdl, name_filter):
    sdl.SDL_Init(0x200)  # SDL_INIT_JOYSTICK
    for _ in range(40):
        sdl.SDL_PumpEvents(); time.sleep(0.05)
    n = C.c_int()
    ids = sdl.SDL_GetJoysticks(C.byref(n))
    found = [(ids[i], sdl.SDL_GetJoystickNameForID(ids[i]).decode()) for i in range(n.value)]
    if not found:
        sys.exit("No joystick found. Is the controller plugged in?")
    jid, name = next((f for f in found if name_filter.lower() in f[1].lower()), found[0])
    buf = C.create_string_buffer(64)
    sdl.SDL_GUIDToString(sdl.SDL_GetJoystickGUIDForID(jid), buf, 64)
    return sdl.SDL_OpenJoystick(jid), name, buf.value.decode()


STEPS = [  # (sdl key, prompt, accepted input: digital | any | stick)
    ("a", "A", "digital"), ("b", "B", "digital"), ("x", "X", "digital"), ("y", "Y", "digital"),
    ("leftshoulder", "LB", "digital"), ("rightshoulder", "RB", "digital"),
    ("lefttrigger", "LT (all the way)", "any"), ("righttrigger", "RT (all the way)", "any"),
    ("back", "View / Back", "digital"), ("start", "Menu / Start", "digital"),
    ("guide", "Xbox / Home (skips after 15s)", "digital"),
    ("leftstick", "LEFT stick click (L3)", "digital"), ("rightstick", "RIGHT stick click (R3)", "digital"),
    ("dpup", "D-pad UP", "digital"), ("dpdown", "D-pad DOWN", "digital"),
    ("dpleft", "D-pad LEFT", "digital"), ("dpright", "D-pad RIGHT", "digital"),
    ("leftx", "LEFT stick RIGHT", "stick"), ("lefty", "LEFT stick DOWN", "stick"),
    ("rightx", "RIGHT stick RIGHT", "stick"), ("righty", "RIGHT stick DOWN", "stick"),
]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sdl", help="path to libSDL3 dylib (default: the one inside PCSX2.app)")
    ap.add_argument("--name", default="GameSir", help="pick the joystick whose name contains this")
    ap.add_argument("--monitor", action="store_true", help="only print moving axes")
    args = ap.parse_args()

    # Without this SDL hands the device to Apple's GameController framework, which never exposes it.
    os.environ["SDL_JOYSTICK_MFI"] = "0"
    app, lib = (None, args.sdl) if args.sdl else find_pcsx2()
    sdl = load_sdl(lib)
    j, name, guid = open_joystick(sdl, args.name)
    na, nb, nh = (sdl.SDL_GetNumJoystickAxes(j), sdl.SDL_GetNumJoystickButtons(j),
                  sdl.SDL_GetNumJoystickHats(j))

    def state():
        sdl.SDL_PumpEvents()
        return ([sdl.SDL_GetJoystickAxis(j, i) for i in range(na)],
                [sdl.SDL_GetJoystickButton(j, i) for i in range(nb)],
                [sdl.SDL_GetJoystickHat(j, i) for i in range(nh)])

    print(f"\n{name}: {guid} ({na} axes, {nb} buttons, {nh} hats)")
    print("Don't touch the controller for 2 seconds...")
    time.sleep(2)
    rest = state()[0]

    if args.monitor:
        print("Move sticks/triggers (Ctrl-C to quit)")
        last = None
        while True:
            ax = state()[0]
            cur = " ".join(f"a{i}={'+' if v > r else '-'}" for i, (v, r) in enumerate(zip(ax, rest))
                           if abs(v - r) > 16000)
            if cur != last:
                print(cur or "(rest)", flush=True); last = cur
            time.sleep(0.02)

    used = set()

    def wait_input(mode, timeout):
        t = time.time()
        while timeout is None or time.time() - t < timeout:
            ax, bt, ht = state()
            if mode != "stick":
                for i, v in enumerate(bt):
                    if v and f"b{i}" not in used: return f"b{i}"
                for i, v in enumerate(ht):
                    if v in (1, 2, 4, 8) and f"h{i}.{v}" not in used: return f"h{i}.{v}"
            if mode != "digital":
                for i, v in enumerate(ax):
                    tok = f"a{i}" not in used and classify_axis(i, v, rest[i], mode == "stick")
                    if tok: return tok
            time.sleep(0.01)

    def wait_release():
        while True:
            ax, bt, ht = state()
            if not any(bt) and not any(ht) and all(abs(a - r) < 8000 for a, r in zip(ax, rest)): return
            time.sleep(0.01)

    print("Press each input once, then release it.\n")
    out = []
    for key, label, mode in STEPS:
        print(f"-> {label} ... ", end="", flush=True)
        tok = wait_input(mode, 15 if key == "guide" else None)
        if tok is None:
            print("skipped"); continue
        print(tok)
        used.add(tok.strip("+-~")); out.append(f"{key}:{tok}")
        wait_release()

    line = f"{guid},{name} (Mac),{','.join(out)},platform:Mac OS X,"
    print("\n" + line)
    if app:  # PCSX2 uses <data>/game_controller_db.txt instead of its bundled one when it exists
        db = os.path.join(PCSX2_DATA, "game_controller_db.txt")
        if not os.path.exists(db):
            shutil.copy(f"{app}/Contents/Resources/game_controller_db.txt", db)
        with open(db) as f:
            keep = [l for l in f if not l.startswith(guid)]
        with open(db, "w") as f:
            f.writelines(keep + [line + "\n"])
        print(f"\nSaved to {db}")


if __name__ == "__main__":
    main()
