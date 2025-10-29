"""MongoDB access layer for the DAACS analytics service."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Iterable, Optional, List, Dict, Any, Tuple

from bson import ObjectId
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from models import (
    User,
    UserAssessment,
    AssessmentItemGroup,
    AssessmentAnswer,
    EventContainer,
    UserEvent,
    SystemMetrics,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_datetime(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, dict) and "$date" in value:
        return _parse_datetime(value["$date"])
    if isinstance(value, (int, float)):
        seconds = value / 1000 if value > 1e12 else value
        return datetime.fromtimestamp(seconds, tz=timezone.utc)
    if isinstance(value, str):
        try:
            normalized = value.replace("Z", "+00:00")
            return datetime.fromisoformat(normalized)
        except ValueError:
            pass
        # numeric string
        try:
            return _parse_datetime(float(value))
        except ValueError:
            return None
    return None


def _to_object_id(value: str) -> Any:
    try:
        return ObjectId(value)
    except Exception:
        return value


SCORE_MAP = {
    "LOW": 30.0,
    "MEDIUM": 60.0,
    "HIGH": 85.0,
}


def _coerce_score_value(value: Any) -> Optional[float]:
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


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------


class MongoRepository:
    def __init__(self, uri: str, database: str):
        self.client = MongoClient(uri)
        self.db: Database = self.client[database]
        self.users: Collection = self.db["users"]
        self.user_assessments: Collection = self.db["user_assessments"]
        self.event_containers: Collection = self.db["event_containers"]

    # Users -----------------------------------------------------------------
    def fetch_users(self, limit: int = 50) -> List[User]:
        docs = self.users.find({}, limit=limit)
        users: List[User] = []
        for doc in docs:
            users.append(User(
                id=str(doc.get("_id", "")),
                username=doc.get("username", ""),
                first_name=doc.get("firstName", ""),
                last_name=doc.get("lastName", ""),
                roles=doc.get("roles", []) or [],
                created_at=_parse_datetime(doc.get("createdDate")) or datetime.now(timezone.utc),
                disabled=bool(doc.get("isUserDisabled", False)),
            ))
        return users

    def fetch_user(self, user_id: str) -> Optional[User]:
        doc = self.users.find_one({"_id": user_id}) or self.users.find_one({"_id": _to_object_id(user_id)})
        if not doc:
            return None
        return User(
            id=str(doc.get("_id", "")),
            username=doc.get("username", ""),
            first_name=doc.get("firstName", ""),
            last_name=doc.get("lastName", ""),
            roles=doc.get("roles", []) or [],
            created_at=_parse_datetime(doc.get("createdDate")) or datetime.now(timezone.utc),
            disabled=bool(doc.get("isUserDisabled", False)),
        )

    # Assessments -----------------------------------------------------------
    def fetch_user_assessments(self, user_id: str) -> List[UserAssessment]:
        docs = self.user_assessments.find({"userId": user_id})
        results: List[UserAssessment] = []
        for doc in docs:
            item_groups: List[AssessmentItemGroup] = []
            for group in doc.get("itemGroups", []) or []:
                answers: List[AssessmentAnswer] = []
                for item in group.get("items", []) or []:
                    score_val = item.get("score", 0)
                    try:
                        score = float(score_val)
                    except (TypeError, ValueError):
                        score = 0.0
                    answers.append(AssessmentAnswer(
                        question_id=item.get("questionId", ""),
                        answer_id=item.get("_id", ""),
                        domain_id=item.get("domainId", ""),
                        score=score,
                        started_at=_parse_datetime(item.get("startDate")),
                        completed_at=_parse_datetime(item.get("completeDate")),
                    ))
                item_groups.append(AssessmentItemGroup(
                    id=group.get("_id", ""),
                    difficulty=group.get("difficulty", "UNKNOWN"),
                    answers=answers,
                ))
            progress_val = doc.get("progressPercentage", 0)
            try:
                progress = float(progress_val)
            except (TypeError, ValueError):
                progress = 0.0
            results.append(UserAssessment(
                id=str(doc.get("_id", "")),
                user_id=doc.get("userId", ""),
                assessment_id=doc.get("assessmentId", ""),
                status=doc.get("status", ""),
                progress=progress,
                overall_score=doc.get("overallScore"),
                started_at=_parse_datetime(doc.get("takenDate")),
                completed_at=_parse_datetime(doc.get("completionDate")),
                item_groups=item_groups,
            ))
        return results

    # Events ----------------------------------------------------------------
    def fetch_event_container(self, user_id: str) -> Optional[EventContainer]:
        doc = self.event_containers.find_one({"userId": user_id})
        if not doc:
            return None
        events: List[UserEvent] = []
        for event in doc.get("userEvents", []) or []:
            payload = event.get("eventData") or {}
            events.append(UserEvent(
                id=event.get("_id", ""),
                event_type=event.get("eventType", ""),
                occurred_at=_parse_datetime(event.get("timestamp")) or datetime.now(timezone.utc),
                url=payload.get("url", ""),
            ))
        return EventContainer(
            id=str(doc.get("_id", "")),
            user_id=doc.get("userId", ""),
            events=events,
        )

    # System metrics --------------------------------------------------------
    def compute_system_metrics(self) -> SystemMetrics:
        total_users = self.users.count_documents({})
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)

        active_users = len(self.event_containers.distinct(
            "userId", {"userEvents.timestamp": {"$gte": thirty_days_ago}}
        ))
        if active_users == 0:
            active_users = self.users.count_documents({"createdDate": {"$gte": thirty_days_ago}})

        total_assessments = self.user_assessments.count_documents({})

        avg_score = 0.0
        pipeline = [{"$group": {"_id": None, "avg": {"$avg": "$overallScore"}}}]
        result = list(self.user_assessments.aggregate(pipeline))
        if result and result[0].get("avg") is not None:
            avg_score = float(result[0]["avg"])

        hours = [0] * 24
        page_counts: Dict[str, int] = {}
        docs = self.event_containers.find({}, {"userEvents": 1})
        for doc in docs:
            for event in doc.get("userEvents", []) or []:
                ts = _parse_datetime(event.get("timestamp"))
                if ts:
                    hours[ts.hour] += 1
                url = (event.get("eventData") or {}).get("url")
                if url:
                    page_counts[url] = page_counts.get(url, 0) + 1

        peak_hours = [hour for hour, count in sorted(enumerate(hours), key=lambda x: x[1], reverse=True)[:6] if count]
        top_pages = dict(sorted(page_counts.items(), key=lambda item: item[1], reverse=True)[:10])

        return SystemMetrics(
            total_users=total_users,
            active_users=active_users,
            total_assessments=total_assessments,
            average_score=avg_score,
            peak_hours=peak_hours,
            top_pages=top_pages,
        )

    def users_created_over_time(self, start: datetime, end: datetime) -> List[Dict[str, Any]]:
        pipeline = [
            {"$match": {"createdDate": {"$gte": start, "$lte": end}}},
            {
                "$project": {
                    "day": {"$dateToString": {"format": "%Y-%m-%d", "date": "$createdDate"}}
                }
            },
            {"$group": {"_id": "$day", "count": {"$sum": 1}}},
            {"$sort": {"_id": 1}},
        ]
        docs = list(self.users.aggregate(pipeline))
        return [{"date": doc["_id"], "count": doc["count"]} for doc in docs]

    def user_assessment_activity(self, start: datetime, end: datetime) -> Dict[str, List[Dict[str, Any]]]:
        started_pipeline = [
            {"$match": {"takenDate": {"$gte": start, "$lte": end}}},
            {
                "$project": {
                    "day": {"$dateToString": {"format": "%Y-%m-%d", "date": "$takenDate"}}
                }
            },
            {"$group": {"_id": "$day", "count": {"$sum": 1}}},
            {"$sort": {"_id": 1}},
        ]
        completed_pipeline = [
            {"$match": {"completionDate": {"$gte": start, "$lte": end}}},
            {
                "$project": {
                    "day": {"$dateToString": {"format": "%Y-%m-%d", "date": "$completionDate"}}
                }
            },
            {"$group": {"_id": "$day", "count": {"$sum": 1}}},
            {"$sort": {"_id": 1}},
        ]
        started = [{"date": doc["_id"], "count": doc["count"]} for doc in self.user_assessments.aggregate(started_pipeline)]
        completed = [{"date": doc["_id"], "count": doc["count"]} for doc in self.user_assessments.aggregate(completed_pipeline)]
        return {"started": started, "completed": completed}

    def answer_choice_counts(self, start: datetime, end: datetime) -> List[Dict[str, Any]]:
        pipeline = [
            {
                "$match": {
                    "itemGroups.items.startDate": {"$gte": start},
                    "itemGroups.items.completeDate": {"$lte": end},
                }
            },
            {"$unwind": "$itemGroups"},
            {"$unwind": "$itemGroups.items"},
            {
                "$match": {
                    "itemGroups.items.startDate": {"$gte": start},
                    "itemGroups.items.completeDate": {"$lte": end},
                }
            },
            {
                "$group": {
                    "_id": {
                        "answer": "$itemGroups.items.chosenItemAnswerId",
                        "question": "$itemGroups.items.questionId",
                    },
                    "count": {"$sum": 1},
                }
            },
            {"$sort": {"count": -1}},
        ]
        docs = list(self.user_assessments.aggregate(pipeline))
        return [
            {
                "questionId": doc["_id"].get("question"),
                "answerId": doc["_id"].get("answer"),
                "count": doc["count"],
            }
            for doc in docs
        ]

    def navigation_events(self, user_id: str, start: datetime, end: datetime) -> List[Dict[str, Any]]:
        doc = self.event_containers.find_one({"userId": user_id})
        if not doc:
            return []
        events = []
        for event in doc.get("userEvents", []) or []:
            ts = _parse_datetime(event.get("timestamp"))
            if not ts or ts < start or ts > end:
                continue
            payload = event.get("eventData") or {}
            events.append({
                "timestamp": ts.isoformat(),
                "url": payload.get("url", ""),
                "title": payload.get("title", ""),
                "eventType": event.get("eventType", ""),
            })
        events.sort(key=lambda ev: ev["timestamp"])
        return events

    def assessment_time_metrics(self) -> Dict[str, List[Dict[str, Any]]]:
        group_totals: Dict[str, List[float]] = defaultdict(list)
        item_totals: Dict[str, List[float]] = defaultdict(list)

        cursor = self.user_assessments.find({}, {"itemGroups": 1})
        for doc in cursor:
            for group in doc.get("itemGroups", []) or []:
                durations = []
                for item in group.get("items", []) or []:
                    start = _parse_datetime(item.get("startDate"))
                    end = _parse_datetime(item.get("completeDate"))
                    if not start or not end:
                        continue
                    duration = (end - start).total_seconds()
                    item_totals[item.get("questionId", "")].append(duration)
                    durations.append(duration)
                if durations:
                    group_totals[group.get("_id", "")].append(sum(durations) / len(durations))

        group_stats = [
            {
                "groupId": group_id,
                "avgSeconds": sum(values) / len(values),
            }
            for group_id, values in group_totals.items() if values
        ]
        item_stats = [
            {
                "questionId": item_id,
                "avgSeconds": sum(values) / len(values),
            }
            for item_id, values in item_totals.items() if values
        ]
        group_stats.sort(key=lambda g: g["avgSeconds"], reverse=True)
        item_stats.sort(key=lambda g: g["avgSeconds"], reverse=True)
        return {"groups": group_stats[:20], "items": item_stats[:20]}

    def top_users_by_average_score(self, limit: int = 100) -> List[Dict[str, Any]]:
        scores: Dict[str, List[float]] = defaultdict(list)
        cursor = self.user_assessments.find({}, {"userId": 1, "overallScore": 1})
        for doc in cursor:
            user_id = doc.get("userId")
            if not user_id:
                continue
            score = _coerce_score_value(doc.get("overallScore"))
            if score is None:
                continue
            scores[user_id].append(score)

        ranked: List[Tuple[str, float]] = []
        for user_id, values in scores.items():
            if not values:
                continue
            ranked.append((user_id, sum(values) / len(values)))
        ranked.sort(key=lambda x: x[1], reverse=True)
        top = ranked[:limit]

        results: List[Dict[str, Any]] = []
        for user_id, average in top:
            user = self.fetch_user(user_id)
            if not user:
                continue
            results.append({
                "id": user.id,
                "name": user.full_name,
                "username": user.username,
                "average": average,
                "roles": user.roles,
            })
        return results
