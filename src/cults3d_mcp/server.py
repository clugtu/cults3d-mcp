"""Cults3D MCP server entry point."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from .client import Cults3DClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Server("cults3d-mcp")
_client: Cults3DClient | None = None


def _get_client() -> Cults3DClient:
    global _client
    if _client is None:
        _client = Cults3DClient()
    return _client


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="upload_design",
            description="Upload a new design (STL/ZIP) to Cults3D with metadata.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Design title"},
                    "description": {"type": "string", "description": "Full description (Markdown supported)"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags (e.g. ['miniature', 'dnd', 'dragon'])"},
                    "category": {"type": "string", "description": "Category slug (e.g. 'miniatures')"},
                    "license": {"type": "string", "description": "License slug (e.g. 'cc', 'cc-by', 'commercial')"},
                    "price": {"type": "number", "description": "Price in EUR (0 for free)"},
                    "file_path": {"type": "string", "description": "Absolute path to the STL or ZIP file"},
                    "thumbnail_path": {"type": "string", "description": "Path to the listing thumbnail image (JPEG/PNG). Required — Cults3D will not publish a design without at least one image."},
                    "dry_run": {"type": "boolean", "description": "If true, validate inputs and prepare the upload payload but do NOT submit to Cults3D. Use for testing.", "default": False},
                },
                "required": ["name", "description", "tags", "category", "license", "price", "file_path", "thumbnail_path"],
            },
        ),
        types.Tool(
            name="update_design",
            description="Update metadata on an existing Cults3D design.",
            inputSchema={
                "type": "object",
                "properties": {
                    "slug": {"type": "string", "description": "Design slug from the Cults3D URL"},
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "price": {"type": "number"},
                },
                "required": ["slug"],
            },
        ),
        types.Tool(
            name="list_my_designs",
            description="List all designs published under your account with stats.",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "default": 20},
                    "offset": {"type": "integer", "default": 0},
                },
            },
        ),
        types.Tool(
            name="get_design_stats",
            description="Get detailed stats for a design: downloads, likes, comments, price.",
            inputSchema={
                "type": "object",
                "properties": {
                    "slug": {"type": "string", "description": "Design slug from the Cults3D URL"},
                },
                "required": ["slug"],
            },
        ),
        types.Tool(
            name="search_designs",
            description="Search public designs on Cults3D by keyword. Useful for competitor research.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "category": {"type": "string", "description": "Optional category filter"},
                    "limit": {"type": "integer", "default": 20},
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="get_trending",
            description="Get trending designs in a Cults3D category.",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {"type": "string", "default": "miniatures"},
                    "limit": {"type": "integer", "default": 20},
                },
            },
        ),
        types.Tool(
            name="get_comments",
            description="Get all comments on a specific design.",
            inputSchema={
                "type": "object",
                "properties": {
                    "slug": {"type": "string"},
                },
                "required": ["slug"],
            },
        ),
        types.Tool(
            name="reply_to_comment",
            description="Post a reply to a comment on one of your designs.",
            inputSchema={
                "type": "object",
                "properties": {
                    "slug": {"type": "string", "description": "Design slug"},
                    "comment_id": {"type": "string"},
                    "body": {"type": "string", "description": "Reply text"},
                },
                "required": ["slug", "comment_id", "body"],
            },
        ),
        types.Tool(
            name="list_collections",
            description="List your Cults3D collections.",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="add_to_collection",
            description="Add a design to one of your collections.",
            inputSchema={
                "type": "object",
                "properties": {
                    "collection_id": {"type": "string"},
                    "design_slug": {"type": "string"},
                },
                "required": ["collection_id", "design_slug"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
    client = _get_client()

    try:
        if name == "upload_design":
            result = await client.upload_design(
                dry_run=arguments.pop("dry_run", False),
                **arguments,
            )
        elif name == "update_design":
            result = await client.update_design(**arguments)
        elif name == "list_my_designs":
            result = await client.list_my_designs(
                limit=arguments.get("limit", 20),
                offset=arguments.get("offset", 0),
            )
        elif name == "get_design_stats":
            result = await client.get_design_stats(arguments["slug"])
        elif name == "search_designs":
            result = await client.search_designs(
                query=arguments["query"],
                category=arguments.get("category"),
                limit=arguments.get("limit", 20),
            )
        elif name == "get_trending":
            result = await client.get_trending(
                category=arguments.get("category", "miniatures"),
                limit=arguments.get("limit", 20),
            )
        elif name == "get_comments":
            result = await client.get_comments(arguments["slug"])
        elif name == "reply_to_comment":
            result = await client.reply_to_comment(
                creation_slug=arguments["slug"],
                comment_id=arguments["comment_id"],
                body=arguments["body"],
            )
        elif name == "list_collections":
            result = await client.list_collections()
        elif name == "add_to_collection":
            result = await client.add_to_collection(
                collection_id=arguments["collection_id"],
                design_slug=arguments["design_slug"],
            )
        else:
            raise ValueError(f"Unknown tool: {name}")
    except Exception as exc:  # noqa: BLE001
        return [types.TextContent(type="text", text=f"Error: {exc}")]

    return [types.TextContent(type="text", text=json.dumps(result, indent=2, default=str))]


async def _run() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
