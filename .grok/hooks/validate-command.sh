#!/bin/bash
# Read the JSON payload from stdin
PAYLOAD=$(cat -)

# Extract the toolInput command using jq
COMMAND=$(echo "$PAYLOAD" | jq -r '.toolInput.command')

# Check for unauthorized network egress, exfiltration, or deletion commands
if [[ "$COMMAND" == *"rm -rf"* ]] || [[ "$COMMAND" == *"curl"* ]] || [[ "$COMMAND" == *"wget"* ]] || [[ "$COMMAND" == *"nc"* ]]; then
    # Exit 2 denies the action and prints the reason to stdout for the agent to see
    echo '{"decision": "deny", "reason": "Unauthorized command detected by security hook. Do not attempt network egress or destructive operations."}'
    exit 2
fi

# Exit 0 allows the action to proceed
echo '{"decision": "allow"}'
exit 0
