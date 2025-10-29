"""MongoDB access layer for the DAACS analytics service."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone, timedelta
from calendar import monthrange
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
            dt = datetime.fromisoformat(normalized)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
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
        self.assessments: Collection = self.db["assessments"]

    def _group_and_item_names(self) -> Tuple[Dict[str, str], Dict[str, str]]:
        group_names: Dict[str, str] = {}
        item_names: Dict[str, str] = {}
        cursor = self.assessments.find({}, {"title": 1, "itemGroups": 1})
        for doc in cursor:
            assessment_title = doc.get("title", "Assessment")
            for group in doc.get("itemGroups", []) or []:
                group_id = group.get("_id")
                label = group.get("label") or group.get("title") or f"Group {group_id[:6]}"
                if group_id:
                    group_names[group_id] = f"{assessment_title} — {label}"
                for item in group.get("items", []) or []:
                    item_id = item.get("itemId") or item.get("_id")
                    prompt = item.get("prompt") or item.get("title") or item.get("label") or f"Question {item_id[:6]}"
                    if item_id:
                        item_names[item_id] = prompt
        return group_names, item_names

    def _answer_label_map(self) -> Dict[str, str]:
        """Attempt to build a mapping of answer option id -> human label by
        scanning the assessments metadata structure. The schema can vary, so we
        search a handful of likely keys.
        """
        id_to_label: Dict[str, str] = {}
        cursor = self.assessments.find({}, {"itemGroups": 1, "items": 1})
        for doc in cursor:
            groups = doc.get("itemGroups") or doc.get("groups") or []
            top_items = doc.get("items", []) or []
            containers = []
            if isinstance(groups, list):
                containers.extend(groups)
            if isinstance(top_items, list):
                containers.append({"items": top_items})
            for group in containers:
                for item in (group.get("items") or []):
                    for key in ("answers", "answerOptions", "options", "responses", "choices"):
                        opts = item.get(key)
                        if not isinstance(opts, list):
                            continue
                        for opt in opts:
                            opt_id = opt.get("_id") or opt.get("id") or opt.get("answerId")
                            label = opt.get("label") or opt.get("text") or opt.get("title") or opt.get("value")
                            if opt_id and isinstance(label, str):
                                id_to_label.setdefault(str(opt_id), label)
        return id_to_label

    def _extract_answer_label(self, item: Dict[str, Any], label_map: Dict[str, str]) -> Optional[str]:
        """Extract a human-readable answer label from an assessment item response.
        Handles multiple possible schemas for answer IDs and labels.
        """
        # Try common ID fields first and map to labels
        id_keys = [
            "chosenItemAnswerId", "answerId", "chosenAnswerId", "selectedAnswerId",
            "selectedOptionId", "responseId", "choiceId", "id", "_id",
        ]
        for key in id_keys:
            ans_id = item.get(key)
            if ans_id:
                label = label_map.get(str(ans_id))
                if label:
                    return label
        # Fallback to direct label/text fields if present
        label_keys = [
            "answerLabel", "selectedLabel", "chosenItemAnswerLabel", "answerText",
            "text", "label", "value", "title",
        ]
        for key in label_keys:
            label = item.get(key)
            if isinstance(label, str) and label.strip():
                return label.strip()
        return None

    def _assessment_ids_for_category(self, category: Optional[str]) -> List[str]:
        if not category:
            return []
        key = str(category).strip().lower()
        # Build a permissive regex to catch common field variants
        if key == "college_skills":
            patterns = [
                {"assessmentCategory": {"$regex": "^COLLEGE[_\- ]?SKILLS$", "$options": "i"}},
                {"label": {"$regex": "college[_\- ]?skills", "$options": "i"}},
                {"title": {"$regex": "college[_\- ]?skills", "$options": "i"}},
                {"_id": {"$regex": "^college[_\- ]?skills$", "$options": "i"}},
            ]
        else:
            # Fallback: match category key anywhere in category/label/title/id
            escaped = key.replace("_", "[_\- ]?")
            patterns = [
                {"assessmentCategory": {"$regex": escaped, "$options": "i"}},
                {"label": {"$regex": escaped, "$options": "i"}},
                {"title": {"$regex": escaped, "$options": "i"}},
                {"_id": {"$regex": escaped, "$options": "i"}},
            ]
        query = {"$or": patterns}
        ids: List[str] = []
        cursor = self.assessments.find(query, {"_id": 1})
        for doc in cursor:
            ids.append(str(doc.get("_id")))
        return ids

    def list_assessments(self, query: Optional[str] = None, limit: int = 25, category: Optional[str] = None) -> List[Dict[str, str]]:
        projection = {"_id": 1, "title": 1}
        ids_filter = set(self._assessment_ids_for_category(category)) if category else None
        docs = self.assessments.find({}, projection)
        results: List[Dict[str, str]] = []
        q = (query or "").strip().lower()
        for doc in docs:
            aid = str(doc.get("_id"))
            if ids_filter is not None and aid not in ids_filter:
                continue
            title = (doc.get("title") or "").strip()
            if q:
                if q in aid.lower() or q in title.lower():
                    results.append({"id": aid, "title": title})
            else:
                results.append({"id": aid, "title": title})
            if len(results) >= limit:
                break
        return results

    def _question_text_map(self, assessment_id: Optional[str]) -> Dict[str, str]:
        mapping: Dict[str, str] = {}
        if not assessment_id:
            return mapping
        doc = self.assessments.find_one({"_id": assessment_id}) or self.assessments.find_one({"_id": _to_object_id(assessment_id)})
        if not doc:
            return mapping
        for group in doc.get("itemGroups", []) or []:
            for item in group.get("items", []) or []:
                qid = item.get("itemId") or item.get("questionId") or item.get("_id")
                prompt = item.get("prompt") or item.get("title") or item.get("label")
                if qid and isinstance(prompt, str):
                    mapping[str(qid)] = prompt
        return mapping

    def answer_option_counts_per_question(self, assessment_id: Optional[str] = None, category: Optional[str] = None) -> Dict[str, List[int]]:
        """For an assessment (or all), return counts of selections per answer label,
        aggregated across questions; result format suitable for ridgeline: label -> list of per-question counts.
        """
        label_map = self._answer_label_map()
        per_question_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        query: Dict[str, Any] = {}
        if assessment_id:
            query["assessmentId"] = assessment_id
        elif category:
            ids = self._assessment_ids_for_category(category)
            if not ids:
                return {}
            query["assessmentId"] = {"$in": ids}
        cursor = self.user_assessments.find(query, {"itemGroups": 1, "assessmentId": 1})
        for doc in cursor:
            for group in doc.get("itemGroups", []) or []:
                for item in group.get("items", []) or []:
                    qid = item.get("questionId") or item.get("itemId") or item.get("_id")
                    if not qid:
                        continue
                    label = self._extract_answer_label(item, label_map)
                    if not label:
                        # Skip options without a known human-readable label
                        continue
                    per_question_counts[str(qid)][label] += 1

        # Transform into label -> list[counts] over questions
        label_to_series: Dict[str, List[int]] = defaultdict(list)
        for qid, label_counts in per_question_counts.items():
            for label, count in label_counts.items():
                label_to_series[label].append(int(count))
        return dict(label_to_series)

    def answer_counts_by_question(self, assessment_id: str) -> Dict[str, Dict[str, int]]:
        label_map = self._answer_label_map()
        per_question_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        cursor = self.user_assessments.find({"assessmentId": assessment_id}, {"itemGroups": 1})
        for doc in cursor:
            for group in doc.get("itemGroups", []) or []:
                for item in group.get("items", []) or []:
                    qid = item.get("questionId") or item.get("itemId") or item.get("_id")
                    if not qid:
                        continue
                    label = self._extract_answer_label(item, label_map)
                    if not label:
                        continue
                    per_question_counts[str(qid)][label] += 1
        return {qid: dict(counts) for qid, counts in per_question_counts.items()}

    # Users -----------------------------------------------------------------
    def fetch_users(self, limit: int = 50, query: Optional[str] = None) -> List[User]:
        filter_doc: Dict[str, Any] = {}
        if query:
            regex = {"$regex": query, "$options": "i"}
            filter_doc = {
                "$or": [
                    {"username": regex},
                    {"firstName": regex},
                    {"lastName": regex},
                    {
                        "$expr": {
                            "$regexMatch": {
                                "input": {
                                    "$trim": {
                                        "input": {
                                            "$concat": [
                                                {"$ifNull": ["$firstName", ""]},
                                                " ",
                                                {"$ifNull": ["$lastName", ""]},
                                            ]
                                        }
                                    }
                                },
                                "regex": query,
                                "options": "i",
                            }
                        }
                    },
                ]
            }

        docs = self.users.find(filter_doc).sort([("firstName", 1), ("lastName", 1)]).limit(limit)
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
        start = start.astimezone(timezone.utc)
        end = end.astimezone(timezone.utc)
        counts: Dict[str, int] = defaultdict(int)
        cursor = self.users.find({}, {"createdDate": 1})
        for doc in cursor:
            dt = _parse_datetime(doc.get("createdDate"))
            if not dt:
                continue
            dt = dt.astimezone(timezone.utc)
            if dt < start or dt >= end:
                continue
            key = dt.strftime("%Y-%m-%d")
            counts[key] += 1
        return [{"date": day, "count": counts[day]} for day in sorted(counts.keys())]

    def user_assessment_activity(self, start: datetime, end: datetime) -> Dict[str, List[Dict[str, Any]]]:
        start = start.astimezone(timezone.utc)
        end = end.astimezone(timezone.utc)
        started_counts: Dict[str, int] = defaultdict(int)
        completed_counts: Dict[str, int] = defaultdict(int)
        cursor = self.user_assessments.find({}, {"takenDate": 1, "completionDate": 1})
        for doc in cursor:
            taken = _parse_datetime(doc.get("takenDate"))
            if taken:
                taken = taken.astimezone(timezone.utc)
                if start <= taken < end:
                    key = taken.strftime("%Y-%m-%d")
                    started_counts[key] += 1
            completed = _parse_datetime(doc.get("completionDate"))
            if completed:
                completed = completed.astimezone(timezone.utc)
                if start <= completed < end:
                    key = completed.strftime("%Y-%m-%d")
                    completed_counts[key] += 1
        started = [{"date": day, "count": started_counts[day]} for day in sorted(started_counts.keys())]
        completed = [{"date": day, "count": completed_counts[day]} for day in sorted(completed_counts.keys())]
        return {"started": started, "completed": completed}

    def answer_choice_counts(self, start: datetime, end: datetime) -> List[Dict[str, Any]]:
        start = start.astimezone(timezone.utc)
        end = end.astimezone(timezone.utc)
        counts: Dict[Tuple[str, str], int] = defaultdict(int)
        question_names: Dict[str, str] = {}
        cursor = self.user_assessments.find({}, {"itemGroups": 1})
        for doc in cursor:
            for group in doc.get("itemGroups", []) or []:
                for item in group.get("items", []) or []:
                    start_dt = _parse_datetime(item.get("startDate"))
                    end_dt = _parse_datetime(item.get("completeDate"))
                    if not start_dt or not end_dt:
                        continue
                    start_dt = start_dt.astimezone(timezone.utc)
                    end_dt = end_dt.astimezone(timezone.utc)
                    if start_dt < start or end_dt >= end:
                        continue
                    question_id = item.get("questionId")
                    answer_id = item.get("chosenItemAnswerId")
                    key = (question_id, answer_id)
                    counts[key] += 1
                    prompt = item.get("prompt")
                    if question_id and prompt:
                        question_names.setdefault(question_id, prompt)
        results = [
            {
                "questionId": question,
                "answerId": answer,
                "count": count,
                "questionName": question_names.get(question) or (f"Question {question[:8]}" if question else "Question"),
            }
            for (question, answer), count in counts.items()
        ]
        results.sort(key=lambda entry: entry["count"], reverse=True)
        return results

    def answer_choice_counts_year(self, year: int) -> List[Dict[str, Any]]:
        start = datetime(year, 1, 1, tzinfo=timezone.utc)
        end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        buckets: Dict[Tuple[int, int], int] = defaultdict(int)
        cursor = self.user_assessments.find({}, {"itemGroups": 1})
        for doc in cursor:
            for group in doc.get("itemGroups", []) or []:
                for item in group.get("items", []) or []:
                    ts = _parse_datetime(item.get("startDate")) or _parse_datetime(item.get("completeDate"))
                    if not ts:
                        continue
                    ts = ts.astimezone(timezone.utc)
                    if ts < start or ts >= end:
                        continue
                    month = ts.month
                    weekday = ts.weekday()
                    buckets[(month, weekday)] += 1
        return [
            {"month": m, "weekday": w, "count": c}
            for (m, w), c in buckets.items()
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

    def users_with_navigation(self, start: datetime, end: datetime) -> List[User]:
        start = start.astimezone(timezone.utc)
        end = end.astimezone(timezone.utc)
        candidate_ids: set[str] = set()
        cursor = self.event_containers.find({}, {"userId": 1, "userEvents.timestamp": 1})
        for doc in cursor:
            uid = doc.get("userId")
            if not uid:
                continue
            for ev in doc.get("userEvents", []) or []:
                ts = _parse_datetime(ev.get("timestamp"))
                if not ts:
                    continue
                ts = ts.astimezone(timezone.utc)
                if start <= ts < end:
                    candidate_ids.add(uid)
                    break
        users: List[User] = []
        for uid in candidate_ids:
            user = self.fetch_user(uid)
            if user:
                users.append(user)
        # sort by name
        users.sort(key=lambda u: (u.last_name or "", u.first_name or "", u.username or ""))
        return users

    def assessment_time_metrics(self) -> Dict[str, List[Dict[str, Any]]]:
        group_totals: Dict[str, List[float]] = defaultdict(list)
        item_totals: Dict[str, List[float]] = defaultdict(list)
        item_names: Dict[str, str] = {}
        group_names: Dict[str, str] = {}

        cursor = self.user_assessments.find({}, {"itemGroups": 1})
        for doc in cursor:
            for group in doc.get("itemGroups", []) or []:
                group_id = group.get("_id", "")
                durations = []
                for item in group.get("items", []) or []:
                    start = _parse_datetime(item.get("startDate"))
                    end = _parse_datetime(item.get("completeDate"))
                    if not start or not end:
                        continue
                    duration = (end - start).total_seconds()
                    qid = item.get("questionId", "")
                    item_totals[qid].append(duration)
                    durations.append(duration)
                    if "prompt" in item and item.get("prompt"):
                        item_names.setdefault(qid, item.get("prompt"))
                if durations:
                    group_totals[group_id].append(sum(durations) / len(durations))

        group_names_map, item_names_map = self._group_and_item_names()
        if group_names_map:
            group_names.update(group_names_map)
        if item_names_map:
            for key, value in item_names_map.items():
                item_names.setdefault(key, value)

        group_stats = [
            {
                "groupId": group_id,
                "groupName": group_names.get(group_id, f"Group {group_id[:8]}"),
                "avgSeconds": sum(values) / len(values),
            }
            for group_id, values in group_totals.items() if values
        ]
        item_stats = [
            {
                "questionId": item_id,
                "questionName": item_names.get(item_id, f"Question {item_id[:8]}"),
                "avgSeconds": sum(values) / len(values),
            }
            for item_id, values in item_totals.items() if values
        ]
        group_stats.sort(key=lambda g: g["avgSeconds"], reverse=True)
        item_stats.sort(key=lambda g: g["avgSeconds"], reverse=True)
        return {"groups": group_stats[:20], "items": item_stats[:20]}

    def login_heatmap(self, start: datetime, end: datetime) -> List[Dict[str, Any]]:
        start = start.astimezone(timezone.utc)
        end = end.astimezone(timezone.utc)
        counts: Dict[Tuple[int, int], int] = defaultdict(int)
        cursor = self.event_containers.find({}, {"userEvents": 1})
        for doc in cursor:
            for event in doc.get("userEvents", []) or []:
                ts = _parse_datetime(event.get("timestamp"))
                if not ts:
                    continue
                ts = ts.astimezone(timezone.utc)
                if ts < start or ts >= end:
                    continue
                etype = event.get("eventType")
                # Count only login-like events if present; otherwise fall back to any event
                if etype and etype.upper() != "LOGIN":
                    continue
                month = ts.month
                day = ts.day
                counts[(month, day)] += 1
        results = [
            {"month": m, "day": d, "count": c}
            for (m, d), c in counts.items()
        ]
        results.sort(key=lambda x: (x["month"], x["day"]))
        return results

    def login_heatmap_year(self, year: int) -> List[Dict[str, Any]]:
        start = datetime(year, 1, 1, tzinfo=timezone.utc)
        end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        counts: Dict[Tuple[int, int], int] = defaultdict(int)
        cursor = self.event_containers.find({}, {"userEvents": 1})
        for doc in cursor:
            for event in doc.get("userEvents", []) or []:
                ts = _parse_datetime(event.get("timestamp"))
                if not ts:
                    continue
                ts = ts.astimezone(timezone.utc)
                if ts < start or ts >= end:
                    continue
                etype = event.get("eventType")
                if etype and etype.upper() != "LOGIN":
                    continue
                month = ts.month
                weekday = ts.weekday()  # Monday=0
                counts[(month, weekday)] += 1
        results = [
            {"month": m, "weekday": w, "count": c}
            for (m, w), c in counts.items()
        ]
        results.sort(key=lambda x: (x["weekday"], x["month"]))
        return results

    def login_daily_counts_year(self, year: int) -> List[Dict[str, Any]]:
        start = datetime(year, 1, 1, tzinfo=timezone.utc)
        end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        daily: Dict[int, int] = defaultdict(int)
        cursor = self.event_containers.find({}, {"userEvents": 1})
        for doc in cursor:
            for event in doc.get("userEvents", []) or []:
                ts = _parse_datetime(event.get("timestamp"))
                if not ts:
                    continue
                ts = ts.astimezone(timezone.utc)
                if ts < start or ts >= end:
                    continue
                etype = event.get("eventType")
                if etype and etype.upper() != "LOGIN":
                    continue
                day_of_year = ts.timetuple().tm_yday
                daily[day_of_year] += 1
        # Determine number of days in the year
        days_in_year = (datetime(year + 1, 1, 1, tzinfo=timezone.utc) - datetime(year, 1, 1, tzinfo=timezone.utc)).days
        return [{"day": d, "count": daily.get(d, 0)} for d in range(1, days_in_year + 1)]

    def login_daily_counts_month(self, year: int, month: int) -> List[Dict[str, Any]]:
        start = datetime(year, month, 1, tzinfo=timezone.utc)
        if month == 12:
            end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            end = datetime(year, month + 1, 1, tzinfo=timezone.utc)
        days_in_month = monthrange(year, month)[1]
        daily: Dict[int, int] = defaultdict(int)
        cursor = self.event_containers.find({}, {"userEvents": 1})
        for doc in cursor:
            for event in doc.get("userEvents", []) or []:
                ts = _parse_datetime(event.get("timestamp"))
                if not ts:
                    continue
                ts = ts.astimezone(timezone.utc)
                if ts < start or ts >= end:
                    continue
                etype = event.get("eventType")
                if etype and etype.upper() != "LOGIN":
                    continue
                day = ts.day
                daily[day] += 1
        return [{"day": d, "count": daily.get(d, 0)} for d in range(1, days_in_month + 1)]

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
