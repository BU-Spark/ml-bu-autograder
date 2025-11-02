import logging
from typing import Optional

from app.models.rubric import Rubric
from app.models.rubric_review import RubricCritique
from app.utils.llm_service import LLMService, PromptBuilder, PromptRole


class RubricRefinementService:
    def __init__(self):
        self.llm = LLMService.get_instance()
        if self.llm is None:
            raise RuntimeError("LLMService is not initialized")

    def critique_rubric(self, assignment, rubric: Rubric, instructions: Optional[str] = None) -> RubricCritique:
        prompt = (
            PromptBuilder.builder()
            .add_message(
                PromptRole.SYSTEM,
                "You are an expert educational assessment auditor. Your job is to REVIEW the rubric, not to rewrite it. "
                "Identify clear weaknesses with actionable recommendations. Keep feedback specific and concise.",
            )
            .add_message(PromptRole.USER, "Assignment details for context:")
            .add_json_input(PromptRole.USER, assignment)
            .add_message(PromptRole.USER, "Rubric to review:")
            .add_json_input(PromptRole.USER, rubric)
            .add_message(
                PromptRole.USER,
                "Evaluate the rubric on: specificity/measurability, point distribution fairness, coverage of required skills, "
                "clarity of instructor guidelines, duplication/ambiguity, and appropriate grading flags. "
                "If criteria are missing or points don’t add up per question, flag them. "
                "Return a structured RubricCritique. Do NOT propose a new rubric in this step.",
            )
        )

        if instructions:
            prompt.add_message(
                PromptRole.USER,
                f"Instructor notes to consider during review: {instructions}",
            )

        logging.debug(prompt.debug_string())
        messages = prompt.build()
        return self.llm.generate_structured_response(messages, RubricCritique)

    def refine_rubric(
        self,
        assignment,
        original_rubric: Rubric,
        critique: RubricCritique,
        instructions: Optional[str] = None,
    ) -> Rubric:
        base = (
            PromptBuilder.builder()
            .add_message(
                PromptRole.SYSTEM,
                "You are an expert in improving assessment rubrics. Revise the rubric by addressing EVERY weakness in the critique. "
                "Preserve the assignment's intent. Use precise, measurable criteria. Keep structure clean and logical.",
            )
            .add_message(PromptRole.USER, "Assignment details:")
            .add_json_input(PromptRole.USER, assignment)
            .add_message(PromptRole.USER, "Original rubric:")
            .add_json_input(PromptRole.USER, original_rubric)
            .add_message(PromptRole.USER, "Critique to address:")
            .add_json_input(PromptRole.USER, critique)
            .add_message(
                PromptRole.USER,
                "Revise the rubric to fix all weaknesses. \n"
                "Requirements:\n"
                "- Make criteria specific, measurable, and objective.\n"
                "- Ensure per-question grading_criteria points sum EXACTLY to that question's max_points.\n"
                "- Add missing criteria where needed.\n"
                "- Add/clarify instructor_guideline where helpful.\n"
                "- Only adjust per-question max_points if strictly necessary; if adjusted, ensure all sums match and reflect fairness.",
            )
        )

        if instructions:
            base.add_message(
                PromptRole.USER,
                f"Instructor-specific refinement instructions: {instructions}",
            )

        logging.debug(base.debug_string())
        messages = base.build()
        try:
            return self.llm.generate_structured_response(messages, Rubric)
        except Exception as e:
            # One guided retry with the validation error surfaced
            logging.warning("First refinement attempt failed, retrying with validation error context: %s", str(e))
            retry = (
                base
                .add_message(
                    PromptRole.USER,
                    "The previous output failed validation with this error: "
                    f"{str(e)}\n"
                    "Please ONLY correct the validation issues and return a valid Rubric that satisfies all constraints.",
                )
            )
            return self.llm.generate_structured_response(retry.build(), Rubric)

