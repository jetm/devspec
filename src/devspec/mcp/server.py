"""devspec MCP server - FastMCP app instance and configuration."""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    name="devspec",
    instructions="Spec-driven development workflow engine. Use devspec tools to manage changes and artifacts.",
)

# Register tools and resources by importing them
import devspec.mcp.resources  # noqa: F401, E402
import devspec.mcp.tools  # noqa: F401, E402


def main():
    """Entry point for devspec-mcp console script."""
    mcp.run(transport="stdio")
