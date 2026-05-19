from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field
from app.models.rubric import Rubric


class WeaknessSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Weakness(BaseModel):
    id: str = Field(..., description="Unique identifier for the weakness finding.")
    title: str = Field(..., description="Short, human-readable title for the weakness.")
    description: str = Field(..., description="Detailed explanation of the weakness and why it matters.")
    severity: WeaknessSeverity = Field(..., description="Severity level of the weakness.")
    suggestion: str = Field(..., description="Actionable recommendation to fix or improve this weakness.")
    question_index: Optional[int] = Field(
        None,
        description="If the weakness is specific to a sub-rubric, include the question index. Omit for global issues.",
    )


class RubricCritique(BaseModel):
    overall_score: int = Field(
        ..., ge=0, le=100, description="Quality score for the rubric on a 0–100 scale."
    )
    summary: str = Field(..., description="Overall summary of rubric quality and main takeaways.")
    weaknesses: List[Weakness] = Field(
        default_factory=list,
        description="List of specific, actionable weaknesses detected in the rubric.",
    )


class RubricRefinementResponse(BaseModel):
    saved: bool = Field(..., description="Whether the improved rubric was saved to storage.")
    critique: RubricCritique = Field(..., description="AI critique details.")
    improved_rubric: Rubric = Field(..., description="Revised rubric after addressing weaknesses.")
