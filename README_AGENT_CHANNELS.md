# Tmux MCP Server - Agent Channels Edition (Testing Branch)

## 🚀 Agent Communication Channels Feature

This testing branch introduces **Agent Communication Channels** - a system for controlling inter-agent communication using invisible Unicode characters embedded in tmux session names.

### 🎯 Key Concepts

1. **Invisible Channel Markers**: Uses zero-width Unicode characters that are invisible to users but detectable programmatically
2. **Channel Isolation**: Agents can be isolated or grouped into communication channels
3. **Broadcast Capability**: Send messages to all agents in a channel or across all channels
4. **Dynamic Channel Switching**: Move agents between channels on the fly

### 📡 Available Channels

- **Channel A** (`\u200B`) - Primary communication channel
- **Channel B** (`\u200C`) - Secondary communication channel  
- **Channel C** (`\u200D`) - Tertiary communication channel
- **Channel D** (`\u2060`) - Quaternary communication channel
- **Channel E** (`\uFEFF`) - Emergency/Priority channel
- **BROADCAST** (`\u200E`) - Broadcast to all agents
- **ISOLATED** (`\u200F`) - No inter-agent communication

### 🛠️ New Tools

#### Agent Channel Management
- `create_agent_session`: Create an agent session with a specific channel
- `find_agents_in_channel`: Find all agents in a specific channel
- `broadcast_to_channel`: Send a message to all agents in a channel
- `change_agent_channel`: Move an agent to a different channel

#### Enhanced Original Tools
- `launch_agent`: Now supports optional channel assignment
- `list_tmux_sessions`: Shows channel information for each session

### 📦 New Resource
- `tmux://agent-channels`: Real-time channel membership information

## 🔧 Installation

### Testing Branch Setup
```bash
# Clone and checkout testing branch
git clone https://github.com/rinadelph/tmux-mcp.git
cd tmux-mcp
git checkout testing/agent-channels

# Install dependencies
pip install -r requirements.txt
```

### Add Agent Channels Server to Claude
```bash
# Add the agent channels version
claude mcp add --scope user --transport stdio tmux-agent-channels python "$(pwd)/tmux_mcp_agent_channels.py"
```

## 📖 Usage Examples

### Create Agent Network
```python
# Create three agents on the same channel for communication
create_agent_session("agent1", "A")
create_agent_session("agent2", "A") 
create_agent_session("agent3", "A")

# They can now communicate with each other
broadcast_to_channel("A", "Hello team!")
```

### Isolate an Agent
```python
# Isolate an agent from all communications
change_agent_channel("agent1", "ISOLATED")
```

### Multi-Channel Setup
```python
# Setup different teams on different channels
create_agent_session("frontend-agent", "B")
create_agent_session("backend-agent", "B")

create_agent_session("data-agent", "C")
create_agent_session("ml-agent", "C")

# Broadcast to specific teams
broadcast_to_channel("B", "Frontend/Backend sync meeting")
broadcast_to_channel("C", "Data pipeline update")
```

### Emergency Broadcast
```python
# Send urgent message to ALL agents
broadcast_to_channel("BROADCAST", "System maintenance in 5 minutes")
```

## 🏗️ Architecture

```
Agent Sessions with Channel Tags
├── Session Name: "agent1" + invisible unicode
├── Channel Detection: Programmatic scanning
├── Communication Rules:
│   ├── Same Channel → Can communicate
│   ├── Different Channels → Isolated
│   ├── BROADCAST → Receives all
│   └── ISOLATED → No communication
└── Dynamic Switching: Real-time channel changes
```

## 🧪 Testing

This is a testing branch for experimental features. Please report any issues or suggestions.

## ⚠️ Known Limitations

- Channel markers are invisible but still present in session names
- Some terminal emulators may have issues with zero-width characters
- Channel information persists only during tmux session lifetime

## 🔄 Merging to Main

Once testing is complete and stable:
```bash
git checkout master
git merge testing/agent-channels
git push origin master
```