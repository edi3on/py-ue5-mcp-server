# unreal_mcp_server.py
# Model Context Protocol (MCP) server for Unreal Engine integration
# Updated to use centimeters as the default unit and specify Snowman dimensions

import logging
import json
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator, Dict, Any, List, Optional, Tuple
import traceback
import os
import requests
import time
import sys

from mcp.server.fastmcp import FastMCP, Context

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Unreal-MCP-Server")

# Default Unreal Engine Remote Control API settings
UE_HOST = "http://127.0.0.1"  # localhost
UE_PORT = "30010"             # default port
UE_URL = f"{UE_HOST}:{UE_PORT}/remote/object/call"

# Default units and dimensions
# 1 Unreal Unit = 1 centimeter (UE default is actually 1 UU = 1 cm, but now explicitly documented)
# Snowman dimensions (in centimeters)
SNOWMAN_WIDTH = 350  # 3.5 meters
SNOWMAN_LENGTH = 350  # 3.5 meters
SNOWMAN_HEIGHT_DEFAULT = 400  # 4.0 meters (approximate default height)

@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
    """Manage server startup and shutdown lifecycle"""
    
    try:
        logger.info("Unreal Engine MCP server starting up...")
        logger.info("Default unit system: CENTIMETERS (1 Unreal Unit = 1 cm)")
        logger.info(f"Snowman standard dimensions: {SNOWMAN_WIDTH}cm x {SNOWMAN_LENGTH}cm")
        
        # Test Unreal Engine Remote Control API connection on startup
        try:
            # Get list of actors to test connection
            payload = {
                "objectPath": "/Script/UnrealEd.Default__EditorActorSubsystem",
                "functionName": "GetAllLevelActors"
            }
            
            response = requests.put(UE_URL, json=payload, timeout=5)
            response.raise_for_status()
            logger.info("Connected to Unreal Engine Remote Control API")
        except Exception as e:
            logger.warning(f"Could not connect to Unreal Engine Remote Control API: {e}")
            logger.warning("Make sure Unreal Engine is running with Remote Control API enabled")
            
        # Return an empty context
        yield {}
    finally:
        # Shutdown logging
        logger.info("Unreal Engine MCP server shut down")

# Create the MCP server with lifespan support
mcp = FastMCP(
    "Unreal-Engine-MCP",
    description="Unreal Engine integration through the Model Context Protocol (Default unit: CENTIMETERS)",
    lifespan=server_lifespan
)

# Helper functions for the Unreal Engine integration
async def get_all_level_actors() -> List[str]:
    """Returns list of all level actors"""
    payload = {
        "objectPath": "/Script/UnrealEd.Default__EditorActorSubsystem",
        "functionName": "GetAllLevelActors"
    }
    
    try:
        response = requests.put(UE_URL, json=payload, timeout=5)
        response.raise_for_status()
        result = response.json()
        return result.get("ReturnValue", [])
    except requests.exceptions.RequestException as e:
        logger.error(f"Error getting level actors: {e}")
        return []

async def spawn_blueprint_actor(
    blueprint_path: str, 
    location: Tuple[float, float, float] = (0, 0, 0), 
    rotation: Tuple[float, float, float] = (0, 0, 0), 
    scale: Tuple[float, float, float] = (1, 1, 1), 
    name: Optional[str] = None
) -> Optional[str]:
    """
    Spawns a blueprint actor in Unreal Engine using the Remote Control API
    
    Parameters:
        blueprint_path: Path to the blueprint asset in the content browser
        location: tuple of (x, y, z) coordinates in centimeters
        rotation: tuple of (pitch, yaw, roll) in degrees
        scale: tuple of (x, y, z) scale factors
        name: Optional name for the spawned actor
        
    Returns:
        str: Actor path if successful, None if failed
    """
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

    try:
        # Spawn the actor
        logger.info(f"Spawning {blueprint_path} at location {location}cm")
        response = requests.put(UE_URL, json=spawn_payload, timeout=5)
        response.raise_for_status()
        result = response.json()
        actor_path = result.get("ReturnValue")
        
        if not actor_path:
            logger.error("No actor path returned from spawn request")
            return None
            
        # Set scale if needed
        if scale != (1, 1, 1):
            set_scale_payload = {
                "objectPath": actor_path,
                "functionName": "SetActorScale3D",
                "parameters": {
                    "NewScale3D": {"X": scale[0], "Y": scale[1], "Z": scale[2]}
                }
            }
            
            response = requests.put(UE_URL, json=set_scale_payload, timeout=5)
            response.raise_for_status()
            
        # Set name if provided
        if name:
            set_name_payload = {
                "objectPath": actor_path,
                "functionName": "SetActorLabel",
                "parameters": {
                    "NewActorLabel": name
                }
            }
            
            response = requests.put(UE_URL, json=set_name_payload, timeout=5)
            response.raise_for_status()
            
        logger.info(f"Successfully spawned actor: {actor_path}")
        return actor_path
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Error spawning blueprint actor: {e}")
        if hasattr(e, 'response') and e.response:
            logger.error(f"Response details: {e.response.text}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return None

async def duplicate_snowman(
    snowman_actor_path: str, 
    location: Tuple[float, float, float], 
    rotation: Tuple[float, float, float], 
    scale: Tuple[float, float, float], 
    name: Optional[str]
) -> Optional[str]:
    """
    Calls the Duplicate function in Snowman_BP to create a new snowman
    
    Parameters:
        snowman_actor_path: Path of the source snowman actor
        location: tuple of (x, y, z) coordinates in centimeters
        rotation: tuple of (pitch, yaw, roll) in degrees
        scale: tuple of (x, y, z) scale factors
        name: Name for the duplicated snowman
        
    Returns:
        str: Actor path of the duplicated snowman if successful, None if failed
    """
    # Create a properly formatted FTransform structure for UE
    transform = {
        "__type": "Transform",
        "Rotation": {
            "__type": "Quat",
            "X": 0.0,
            "Y": 0.0,
            "Z": 0.0,
            "W": 1.0
        },
        "Scale3D": {
            "__type": "Vector",
            "X": scale[0],
            "Y": scale[1],
            "Z": scale[2]
        },
        "Translation": {
            "__type": "Vector",
            "X": location[0],
            "Y": location[1],
            "Z": location[2]
        }
    }
    
    # Alternative transform formats if needed
    transform_alt1 = {
        "Translation": {"X": location[0], "Y": location[1], "Z": location[2]},
        "Rotation": {"X": 0.0, "Y": 0.0, "Z": 0.0, "W": 1.0},
        "Scale3D": {"X": scale[0], "Y": scale[1], "Z": scale[2]}
    }
    
    transform_alt2 = {
        "Translation": [location[0], location[1], location[2]],
        "Rotation": [0.0, 0.0, 0.0, 1.0],  # Quaternion X,Y,Z,W
        "Scale3D": [scale[0], scale[1], scale[2]]
    }
    
    # Try with the primary transform format
    duplicate_payload = {
        "objectPath": snowman_actor_path,
        "functionName": "Duplicate",
        "parameters": {
            "NewTransform": transform
        },
        "generateTransaction": True
    }
    
    try:
        logger.info(f"Duplicating snowman from {snowman_actor_path} to location {location}cm")
        
        # Get actors before duplication
        before_actors = await get_all_level_actors()
        
        # Send the duplication request
        response = requests.put(UE_URL, json=duplicate_payload, timeout=5)
        response.raise_for_status()
        result = response.json()
        
        # Wait for the actor to be created
        await asyncio.sleep(0.5)
        
        # Check if we got a valid return value
        new_actor_path = result.get("ReturnValue")
        
        # If not, try to find the new actor
        if not new_actor_path:
            # Try to find the new actor
            after_actors = await get_all_level_actors()
            new_actors = [actor for actor in after_actors if actor not in before_actors]
            
            if new_actors:
                new_actor_path = new_actors[-1]
                logger.info(f"Found new actor: {new_actor_path}")
            else:
                # If no new actor was found, try alternate transform formats
                logger.info("No return value and no new actor found. Trying alternate transform format...")
                
                # Try first alternative format
                duplicate_payload["parameters"]["NewTransform"] = transform_alt1
                response = requests.put(UE_URL, json=duplicate_payload, timeout=5)
                response.raise_for_status()
                
                await asyncio.sleep(0.5)
                after_actors = await get_all_level_actors()
                new_actors = [actor for actor in after_actors if actor not in before_actors]
                
                if new_actors:
                    new_actor_path = new_actors[-1]
                    logger.info(f"Found new actor with alt format 1: {new_actor_path}")
                else:
                    # Try second alternative format
                    duplicate_payload["parameters"]["NewTransform"] = transform_alt2
                    response = requests.put(UE_URL, json=duplicate_payload, timeout=5)
                    response.raise_for_status()
                    
                    await asyncio.sleep(0.5)
                    after_actors = await get_all_level_actors()
                    new_actors = [actor for actor in after_actors if actor not in before_actors]
                    
                    if new_actors:
                        new_actor_path = new_actors[-1]
                        logger.info(f"Found new actor with alt format 2: {new_actor_path}")
                    else:
                        logger.error("Failed to duplicate actor with all transform formats.")
                        return None
        
        # If we have a new actor path, set its properties
        if new_actor_path:
            # Set the location directly to ensure it's in the right place
            set_location_payload = {
                "objectPath": new_actor_path,
                "functionName": "SetActorLocation",
                "parameters": {
                    "NewLocation": {"X": location[0], "Y": location[1], "Z": location[2]}
                }
            }
            response = requests.put(UE_URL, json=set_location_payload, timeout=5)
            response.raise_for_status()
            
            # Set the rotation
            set_rotation_payload = {
                "objectPath": new_actor_path,
                "functionName": "SetActorRotation",
                "parameters": {
                    "NewRotation": {"Pitch": rotation[0], "Yaw": rotation[1], "Roll": rotation[2]}
                }
            }
            response = requests.put(UE_URL, json=set_rotation_payload, timeout=5)
            response.raise_for_status()
            
            # Set the scale
            set_scale_payload = {
                "objectPath": new_actor_path,
                "functionName": "SetActorScale3D",
                "parameters": {
                    "NewScale3D": {"X": scale[0], "Y": scale[1], "Z": scale[2]}
                }
            }
            response = requests.put(UE_URL, json=set_scale_payload, timeout=5)
            response.raise_for_status()
            
            # Set name if provided
            if name:
                set_name_payload = {
                    "objectPath": new_actor_path,
                    "functionName": "SetActorLabel",
                    "parameters": {
                        "NewActorLabel": name
                    }
                }
                response = requests.put(UE_URL, json=set_name_payload, timeout=5)
                response.raise_for_status()
            
            logger.info(f"Successfully duplicated snowman: {new_actor_path}")
            return new_actor_path
        
        return None
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Error duplicating snowman: {e}")
        if hasattr(e, 'response') and e.response:
            logger.error(f"Response details: {e.response.text}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return None

# Register MCP tools for Unreal Engine integration
@mcp.tool()
async def get_all_scene_actors(ctx: Context) -> str:
    """
    Get a list of all actors in the current level
    
    Returns:
        JSON string containing the list of actor paths
    """
    try:
        actors = await get_all_level_actors()
        return json.dumps({"actors": actors, "count": len(actors)}, indent=2)
    except Exception as e:
        logger.error(f"Error in get_all_scene_actors: {str(e)}")
        logger.error(traceback.format_exc())
        return f"Error getting scene actors: {str(e)}"

@mcp.tool()
async def spawn_actor(
    ctx: Context, 
    blueprint_path: str, 
    x: float = 0.0, 
    y: float = 0.0, 
    z: float = 0.0,
    pitch: float = 0.0,
    yaw: float = 0.0,
    roll: float = 0.0,
    scale_x: float = 1.0,
    scale_y: float = 1.0,
    scale_z: float = 1.0,
    name: Optional[str] = None
) -> str:
    """
    Spawn a blueprint actor in the current Unreal Engine level
    
    Parameters:
        blueprint_path: Path to the blueprint asset (e.g., "/Game/Snowman_BP.Snowman_BP_C")
        x, y, z: Location coordinates in centimeters
        pitch, yaw, roll: Rotation angles in degrees
        scale_x, scale_y, scale_z: Scale factors
        name: Optional name for the spawned actor
        
    Returns:
        JSON string with the result of the spawn operation
    """
    try:
        location = (x, y, z)
        rotation = (pitch, yaw, roll)
        scale = (scale_x, scale_y, scale_z)
        
        actor_path = await spawn_blueprint_actor(
            blueprint_path=blueprint_path,
            location=location,
            rotation=rotation,
            scale=scale,
            name=name
        )
        
        if actor_path:
            return json.dumps({
                "success": True,
                "actor_path": actor_path,
                "location_cm": {"x": x, "y": y, "z": z},
                "rotation": {"pitch": pitch, "yaw": yaw, "roll": roll},
                "scale": {"x": scale_x, "y": scale_y, "z": scale_z},
                "name": name or "Unnamed"
            }, indent=2)
        else:
            return json.dumps({
                "success": False,
                "error": "Failed to spawn actor"
            }, indent=2)
            
    except Exception as e:
        logger.error(f"Error in spawn_actor: {str(e)}")
        logger.error(traceback.format_exc())
        return json.dumps({
            "success": False,
            "error": str(e)
        }, indent=2)

@mcp.tool()
async def spawn_snowman_family(
    ctx: Context,
    base_x: float = 0.0,
    base_y: float = 0.0,
    base_z: float = 0.0,
    spread: float = 1.0,
    random_placement: bool = True
) -> str:
    """
    Spawns a family of three snowmen in the current Unreal Engine level
    
    This will create one Snowman_BP actor and use its Duplicate function to create two more snowmen.
    The snowmen will be placed at varying distances from the base position and with different sizes.
    Each standard snowman is 350cm x 350cm (3.5m x 3.5m) in width and length.
    
    Parameters:
        base_x, base_y, base_z: Base position for the first snowman in centimeters
        spread: Factor to multiply the spacing between snowmen (default 1.0)
        random_placement: If True, adds some randomness to positions and sizes
        
    Returns:
        JSON string with details of the spawned snowmen
    """
    try:
        # Path to the Snowman_BP blueprint asset
        snowman_bp_path = "/Game/Snowman_BP.Snowman_BP_C"
        
        # Define positions for the three snowmen (in centimeters)
        if random_placement:
            import random
            offset_factor = spread * random.uniform(0.8, 1.2)
        else:
            offset_factor = spread
            
        # Calculate appropriate spacing based on snowman dimensions
        # Spacing should take into account the width of the snowmen (350cm)
        spacing_x = SNOWMAN_WIDTH * 1.5  # 1.5 times the width for good spacing
        spacing_y = SNOWMAN_LENGTH * 1.5
        
        positions = [
            (base_x, base_y, base_z),                                      # First snowman at base position
            (base_x - spacing_x * offset_factor, base_y + spacing_y * 0.6 * offset_factor, base_z),  # Second snowman
            (base_x + spacing_x * 1.2 * offset_factor, base_y - spacing_y * 0.4 * offset_factor, base_z)   # Third snowman
        ]
        
        # Define scales for the snowmen (varying sizes)
        scales = [
            (1.2, 1.2, 1.2),      # First snowman (slightly larger)
            (0.9, 0.9, 0.9),      # Second snowman (smaller)
            (1.4, 1.4, 1.4)       # Third snowman (largest)
        ]
        
        # Define rotations - facing different directions
        rotations = [
            (0, 0, 0),            # First snowman facing forward
            (0, 135, 0),          # Second snowman facing southeast
            (0, -45, 0)           # Third snowman facing northeast
        ]
        
        # Names for the snowmen
        names = [
            "Snowman_Center",
            "Snowman_Left",
            "Snowman_Right"
        ]
        
        # Spawn the first snowman normally
        spawned_actors = []
        first_snowman = await spawn_blueprint_actor(
            blueprint_path=snowman_bp_path,
            location=positions[0],
            rotation=rotations[0],
            scale=scales[0],
            name=names[0]
        )
        
        if not first_snowman:
            return json.dumps({
                "success": False,
                "error": "Failed to spawn first snowman, cannot continue",
                "snowmen": []
            }, indent=2)
            
        spawned_actors.append({
            "actor_path": first_snowman,
            "location_cm": {"x": positions[0][0], "y": positions[0][1], "z": positions[0][2]},
            "size_cm": {"width": SNOWMAN_WIDTH * scales[0][0], "length": SNOWMAN_LENGTH * scales[0][1]},
            "rotation": {"pitch": rotations[0][0], "yaw": rotations[0][1], "roll": rotations[0][2]},
            "scale": {"x": scales[0][0], "y": scales[0][1], "z": scales[0][2]},
            "name": names[0]
        })
        
        # Wait briefly to make actor detection more reliable
        await asyncio.sleep(0.5)
        
        # Now duplicate the first snowman to create the other two
        for i in range(1, 3):
            duplicated_snowman = await duplicate_snowman(
                snowman_actor_path=first_snowman,
                location=positions[i],
                rotation=rotations[i],
                scale=scales[i],
                name=names[i]
            )
            
            if duplicated_snowman:
                spawned_actors.append({
                    "actor_path": duplicated_snowman,
                    "location_cm": {"x": positions[i][0], "y": positions[i][1], "z": positions[i][2]},
                    "size_cm": {"width": SNOWMAN_WIDTH * scales[i][0], "length": SNOWMAN_LENGTH * scales[i][1]},
                    "rotation": {"pitch": rotations[i][0], "yaw": rotations[i][1], "roll": rotations[i][2]},
                    "scale": {"x": scales[i][0], "y": scales[i][1], "z": scales[i][2]},
                    "name": names[i]
                })
            else:
                logger.warning(f"Failed to duplicate snowman {i+1}")
            
            # Wait briefly between duplications to make actor detection more reliable
            await asyncio.sleep(0.5)
        
        return json.dumps({
            "success": True,
            "standard_snowman_dimensions_cm": {"width": SNOWMAN_WIDTH, "length": SNOWMAN_LENGTH},
            "snowmen_count": len(spawned_actors),
            "snowmen": spawned_actors
        }, indent=2)
            
    except Exception as e:
        logger.error(f"Error in spawn_snowman_family: {str(e)}")
        logger.error(traceback.format_exc())
        return json.dumps({
            "success": False,
            "error": str(e),
            "snowmen": []
        }, indent=2)

@mcp.tool()
async def modify_actor(
    ctx: Context,
    actor_path: str,
    x: Optional[float] = None,
    y: Optional[float] = None,
    z: Optional[float] = None,
    pitch: Optional[float] = None,
    yaw: Optional[float] = None,
    roll: Optional[float] = None,
    scale_x: Optional[float] = None,
    scale_y: Optional[float] = None,
    scale_z: Optional[float] = None,
    name: Optional[str] = None
) -> str:
    """
    Modify an existing actor's properties in the Unreal Engine level
    
    Parameters:
        actor_path: Path to the actor to modify
        x, y, z: New location coordinates in centimeters (if provided)
        pitch, yaw, roll: New rotation angles in degrees (if provided)
        scale_x, scale_y, scale_z: New scale factors (if provided)
        name: New name for the actor (if provided)
        
    Returns:
        JSON string with the result of the modification operation
    """
    try:
        modified = False
        results = {}
        
        # Set location if any coordinate is provided
        if any(param is not None for param in [x, y, z]):
            # Get current location first for coordinates that weren't specified
            get_location_payload = {
                "objectPath": actor_path,
                "functionName": "GetActorLocation"
            }
            
            try:
                response = requests.put(UE_URL, json=get_location_payload, timeout=5)
                response.raise_for_status()
                current_loc = response.json().get("ReturnValue", {"X": 0, "Y": 0, "Z": 0})
                
                # Use current values for any coordinate not specified
                new_x = x if x is not None else current_loc.get("X", 0)
                new_y = y if y is not None else current_loc.get("Y", 0)
                new_z = z if z is not None else current_loc.get("Z", 0)
                
                # Set the new location
                set_location_payload = {
                    "objectPath": actor_path,
                    "functionName": "SetActorLocation",
                    "parameters": {
                        "NewLocation": {"X": new_x, "Y": new_y, "Z": new_z}
                    }
                }
                
                response = requests.put(UE_URL, json=set_location_payload, timeout=5)
                response.raise_for_status()
                modified = True
                results["location_cm"] = {"x": new_x, "y": new_y, "z": new_z}
                
            except Exception as e:
                logger.error(f"Error setting actor location: {e}")
                results["location_error"] = str(e)
        
        # Set rotation if any angle is provided
        if any(param is not None for param in [pitch, yaw, roll]):
            # Get current rotation first for angles that weren't specified
            get_rotation_payload = {
                "objectPath": actor_path,
                "functionName": "GetActorRotation"
            }
            
            try:
                response = requests.put(UE_URL, json=get_rotation_payload, timeout=5)
                response.raise_for_status()
                current_rot = response.json().get("ReturnValue", {"Pitch": 0, "Yaw": 0, "Roll": 0})
                
                # Use current values for any angle not specified
                new_pitch = pitch if pitch is not None else current_rot.get("Pitch", 0)
                new_yaw = yaw if yaw is not None else current_rot.get("Yaw", 0)
                new_roll = roll if roll is not None else current_rot.get("Roll", 0)
                
                # Set the new rotation
                set_rotation_payload = {
                    "objectPath": actor_path,
                    "functionName": "SetActorRotation",
                    "parameters": {
                        "NewRotation": {"Pitch": new_pitch, "Yaw": new_yaw, "Roll": new_roll}
                    }
                }
                
                response = requests.put(UE_URL, json=set_rotation_payload, timeout=5)
                response.raise_for_status()
                modified = True
                results["rotation"] = {"pitch": new_pitch, "yaw": new_yaw, "roll": new_roll}
                
            except Exception as e:
                logger.error(f"Error setting actor rotation: {e}")
                results["rotation_error"] = str(e)
        
        # Set scale if any scale factor is provided
        if any(param is not None for param in [scale_x, scale_y, scale_z]):
            # Get current scale first for factors that weren't specified
            get_scale_payload = {
                "objectPath": actor_path,
                "functionName": "GetActorScale3D"
            }
            
            try:
                response = requests.put(UE_URL, json=get_scale_payload, timeout=5)
                response.raise_for_status()
                current_scale = response.json().get("ReturnValue", {"X": 1, "Y": 1, "Z": 1})
                
                # Use current values for any scale factor not specified
                new_scale_x = scale_x if scale_x is not None else current_scale.get("X", 1)
                new_scale_y = scale_y if scale_y is not None else current_scale.get("Y", 1)
                new_scale_z = scale_z if scale_z is not None else current_scale.get("Z", 1)
                
                # Set the new scale
                set_scale_payload = {
                    "objectPath": actor_path,
                    "functionName": "SetActorScale3D",
                    "parameters": {
                        "NewScale3D": {"X": new_scale_x, "Y": new_scale_y, "Z": new_scale_z}
                    }
                }
                
                response = requests.put(UE_URL, json=set_scale_payload, timeout=5)
                response.raise_for_status()
                modified = True
                
                # If this is a snowman, also include the actual dimensions
                if "Snowman_BP" in actor_path:
                    results["scale"] = {
                        "x": new_scale_x, 
                        "y": new_scale_y, 
                        "z": new_scale_z,
                        "actual_dimensions_cm": {
                            "width": SNOWMAN_WIDTH * new_scale_x,
                            "length": SNOWMAN_LENGTH * new_scale_y
                        }
                    }
                else:
                    results["scale"] = {"x": new_scale_x, "y": new_scale_y, "z": new_scale_z}
                
            except Exception as e:
                logger.error(f"Error setting actor scale: {e}")
                results["scale_error"] = str(e)
        
        # Set name if provided
        if name is not None:
            try:
                set_name_payload = {
                    "objectPath": actor_path,
                     "functionName": "SetActorLabel",
                    "parameters": {
                        "NewActorLabel": name
                    }
                }
                
                response = requests.put(UE_URL, json=set_name_payload, timeout=5)
                response.raise_for_status()
                modified = True
                results["name"] = name
                
            except Exception as e:
                logger.error(f"Error setting actor name: {e}")
                results["name_error"] = str(e)
        
        if modified:
            return json.dumps({
                "success": True,
                "actor_path": actor_path,
                "modified": results
            }, indent=2)
        else:
            return json.dumps({
                "success": False,
                "actor_path": actor_path,
                "error": "No modifications were specified",
                "results": results
            }, indent=2)
            
    except Exception as e:
        logger.error(f"Error in modify_actor: {str(e)}")
        logger.error(traceback.format_exc())
        return json.dumps({
            "success": False,
            "error": str(e)
        }, indent=2)

# If this module is run directly, start the server
if __name__ == "__main__":
    try:
        logger.info("Starting Unreal Engine MCP server...")
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Error running Unreal Engine MCP server: {str(e)}")
        traceback.print_exc()