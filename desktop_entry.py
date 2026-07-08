"""PyInstaller entry point for Agent Hub desktop app.

When packaged by PyInstaller, this script becomes the main entry point
of the agent-hub-backend binary. It calls the same main() function
used by the CLI, passing --desktop to enable desktop mode.
"""

import sys
from agent_hub.main import main

if __name__ == "__main__":
    sys.argv = ["agent-hub-backend", "start", "--desktop"]
    main()
