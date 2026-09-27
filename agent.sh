#!/bin/sh
# Sets SDL_JOYSTICK_MFI=0 for every app launched from Finder/Dock, on every login.
# Usage: ./agent.sh install | uninstall
set -e
LABEL=com.dansp.sdl-joystick-mfi
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

case "$1" in
install)
  mkdir -p "$HOME/Library/LaunchAgents"
  cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>Label</key>
	<string>$LABEL</string>
	<key>ProgramArguments</key>
	<array>
		<string>/bin/launchctl</string>
		<string>setenv</string>
		<string>SDL_JOYSTICK_MFI</string>
		<string>0</string>
	</array>
	<key>RunAtLoad</key>
	<true/>
</dict>
</plist>
EOF
  launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
  launchctl bootstrap "gui/$(id -u)" "$PLIST"
  echo "Installed. SDL_JOYSTICK_MFI=$(launchctl getenv SDL_JOYSTICK_MFI). Quit and reopen your emulator."
  ;;
uninstall)
  launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
  rm -f "$PLIST"
  launchctl unsetenv SDL_JOYSTICK_MFI
  echo "Removed."
  ;;
*)
  echo "usage: $0 install|uninstall" >&2; exit 1 ;;
esac
