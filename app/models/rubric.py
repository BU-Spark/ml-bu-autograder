# app/models/rubric.py

import re
from enum import Enum
from typing import List, Optional
import math

from pydantic import BaseModel, Field, field_validator, root_validator


class GradingFlag(str, Enum):
    IGNORE_SPELLINGS = "IGNORE_SPELLINGS"
    IGNORE_GRAMMAR = "IGNORE_GRAMMAR"
    ORIGINALITY = "ORIGINALITY"
    IGNORE_FORMATTING = "IGNORE_FORMATTING"


class GradingCriteria(BaseModel):
    criteria_id: str = Field(..., description="Title...")
    criteria: str = Field(..., description="A detailed description...")
    points: float = Field(..., ge=0, description="Points (non-negative).")


class SubRubric(BaseModel):
    question_index: int = Field(..., description="Index...")
    max_points: float = Field(..., ge=0, description="Max points (non-negative).")
    leniency: Optional[int] = Field(None, ge=1, le=5, description="Leniency...")
    instructor_guideline: Optional[str] = Field(None, description="Guidelines...")
    grading_criteria: List[GradingCriteria] = Field(default_factory=list, description="Criteria list.")

    @field_validator('grading_criteria')
    @classmethod
    def check_points_sum(cls, criteria_list: List[GradingCriteria], info) -> List[GradingCriteria]:
        max_points = info.data.get('max_points')
        criteria = criteria_list
        if isinstance(max_points, (int, float)) and max_points >= 0 and criteria is not None:
            current_sum = sum(c.points for c in criteria if c and hasattr(c, 'points'))
            if not math.isclose(current_sum, max_points):
                q_index = info.data.get('question_index', 'N/A')
                raise ValueError(
                    f"Sum of criteria points ({current_sum}) does not match max_points ({max_points}) "
                    f"for question index {q_index}"
                )
        return criteria_list


class Rubric(BaseModel):
    semester: str = Field(..., description="Semester...")
    course_id: str = Field(..., description="Course ID.")
    # --- CHANGED TYPE: Back to str ---
    assignment_id: str = Field(..., description="Associated assignment's string ID.")
    # --- END CHANGE ---
    grading_flags: List[GradingFlag] = Field(default_factory=list, description="Flags...")
    leniency: int = Field(3, ge=1, le=5, description="Leniency...")
    overall_instructor_guidelines: Optional[str] = Field(None, description="Guidelines...")
    sub_rubrics: List[SubRubric] = Field(..., description="Sub-rubrics...")

    @field_validator("course_id", mode="before")
    def normalize_lowercase(cls, value: str) -> str:
        if not isinstance(value, str): raise TypeError("course_id must be a string")
        return value.strip().lower()

    @field_validator("semester", mode='before')
    def validate_semester(cls, value: str) -> str:
        if not isinstance(value, str): raise TypeError("semester must be a string")
        val_strip = value.strip()
        if not re.fullmatch(r"[a-z]{1,12}[0-9]{4}", val_strip.lower()):
             raise ValueError("Semester is in an invalid format...")
        return val_strip.lower()

    # --- ADDED: Ensure assignment_id is a string if it comes in differently ---
    # Optional: Add validator if you expect numbers sometimes and need to convert
    @field_validator("assignment_id", mode="before")
    def ensure_assignment_id_is_string(cls, value):
        if value is None: # Should not happen if field is required (...)
             raise ValueError("assignment_id is required")
        if not isinstance(value, str):
            # Log warning if needed: logger.warning(f"Converting non-string assignment_id '{value}' to string.")
            return str(value)
        return value # Return the string value
    # --- END ADDED ---