#!/bin/bash

# Script to restart the siam-pixel hotfolder agent
echo "Restarting com.siam-pixel.hotfolder.agent..."

# Unload the agent
launchctl unload /Users/hetzner/Library/LaunchAgents/com.siam-pixel.hotfolder.agent.plist
echo "Agent unloaded."

# Load the agent
launchctl load /Users/hetzner/Library/LaunchAgents/com.siam-pixel.hotfolder.agent.plist
echo "Agent loaded."

echo "Restart complete."
