import math
import time


def recency_score(timestamp: float, half_life_days: float = 7.0) -> float:
    """Exponential decay: 1.0 at creation → 0.5 after 7 days → ~0 after ~49 days."""
    age_days = (time.time() - timestamp) / 86400.0
    return math.exp(-age_days * math.log(2) / half_life_days)


def score_memory(similarity: float, timestamp: float) -> float:
    """Blend semantic similarity (70%) with recency (30%)."""
    return 0.7 * similarity + 0.3 * recency_score(timestamp)
