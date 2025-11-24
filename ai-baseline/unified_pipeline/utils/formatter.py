"""Output formatting utilities for rubrics and critiques."""

import logging

from app.models.assignment import Assignment
from app.models.rubric import Rubric
from app.models.rubric_review import RubricCritique

logger = logging.getLogger(__name__)


class RubricFormatter:
    """Formatter for displaying rubrics and critiques."""
    
    @staticmethod
    def print_critique(critique: RubricCritique):
        """Pretty print a rubric critique."""
        print("\n" + "="*80)
        print("RUBRIC CRITIQUE")
        print("="*80)
        print(f"\nOverall Score: {critique.overall_score}/100")
        print(f"\nSummary:\n{critique.summary}")
        
        if critique.weaknesses:
            print(f"\nWeaknesses Found: {len(critique.weaknesses)}")
            for i, weakness in enumerate(critique.weaknesses, 1):
                print(f"\n  Weakness {i}:")
                print(f"    Title: {weakness.title}")
                print(f"    Severity: {weakness.severity}")
                if weakness.question_index is not None:
                    print(f"    Question Index: {weakness.question_index}")
                print(f"    Description: {weakness.description}")
                print(f"    Suggestion: {weakness.suggestion}")
        else:
            print("\nNo weaknesses found!")
    
    @staticmethod
    def print_rubric(rubric: Rubric, title: str = "RUBRIC"):
        """Pretty print a rubric."""
        print("\n" + "="*80)
        print(title)
        print("="*80)
        print(f"\nSemester: {rubric.semester}")
        print(f"Course ID: {rubric.course_id}")
        print(f"Assignment ID: {rubric.assignment_id}")
        
        if rubric.grading_flags:
            print(f"Grading Flags: {', '.join([f.value for f in rubric.grading_flags])}")
        
        if rubric.overall_instructor_guidelines:
            print(f"\nOverall Guidelines:\n{rubric.overall_instructor_guidelines}")
        
        if rubric.sub_rubrics:
            print(f"\nSub-rubrics ({len(rubric.sub_rubrics)}):")
            for sub_rubric in rubric.sub_rubrics:
                print(f"\n  Question {sub_rubric.question_index} (Max Points: {sub_rubric.max_points})")
                if sub_rubric.instructor_guideline:
                    print(f"    Guideline: {sub_rubric.instructor_guideline}")
                if sub_rubric.grading_criteria:
                    print(f"    Grading Criteria ({len(sub_rubric.grading_criteria)}):")
                    total_points = 0.0
                    for criteria in sub_rubric.grading_criteria:
                        print(f"      - {criteria.criteria_id}: {criteria.points} pts")
                        print(f"        {criteria.criteria}")
                        total_points += criteria.points
                    print(f"    Total Points: {total_points} (Expected: {sub_rubric.max_points})")
                    if abs(total_points - sub_rubric.max_points) > 0.01:
                        print(f"      WARNING: Point mismatch!")
    
    @staticmethod
    def print_new_rubric(rubric: Rubric, assignment: Assignment):
        """Print the refined rubric with title format: 'new rubric, quiz question #'."""
        if not rubric.sub_rubrics:
            logger.warning("No sub-rubrics found in rubric")
            return
        
        # Get question numbers from sub-rubrics
        question_numbers = [sub.question_index for sub in rubric.sub_rubrics]
        
        # Print each question's rubric separately
        for question_idx in question_numbers:
            sub_rubric = next((sr for sr in rubric.sub_rubrics if sr.question_index == question_idx), None)
            if not sub_rubric:
                continue
            
            # Get question text if available
            question_text = ""
            if assignment.questions and question_idx < len(assignment.questions):
                question_text = assignment.questions[question_idx].question_text
            
            print("\n" + "="*80)
            print(f"new rubric, quiz question {question_idx + 1}")
            print("="*80)
            
            if question_text:
                print(f"\nQuestion {question_idx + 1}: {question_text}")
            
            print(f"\nMax Points: {sub_rubric.max_points}")
            
            if sub_rubric.instructor_guideline:
                print(f"\nInstructor Guideline:\n{sub_rubric.instructor_guideline}")
            
            if rubric.overall_instructor_guidelines:
                print(f"\nOverall Guidelines:\n{rubric.overall_instructor_guidelines}")
            
            if sub_rubric.grading_criteria:
                print(f"\nGrading Criteria:")
                total_points = 0.0
                for i, criteria in enumerate(sub_rubric.grading_criteria, 1):
                    print(f"\n  {i}. {criteria.criteria_id} ({criteria.points} points)")
                    print(f"     {criteria.criteria}")
                    total_points += criteria.points
                print(f"\nTotal Points: {total_points} / {sub_rubric.max_points}")
                if abs(total_points - sub_rubric.max_points) > 0.01:
                    print(f"  WARNING: Point mismatch!")
            else:
                print("\nNo grading criteria specified.")
            
            if rubric.grading_flags:
                print(f"\nGrading Flags: {', '.join([f.value for f in rubric.grading_flags])}")

