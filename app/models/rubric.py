# app/models/rubric.py

import re
from enum import Enum
from typing import List, Optional
import math

<<<<<<< HEAD
from pydantic import BaseModel, Field, field_validator, root_validator
=======
from pydantic import BaseModel, Field, field_validator, model_validator
>>>>>>> 403752feee3206c64f1870525767b22004419e97


class GradingFlag(str, Enum):
    IGNORE_SPELLINGS = "IGNORE_SPELLINGS"
    IGNORE_GRAMMAR = "IGNORE_GRAMMAR"
    ORIGINALITY = "ORIGINALITY"
    IGNORE_FORMATTING = "IGNORE_FORMATTING"

    def get_description(self):
        if self == GradingFlag.IGNORE_SPELLINGS:
            return "Ignore minor spelling mistakes if they do not affect the comprehension of the material."
        elif self == GradingFlag.IGNORE_GRAMMAR:
            return "Ignore minor grammar issues if they do not affect the comprehension of the material."
        elif self == GradingFlag.ORIGINALITY:
            return "Reward originality and thoughtful ideas."
        else:
            return "Unknown flag."


class GradingCriteria(BaseModel):
    criteria_id: str = Field(..., description="Title...")
    criteria: str = Field(..., description="A detailed description...")
    points: float = Field(..., ge=0, description="Points (non-negative).")


class SubRubric(BaseModel):
<<<<<<< HEAD
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
=======
    """
    Sub-rubric for an individual question.
    """
    question_index: int = Field(..., description="Index of the question.")
    max_points: float = Field(..., description="Maximum points for this question.")
    instructor_guideline: Optional[str] = Field(
        None, description="General instruction guidelines outline the grading rules for the question."
    )
    grading_criteria: Optional[List[GradingCriteria]] = Field(None, description="A breakdown of the grading criteria. "
                                                                                "If this field is specified, "
                                                                                "the sum of the points allocated to "
                                                                                "each grading criteria must sum to "
                                                                                "'max_points'.")
>>>>>>> 403752feee3206c64f1870525767b22004419e97

    @model_validator(mode="after")
    def check_grading_criteria(cls, values):
        max_points = values.max_points
        grading_criteria = values.grading_criteria
        if grading_criteria is not None and len(grading_criteria) != 0:
            total_allocated = 0
            for criteria in grading_criteria:
                # Check each criterion individually
                if criteria.points > max_points:
                    raise ValueError(
                        f"Points allocated to grading criteria '{criteria.criteria_id}' "
                        f"({criteria.points}) exceeds the maximum points allocated to"
                        f" the whole question ({max_points})."
                    )
                total_allocated += criteria.points
            # Compare sum of points to the parent max_points
            if total_allocated != max_points:
                raise ValueError(
                    f"The sum of grading criteria points ({total_allocated}) does not equal "
                    f"max_points ({max_points})."
                )
        return values


class Rubric(BaseModel):
<<<<<<< HEAD
    semester: str = Field(..., description="Semester...")
    course_id: str = Field(..., description="Course ID.")
    # --- CHANGED TYPE: Back to str ---
    assignment_id: str = Field(..., description="Associated assignment's string ID.")
    # --- END CHANGE ---
    grading_flags: List[GradingFlag] = Field(default_factory=list, description="Flags...")
    leniency: int = Field(3, ge=1, le=5, description="Leniency...")
    overall_instructor_guidelines: Optional[str] = Field(None, description="Guidelines...")
    sub_rubrics: List[SubRubric] = Field(..., description="Sub-rubrics...")
=======
    """
    Rubric object containing grading instructions.
    """
    semester: str = Field(..., description="The semester associated with the course.")
    course_id: str = Field(..., description="Associated course identifier.")
    assignment_id: str = Field(..., description="Associated assignment's ID.")
    grading_flags: Optional[List[GradingFlag]] = Field(
        None, description=(
            "List of grading flags that modify grading behavior. Options:\n"
            "- `IGNORE_SPELLINGS`: Ignore minor spelling mistakes.\n"
            "- `IGNORE_GRAMMAR`: Ignore minor grammar issues.\n"
            "- `ORIGINALITY`: Reward originality and deduct for unoriginal ideas."
        )
    )
    overall_instructor_guidelines: Optional[str] = Field(
        None, description="General grading criteria applicable to all questions."
    )
    sub_rubrics: List[SubRubric] = Field(
        default_factory=list,
        description="List of sub-rubrics specifying grading for individual questions.",
    )
>>>>>>> 403752feee3206c64f1870525767b22004419e97

    @field_validator("course_id", mode="before")
    def normalize_lowercase(cls, value: str) -> str:
        if not isinstance(value, str): raise TypeError("course_id must be a string")
        return value.strip().lower()

    @field_validator("semester", mode='before')
    def validate_semester(cls, value: str) -> str:
<<<<<<< HEAD
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
=======
        """Converts to lowercase and trims spaces."""
        if re.fullmatch("[a-z]{1,12}[0-9]{4}", value) is None:
            raise ValueError("Semester is in an invalid format. "
                             "Correct format (case-sensitive) looks like: seasonYYYY. (e.g. spring2025)")
        return value.strip().lower()
>>>>>>> 403752feee3206c64f1870525767b22004419e97
