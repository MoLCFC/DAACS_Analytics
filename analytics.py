"""Analytics computations built on top of the MongoRepository."""

from __future__ import annotations

from collections import defaultdict
from statistics import mean
from typing import Dict, Any, Optional

from database import MongoRepository

SCORE_MAP = {
    "LOW": 30.0,
    "MEDIUM": 60.0,
    "HIGH": 85.0,
}


def _coerce_score(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip().upper()
        if cleaned in SCORE_MAP:
            return SCORE_MAP[cleaned]
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def _safe_round(value: Any, digits: int = 0) -> float:
    numeric = _coerce_score(value)
    if numeric is None:
        return 0.0
    try:
        return round(float(numeric), digits)
    except (TypeError, ValueError):
        return 0.0


class AnalyticsEngine:
    def __init__(self, repo: MongoRepository):
        self.repo = repo

    # ------------------------------------------------------------------
    # System dashboard
    # ------------------------------------------------------------------
    def system_dashboard(self) -> Dict[str, Any]:
        metrics = self.repo.compute_system_metrics()

        histogram = defaultdict(int)
        total = 0
        cursor = self.repo.user_assessments.find({}, {"overallScore": 1})
        for doc in cursor:
            score = _coerce_score(doc.get("overallScore"))
            if score is None:
                continue
            score = max(0.0, min(score, 100.0))
            bucket = int(score // 10) * 10
            histogram[bucket] += 1
            total += 1

        score_ranges = [
            {
                "range": f"{bucket}-{min(bucket + 10, 100)}",
                "count": count,
                "percentage": _safe_round((count / total) * 100 if total else 0, 1),
            }
            for bucket, count in sorted(histogram.items())
        ]

        return {
            "system_overview": {
                "total_users": metrics.total_users,
                "active_users": metrics.active_users,
                "total_assessments": metrics.total_assessments,
                "average_score": _safe_round(metrics.average_score, 2),
                "activity_rate": _safe_round((metrics.active_users / metrics.total_users) * 100 if metrics.total_users else 0, 1),
            },
            "performance_distribution": {"score_distribution": score_ranges},
            "peak_usage_hours": metrics.peak_hours,
            "most_visited_pages": metrics.top_pages,
        }

    # ------------------------------------------------------------------
    # User analytics
    # ------------------------------------------------------------------
    def user_analytics(self, user_id: str) -> Dict[str, Any]:
        user = self.repo.fetch_user(user_id)
        if not user:
            return {"error": "User not found"}

        assessments = self.repo.fetch_user_assessments(user_id)
        events_summary = self.event_summary(user_id)

        scores = []
        for ass in assessments:
            score = _coerce_score(ass.overall_score)
            if score is not None:
                scores.append(score)
        durations = [ass.duration_minutes for ass in assessments if ass.duration_minutes]

        return {
            "user": {
                "id": user.id,
                "name": user.full_name,
                "roles": user.roles,
            },
            "summary": {
                "assessments": len(assessments),
                "average_score": _safe_round(mean(scores), 2) if scores else 0,
                "average_duration": _safe_round(mean(durations), 1) if durations else 0,
                "events": events_summary.get("events", 0),
            },
            "assessments": [
                {
                    "assessment_id": ass.assessment_id,
                    "status": ass.status,
                    "overall_score": ass.overall_score,
                    "progress": ass.progress,
                    "duration_minutes": ass.duration_minutes,
                }
                for ass in assessments
            ],
        }

    def event_summary(self, user_id: str) -> Dict[str, Any]:
        container = self.repo.fetch_event_container(user_id)
        if not container:
            return {"events": 0, "logins": 0, "pages": 0}

        logins = sum(1 for event in container.events if event.event_type == "LOGIN")
        pages = len({event.url for event in container.events if event.url})

        return {
            "events": len(container.events),
            "logins": logins,
            "pages": pages,
        }
