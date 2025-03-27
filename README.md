# MCP Pydantic AI Integration

A project that integrates the Model Context Protocol (MCP) with Pydantic AI to create intelligent agents with tool-using capabilities.

## Overview

This project demonstrates how to use the Model Context Protocol (MCP) with Pydantic AI to build agent applications that can interact with various tools and services. The implementation includes:

- Integration with filesystem tools via MCP
- Integration with Brave Search API
- Support for OpenAI and Gemini models
- A simple CLI chat interface

## Prerequisites

- Python 3.8+
- Node.js (for MCP filesystem server)
- Docker (for Brave Search MCP server)
- OpenAI API key or Gemini API key (depending on the model choice)

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd mcp_intro
   ```

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables in `.env` file:
   ```
   OPENAI_API_KEY=your_openai_api_key
   GEMINI_API_KEY=your_gemini_api_key
   MODEL_CHOICE=gpt-4o-mini  # or gemini-2.0-flash
   BRAVE_API_KEY=your_brave_api_key
   ```

## Project Structure

- `pydantic_mcp_agent.py`: Main agent implementation with CLI chat interface
- `mcp_client.py`: Client implementation for MCP servers
- `mcp_config.json`: Configuration for MCP servers
- `.env`: Environment variables (API keys, model choice)

## Usage

Run the CLI chat interface:

```bash
python pydantic_mcp_agent.py
```

This will start a chat session where you can interact with the agent. The agent can use tools from the configured MCP servers to help answer your questions.

## MCP Servers

The project is configured to use the following MCP servers:

1. **Filesystem Server**: Provides access to local filesystem operations
   - Implementation: `@modelcontextprotocol/server-filesystem`
   - Configuration in `mcp_config.json`

2. **Brave Search Server**: Provides web search capabilities
   - Implementation: Docker container `mcp/brave-search`
   - Requires Brave API key in environment variables

## Customization

You can modify the `mcp_config.json` file to add or remove MCP servers. Each server requires:
- A unique name
- Command to start the server
- Arguments for the command
- Optional environment variables

## Model Selection

The agent can use either OpenAI or Gemini models. The model choice is configured in:
1. The `.env` file via the `MODEL_CHOICE` variable
2. Directly in the code by uncommenting the appropriate line in `get_pydantic_ai_agent()`

## License



## Contributing


