from app.models import Claim, ClaimEvidence

class ClaimsEngine:
    def build(self, *, decision: dict, retrieved_sources: list) -> list[Claim]:
        claims = []

        def get_value(source, key, default=None):
            if isinstance(source, dict):
                return source.get(key, default)
            return getattr(source, key, default)

        source_map = {}
        for index, source in enumerate(retrieved_sources, start=1):
            source_id = get_value(source, "source_id", index)
            try:
                source_id = int(source_id)
            except (TypeError, ValueError):
                continue
            source_map[source_id] = source

        raw_claims = decision.get("claims", [])
        if not isinstance(raw_claims, list):
            return []

        for raw_claim in raw_claims:
            if not isinstance(raw_claim, dict):
                continue
            text = str(raw_claim.get("text", "") or raw_claim.get("claim", "") or "").strip()
            if not text:
                continue

            raw_source_ids = raw_claim.get("source_ids", [])
            if not isinstance(raw_source_ids, list):
                raw_source_ids = []

            valid_source_ids = []
            for source_id in raw_source_ids:
                try:
                    source_id = int(source_id)
                except (TypeError, ValueError):
                    continue
                if source_id in source_map:
                    valid_source_ids.append(source_id)

            valid_source_ids = list(dict.fromkeys(valid_source_ids))
            evidence = []

            for source_id in valid_source_ids:
                source = source_map[source_id]
                evidence.append(ClaimEvidence(
                    source_id=source_id,
                    document_id=get_value(source, "document_id"),
                    source_file=get_value(source, "source_file"),
                    page=get_value(source, "page"),
                    chunk_id=get_value(source, "chunk_id"),
                    score=get_value(source, "score"),
                    content=get_value(source, "content", ""),
                ))

            supported = len(valid_source_ids) > 0
            claims.append(Claim(
                text=text,
                supported=supported,
                source_ids=valid_source_ids,
                evidence=evidence,
                reason=("Твърдението има валидно посочени доказателства."
                        if supported else
                        "Твърдението няма валидно посочени доказателства."),
            ))

        return claims
