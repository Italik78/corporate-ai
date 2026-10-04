from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchAny, MatchValue, PointStruct


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

    def get_document_chunks(
        self,
        document_id: str,
        version: int,
        access_scopes: tuple[str, ...],
        classifications: tuple[str, ...],
        project_ids: tuple[str, ...],
        lifecycle_status: str = "CURRENT",
    ) -> list[dict[str, Any]]:
        chunks: list[dict[str, Any]] = []
        offset = None

        while True:
            points, next_offset = self.client.scroll(
                collection_name=self.collection,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="lifecycle_status",
                            match=MatchValue(value=lifecycle_status),
                        ),
                        FieldCondition(
                            key="access_scope",
                            match=MatchAny(any=list(access_scopes)),
                        ),
                        FieldCondition(
                            key="classification",
                            match=MatchAny(any=list(classifications)),
                        ),
                        FieldCondition(
                            key="canonical_source_verified",
                            match=MatchValue(value=True),
                        ),
                        FieldCondition(
                            key="document_id",
                            match=MatchValue(value=document_id),
                        ),
                        FieldCondition(
                            key="version",
                            match=MatchValue(value=version),
                        ),
                    ] + (
                        [] if "*" in project_ids else [
                            FieldCondition(
                                key="project_id",
                                match=MatchAny(any=list(project_ids)),
                            )
                        ]
                    )
                ),
                with_payload=True,
                limit=1000,
                offset=offset,
            )

            chunks.extend(
                point.payload
                for point in points
                if point.payload
            )

            if next_offset is None:
                break

            offset = next_offset

        return chunks

    def search(
        self,
        vector: list[float],
        limit: int,
        score_threshold: float,
        document_id: str | None = None,
        version: int | None = None,
        lifecycle_status: str | None = None,
        access_scopes: tuple[str, ...] = (),
        classifications: tuple[str, ...] = (),
        project_ids: tuple[str, ...] = (),
    ) -> list[Any]:
        # Authorization filters are mandatory. Empty values are a programming
        # or configuration error and must never degrade into unfiltered search.
        if not access_scopes or not classifications or not project_ids:
            raise ValueError("authorization filters are required")
        must = [
            FieldCondition(
                key="lifecycle_status",
                match=MatchValue(value=lifecycle_status or "CURRENT"),
            ),
            FieldCondition(
                key="access_scope",
                match=MatchAny(any=list(access_scopes)),
            ),
            FieldCondition(
                key="classification",
                match=MatchAny(any=list(classifications)),
            ),
            FieldCondition(
                key="canonical_source_verified",
                match=MatchValue(value=True),
            ),
        ]
        if document_id is not None:
            must.append(FieldCondition(key="document_id", match=MatchValue(value=document_id)))
        if version is not None:
            must.append(FieldCondition(key="version", match=MatchValue(value=version)))
        if "*" not in project_ids:
            must.append(
                FieldCondition(
                    key="project_id",
                    match=MatchAny(any=list(project_ids)),
                )
            )

        query_filter = Filter(must=must)

        return self.client.query_points(
            collection_name=self.collection,
            query=vector,
            query_filter=query_filter,
            limit=limit,
            score_threshold=score_threshold,
            with_payload=True,
        ).points
