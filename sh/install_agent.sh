#!/bin/bash

PLIST_NAME="com.siampixel.hotfolder.agent.plist"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_NAME"
PYTHON_PATH="/Volumes/Storage/scripts/py_cur_hotfolder-agent/venv/bin/python3"
PROJECT_DIR="/Volumes/Storage/scripts/py_cur_hotfolder-agent"
MAIN_SCRIPT="$PROJECT_DIR/src/main.py"

# Create plist file if it doesn't exist
if [ ! -f "$PLIST_PATH" ]; then
  echo "Creating $PLIST_PATH..."
  cat > "$PLIST_PATH" <<EOL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.siampixel.hotfolder.agent</string>
  <key>ProgramArguments</key>
  <array>
    <string>$PYTHON_PATH</string>
    <string>$MAIN_SCRIPT</string>
  </array>
  <key>WorkingDirectory</key>
  <string>$PROJECT_DIR</string>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>/tmp/hotfolder.out</string>
  <key>StandardErrorPath</key>
  <string>/tmp/hotfolder.err</string>
</dict>
</plist>
EOL
  echo "Plist created."
else
  echo "$PLIST_PATH already exists."
fi

# Check if agent is loaded
launchctl list | grep -q com.siampixel.hotfolder.agent
if [ $? -eq 0 ]; then
  echo "Agent is already loaded."
else
  echo "Loading agent..."
  launchctl load "$PLIST_PATH"
  echo "Agent loaded."
fi
