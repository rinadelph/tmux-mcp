#!/usr/bin/env python3
"""
Tmux MCP Server with Agent Channels - Model Context Protocol server for tmux control
Includes invisible Unicode character tagging for agent communication channels
"""

import asyncio
import json
import sys
import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from enum import Enum

from mcp.server.fastmcp import FastMCP, Context
from mcp.server.fastmcp.prompts import base
import mcp.types as types

# Set up logging to stderr (important for MCP stdio servers)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr  # Critical: logs must go to stderr, not stdout
)
logger = logging.getLogger(__name__)

# Create the MCP server
mcp = FastMCP(
    name="Tmux Agent Channel Control",
    instructions="""
    This MCP server provides tools for controlling tmux sessions with agent channel support.
    It uses invisible Unicode characters to tag sessions for different communication channels,
    allowing agents to communicate or be isolated from each other.
    """
)

# Agent Channel System using Zero-Width Unicode Characters
class AgentChannel(Enum):
    """
    Different channels using zero-width Unicode characters
    These are invisible but can be detected programmatically
    """
    CHANNEL_A = '\u200B'  # Zero Width Space - Channel A
    CHANNEL_B = '\u200C'  # Zero Width Non-Joiner - Channel B  
    CHANNEL_C = '\u200D'  # Zero Width Joiner - Channel C
    CHANNEL_D = '\u2060'  # Word Joiner - Channel D
    CHANNEL_E = '\uFEFF'  # Zero Width No-Break Space - Channel E
    BROADCAST = '\u200E'  # Left-to-Right Mark - Broadcast to all
    ISOLATED = '\u200F'  # Right-to-Left Mark - Isolated/No communication

# Channel descriptions for user understanding
CHANNEL_DESCRIPTIONS = {
    AgentChannel.CHANNEL_A: "Primary communication channel",
    AgentChannel.CHANNEL_B: "Secondary communication channel",
    AgentChannel.CHANNEL_C: "Tertiary communication channel",
    AgentChannel.CHANNEL_D: "Quaternary communication channel",
    AgentChannel.CHANNEL_E: "Emergency/Priority channel",
    AgentChannel.BROADCAST: "Broadcast to all agents",
    AgentChannel.ISOLATED: "Isolated - no inter-agent communication"
}

# Global state for managing agent sessions
agent_sessions: Dict[str, str] = {}  # session_name -> channel_char mapping


def get_channel_from_session(session_name: str) -> Optional[AgentChannel]:
    """Extract channel identifier from session name"""
    for channel in AgentChannel:
        if channel.value in session_name:
            return channel
    return None


def clean_session_name(session_name: str) -> str:
    """Remove all channel identifiers from session name"""
    clean_name = session_name
    for channel in AgentChannel:
        clean_name = clean_name.replace(channel.value, '')
    return clean_name


def add_channel_to_session(session_name: str, channel: AgentChannel) -> str:
    """Add channel identifier to session name"""
    # Remove any existing channel markers first
    clean_name = clean_session_name(session_name)
    # Add the new channel marker at the end
    return f"{clean_name}{channel.value}"


# --- Resources ---

@mcp.resource("tmux://agent-channels")
async def get_agent_channels() -> str:
    """Get information about agent sessions and their channels"""
    try:
        proc = await asyncio.create_subprocess_exec(
            'tmux', 'list-sessions',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            return json.dumps({"error": "No tmux sessions found", "channels": {}})
        
        channels_info = {
            "broadcast": [],
            "channel_a": [],
            "channel_b": [],
            "channel_c": [],
            "channel_d": [],
            "channel_e": [],
            "isolated": [],
            "untagged": []
        }
        
        for line in stdout.decode().strip().split('\n'):
            if line:
                session_name = line.split(':')[0]
                channel = get_channel_from_session(session_name)
                clean_name = clean_session_name(session_name)
                
                if channel == AgentChannel.BROADCAST:
                    channels_info["broadcast"].append(clean_name)
                elif channel == AgentChannel.CHANNEL_A:
                    channels_info["channel_a"].append(clean_name)
                elif channel == AgentChannel.CHANNEL_B:
                    channels_info["channel_b"].append(clean_name)
                elif channel == AgentChannel.CHANNEL_C:
                    channels_info["channel_c"].append(clean_name)
                elif channel == AgentChannel.CHANNEL_D:
                    channels_info["channel_d"].append(clean_name)
                elif channel == AgentChannel.CHANNEL_E:
                    channels_info["channel_e"].append(clean_name)
                elif channel == AgentChannel.ISOLATED:
                    channels_info["isolated"].append(clean_name)
                else:
                    channels_info["untagged"].append(clean_name)
        
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "channels": channels_info,
            "descriptions": {k.name: v for k, v in CHANNEL_DESCRIPTIONS.items()}
        }, indent=2)
        
    except Exception as e:
        logger.error(f"Error getting agent channels: {e}")
        return json.dumps({"error": str(e), "channels": {}})


# --- Tools ---

@mcp.tool()
async def create_agent_session(
    agent_name: str,
    channel: str,
    ctx: Context
) -> Dict[str, Any]:
    """
    Create a new tmux session for an agent with a specific channel
    
    Args:
        agent_name: Name for the agent session (visible part)
        channel: Channel identifier (A, B, C, D, E, BROADCAST, or ISOLATED)
    
    Returns success status and session details
    """
    # Map string input to channel enum
    channel_map = {
        'A': AgentChannel.CHANNEL_A,
        'B': AgentChannel.CHANNEL_B,
        'C': AgentChannel.CHANNEL_C,
        'D': AgentChannel.CHANNEL_D,
        'E': AgentChannel.CHANNEL_E,
        'BROADCAST': AgentChannel.BROADCAST,
        'ISOLATED': AgentChannel.ISOLATED
    }
    
    channel_enum = channel_map.get(channel.upper())
    if not channel_enum:
        await ctx.error(f"Invalid channel: {channel}")
        return {
            "success": False,
            "error": f"Invalid channel. Choose from: {', '.join(channel_map.keys())}"
        }
    
    # Create session name with channel marker
    session_name = add_channel_to_session(agent_name, channel_enum)
    
    await ctx.info(f"Creating agent session '{agent_name}' on channel {channel}")
    
    try:
        proc = await asyncio.create_subprocess_exec(
            'tmux', 'new-session', '-d', '-s', session_name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            error_msg = stderr.decode().strip()
            await ctx.error(f"Failed to create session: {error_msg}")
            return {"success": False, "error": error_msg}
        
        agent_sessions[session_name] = channel_enum.value
        
        return {
            "success": True,
            "agent_name": agent_name,
            "session_name": session_name,
            "channel": channel,
            "channel_description": CHANNEL_DESCRIPTIONS[channel_enum],
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        await ctx.error(f"Error creating agent session: {str(e)}")
        return {"success": False, "error": str(e)}


@mcp.tool()
async def find_agents_in_channel(
    channel: str,
    ctx: Context
) -> List[Dict[str, str]]:
    """
    Find all agents in a specific communication channel
    
    Args:
        channel: Channel identifier (A, B, C, D, E, BROADCAST, or ISOLATED)
    
    Returns list of agents in the specified channel
    """
    channel_map = {
        'A': AgentChannel.CHANNEL_A,
        'B': AgentChannel.CHANNEL_B,
        'C': AgentChannel.CHANNEL_C,
        'D': AgentChannel.CHANNEL_D,
        'E': AgentChannel.CHANNEL_E,
        'BROADCAST': AgentChannel.BROADCAST,
        'ISOLATED': AgentChannel.ISOLATED
    }
    
    channel_enum = channel_map.get(channel.upper())
    if not channel_enum:
        await ctx.error(f"Invalid channel: {channel}")
        return []
    
    await ctx.info(f"Finding agents in channel {channel}")
    
    try:
        proc = await asyncio.create_subprocess_exec(
            'tmux', 'list-sessions',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            return []
        
        agents = []
        for line in stdout.decode().strip().split('\n'):
            if line:
                session_name = line.split(':')[0]
                session_channel = get_channel_from_session(session_name)
                
                if session_channel == channel_enum:
                    clean_name = clean_session_name(session_name)
                    agents.append({
                        "agent_name": clean_name,
                        "session_name": session_name,
                        "channel": channel,
                        "info": ':'.join(line.split(':')[1:]).strip()
                    })
        
        await ctx.info(f"Found {len(agents)} agents in channel {channel}")
        return agents
        
    except Exception as e:
        await ctx.error(f"Error finding agents: {str(e)}")
        return []


@mcp.tool()
async def broadcast_to_channel(
    channel: str,
    message: str,
    ctx: Context
) -> Dict[str, Any]:
    """
    Broadcast a message to all agents in a specific channel
    
    Args:
        channel: Channel to broadcast to (A, B, C, D, E, or BROADCAST for all)
        message: Message to broadcast
    
    Returns broadcast status and recipient count
    """
    agents = await find_agents_in_channel(channel, ctx)
    
    if channel.upper() == 'BROADCAST':
        # Also get all agents from all channels
        all_agents = []
        for ch in ['A', 'B', 'C', 'D', 'E']:
            all_agents.extend(await find_agents_in_channel(ch, ctx))
        agents = all_agents
    
    successful_sends = 0
    failed_sends = 0
    
    for agent in agents:
        try:
            # Send message to each agent
            proc1 = await asyncio.create_subprocess_exec(
                'tmux', 'send-keys', '-t', agent['session_name'], message,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc1.communicate()
            
            # Wait before sending Enter
            await asyncio.sleep(0.5)
            
            proc2 = await asyncio.create_subprocess_exec(
                'tmux', 'send-keys', '-t', agent['session_name'], 'Enter',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc2.communicate()
            
            if proc1.returncode == 0 and proc2.returncode == 0:
                successful_sends += 1
            else:
                failed_sends += 1
                
        except Exception as e:
            logger.error(f"Error sending to {agent['agent_name']}: {e}")
            failed_sends += 1
    
    await ctx.info(f"Broadcast complete: {successful_sends} successful, {failed_sends} failed")
    
    return {
        "success": successful_sends > 0,
        "channel": channel,
        "message": message,
        "recipients": len(agents),
        "successful_sends": successful_sends,
        "failed_sends": failed_sends,
        "timestamp": datetime.now().isoformat()
    }


@mcp.tool()
async def change_agent_channel(
    agent_name: str,
    new_channel: str,
    ctx: Context
) -> Dict[str, Any]:
    """
    Change an agent's communication channel
    
    Args:
        agent_name: Name of the agent (or current session name)
        new_channel: New channel (A, B, C, D, E, BROADCAST, or ISOLATED)
    
    Returns success status
    """
    channel_map = {
        'A': AgentChannel.CHANNEL_A,
        'B': AgentChannel.CHANNEL_B,
        'C': AgentChannel.CHANNEL_C,
        'D': AgentChannel.CHANNEL_D,
        'E': AgentChannel.CHANNEL_E,
        'BROADCAST': AgentChannel.BROADCAST,
        'ISOLATED': AgentChannel.ISOLATED
    }
    
    new_channel_enum = channel_map.get(new_channel.upper())
    if not new_channel_enum:
        await ctx.error(f"Invalid channel: {new_channel}")
        return {
            "success": False,
            "error": f"Invalid channel. Choose from: {', '.join(channel_map.keys())}"
        }
    
    await ctx.info(f"Changing agent '{agent_name}' to channel {new_channel}")
    
    try:
        # Find the current session
        proc = await asyncio.create_subprocess_exec(
            'tmux', 'list-sessions',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await proc.communicate()
        
        current_session = None
        for line in stdout.decode().strip().split('\n'):
            if line:
                session_name = line.split(':')[0]
                clean_name = clean_session_name(session_name)
                if clean_name == agent_name or session_name == agent_name:
                    current_session = session_name
                    break
        
        if not current_session:
            return {
                "success": False,
                "error": f"Agent session '{agent_name}' not found"
            }
        
        # Create new session name with new channel
        clean_name = clean_session_name(current_session)
        new_session_name = add_channel_to_session(clean_name, new_channel_enum)
        
        # Rename the tmux session
        proc = await asyncio.create_subprocess_exec(
            'tmux', 'rename-session', '-t', current_session, new_session_name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            error_msg = stderr.decode().strip()
            await ctx.error(f"Failed to change channel: {error_msg}")
            return {"success": False, "error": error_msg}
        
        # Update tracking
        if current_session in agent_sessions:
            del agent_sessions[current_session]
        agent_sessions[new_session_name] = new_channel_enum.value
        
        return {
            "success": True,
            "agent_name": clean_name,
            "old_session": current_session,
            "new_session": new_session_name,
            "new_channel": new_channel,
            "channel_description": CHANNEL_DESCRIPTIONS[new_channel_enum],
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        await ctx.error(f"Error changing channel: {str(e)}")
        return {"success": False, "error": str(e)}


# Include all the original tools from tmux_mcp_server.py
# (These are included for backward compatibility)

@mcp.tool()
async def list_tmux_sessions(ctx: Context) -> List[Dict[str, str]]:
    """
    List all active tmux sessions with channel information
    
    Returns a list of session information including name, channel, and details
    """
    await ctx.info("Listing tmux sessions with channels")
    
    try:
        proc = await asyncio.create_subprocess_exec(
            'tmux', 'list-sessions',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            await ctx.warning("No tmux sessions found")
            return []
        
        sessions = []
        for line in stdout.decode().strip().split('\n'):
            if line:
                parts = line.split(':')
                session_name = parts[0]
                session_info = ':'.join(parts[1:]) if len(parts) > 1 else ""
                
                channel = get_channel_from_session(session_name)
                clean_name = clean_session_name(session_name)
                
                session_data = {
                    "name": session_name,
                    "clean_name": clean_name,
                    "info": session_info.strip(),
                    "full_line": line
                }
                
                if channel:
                    session_data["channel"] = channel.name
                    session_data["channel_description"] = CHANNEL_DESCRIPTIONS[channel]
                
                sessions.append(session_data)
        
        await ctx.info(f"Found {len(sessions)} tmux sessions")
        return sessions
        
    except Exception as e:
        await ctx.error(f"Error listing sessions: {str(e)}")
        raise


@mcp.tool()
async def launch_agent(
    agent: str,
    session_name: str,
    channel: Optional[str],
    ctx: Context
) -> Dict[str, Any]:
    """
    Launch an AI agent in a tmux session with optional channel assignment
    
    Supported agents:
    - gemini: Launch Gemini CLI
    - claude: Launch Claude CLI  
    - codex: Launch Codex CLI
    - swarm: Launch SwarmCode
    
    Args:
        agent: The agent to launch (gemini, claude, codex, or swarm)
        session_name: Name of the tmux session to launch in
        channel: Optional channel (A, B, C, D, E, BROADCAST, or ISOLATED)
    
    Returns success status and details
    """
    # Map agent names to commands
    agent_commands = {
        "gemini": "gemini",
        "claude": "claude",
        "codex": "codex",
        "swarm": "swarmcode"
    }
    
    # Validate agent
    if agent.lower() not in agent_commands:
        await ctx.error(f"Unknown agent: {agent}. Supported: {', '.join(agent_commands.keys())}")
        return {
            "success": False,
            "error": f"Unknown agent: {agent}. Supported agents: gemini, claude, codex, swarm"
        }
    
    # Handle channel assignment if provided
    if channel:
        result = await change_agent_channel(session_name, channel, ctx)
        if result["success"]:
            session_name = result["new_session"]
    
    command = agent_commands[agent.lower()]
    await ctx.info(f"Launching {agent} in session '{session_name}' with command: {command}")
    
    try:
        # Send the command to launch the agent
        proc = await asyncio.create_subprocess_exec(
            'tmux', 'send-keys', '-t', session_name, command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            error_msg = stderr.decode().strip()
            await ctx.error(f"Failed to launch {agent}: {error_msg}")
            return {"success": False, "error": error_msg}
        
        # Wait a moment
        await asyncio.sleep(0.5)
        
        # Send Enter to execute
        proc2 = await asyncio.create_subprocess_exec(
            'tmux', 'send-keys', '-t', session_name, 'Enter',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await proc2.communicate()
        
        response = {
            "success": True,
            "agent": agent,
            "command": command,
            "session": session_name,
            "timestamp": datetime.now().isoformat()
        }
        
        if channel:
            response["channel"] = channel
        
        await ctx.info(f"Successfully launched {agent} in '{session_name}'")
        return response
        
    except Exception as e:
        await ctx.error(f"Error launching {agent}: {str(e)}")
        return {"success": False, "error": str(e)}


# --- Prompts ---

@mcp.prompt(title="Create Agent Network")
def create_agent_network_prompt(agents: List[str], channel: str) -> str:
    """Create a network of agents on the same channel"""
    agent_list = '\n'.join([f"- {agent}" for agent in agents])
    return f"""Please create the following agents on channel {channel}:

{agent_list}

This will allow them to communicate with each other.
Use the create_agent_session tool for each agent."""


@mcp.prompt(title="Isolate Agent")
def isolate_agent_prompt(agent_name: str) -> str:
    """Isolate an agent from all communications"""
    return f"""Please isolate agent '{agent_name}' from all other agents.

Change their channel to ISOLATED using the change_agent_channel tool.
This will prevent them from receiving or sending messages to other agents."""


@mcp.prompt(title="Setup Communication Bridge")
def setup_bridge_prompt(channel_a: str, channel_b: str) -> str:
    """Setup a communication bridge between two channels"""
    return f"""Please setup communication between channel {channel_a} and channel {channel_b}.

You'll need to:
1. Find agents in both channels using find_agents_in_channel
2. Create a bridge agent on BROADCAST channel
3. Route messages between the channels

This allows selective inter-channel communication."""


# Main entry point
if __name__ == "__main__":
    # Run the MCP server using stdio transport
    mcp.run(transport="stdio")