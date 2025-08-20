#!/usr/bin/env python3
"""
Tmux MCP Server - Model Context Protocol server for tmux control
Provides tools and resources for managing tmux sessions via MCP
"""

import asyncio
import json
import sys
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

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
    name="Tmux Control Server",
    instructions="""
    This MCP server provides tools for controlling and managing tmux sessions.
    It allows you to list sessions, send messages, manage timers, and perform
    automated sequences like the exit/continue cycle.
    """
)

# Global state for timers and cycles
active_timers: Dict[str, asyncio.Task] = {}
active_cycles: Dict[str, asyncio.Task] = {}


# --- Resources ---

@mcp.resource("tmux://sessions")
async def list_sessions_resource() -> str:
    """Get current tmux sessions as a resource"""
    try:
        proc = await asyncio.create_subprocess_exec(
            'tmux', 'list-sessions',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            return json.dumps({"error": "No tmux sessions found", "sessions": []})
        
        sessions = []
        for line in stdout.decode().strip().split('\n'):
            if line:
                parts = line.split(':')
                session_name = parts[0]
                session_info = ':'.join(parts[1:]) if len(parts) > 1 else ""
                sessions.append({
                    "name": session_name,
                    "info": session_info.strip(),
                    "full_line": line
                })
        
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "count": len(sessions),
            "sessions": sessions
        }, indent=2)
    except Exception as e:
        logger.error(f"Error listing sessions: {e}")
        return json.dumps({"error": str(e), "sessions": []})


@mcp.resource("tmux://timers")
async def get_active_timers() -> str:
    """Get information about active timers"""
    timer_info = []
    for session_name, task in active_timers.items():
        timer_info.append({
            "session": session_name,
            "active": not task.done(),
            "cancelled": task.cancelled()
        })
    
    return json.dumps({
        "timestamp": datetime.now().isoformat(),
        "active_timers": timer_info
    }, indent=2)


@mcp.resource("tmux://cycles")
async def get_active_cycles() -> str:
    """Get information about active auto-cycles"""
    cycle_info = []
    for session_name, task in active_cycles.items():
        cycle_info.append({
            "session": session_name,
            "active": not task.done(),
            "cancelled": task.cancelled()
        })
    
    return json.dumps({
        "timestamp": datetime.now().isoformat(),
        "active_cycles": cycle_info
    }, indent=2)


# --- Tools ---

@mcp.tool()
async def list_tmux_sessions(ctx: Context) -> List[Dict[str, str]]:
    """
    List all active tmux sessions
    
    Returns a list of session information including name and details
    """
    await ctx.info("Listing tmux sessions")
    
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
                sessions.append({
                    "name": session_name,
                    "info": session_info.strip(),
                    "full_line": line
                })
        
        await ctx.info(f"Found {len(sessions)} tmux sessions")
        return sessions
        
    except Exception as e:
        await ctx.error(f"Error listing sessions: {str(e)}")
        raise


@mcp.tool()
async def send_message_to_session(
    session_name: str,
    message: str,
    ctx: Context
) -> Dict[str, Any]:
    """
    Send a message to a specific tmux session
    
    Types the message, waits 1 second, then presses Enter
    
    Args:
        session_name: Name of the tmux session
        message: Message to send
    
    Returns success status and details
    """
    await ctx.info(f"Sending message to session '{session_name}': {message}")
    
    try:
        # Send the message (just type it)
        proc1 = await asyncio.create_subprocess_exec(
            'tmux', 'send-keys', '-t', session_name, message,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        _, stderr1 = await proc1.communicate()
        
        if proc1.returncode != 0:
            error_msg = stderr1.decode().strip()
            await ctx.error(f"Failed to send message: {error_msg}")
            return {"success": False, "error": error_msg}
        
        # Wait 1 second
        await asyncio.sleep(1)
        
        # Send Enter key
        proc2 = await asyncio.create_subprocess_exec(
            'tmux', 'send-keys', '-t', session_name, 'Enter',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await proc2.communicate()
        
        await ctx.info(f"Message sent successfully to '{session_name}'")
        return {
            "success": True,
            "session": session_name,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        await ctx.error(f"Error sending message: {str(e)}")
        return {"success": False, "error": str(e)}


@mcp.tool()
async def start_message_timer(
    session_name: str,
    message: str,
    interval_seconds: float,
    ctx: Context
) -> Dict[str, Any]:
    """
    Start a timer to repeatedly send a message to a tmux session
    
    Args:
        session_name: Name of the tmux session
        message: Message to send repeatedly
        interval_seconds: Interval between messages in seconds
    
    Returns timer status information
    """
    global active_timers
    
    # Stop existing timer for this session if any
    if session_name in active_timers:
        active_timers[session_name].cancel()
        await ctx.info(f"Cancelled existing timer for '{session_name}'")
    
    await ctx.info(f"Starting timer for '{session_name}' with {interval_seconds}s interval")
    
    async def timer_loop():
        while True:
            try:
                # Send message
                proc1 = await asyncio.create_subprocess_exec(
                    'tmux', 'send-keys', '-t', session_name, message,
                    stderr=asyncio.subprocess.PIPE
                )
                await proc1.communicate()
                
                # Send Enter
                proc2 = await asyncio.create_subprocess_exec(
                    'tmux', 'send-keys', '-t', session_name, 'C-m',
                    stderr=asyncio.subprocess.PIPE
                )
                await proc2.communicate()
                
                await asyncio.sleep(interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Timer error: {e}")
                break
    
    # Create and store the timer task
    task = asyncio.create_task(timer_loop())
    active_timers[session_name] = task
    
    return {
        "success": True,
        "session": session_name,
        "message": message,
        "interval": interval_seconds,
        "status": "started"
    }


@mcp.tool()
async def stop_message_timer(
    session_name: str,
    ctx: Context
) -> Dict[str, Any]:
    """
    Stop an active message timer for a tmux session
    
    Args:
        session_name: Name of the tmux session
    
    Returns status information
    """
    global active_timers
    
    if session_name not in active_timers:
        await ctx.warning(f"No active timer for session '{session_name}'")
        return {
            "success": False,
            "error": f"No active timer for session '{session_name}'"
        }
    
    active_timers[session_name].cancel()
    del active_timers[session_name]
    
    await ctx.info(f"Stopped timer for session '{session_name}'")
    return {
        "success": True,
        "session": session_name,
        "status": "stopped"
    }


@mcp.tool()
async def start_auto_cycle(
    session_name: str,
    ctx: Context,
    initial_delay_seconds: float = 0,
    cycle_interval_minutes: float = 4
) -> Dict[str, Any]:
    """
    Start auto exit/continue cycle for a tmux session
    
    This performs:
    1. Send Ctrl+C 5 times (200ms apart)
    2. Wait 1 second
    3. Execute 'mullvad reconnect'
    4. Wait 3 seconds
    5. Execute 'claudex -c'
    6. Repeat every cycle_interval_minutes
    
    Args:
        session_name: Name of the tmux session
        initial_delay_seconds: Initial delay before first cycle (default: 0)
        cycle_interval_minutes: Minutes between cycles (default: 4)
    
    Returns cycle status information
    """
    global active_cycles
    
    # Stop existing cycle for this session if any
    if session_name in active_cycles:
        active_cycles[session_name].cancel()
        await ctx.info(f"Cancelled existing cycle for '{session_name}'")
    
    await ctx.info(f"Starting auto-cycle for '{session_name}'")
    
    async def execute_sequence():
        """Execute the exit/continue sequence"""
        # Send Ctrl+C 5 times
        for i in range(5):
            proc = await asyncio.create_subprocess_exec(
                'tmux', 'send-keys', '-t', session_name, 'C-c',
                stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()
            await asyncio.sleep(0.2)
        
        # Wait 1 second
        await asyncio.sleep(1)
        
        # Send mullvad reconnect
        proc1 = await asyncio.create_subprocess_exec(
            'tmux', 'send-keys', '-t', session_name, 'mullvad reconnect',
            stderr=asyncio.subprocess.PIPE
        )
        await proc1.communicate()
        
        proc2 = await asyncio.create_subprocess_exec(
            'tmux', 'send-keys', '-t', session_name, 'Enter',
            stderr=asyncio.subprocess.PIPE
        )
        await proc2.communicate()
        
        # Wait 3 seconds
        await asyncio.sleep(3)
        
        # Send claudex -c
        proc3 = await asyncio.create_subprocess_exec(
            'tmux', 'send-keys', '-t', session_name, 'claudex -c',
            stderr=asyncio.subprocess.PIPE
        )
        await proc3.communicate()
        
        proc4 = await asyncio.create_subprocess_exec(
            'tmux', 'send-keys', '-t', session_name, 'Enter',
            stderr=asyncio.subprocess.PIPE
        )
        await proc4.communicate()
        
        await ctx.report_progress(
            progress=1.0,
            message=f"Completed cycle for '{session_name}'"
        )
    
    async def cycle_loop():
        # Initial delay if specified
        if initial_delay_seconds > 0:
            await asyncio.sleep(initial_delay_seconds)
        
        while True:
            try:
                await execute_sequence()
                # Wait for next cycle
                await asyncio.sleep(cycle_interval_minutes * 60)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cycle error: {e}")
                break
    
    # Create and store the cycle task
    task = asyncio.create_task(cycle_loop())
    active_cycles[session_name] = task
    
    return {
        "success": True,
        "session": session_name,
        "initial_delay": initial_delay_seconds,
        "cycle_interval_minutes": cycle_interval_minutes,
        "status": "started"
    }


@mcp.tool()
async def stop_auto_cycle(
    session_name: str,
    ctx: Context
) -> Dict[str, Any]:
    """
    Stop an active auto-cycle for a tmux session
    
    Args:
        session_name: Name of the tmux session
    
    Returns status information
    """
    global active_cycles
    
    if session_name not in active_cycles:
        await ctx.warning(f"No active cycle for session '{session_name}'")
        return {
            "success": False,
            "error": f"No active cycle for session '{session_name}'"
        }
    
    active_cycles[session_name].cancel()
    del active_cycles[session_name]
    
    await ctx.info(f"Stopped auto-cycle for session '{session_name}'")
    return {
        "success": True,
        "session": session_name,
        "status": "stopped"
    }


@mcp.tool()
async def launch_agent(
    agent: str,
    session_name: str,
    ctx: Context
) -> Dict[str, Any]:
    """
    Launch an AI agent in a tmux session
    
    Supported agents:
    - gemini: Launch Gemini CLI
    - claude: Launch Claude CLI  
    - codex: Launch Codex CLI
    - swarm: Launch SwarmCode
    
    Args:
        agent: The agent to launch (gemini, claude, codex, or swarm)
        session_name: Name of the tmux session to launch in
    
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
        
        await ctx.info(f"Successfully launched {agent} in '{session_name}'")
        return {
            "success": True,
            "agent": agent,
            "command": command,
            "session": session_name,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        await ctx.error(f"Error launching {agent}: {str(e)}")
        return {"success": False, "error": str(e)}


@mcp.tool()
async def send_ctrl_c(
    session_name: str,
    ctx: Context,
    count: int = 1
) -> Dict[str, Any]:
    """
    Send Ctrl+C to a tmux session
    
    Args:
        session_name: Name of the tmux session
        count: Number of times to send Ctrl+C (default: 1)
    
    Returns success status
    """
    await ctx.info(f"Sending Ctrl+C {count} times to '{session_name}'")
    
    try:
        for i in range(count):
            proc = await asyncio.create_subprocess_exec(
                'tmux', 'send-keys', '-t', session_name, 'C-c',
                stderr=asyncio.subprocess.PIPE
            )
            _, stderr = await proc.communicate()
            
            if proc.returncode != 0:
                error_msg = stderr.decode().strip()
                await ctx.error(f"Failed to send Ctrl+C: {error_msg}")
                return {"success": False, "error": error_msg, "sent": i}
            
            if i < count - 1:
                await asyncio.sleep(0.1)
        
        return {
            "success": True,
            "session": session_name,
            "count": count
        }
        
    except Exception as e:
        await ctx.error(f"Error sending Ctrl+C: {str(e)}")
        return {"success": False, "error": str(e)}


# --- Prompts ---

@mcp.prompt(title="Quick Message")
def quick_message_prompt(session_name: str, message: str) -> str:
    """Send a quick message to a tmux session"""
    return f"""Please send the following message to tmux session '{session_name}':

Message: {message}

Use the send_message_to_session tool to accomplish this."""


@mcp.prompt(title="Setup Timer")
def setup_timer_prompt(session_name: str, message: str, interval: str) -> List[base.Message]:
    """Setup a message timer for a tmux session"""
    return [
        base.UserMessage(f"I want to set up a timer for tmux session '{session_name}'"),
        base.UserMessage(f"Message to send: {message}"),
        base.UserMessage(f"Interval: {interval} seconds"),
        base.AssistantMessage("I'll set up a timer to send that message repeatedly. Let me start that for you.")
    ]


@mcp.prompt(title="Manage Auto Cycle")
def manage_auto_cycle_prompt(action: str, session_name: str) -> str:
    """Manage auto-cycle for a tmux session"""
    if action.lower() == "start":
        return f"""Please start the auto exit/continue cycle for tmux session '{session_name}'.

This should:
1. Send Ctrl+C 5 times
2. Wait 1 second
3. Execute 'mullvad reconnect'
4. Wait 3 seconds
5. Execute 'claudex -c'
6. Repeat every 4 minutes

Use the start_auto_cycle tool."""
    else:
        return f"Please stop the auto-cycle for tmux session '{session_name}' using the stop_auto_cycle tool."


@mcp.prompt(title="Launch AI Agent")
def launch_agent_prompt(agent: str, session_name: str) -> str:
    """Launch an AI agent in a tmux session"""
    return f"""Please launch the {agent} agent in tmux session '{session_name}'.

Available agents:
- gemini: Gemini CLI
- claude: Claude CLI  
- codex: Codex CLI
- swarm: SwarmCode (uses 'swarmcode' command)

Use the launch_agent tool to start the agent."""


# Main entry point
if __name__ == "__main__":
    # Run the MCP server using stdio transport
    # This is the standard way to run MCP servers for Claude Desktop
    mcp.run(transport="stdio")