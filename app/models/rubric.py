import re
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class GradingFlag(str, Enum):
    """
    Enumeration of possible grading flags.

    These flags modify the grading behavior of the rubric.
    """
    IGNORE_SPELLINGS = "IGNORE_SPELLINGS"

    IGNORE_GRAMMAR = "IGNORE_GRAMMAR"

    ORIGINALITY = "ORIGINALITY"

    IGNORE_FORMATTING = "IGNORE_FORMATTING"


class GradingCriteria(BaseModel):
    """
    Represents a grading criteria for an individual question.
    """
    criteria_id: str = Field(..., description="Title of the grading criteria.")
    criteria: str = Field(..., description="A detailed description of this grading criteria outlining what "
                                           "exactly constitutes as fulfilling this criteria.")
    points: float = Field(..., description="The amount of points allocated to this criteria.")


class SubRubric(BaseModel):
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
            "- `ORIGINALITY`: Reward originality and deduct for unoriginal ideas.\n"
            "- `IGNORE_FORMATTING`: Ignore formatting issues."
        )
    )
    overall_instructor_guidelines: Optional[str] = Field(
        None, description="General grading criteria applicable to all questions."
    )
    sub_rubrics: List[SubRubric] = Field(
        ...,
        description="List of sub-rubrics specifying grading for individual questions.",
    )

    
    @field_validator("course_id", mode="before")
    def normalize_lowercase(cls, value: str) -> str:
        """Converts course_id and semester to lowercase and trims spaces."""
        return value.strip().lower()

    
    @field_validator("semester", mode='before')
    def validate_semester(cls, value: str) -> str:
        """Converts to lowercase and trims spaces."""
        if re.fullmatch("[a-z]{1,12}[0-9]{4}", value) is None:
            raise ValueError("Semester is in an invalid format. "
                             "Correct format (case-sensitive) looks like: seasonYYYY. (e.g. spring2025)")
        return value.strip().lower()
