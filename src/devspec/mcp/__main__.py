"""Entry point for devspec MCP server. Run with: python -m devspec.mcp"""

from devspec.mcp.server import mcp

mcp.run(transport="stdio")
