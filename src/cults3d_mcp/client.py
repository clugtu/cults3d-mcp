"""Cults3D API client.

Uses the internal GraphQL API at https://cults3d.com/graphql.
Authentication is JWT-based (Devise token auth).
"""

from __future__ import annotations

import os
import logging
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

CULTS_BASE = "https://cults3d.com"
CULTS_GRAPHQL = f"{CULTS_BASE}/graphql"
CULTS_LOGIN = f"{CULTS_BASE}/users/sign_in.json"


class Cults3DClient:
    """Authenticated Cults3D API client."""

    def __init__(
        self,
        email: str | None = None,
        password: str | None = None,
        token: str | None = None,
    ) -> None:
        self.email = email or os.environ["CULTS3D_EMAIL"]
        self.password = password or os.environ["CULTS3D_PASSWORD"]
        self._token: str | None = token or os.environ.get("CULTS3D_TOKEN")
        self._http = httpx.AsyncClient(
            timeout=30.0,
            headers={"User-Agent": "cults3d-mcp/0.1.0"},
            follow_redirects=True,
        )

    async def _ensure_token(self) -> str:
        if self._token:
            return self._token
        resp = await self._http.post(
            CULTS_LOGIN,
            json={"user": {"email": self.email, "password": self.password}},
        )
        resp.raise_for_status()
        data = resp.json()
        token = data.get("authentication_token") or data.get("token")
        if not token:
            raise RuntimeError(f"Login failed: {data}")
        self._token = token
        logger.info("Logged in to Cults3D")
        return self._token

    async def _gql(
        self,
        query: str,
        variables: dict[str, Any] | None = None,
        operation: str | None = None,
    ) -> dict[str, Any]:
        token = await self._ensure_token()
        payload: dict[str, Any] = {"query": query}
        if variables:
            payload["variables"] = variables
        if operation:
            payload["operationName"] = operation
        resp = await self._http.post(
            CULTS_GRAPHQL,
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()
        body = resp.json()
        if "errors" in body:
            raise RuntimeError(f"GraphQL errors: {body['errors']}")
        return body.get("data", {})

    # ------------------------------------------------------------------
    # Designs
    # ------------------------------------------------------------------

    async def list_my_designs(
        self, limit: int = 20, offset: int = 0
    ) -> list[dict[str, Any]]:
        q = """
        query MyDesigns($limit: Int, $offset: Int) {
          me {
            creations(limit: $limit, offset: $offset) {
              id
              slug
              name
              publishedAt
              downloadCount
              likesCount
              commentsCount
              price
              currency
              illustrationImageUrl
              url
            }
          }
        }
        """
        data = await self._gql(q, {"limit": limit, "offset": offset}, "MyDesigns")
        return data.get("me", {}).get("creations", [])

    async def get_design_stats(self, slug: str) -> dict[str, Any]:
        q = """
        query DesignStats($slug: String!) {
          creation(slug: $slug) {
            id
            slug
            name
            publishedAt
            downloadCount
            likesCount
            commentsCount
            price
            currency
            url
            illustrationImageUrl
          }
        }
        """
        data = await self._gql(q, {"slug": slug}, "DesignStats")
        return data.get("creation", {})

    async def search_designs(
        self,
        query: str,
        category: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        q = """
        query SearchDesigns($query: String!, $limit: Int) {
          searchCreations(q: $query, limit: $limit) {
            id
            slug
            name
            publishedAt
            downloadCount
            likesCount
            price
            currency
            url
            illustrationImageUrl
            maker { nick }
          }
        }
        """
        data = await self._gql(q, {"query": query, "limit": limit}, "SearchDesigns")
        results = data.get("searchCreations", [])
        if category:
            results = [r for r in results if category.lower() in str(r).lower()]
        return results

    async def get_trending(
        self, category: str = "miniatures", limit: int = 20
    ) -> list[dict[str, Any]]:
        q = """
        query TrendingDesigns($category: String!, $limit: Int) {
          trendingCreations(category: $category, limit: $limit) {
            id
            slug
            name
            downloadCount
            likesCount
            price
            currency
            url
            illustrationImageUrl
            maker { nick }
          }
        }
        """
        data = await self._gql(q, {"category": category, "limit": limit}, "TrendingDesigns")
        return data.get("trendingCreations", [])

    # ------------------------------------------------------------------
    # Comments
    # ------------------------------------------------------------------

    async def get_comments(self, slug: str) -> list[dict[str, Any]]:
        q = """
        query DesignComments($slug: String!) {
          creation(slug: $slug) {
            comments {
              id
              body
              createdAt
              author { nick }
            }
          }
        }
        """
        data = await self._gql(q, {"slug": slug}, "DesignComments")
        return data.get("creation", {}).get("comments", [])

    async def reply_to_comment(
        self, creation_slug: str, comment_id: str, body: str
    ) -> dict[str, Any]:
        q = """
        mutation ReplyToComment($input: CreateCommentInput!) {
          createComment(input: $input) {
            comment { id body createdAt }
            errors
          }
        }
        """
        data = await self._gql(
            q,
            {"input": {"creationSlug": creation_slug, "parentId": comment_id, "body": body}},
            "ReplyToComment",
        )
        return data.get("createComment", {})

    # ------------------------------------------------------------------
    # Collections
    # ------------------------------------------------------------------

    async def list_collections(self) -> list[dict[str, Any]]:
        q = """
        query MyCollections {
          me {
            collections {
              id
              name
              creationsCount
              url
            }
          }
        }
        """
        data = await self._gql(q, operation="MyCollections")
        return data.get("me", {}).get("collections", [])

    async def add_to_collection(
        self, collection_id: str, design_slug: str
    ) -> dict[str, Any]:
        q = """
        mutation AddToCollection($collectionId: ID!, $creationSlug: String!) {
          addCreationToCollection(
            input: { collectionId: $collectionId, creationSlug: $creationSlug }
          ) {
            collection { id name creationsCount }
            errors
          }
        }
        """
        data = await self._gql(
            q,
            {"collectionId": collection_id, "creationSlug": design_slug},
            "AddToCollection",
        )
        return data.get("addCreationToCollection", {})

    # ------------------------------------------------------------------
    # Upload (multipart)
    # ------------------------------------------------------------------

    async def upload_design(
        self,
        name: str,
        description: str,
        tags: list[str],
        category: str,
        license: str,
        price: float,
        file_path: str,
        thumbnail_path: str,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Upload a new design via multipart form-data.

        This uses the web form endpoint (not GraphQL) as that is what the
        Cults3D frontend uses for uploads.

        ``thumbnail_path`` is required — Cults3D will not publish a design
        without at least one illustration image.

        Set ``dry_run=True`` to validate inputs and build the payload without
        actually submitting to Cults3D. Useful for testing.
        """
        if not Path(file_path).exists():
            raise FileNotFoundError(f"STL/ZIP not found: {file_path}")
        if not Path(thumbnail_path).exists():
            raise FileNotFoundError(f"Thumbnail not found: {thumbnail_path}")

        files: dict[str, Any] = {
            "creation[name]": (None, name),
            "creation[description]": (None, description),
            "creation[tag_names]": (None, ",".join(tags)),
            "creation[category_slug]": (None, category),
            "creation[license]": (None, license),
            "creation[price]": (None, str(price)),
        }
        file_bytes = Path(file_path).read_bytes()
        files["creation[files][]"] = (Path(file_path).name, file_bytes, "application/octet-stream")
        thumb_bytes = Path(thumbnail_path).read_bytes()
        thumb_mime = "image/png" if thumbnail_path.lower().endswith(".png") else "image/jpeg"
        files["creation[illustration]"] = (
            Path(thumbnail_path).name,
            thumb_bytes,
            thumb_mime,
        )

        if dry_run:
            return {
                "dry_run": True,
                "status": "validated",
                "file": Path(file_path).name,
                "thumbnail": Path(thumbnail_path).name,
                "name": name,
                "tags": tags,
                "category": category,
                "price": price,
            }

        token = await self._ensure_token()
        resp = await self._http.post(
            f"{CULTS_BASE}/en/creations",
            files=files,
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()
        # Parse the redirect URL to extract the new design slug
        location = resp.headers.get("location", "")
        slug = location.rstrip("/").split("/")[-1]
        return {"slug": slug, "url": f"{CULTS_BASE}/en/3d-model/{slug}", "status": "created"}

    async def update_design(
        self,
        slug: str,
        name: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
        price: float | None = None,
    ) -> dict[str, Any]:
        fields: dict[str, Any] = {}
        if name:
            fields["name"] = name
        if description:
            fields["description"] = description
        if tags is not None:
            fields["tagNames"] = tags
        if price is not None:
            fields["price"] = price
        q = """
        mutation UpdateDesign($slug: String!, $fields: UpdateCreationInput!) {
          updateCreation(slug: $slug, input: $fields) {
            creation { id slug name }
            errors
          }
        }
        """
        data = await self._gql(q, {"slug": slug, "fields": fields}, "UpdateDesign")
        return data.get("updateCreation", {})

    async def aclose(self) -> None:
        await self._http.aclose()
