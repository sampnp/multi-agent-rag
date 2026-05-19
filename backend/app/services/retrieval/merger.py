_SOURCE_WEIGHT = {"vector": 1.0, "keyword": 0.85, "graph": 0.90, "web": 0.75}


def _temporal_boost(result: dict) -> float:
    # Web results are assumed more recent
    return 0.08 if result["source"] == "web" else 0.0


def merge_and_rank(results_by_source: dict[str, list[dict]], limit: int = 8) -> list[dict]:
    all_results: list[dict] = []
    for source, results in results_by_source.items():
        weight = _SOURCE_WEIGHT.get(source, 1.0)
        if not results:
            continue
        max_score = max(r["score"] for r in results) or 1.0
        for r in results:
            r["score"] = (r["score"] / max_score) * weight + _temporal_boost(r)
        all_results.extend(results)

    # Deduplicate — skip if the first 120 chars are near-identical to a seen result
    seen: set[str] = set()
    deduped: list[dict] = []
    for r in sorted(all_results, key=lambda x: x["score"], reverse=True):
        key = r["text"][:120].lower().strip()
        if key not in seen:
            seen.add(key)
            deduped.append(r)

    return deduped[:limit]
