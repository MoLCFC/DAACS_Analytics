"""Core data models used by the DAACS analytics service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any


@dataclass
class User:
    id: str
    username: str
    first_name: str
    last_name: str
    roles: List[str]
    created_at: datetime
    disabled: bool

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def is_student(self) -> bool:
        return "ROLE_STUDENT" in self.roles


@dataclass
class AssessmentAnswer:
    question_id: str
    answer_id: str
    domain_id: str
    score: float
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    @property
    def duration_seconds(self) -> float:
        if not self.started_at or not self.completed_at:
            return 0.0
        return (self.completed_at - self.started_at).total_seconds()


@dataclass
class AssessmentItemGroup:
    id: str
    difficulty: str
    answers: List[AssessmentAnswer]

    @property
    def score(self) -> float:
        return sum(ans.score for ans in self.answers)


@dataclass
class UserAssessment:
    id: str
    user_id: str
    assessment_id: str
    status: str
    progress: float
    overall_score: float
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    item_groups: List[AssessmentItemGroup]

    @property
    def duration_minutes(self) -> float:
        if not self.started_at or not self.completed_at:
            return 0.0
        return (self.completed_at - self.started_at).total_seconds() / 60


@dataclass
class UserEvent:
    id: str
    event_type: str
    occurred_at: datetime
    url: str


@dataclass
class EventContainer:
    id: str
    user_id: str
    events: List[UserEvent]


@dataclass
class SystemMetrics:
    total_users: int
    active_users: int
    total_assessments: int
    average_score: float
    peak_hours: List[int]
    top_pages: Dict[str, int]
