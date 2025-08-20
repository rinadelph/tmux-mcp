# Tmux MCP Server

A comprehensive tmux control system implementing the Model Context Protocol (MCP) for seamless integration with Claude Desktop and other MCP-compatible clients. This project provides multiple interfaces for tmux session management, including a GUI application, UV-based async implementation, and a full MCP stdio server.

## 🚀 Features

### MCP Server (tmux_mcp_server.py)
- **Full MCP Protocol Implementation**: JSON-RPC 2.0 over stdio
- **Tools**: 
  - `list_tmux_sessions`: List all active tmux sessions
  - `send_message_to_session`: Send messages to specific sessions
  - `start_message_timer`: Set up repeated message sending
  - `stop_message_timer`: Stop active timers
  - `start_auto_cycle`: Start automated exit/continue cycles
  - `stop_auto_cycle`: Stop active cycles
  - `send_ctrl_c`: Send Ctrl+C signals to sessions
- **Resources**:
  - `tmux://sessions`: Real-time session information
  - `tmux://timers`: Active timer status
  - `tmux://cycles`: Auto-cycle status
- **Prompts**: Pre-defined templates for common operations

### GUI Applications
- **tmux_messenger.py**: Threading-based GUI with Tkinter
- **tmux_messenger_uv.py**: High-performance UV (libuv) event loop implementation

## 📋 Requirements

- Python 3.8+
- tmux installed on system
- MCP SDK (`mcp>=0.9.0`)
- pyuv library (for UV version)
- tkinter (usually comes with Python)

## 🔧 Installation

### Using pip
```bash
pip install -r requirements.txt
```

### Using uv (recommended for MCP server)
```bash
uv sync
```

## 🎯 Usage

### MCP Server (Recommended)

#### Run directly via stdio
```bash
python tmux_mcp_server.py
```

#### Install in Claude Desktop
1. Copy the configuration to Claude Desktop's config directory:
```bash
# macOS
cp claude_desktop_config.json ~/Library/Application\ Support/Claude/claude_desktop_config.json

# Linux
cp claude_desktop_config.json ~/.config/Claude/claude_desktop_config.json

# Windows
copy claude_desktop_config.json %APPDATA%\Claude\claude_desktop_config.json
```

2. Restart Claude Desktop

3. The tmux server will be available in Claude's MCP tools

#### Using with MCP Inspector
```bash
# Test the server
npx @modelcontextprotocol/inspector python tmux_mcp_server.py
```

### GUI Applications

#### Original Version (threading-based)
```bash
python tmux_messenger.py
```

#### UV Version (libuv-based)
```bash
python tmux_messenger_uv.py
```

## 🏗️ Architecture

### MCP Server Architecture
```
Client (Claude) <-> JSON-RPC 2.0 <-> stdio <-> MCP Server <-> tmux
```

The MCP server:
- Reads JSON-RPC messages from stdin
- Writes responses to stdout  
- Logs to stderr (critical for MCP protocol compliance)
- Manages async tasks for timers and cycles
- Provides real-time resources via URI scheme

### UV Implementation
- `pyuv.Loop`: Main event loop
- `pyuv.Process`: Non-blocking process spawning
- `pyuv.Timer`: Precise timer operations
- `pyuv.Pipe`: Process I/O handling
- `pyuv.StdIO`: stdio configuration

## 🔄 Auto-Cycle Sequence

The auto-cycle feature performs:
1. Send Ctrl+C 5 times (200ms apart)
2. Wait 1 second
3. Execute `mullvad reconnect`
4. Wait 3 seconds
5. Execute `claudex -c`
6. Repeat every 4 minutes (configurable)

## 🛠️ Development

### Running Tests
```bash
pytest tests/
```

### Type Checking
```bash
pyright tmux_mcp_server.py
```

### Linting
```bash
ruff check .
ruff format .
```

## 📝 MCP Protocol Details

### Message Format
All messages follow JSON-RPC 2.0 specification:
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "send_message_to_session",
    "arguments": {
      "session_name": "main",
      "message": "echo 'Hello from MCP'"
    }
  },
  "id": 1
}
```

### Resources
Resources are accessed via URI scheme:
- `tmux://sessions` - List of current sessions
- `tmux://timers` - Active timer information
- `tmux://cycles` - Auto-cycle status

### Error Handling
- All errors are logged to stderr
- Tools return structured error responses
- Async operations are properly cancelled on shutdown

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Implement your changes with tests
4. Ensure type checking and linting pass
5. Submit a pull request

## 📄 License

MIT License - See LICENSE file for details

## 🔗 Related Projects

- [Model Context Protocol](https://modelcontextprotocol.io)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [libuv](https://libuv.org)
