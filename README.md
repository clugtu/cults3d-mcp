# cults3d-mcp

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server for [Cults3D](https://cults3d.com) — the leading marketplace for 3D printing designs.

Enables AI agents to upload designs, track stats, manage listings, and monitor community engagement on Cults3D.

> **First open-source MCP server for Cults3D.**

---

## Features

| Tool | Description |
|------|-------------|
| `upload_design` | Upload a new STL/ZIP with title, description, tags, category, price |
| `update_design` | Edit metadata on an existing listing |
| `list_my_designs` | List all your published designs with status and stats |
| `get_design_stats` | Downloads, likes, comments, revenue for a design |
| `search_designs` | Search public designs by keyword (competitor research) |
| `get_trending` | Trending designs in a category |
| `get_comments` | Read comments on a design |
| `reply_to_comment` | Post a reply to a comment |
| `list_collections` | List your Cults3D collections |
| `add_to_collection` | Add a design to a collection |

---

## Installation

```bash
pip install cults3d-mcp
```

Or run directly with `uvx`:

```bash
uvx cults3d-mcp
```

---

## Configuration

Create a `.env` file (see `.env.template`):

```env
CULTS3D_EMAIL=your@email.com
CULTS3D_PASSWORD=yourpassword
```

Authentication uses Cults3D's token-based auth (JWT). The server logs in on startup and refreshes the token automatically.

---

## MCP Client Setup

Add to your MCP config (`~/.config/claude/claude_desktop_config.json` or equivalent):

```json
{
  "mcpServers": {
    "cults3d": {
      "command": "uvx",
      "args": ["cults3d-mcp"],
      "env": {
        "CULTS3D_EMAIL": "your@email.com",
        "CULTS3D_PASSWORD": "yourpassword"
      }
    }
  }
}
```

---

## Development

```bash
git clone https://github.com/clugtu/cults3d-mcp
cd cults3d-mcp
pip install -e ".[dev]"
pytest
```

---

## API Notes

Cults3D uses an internal GraphQL API (`https://cults3d.com/graphql`). This server uses reverse-engineered queries from the web interface. It is not an officially supported integration.

- **Rate limits**: Be respectful — add delays between bulk operations
- **Auth**: Session-based JWT, refreshed every ~24h
- **File uploads**: Multipart form-data for STL/ZIP files

---

## License

MIT — see [LICENSE](LICENSE)

---

## Related

- [pinterest-mcp](https://github.com/clugtu/pinterest-mcp) — Pinterest MCP server
