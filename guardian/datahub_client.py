"""
DataHub Health Guardian — DataHub Client Wrapper

Provides high-level methods for interacting with DataHub's REST API
to query metadata, lineage, data quality, and manage tags.
"""
import logging
from datetime import datetime, timezone
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class DataHubClient:
    """Client for interacting with DataHub GMS REST API."""

    def __init__(self, gms_url: str, token: str):
        self.gms_url = gms_url.rstrip("/")
        self.token = token
        self._client = httpx.Client(
            base_url=self.gms_url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    def test_connection(self) -> bool:
        """Test connection to DataHub GMS."""
        try:
            resp = self._client.get("/config")
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False

    def search_datasets(self, query: str = "*", count: int = 20) -> list[dict]:
        """Search for datasets in DataHub."""
        payload = {
            "input": query,
            "entity": "dataset",
            "start": 0,
            "count": count,
        }
        try:
            resp = self._client.post("/entities?action=search", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data.get("value", {}).get("entities", [])
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def get_dataset_details(self, urn: str) -> dict[str, Any]:
        """Get full details for a dataset by URN."""
        try:
            resp = self._client.get(
                f"/entities/{urn}",
                params={"aspects": [
                    "datasetProperties",
                    "schemaMetadata",
                    "ownership",
                    "globalTags",
                    "status",
                    "datasetProfile",
                ]},
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Failed to get dataset {urn}: {e}")
            return {}

    def get_lineage(self, urn: str, direction: str = "DOWNSTREAM", depth: int = 3) -> dict:
        """Get lineage for a dataset."""
        try:
            resp = self._client.get(
                f"/relationships",
                params={
                    "urn": urn,
                    "direction": direction,
                    "types": ["DownstreamOf", "Produces", "Consumes"],
                    "count": 100,
                },
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Lineage query failed for {urn}: {e}")
            return {}

    def get_graphql(self, query: str, variables: dict | None = None) -> dict:
        """Execute a GraphQL query against DataHub."""
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        try:
            resp = self._client.post("/api/graphql", json=payload)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"GraphQL query failed: {e}")
            return {}

    def search_all_datasets_graphql(self, query: str = "*", count: int = 50) -> list[dict]:
        """Search all datasets using GraphQL for richer results."""
        gql = """
        query searchDatasets($input: SearchInput!) {
            search(input: $input) {
                total
                searchResults {
                    entity {
                        urn
                        type
                        ... on Dataset {
                            name
                            platform {
                                name
                            }
                            properties {
                                name
                                description
                                qualifiedName
                                lastModified {
                                    time
                                }
                            }
                            schemaMetadata {
                                fields {
                                    fieldPath
                                    type
                                    description
                                    nullable
                                }
                            }
                            ownership {
                                owners {
                                    owner {
                                        urn
                                        ... on CorpUser {
                                            username
                                        }
                                    }
                                }
                            }
                            globalTags {
                                tags {
                                    tag {
                                        name
                                    }
                                }
                            }
                            deprecation {
                                deprecated
                                note
                            }
                        }
                    }
                }
            }
        }
        """
        variables = {
            "input": {
                "type": "DATASET",
                "query": query,
                "start": 0,
                "count": count,
            }
        }
        result = self.get_graphql(gql, variables)
        search_results = result.get("data", {}).get("search", {}).get("searchResults", [])
        return [r["entity"] for r in search_results if "entity" in r]

    def add_tag(self, entity_urn: str, tag_urn: str) -> bool:
        """Add a tag to an entity."""
        mutation = """
        mutation addTag($input: TagAssociationInput!) {
            addTag(input: $input)
        }
        """
        variables = {
            "input": {
                "tagUrn": tag_urn,
                "resourceUrn": entity_urn,
            }
        }
        result = self.get_graphql(mutation, variables)
        return "errors" not in result

    def close(self):
        """Close the HTTP client."""
        self._client.close()
