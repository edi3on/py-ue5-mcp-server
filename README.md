# py-ue5-mcp-server
# Unreal Engine 5 MCP Server for Claude

This repository contains a Model Context Protocol (MCP) Python server that enables Claude to interact with Unreal Engine 5 through natural language. By leveraging the Remote Control API, this integration allows you to create, manipulate, and control 3D objects and Blueprint actors in Unreal Engine directly through conversations with Claude.

## Overview

This MCP server bridges the gap between Claude's natural language processing capabilities and Unreal Engine's powerful 3D environment. Users can simply describe what they want to create or modify in Unreal Engine, and Claude will interpret these requests and execute the appropriate actions through the MCP server.

### Key Features

- **Natural Language Control**: Create and manipulate 3D objects using conversational text with Claude
- **Blueprint Actor Interaction**: Access functions in Blueprint actors through simple text prompts
- **Scene Management**: Build, modify, and arrange scenes with text-based instructions
- **Asset Discovery**: Search and utilize assets in your Unreal project through Claude
- **Real-time Feedback**: Get immediate visual results in your Unreal Engine viewport

## Requirements

- Python 3.10+
- Unreal Engine 5.x with Remote Control API plugin enabled
- Claude Desktop (Windows)
- Basic knowledge of Unreal Engine fundamentals

## Installation

### 1. Set Up the Repository

```bash
git clone https://github.com/yourusername/ue5-mcp.git
cd ue5-mcp
pip install uv mcp requests
```

### 2. Configure Claude Desktop

1. Open Claude Desktop
2. Go to File → Settings → Developer → Edit Config
3. Add the following to `claude_desktop_config.json`, adjusting the path to your local repository:

```json
{
  "mcpServers": {
    "ue5-mcp": {
      "command": "uv",
      "args": ["--directory", "C:\\path\\to\\ue5-mcp", "run", "ue5_mcp_server.py"],
      "env": {}
    }
  }
}
```

**Note**: If you have other MCP servers configured, you may need to disable them to prevent conflicts.

### 3. Prepare Unreal Engine

1. Open Unreal Engine and your project
2. Ensure the Remote Control API plugin is enabled:
   - Edit → Plugins → Search for "Remote Control API"
   - Check that it's enabled and restart the editor if needed

## Usage

### Getting Started

1. Launch Unreal Engine with your project
2. Start Claude Desktop (restart it if it was already running)
3. Begin chatting with Claude about creating or modifying content in Unreal Engine

### Example Prompts

Here are some example prompts you can use with Claude:

- "Create a snowman at position 0, 100, 50"
- "Spawn a snowman family in the scene"
- "Modify the center snowman's scale to make it bigger"
- "Move the snowman to position 100, 200, 0"
- "Rotate the snowman 45 degrees"
- "Get a list of all actors in the scene"

### Understanding Units

The server uses **centimeters** as the default unit for all measurements:
- 1 Unreal Unit = 1 centimeter
- A standard snowman has dimensions of approximately 350cm × 350cm (3.5m × 3.5m)
- Positioning and scaling are all relative to this centimeter-based system

## How It Works

### Technical Implementation

The UE5-MCP server uses the following core components:

#### 1. MCP Server Framework

The server is built using FastMCP, which establishes a bidirectional communication channel between Claude and Unreal Engine. The main components are:

```python
# Create the MCP server with lifespan support
mcp = FastMCP(
    "Unreal-Engine-MCP",
    description="Unreal Engine integration through the Model Context Protocol (Default unit: CENTIMETERS)",
    lifespan=server_lifespan
)
```

#### 2. Connection to Unreal Engine

The server connects to Unreal Engine through the Remote Control API, a built-in HTTP server that runs inside Unreal:

```python
# Default Unreal Engine Remote Control API settings
UE_HOST = "http://127.0.0.1"  # localhost
UE_PORT = "30010"             # default port
UE_URL = f"{UE_HOST}:{UE_PORT}/remote/object/call"
```

#### 3. Core Tools

The server exposes several tools to Claude through function decorators:

```python
@mcp.tool()
async def get_all_scene_actors(ctx: Context) -> str:
    """Get a list of all actors in the current level"""
    # Implementation...

@mcp.tool()
async def spawn_actor(ctx: Context, blueprint_path: str, ...) -> str:
    """Spawn a blueprint actor in the current Unreal Engine level"""
    # Implementation...
    
@mcp.tool()
async def spawn_snowman_family(ctx: Context, ...) -> str:
    """Spawns a family of three snowmen in the current Unreal Engine level"""
    # Implementation...
    
@mcp.tool()
async def modify_actor(ctx: Context, actor_path: str, ...) -> str:
    """Modify an existing actor's properties in the Unreal Engine level"""
    # Implementation...
```

#### 4. Actor Manipulation

The server can create and modify actors in the scene through Remote Control API calls:

```python
# Illustrative example of how actor creation works
spawn_payload = {
    "objectPath": "/Script/EditorScriptingUtilities.Default__EditorLevelLibrary",
    "functionName": "SpawnActorFromClass",
    "parameters": {
        "ActorClass": blueprint_path,
        "Location": {"X": location[0], "Y": location[1], "Z": location[2]},
        "Rotation": {"Pitch": rotation[0], "Yaw": rotation[1], "Roll": rotation[2]}
    },
    "generateTransaction": True
}
```

Each action is executed as an HTTP request to the Unreal Engine Remote Control API, which returns results in JSON format.

## Featured Capabilities

### 1. Snowman Family Creation

One of the showcase features is the ability to create a family of snowmen with a single command. The server will:

- Create an initial snowman actor
- Duplicate it to create two more snowmen with different positions, rotations, and scales
- Arrange them in a family formation

This demonstrates how complex scenes can be created with simple natural language commands.

### 2. Blueprint Actor Duplication

The server can duplicate existing actors in the scene using their native Blueprint functions:

```python
async def duplicate_snowman(
    snowman_actor_path: str, 
    location: Tuple[float, float, float], 
    rotation: Tuple[float, float, float], 
    scale: Tuple[float, float, float], 
    name: Optional[str]
) -> Optional[str]:
    """Calls the Duplicate function in a Blueprint actor"""
    # Implementation...
```

### 3. Actor Modification

The server supports modifying any property of an existing actor:

- Change position, rotation, and scale
- Rename actors
- Only update specific properties while preserving others

## Troubleshooting

### Connection Issues

- Ensure Unreal Engine is running before starting Claude Desktop
- Check that the Remote Control API plugin is enabled in Unreal Engine
- Verify no firewall is blocking communication on port 30010 (default port)
- Look for error messages in the Claude Desktop console

### Command Execution Problems

- Start with simple commands to verify basic functionality
- Check the syntax of your requests
- Look for error messages in the Unreal Engine output log
- Ensure the referenced actors or assets exist in your project

### Server Logs

The server generates detailed logs that can help diagnose issues:

```
2023-11-15 14:32:45,123 - Unreal-MCP-Server - INFO - Unreal Engine MCP server starting up...
2023-11-15 14:32:45,125 - Unreal-MCP-Server - INFO - Default unit system: CENTIMETERS (1 Unreal Unit = 1 cm)
2023-11-15 14:32:45,234 - Unreal-MCP-Server - INFO - Connected to Unreal Engine Remote Control API
```

## Development and Customization

### Adding New Functions

To add new functionality to the server:

1. Create a new helper function that implements the desired behavior
2. Expose it to Claude using the `@mcp.tool()` decorator
3. Document the function clearly with docstrings

Example:

```python
@mcp.tool()
async def your_new_function(ctx: Context, param1: str, param2: int) -> str:
    """
    Description of what your function does
    
    Parameters:
        param1: Description of param1
        param2: Description of param2
        
    Returns:
        JSON string with the result
    """
    # Implementation...
```

### Customizing Blueprint Interactions

You can adapt the server to work with your custom Blueprint actors by modifying the existing functions or creating new ones specific to your actors.

## Acknowledgements

This project was inspired by similar MCP integrations for Claude, particularly the original Unreal Engine MCP server by runeape-sats. Special thanks to the Anthropic team for creating Claude and enabling these kinds of integrations.
