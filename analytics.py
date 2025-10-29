"""Analytics computations built on top of the MongoRepository."""

from __future__ import annotations

from collections import defaultdict
from statistics import mean
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, Tuple, List

from database import MongoRepository

SCORE_MAP = {
    "LOW": 30.0,
    "MEDIUM": 60.0,
    "HIGH": 85.0,
}

DEFAULT_RANGE_DAYS = 30


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


def _score_indicator(score: Optional[float]) -> Dict[str, Any]:
    numeric = _coerce_score(score) or 0.0
    if numeric >= 80:
        return {"dots": ["green", "green", "green"], "label": "Excellent"}
    if numeric >= 50:
        return {"dots": ["yellow", "yellow", "gray"], "label": "Needs Attention"}
    return {"dots": ["red", "gray", "gray"], "label": "At Risk"}


def _parse_range(start: Optional[str], end: Optional[str], days: int = DEFAULT_RANGE_DAYS) -> Tuple[datetime, datetime]:
    if end:
        end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
    else:
        end_dt = datetime.now(timezone.utc)
    if start:
        start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
    else:
        start_dt = end_dt - timedelta(days=days)

    if start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=timezone.utc)
    else:
        start_dt = start_dt.astimezone(timezone.utc)
    if end_dt.tzinfo is None:
        end_dt = end_dt.replace(tzinfo=timezone.utc)
    else:
        end_dt = end_dt.astimezone(timezone.utc)

    start_dt = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    end_dt = end_dt.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    return start_dt, end_dt


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

        overview = {
            "total_users": metrics.total_users,
            "active_users": metrics.active_users,
            "total_assessments": metrics.total_assessments,
            "average_score": _safe_round(metrics.average_score, 2),
            "activity_rate": _safe_round((metrics.active_users / metrics.total_users) * 100 if metrics.total_users else 0, 1),
            "score_indicator": _score_indicator(metrics.average_score),
        }

        return {
            "system_overview": overview,
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

        average_score = mean(scores) if scores else 0
        summary = {
            "assessments": len(assessments),
            "average_score": _safe_round(average_score, 2),
            "average_duration": _safe_round(mean(durations), 1) if durations else 0,
            "events": events_summary.get("events", 0),
            "score_indicator": _score_indicator(average_score),
        }

        return {
            "user": {
                "id": user.id,
                "name": user.full_name,
                "roles": user.roles,
            },
            "summary": summary,
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

    # ------------------------------------------------------------------
    # Additional analytics datasets
    # ------------------------------------------------------------------
    def users_created(self, start: Optional[str], end: Optional[str]) -> Dict[str, Any]:
        start_dt, end_dt = _parse_range(start, end)
        series = self.repo.users_created_over_time(start_dt, end_dt)
        return {"series": series, "start": start_dt.isoformat(), "end": end_dt.isoformat()}

    def assessments_activity(self, start: Optional[str], end: Optional[str]) -> Dict[str, Any]:
        start_dt, end_dt = _parse_range(start, end)
        data = self.repo.user_assessment_activity(start_dt, end_dt)
        data.update({"start": start_dt.isoformat(), "end": end_dt.isoformat()})
        return data

    def answer_counts(self, start: Optional[str], end: Optional[str]) -> Dict[str, Any]:
        start_dt, end_dt = _parse_range(start, end)
        counts = self.repo.answer_choice_counts(start_dt, end_dt)
        return {"counts": counts, "start": start_dt.isoformat(), "end": end_dt.isoformat()}

    def answer_counts_year(self, year: int) -> Dict[str, Any]:
        buckets = self.repo.answer_choice_counts_year(year)
        return {"buckets": buckets, "year": year}

    def ridgeline_answer_options(self, assessment_id: Optional[str], category: Optional[str] = None) -> Dict[str, Any]:
        series = self.repo.answer_option_counts_per_question(assessment_id, category)
        # Order Likert-style if present
        order = ["Almost Never", "Not Very Often", "Somewhat Often", "Pretty Often", "Almost Always"]
        labels = sorted(series.keys(), key=lambda l: (order.index(l) if l in order else len(order) + hash(l)%1000))
        result: Dict[str, Any] = {"labels": labels, "series": {label: series[label] for label in labels}}
        if assessment_id:
            per_question = self.repo.answer_counts_by_question(assessment_id)
            question_names = self.repo._question_text_map(assessment_id)
            result["perQuestion"] = per_question
            result["questions"] = [{"id": qid, "text": question_names.get(qid, qid)} for qid in per_question.keys()]
        return result

    def list_assessments(self, q: Optional[str], limit: int = 25, category: Optional[str] = None) -> Dict[str, Any]:
        items = self.repo.list_assessments(q, limit, category)
        return {"assessments": items}

    def navigation_flow(self, user_id: str, start: Optional[str], end: Optional[str]) -> Dict[str, Any]:
        start_dt, end_dt = _parse_range(start, end)
        events = self.repo.navigation_events(user_id, start_dt, end_dt)
        return {"events": events, "start": start_dt.isoformat(), "end": end_dt.isoformat()}

    def users_with_navigation(self, start: Optional[str], end: Optional[str]) -> Dict[str, Any]:
        start_dt, end_dt = _parse_range(start, end)
        users = self.repo.users_with_navigation(start_dt, end_dt)
        return {
            "users": [
                {"id": u.id, "name": u.full_name, "username": u.username, "roles": u.roles}
                for u in users
            ],
            "start": start_dt.isoformat(),
            "end": end_dt.isoformat(),
        }

    def assessment_timings(self) -> Dict[str, Any]:
        metrics = self.repo.assessment_time_metrics()
        return metrics

    def average_question_time(self) -> Dict[str, Any]:
        metrics = self.repo.assessment_time_metrics()
        return metrics

    def top_students(self, limit: int = 100) -> Dict[str, Any]:
        leaderboard = []
        for entry in self.repo.top_users_by_average_score(limit):
            indicator = _score_indicator(entry.get("average"))
            leaderboard.append({
                "id": entry["id"],
                "name": entry["name"],
                "username": entry["username"],
                "roles": entry["roles"],
                "indicator": indicator,
            })
        return {"students": leaderboard}

    def logins_heatmap(self, start: Optional[str], end: Optional[str]) -> Dict[str, Any]:
        start_dt, end_dt = _parse_range(start, end)
        buckets = self.repo.login_heatmap(start_dt, end_dt)
        return {"buckets": buckets, "start": start_dt.isoformat(), "end": end_dt.isoformat()}

    def logins_heatmap_year(self, year: int) -> Dict[str, Any]:
        buckets = self.repo.login_heatmap_year(year)
        return {"buckets": buckets, "year": year}

    def logins_daily_year(self, year: int) -> Dict[str, Any]:
        series = self.repo.login_daily_counts_year(year)
        return {"series": series, "year": year}

    def logins_daily_month(self, year: int, month: int) -> Dict[str, Any]:
        series = self.repo.login_daily_counts_month(year, month)
        return {"series": series, "year": year, "month": month}
