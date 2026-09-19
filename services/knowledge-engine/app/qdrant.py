from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct


class QdrantStore:
    def __init__(
        self,
        url: str,
        collection: str,
    ) -> None:
        self.collection = collection
        self.client = QdrantClient(url=url)

    def health(self) -> bool:
        try:
            collections = self.client.get_collections()
            return any(
                item.name == self.collection
                for item in collections.collections
            )
        except Exception:
            return False

    def upsert(
        self,
        point_id: str,
        vector: list[float],
        payload: dict[str, Any],
    ) -> None:
        self.client.upsert(
            collection_name=self.collection,
            points=[
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload,
                )
            ],
            wait=True,
        )

    def search(
        self,
        vector: list[float],
        limit: int,
        score_threshold: float,
    ) -> list[Any]:
        return self.client.query_points(
            collection_name=self.collection,
            query=vector,
            limit=limit,
            score_threshold=score_threshold,
            with_payload=True,
        ).points
