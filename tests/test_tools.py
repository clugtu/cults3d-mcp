"""Tests for cults3d-mcp tools.

All HTTP calls are mocked — no real Cults3D traffic.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from cults3d_mcp.client import Cults3DClient


@pytest.fixture
def client() -> Cults3DClient:
    return Cults3DClient(email="test@example.com", password="secret", token="fake-token")


# ---------------------------------------------------------------------------
# list_my_designs
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_my_designs(client: Cults3DClient):
    mock_response = {
        "data": {
            "me": {
                "creations": [
                    {
                        "id": "123",
                        "slug": "dragon-miniature",
                        "name": "Dragon Miniature",
                        "downloadCount": 42,
                        "likesCount": 10,
                        "commentsCount": 3,
                        "price": 2.99,
                        "currency": "EUR",
                        "url": "https://cults3d.com/en/3d-model/dragon-miniature",
                    }
                ]
            }
        }
    }
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = MagicMock(return_value=mock_response)

    with patch.object(client._http, "post", new_callable=AsyncMock, return_value=mock_resp):
        results = await client.list_my_designs()

    assert len(results) == 1
    assert results[0]["slug"] == "dragon-miniature"
    assert results[0]["downloadCount"] == 42


# ---------------------------------------------------------------------------
# get_design_stats
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_design_stats(client: Cults3DClient):
    mock_response = {
        "data": {
            "creation": {
                "id": "456",
                "slug": "orc-warrior",
                "name": "Orc Warrior",
                "downloadCount": 100,
                "likesCount": 25,
                "commentsCount": 7,
                "price": 1.50,
                "currency": "EUR",
                "url": "https://cults3d.com/en/3d-model/orc-warrior",
            }
        }
    }
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = MagicMock(return_value=mock_response)

    with patch.object(client._http, "post", new_callable=AsyncMock, return_value=mock_resp):
        stats = await client.get_design_stats("orc-warrior")

    assert stats["slug"] == "orc-warrior"
    assert stats["downloadCount"] == 100


# ---------------------------------------------------------------------------
# search_designs
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_designs(client: Cults3DClient):
    mock_response = {
        "data": {
            "searchCreations": [
                {"id": "1", "slug": "goblin-shaman", "name": "Goblin Shaman", "downloadCount": 55},
                {"id": "2", "slug": "elf-ranger", "name": "Elf Ranger", "downloadCount": 30},
            ]
        }
    }
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = MagicMock(return_value=mock_response)

    with patch.object(client._http, "post", new_callable=AsyncMock, return_value=mock_resp):
        results = await client.search_designs("goblin")

    assert len(results) == 2
    assert results[0]["slug"] == "goblin-shaman"


# ---------------------------------------------------------------------------
# get_comments
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_comments(client: Cults3DClient):
    mock_response = {
        "data": {
            "creation": {
                "comments": [
                    {"id": "c1", "body": "Love this model!", "author": {"nick": "printer_guy"}}
                ]
            }
        }
    }
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = MagicMock(return_value=mock_response)

    with patch.object(client._http, "post", new_callable=AsyncMock, return_value=mock_resp):
        comments = await client.get_comments("dragon-miniature")

    assert len(comments) == 1
    assert comments[0]["body"] == "Love this model!"


# ---------------------------------------------------------------------------
# auth: login
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_login_sets_token():
    client = Cults3DClient(email="a@b.com", password="pw")
    login_resp = MagicMock()
    login_resp.raise_for_status = MagicMock()
    login_resp.json = MagicMock(return_value={"authentication_token": "new-jwt-token"})

    with patch.object(client._http, "post", new_callable=AsyncMock, return_value=login_resp):
        token = await client._ensure_token()

    assert token == "new-jwt-token"
    assert client._token == "new-jwt-token"
