from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue, PointStruct


class QdrantStore:
    def __init__(self, url: str, collection: str) -> None:
        self.collection = collection
        self.client = QdrantClient(url=url)

    def health(self) -> bool:
        try:
            collections = self.client.get_collections()
            return any(item.name == self.collection for item in collections.collections)
        except Exception:
            return False

    def upsert(self, point_id: str, vector: list[float], payload: dict[str, Any]) -> None:
        self.client.upsert(
            collection_name=self.collection,
            points=[PointStruct(id=point_id, vector=vector, payload=payload)],
            wait=True,
        )

    def set_lifecycle_status(
        self,
        document_id: str,
        version: int,
        lifecycle_status: str,
    ) -> None:
        self.client.set_payload(
            collection_name=self.collection,
            payload={"lifecycle_status": lifecycle_status},
            points=Filter(
                must=[
                    FieldCondition(key="document_id", match=MatchValue(value=document_id)),
                    FieldCondition(key="version", match=MatchValue(value=version)),
                ]
            ),
            wait=True,
        )

    def search(
        self,
        vector: list[float],
        limit: int,
        score_threshold: float,
        document_id: str | None = None,
        version: int | None = None,
        lifecycle_status: str | None = None,
    ) -> list[Any]:
        must = []
        if document_id is not None:
            must.append(FieldCondition(key="document_id", match=MatchValue(value=document_id)))
        if version is not None:
            must.append(FieldCondition(key="version", match=MatchValue(value=version)))
        if lifecycle_status is not None:
            must.append(
                FieldCondition(
                    key="lifecycle_status",
                    match=MatchValue(value=lifecycle_status),
                )
            )

        query_filter = Filter(must=must) if must else None

        return self.client.query_points(
            collection_name=self.collection,
            query=vector,
            query_filter=query_filter,
            limit=limit,
            score_threshold=score_threshold,
            with_payload=True,
        ).points
