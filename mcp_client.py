from pydantic_ai import RunContext, Tool as PydanticTool
from pydantic_ai.tools import ToolDefinition
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import Tool as MCPTool
from contextlib import AsyncExitStack
from typing import Any, List
import asyncio
import logging
import shutil
import json
import os

# Configure logging to INFO level to capture tool calls and other details
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def sanitize_schema_for_gemini(schema: dict) -> dict:
    cleaned_schema = schema.copy()
    # Remove fields Gemini doesn't support
    for key in ["$schema", "$id", "title", "description", "additionalProperties", "default"]:
        cleaned_schema.pop(key, None)
    
    if "type" in cleaned_schema:
        cleaned_schema["type"] = cleaned_schema["type"].upper()
    if "properties" in cleaned_schema:
        for prop in cleaned_schema["properties"].values():
            if "type" in prop:
                prop["type"] = prop["type"].upper()
            # Recursively clean nested properties
            prop.pop("additionalProperties", None)
            prop.pop("default", None)
            if "items" in prop:
                prop["items"].pop("additionalProperties", None)
    
    return cleaned_schema

class MCPClient:
    """Manages connections to one or more MCP servers based on mcp_config.json"""

    def __init__(self) -> None:
        self.servers: List[MCPServer] = []
        self.config: dict[str, Any] = {}
        self.tools: List[PydanticTool] = []
        self.exit_stack = AsyncExitStack()

    def load_servers(self, config_path: str) -> None:
        """Load server configuration from a JSON file."""
        with open(config_path, "r") as config_file:
            self.config = json.load(config_file)
        self.servers = [MCPServer(name, config) for name, config in self.config["mcpServers"].items()]
        logging.info(f"Loaded servers: {[type(s).__name__ for s in self.servers]}")
        logging.info(f"Server names: {[s.name for s in self.servers]}")

    async def start(self) -> List[PydanticTool]:
        """Starts each MCP server and returns tools formatted for Pydantic AI."""
        self.tools = []
        logging.info("Starting MCP servers...")
        for server in self.servers:
            try:
                await server.initialize()
                tools = await server.create_pydantic_ai_tools()
                self.tools.extend(tools)
            except Exception as e:
                logging.error(f"Failed to start server {server.name}: {e}")
                raise  # Re-raise to halt execution and debug
        return self.tools

    async def cleanup_servers(self) -> None:
        """Clean up all servers properly."""
        for server in self.servers:
            try:
                await server.cleanup()
            except Exception as e:
                logging.warning(f"Warning during cleanup of server {server.name}: {e}")

    async def cleanup(self) -> None:
        """Clean up all resources including the exit stack."""
        try:
            await self.cleanup_servers()
            await self.exit_stack.aclose()
        except Exception as e:
            logging.warning(f"Warning during final cleanup: {e}")

class MCPServer:
    """Manages MCP server connections and tool execution."""

    def __init__(self, name: str, config: dict[str, Any]) -> None:
        self.name: str = name
        self.config: dict[str, Any] = config
        self.session: ClientSession | None = None
        self._cleanup_lock: asyncio.Lock = asyncio.Lock()
        self.exit_stack: AsyncExitStack = AsyncExitStack()

    async def initialize(self) -> None:
        """Initialize the server connection."""
        command = shutil.which(self.config["command"]) or self.config["command"]
        if not command:
            raise ValueError(f"Invalid command: {self.config['command']}")

        server_params = StdioServerParameters(
            command=command,
            args=self.config["args"],
            env=self.config["env"] if self.config.get("env") else None,
        )
        try:
            stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
            read, write = stdio_transport
            session = await self.exit_stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            self.session = session
        except Exception as e:
            logging.error(f"Error initializing server {self.name}: {e}")
            await self.cleanup()
            raise

    async def create_pydantic_ai_tools(self) -> List[PydanticTool]:
        """Convert MCP tools to Pydantic AI Tools."""
        if not self.session:
            raise ValueError(f"Server {self.name} is not initialized")
        
        # Get the ListToolsResult object from list_tools()
        tools_result = await self.session.list_tools()
        logging.info(f"Tools result for server {self.name}: {tools_result}")
        
        # Extract the tools list from the ListToolsResult object
        if hasattr(tools_result, "tools"):
            tools = tools_result.tools
        else:
            logging.error(f"No 'tools' attribute found in ListToolsResult for server {self.name}")
            return []
        
        # Log the type and contents for debugging
        if tools:
            logging.info(f"Type of tools: {type(tools)}")
            logging.info(f"First tool: {tools[0]}")
        else:
            logging.info(f"No tools returned for server {self.name}")
        
        # Convert tools to PydanticTool instances
        return [self.create_tool_instance(tool) for tool in tools]

    def create_tool_instance(self, tool: Any) -> PydanticTool:
        """Initialize a Pydantic AI Tool from an MCP Tool."""
        # Ensure tool has required attributes
        if not hasattr(tool, 'name') or not hasattr(tool, 'inputSchema'):
            raise ValueError(f"Tool object missing required attributes: {tool}")
        
        name = tool.name
        description = getattr(tool, 'description', "") or ""
        input_schema = tool.inputSchema

        async def execute_tool(**kwargs: Any) -> Any:
            logging.info(f"Server {self.name}: Calling tool: {name} with arguments: {kwargs}")
            return await self.session.call_tool(name, arguments=kwargs)

        async def prepare_tool(ctx: RunContext, tool_def: ToolDefinition) -> ToolDefinition | None:
            cleaned_schema = sanitize_schema_for_gemini(input_schema)
            tool_def.parameters_json_schema = cleaned_schema
            return tool_def
        
        return PydanticTool(
            execute_tool,
            name=name,
            description=description,
            takes_ctx=False,
            prepare=prepare_tool
        )

    async def cleanup(self) -> None:
        """Clean up server resources."""
        async with self._cleanup_lock:
            try:
                await self.exit_stack.aclose()
                self.session = None
            except Exception as e:
                logging.error(f"Error during cleanup of server {self.name}: {e}")

# # Example usage
# async def main():
#     client = MCPClient()
#     config_path = "mcp_config.json"  # Adjust path as needed
#     client.load_servers(config_path)
#     try:
#         tools = await client.start()
#         logging.info(f"Started with tools: {[tool.name for tool in tools]}")
#     except Exception as e:
#         logging.error(f"Error in main: {e}")
#     finally:
#         await client.cleanup()

# if __name__ == "__main__":
#     asyncio.run(main())