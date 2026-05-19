"""Test runner for rubric review functionality."""

import logging
import os
from typing import Optional, Tuple

from app.models.assignment import Assignment
from app.models.rubric import Rubric
from app.models.rubric_review import RubricRefinementResponse, RubricCritique
from app.services.rubric_refinement_service import RubricRefinementService

# Handle both relative and absolute imports
try:
    from ..utils.formatter import RubricFormatter
    from .parser import RubricFileParser
    from ..services.initialization import create_rubric_refinement_service, initialize_llm_service
    from ..utils.storage import RubricStorage
except ImportError:
    # Fallback for when run as script directly
    import sys
    # Add parent directory to path for imports
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    from utils.formatter import RubricFormatter
    from core.parser import RubricFileParser
    from services.initialization import create_rubric_refinement_service, initialize_llm_service
    from utils.storage import RubricStorage

logger = logging.getLogger(__name__)


# Constants for rubric refinement instructions
_CONTEXT_PREFIX = "IMPORTANT CONTEXT: These quizzes are NOT submitted late, and there are not administrative penalties. When reviewing the rubric, "

_BASE_CRITIQUE_INSTRUCTIONS = (
    _CONTEXT_PREFIX +
    "ensure fair and appropriate scoring that rewards quality while being reasonable about partial credit. "
    "The rubric should recognize partial understanding appropriately, but must also create clear distinctions "
    "between different levels of performance. Focus on point distribution, missing criteria, and clarity.\n\n"
    "CRITICAL SCORING PRINCIPLES FOR FAIR GRADING:\n"
    "1. High-level understanding is the #1 scoring factor. Students who demonstrate clear conceptual understanding "
    "should receive strong scores. Additional explanations enhance answers but their absence should NOT subtract from scores "
    "if core understanding is present. However, answers with vague, incomplete, or incorrect understanding should receive "
    "appropriately lower scores to maintain fair differentiation.\n"
    "2. Sentence count is NOT a determining factor of answer quality and must NOT be included in the scoring rubric. "
    "The rubric should focus exclusively on conceptual understanding, accuracy, and completeness of key ideas, not writing length.\n"
    "3. Fair differentiation: The rubric must create meaningful distinctions between excellent, good, adequate, and poor responses. "
    "While partial credit is appropriate, the scoring should accurately reflect the depth and correctness of understanding demonstrated."
)

_BASE_REFINE_INSTRUCTIONS = (
    "IMPORTANT: These quizzes are NOT submitted late, and there are not administrative penalties. When refining the rubric, "
    "ensure it promotes fair and appropriate scoring that accurately reflects student understanding. "
    "Provide opportunities for partial credit when appropriate, but maintain clear and meaningful distinctions "
    "between different levels of performance to ensure fairness.\n\n"
    "CRITICAL SCORING PRINCIPLES TO ENFORCE FOR FAIR GRADING:\n"
    "1. High-level understanding is the #1 scoring factor. Students demonstrating clear, accurate understanding "
    "should receive strong scores. Additional explanations enhance but their absence must NOT reduce scores for answers "
    "that show core understanding. However, ensure that vague, incorrect, or significantly incomplete understanding "
    "receives appropriately lower scores.\n"
    "2. Sentence count or answer length must NOT be included as a scoring criterion. Remove any references to "
    "sentence count, word count, or answer length from the rubric. Focus exclusively on conceptual understanding, accuracy, "
    "and completeness of key ideas.\n"
    "3. Fair performance differentiation: Create clear scoring tiers that distinguish between excellent (demonstrates "
    "deep understanding with accuracy), good (solid understanding with minor gaps), adequate (basic understanding with "
    "some gaps or inaccuracies), and poor (minimal or incorrect understanding) responses. Ensure point distributions "
    "accurately reflect these distinctions."
)


class RubricTestRunner:
    """Test runner for rubric review functionality."""
    
    def __init__(self, rubric_file_path: str):
        self.rubric_file_path = rubric_file_path
        self.parser = None  # Will be initialized after LLM service
        self.service = None
    
    def initialize_service(self) -> bool:
        """Initialize the LLM service."""
        if not initialize_llm_service():
            return False
        
        self.service = create_rubric_refinement_service()
        if self.service is None:
            return False
        
        # Initialize parser after LLM service is ready
        self.parser = RubricFileParser()
        return True
    
    def load_rubric(self) -> Tuple[Assignment, Rubric]:
        """Load and parse the rubric file using LLM."""
        if self.parser is None:
            raise RuntimeError("LLM service must be initialized before loading rubric")
        
        logger.info(f"Loading rubric from: {self.rubric_file_path}")
        return self.parser.parse(self.rubric_file_path)
    
    @staticmethod
    def _combine_instructions(base: str, custom: Optional[str]) -> str:
        """Combine base instructions with custom instructions."""
        return f"{base}\n\n{custom}" if custom else base
    
    def _get_critique_instructions(self, custom: Optional[str] = None) -> str:
        """Get critique instructions with optional custom additions."""
        return self._combine_instructions(_BASE_CRITIQUE_INSTRUCTIONS, custom)
    
    def _get_refine_instructions(
        self, current_score: Optional[int] = None, target_score: Optional[int] = None,
        custom: Optional[str] = None
    ) -> str:
        """Get refine instructions with optional score context and custom additions."""
        prefix = ""
        if current_score is not None and target_score is not None:
            prefix = (
                f"Fix all identified weaknesses. Current score is {current_score}/100, "
                f"target is {target_score}/100. Focus on the most critical issues first.\n\n"
            )
        elif current_score is not None:
            prefix = f"Fix all identified weaknesses. Current score is {current_score}/100.\n\n"
        
        base = prefix + _BASE_REFINE_INSTRUCTIONS
        return self._combine_instructions(base, custom)
    
    def test_critique(self, assignment: Assignment, rubric: Rubric, 
                     instructions: Optional[str] = None) -> Optional[RubricCritique]:
        """Test the critique functionality."""
        self._print_separator("TEST 1: Critique Rubric", "#")
        
        print("\nOriginal Rubric:")
        RubricFormatter.print_rubric(rubric, "ORIGINAL RUBRIC")
        
        print("\n\nGenerating critique...")
        try:
            critique = self.service.critique_rubric(
                assignment, rubric, self._get_critique_instructions(instructions)
            )
            RubricFormatter.print_critique(critique)
            return critique
        except Exception as e:
            logger.error(f"Failed to critique rubric: {e}", exc_info=True)
            return None
    
    def test_refine(self, assignment: Assignment, original_rubric: Rubric,
                   critique: RubricCritique, 
                   instructions: Optional[str] = None) -> Optional[Rubric]:
        """Test the refine functionality."""
        self._print_separator("TEST 2: Refine Rubric", "#")
        
        print("\n\nRefining rubric based on critique...")
        try:
            prefix = "Ensure all point totals are correct and add missing criteria.\n\n"
            refine_instructions = prefix + self._get_refine_instructions(custom=instructions)
            improved_rubric = self.service.refine_rubric(
                assignment, original_rubric, critique, refine_instructions
            )
            
            print("\nImproved Rubric:")
            RubricFormatter.print_rubric(improved_rubric, "IMPROVED RUBRIC")
            
            self._print_separator("REFINED RUBRIC OUTPUT")
            RubricFormatter.print_new_rubric(improved_rubric, assignment)
            
            # Save rubric files
            saved_path = RubricStorage.save_refined_rubric(
                improved_rubric, assignment, self.rubric_file_path
            )
            print(f"\nRefined rubric saved to: {saved_path}")
            
            json_path = RubricStorage.save_refined_rubric_json(improved_rubric)
            print(f"Refined rubric JSON saved to: {json_path}")
            
            return improved_rubric
        except Exception as e:
            logger.error(f"Failed to refine rubric: {e}", exc_info=True)
            return None
    
    def _save_and_print_final_rubric(
        self, rubric: Rubric, assignment: Assignment, critique: RubricCritique
    ) -> None:
        """Save and print the final refined rubric."""
        self._print_separator("FINAL REFINED RUBRIC")
        RubricFormatter.print_new_rubric(rubric, assignment)
        
        saved_path = RubricStorage.save_refined_rubric(rubric, assignment, self.rubric_file_path)
        print(f"\n Final refined rubric saved to: {saved_path}")
        
        json_path = RubricStorage.save_refined_rubric_json(rubric)
        print(f" Refined rubric JSON saved to: {json_path}")
    
    def _print_iteration_summary(self, critique: RubricCritique, target_score: int):
        """Print summary of critique iteration."""
        print(f"\nCritique Score: {critique.overall_score}/100")
        print(f"Target Score: {target_score}/100")
        print(f"Weaknesses Found: {len(critique.weaknesses)}")
    
    @staticmethod
    def _print_separator(text: str, char: str = "="):
        """Print a separator line with text."""
        print(f"\n\n{char*80}")
        print(text)
        print(char*80)
    
    def _print_completion_summary(self, response: RubricRefinementResponse, target_score: int, iterations: int):
        """Print final refinement completion summary."""
        self._print_separator("ITERATIVE REFINEMENT COMPLETE", "-")
        print(f"\nFinal Score: {response.critique.overall_score}/100")
        print(f"Target Score: {target_score}/100")
        print(f"Iterations: {iterations}")
        print(f"Final Weaknesses: {len(response.critique.weaknesses)}")
    
    def iterative_refinement(self, assignment: Assignment, rubric: Rubric,
                            target_score: int = 90, max_iterations: int = 10,
                            instructions: Optional[str] = None) -> Optional[RubricRefinementResponse]:
        """Iteratively refine the rubric until critique score is above target_score.
        
        Args:
            assignment: The assignment associated with the rubric
            rubric: The original rubric to refine
            target_score: Target critique score (default: 90)
            max_iterations: Maximum number of refinement iterations (default: 10)
            instructions: Optional instructions for refinement (will be appended to default no late submission guidance)
            
        Returns:
            RubricRefinementResponse with the final refined rubric and critique
        """
        self._print_separator(
            f"ITERATIVE REFINEMENT (Target Score: {target_score}, Max Iterations: {max_iterations})", "#"
        )
        
        current_rubric = rubric
        iteration = 0
        
        print("\nOriginal Rubric:")
        RubricFormatter.print_rubric(current_rubric, "ORIGINAL RUBRIC")
        
        while iteration < max_iterations:
            iteration += 1
            self._print_separator(f"ITERATION {iteration}/{max_iterations}")
            
            print(f"\nSTEP 1: Generating Critique (Iteration {iteration})")
            print("-"*80)
            try:
                critique = self.service.critique_rubric(
                    assignment, current_rubric,
                    instructions=self._get_critique_instructions(instructions)
                )
                self._print_iteration_summary(critique, target_score)
                
                # Check if we've reached the target score
                if critique.overall_score >= target_score:
                    print(f"\n Target score reached! Score: {critique.overall_score}/100")
                    RubricFormatter.print_critique(critique)
                    
                    self._save_and_print_final_rubric(current_rubric, assignment, critique)
                    
                    response = RubricRefinementResponse(
                        saved=True, critique=critique, improved_rubric=current_rubric
                    )
                    
                    self._print_completion_summary(response, target_score, iteration)
                    return response
                
                # If not at target, show critique details
                if iteration == 1 or len(critique.weaknesses) > 0:
                    RubricFormatter.print_critique(critique)
                
            except Exception as e:
                logger.error(f"Failed to critique rubric in iteration {iteration}: {e}", exc_info=True)
                return None
            
            print(f"\n\nSTEP 2: Refining Rubric (Iteration {iteration})")
            print("-"*80)
            try:
                refined_rubric = self.service.refine_rubric(
                    assignment, current_rubric, critique,
                    instructions=self._get_refine_instructions(
                        critique.overall_score, target_score, instructions
                    )
                )
                
                print(f"\n Rubric refined (Iteration {iteration})")
                print(f"Previous Score: {critique.overall_score}/100")
                
                # Update current rubric for next iteration
                current_rubric = refined_rubric
                
            except Exception as e:
                logger.error(f"Failed to refine rubric in iteration {iteration}: {e}", exc_info=True)
                return None
        
        self._print_separator(f"MAX ITERATIONS REACHED ({max_iterations})")
        print("\nGetting final critique...")
        
        try:
            final_critique = self.service.critique_rubric(
                assignment, current_rubric,
                instructions=self._get_critique_instructions(instructions)
            )
            
            self._print_iteration_summary(final_critique, target_score)
            
            if final_critique.overall_score < target_score:
                print(f"\n  Target score not reached after {max_iterations} iterations")
            else:
                print(f"\n Target score reached!")
            
            RubricFormatter.print_critique(final_critique)
            self._save_and_print_final_rubric(current_rubric, assignment, final_critique)
            
            response = RubricRefinementResponse(
                saved=True, critique=final_critique, improved_rubric=current_rubric
            )
            
            self._print_completion_summary(response, target_score, max_iterations)
            return response
            
        except Exception as e:
            logger.error(f"Failed to get final critique: {e}", exc_info=True)
            return None
    
    def test_full_workflow(self, assignment: Assignment, rubric: Rubric) -> Optional[RubricRefinementResponse]:
        """Test the complete workflow."""
        self._print_separator("TEST 3: Full Workflow (Critique + Refine)", "#")
        
        print("\nOriginal Rubric:")
        RubricFormatter.print_rubric(rubric, "ORIGINAL RUBRIC")
        
        print("\n\nSTEP 1: Generating Critique")
        print("-"*80)
        try:
            custom_instructions = "Focus on point distribution and missing criteria.\n\n"
            critique = self.service.critique_rubric(
                assignment, rubric,
                instructions=self._combine_instructions(
                    custom_instructions + _BASE_CRITIQUE_INSTRUCTIONS, None
                )
            )
            RubricFormatter.print_critique(critique)
        except Exception as e:
            logger.error(f"Failed to critique rubric: {e}", exc_info=True)
            return None
        
        print("\n\nSTEP 2: Refining Rubric")
        print("-"*80)
        try:
            prefix = "Fix all identified weaknesses and ensure point totals are correct.\n\n"
            improved_rubric = self.service.refine_rubric(
                assignment, rubric, critique,
                instructions=prefix + self._get_refine_instructions()
            )
            RubricFormatter.print_rubric(improved_rubric, "IMPROVED RUBRIC")
            
            self._print_separator("REFINED RUBRIC OUTPUT")
            RubricFormatter.print_new_rubric(improved_rubric, assignment)
            
            saved_path = RubricStorage.save_refined_rubric(
                improved_rubric, assignment, self.rubric_file_path
            )
            print(f"\nRefined rubric saved to: {saved_path}")
            
            json_path = RubricStorage.save_refined_rubric_json(improved_rubric)
            print(f"Refined rubric JSON saved to: {json_path}")
            
            response = RubricRefinementResponse(
                saved=False, critique=critique, improved_rubric=improved_rubric
            )
            
            self._print_separator("WORKFLOW COMPLETE", "-")
            print(f"\nResponse saved: {response.saved}")
            print(f"Critique score: {response.critique.overall_score}/100")
            print(f"Number of weaknesses found: {len(response.critique.weaknesses)}")
            
            return response
        except Exception as e:
            logger.error(f"Failed to refine rubric: {e}", exc_info=True)
            return None

