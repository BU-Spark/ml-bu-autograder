#!/usr/bin/env python3
"""
Orchestrates the complete grading pipeline:
1. Refines rubric
2. Loads refined rubric into grading system
3. Grades all student answers from CSV
4. Saves results to CSV
"""

"""
For now, this code is partially complete.
It has been tested on with hardcoded values for the quiz_id, not yet scalable to other quizzes unless the quiz_id is passed as an argument.

TODO;
- [ ] Scale to other quizzes by passing the quiz_id as an argument.
"""
import csv
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from dotenv import load_dotenv
from openai import AzureOpenAI

# Path setup
_script_file = Path(__file__).resolve()
PROJECT_ROOT = _script_file.parents[1]  # unified_pipeline -> ai-baseline
PARENT_ROOT = _script_file.parents[2]  # ai-baseline -> ml-bu-autograder

# Add paths for imports (parent_root first for 'app' module precedence)
sys.path.insert(0, str(PARENT_ROOT))
sys.path.insert(1, str(PROJECT_ROOT))
sys.path.insert(2, str(_script_file.parent))

# Setup logging and environment
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
load_dotenv()


def _get_rubric_paths(quiz_id: str = "quiz_1") -> tuple[Path, Path]:
    """Get paths for refined and original rubric files."""
    return (
        PROJECT_ROOT / "data" / "rubric-refined" / quiz_id / "rubric_refined.txt",
        PROJECT_ROOT / "data" / quiz_id / "rubric.txt"
    )


def refine_rubric() -> bool:
    """Run the rubric refinement process."""
    logger.info("Step 1: Refining rubric...")
    
    refined_path, _ = _get_rubric_paths()
    if refined_path.exists():
        logger.info(f"Refined rubric already exists at {refined_path}. Skipping refinement.")
        return True
    
    try:
        from core.runner import RubricTestRunner
        from services.initialization import initialize_llm_service
        from config import DEFAULT_RUBRIC_FILE, DEFAULT_TARGET_SCORE, DEFAULT_MAX_ITERATIONS
        
        if not initialize_llm_service():
            logger.warning("Failed to initialize LLM service. Skipping refinement.")
            return False
        
        runner = RubricTestRunner(DEFAULT_RUBRIC_FILE)
        if not runner.initialize_service():
            logger.warning("Failed to initialize rubric refinement service. Skipping refinement.")
            return False
        
        assignment, rubric = runner.load_rubric()
        response = runner.iterative_refinement(
            assignment, rubric,
            target_score=DEFAULT_TARGET_SCORE,
            max_iterations=DEFAULT_MAX_ITERATIONS
        )
        
        if response:
            logger.info("Rubric refinement completed")
            return True
        logger.warning("Rubric refinement did not complete successfully")
        return False
    except Exception as e:
        logger.warning(f"Failed to refine rubric: {e}. Skipping refinement.")
        return False


def load_refined_rubric() -> str:
    """Load the refined rubric text."""
    logger.info("Step 2: Loading refined rubric...")
    
    refined_path, original_path = _get_rubric_paths()
    rubric_path = refined_path if refined_path.exists() else original_path
    
    if not rubric_path.exists():
        raise FileNotFoundError(
            f"Rubric file not found. Searched:\n  - {refined_path}\n  - {original_path}"
        )
    
    rubric_text = rubric_path.read_text(encoding='utf-8')
    logger.info(f"Loaded rubric from {rubric_path.name} ({len(rubric_text)} characters)")
    return rubric_text


def get_grading_system_prompt(rubric_text: str) -> str:
    """Build the complete system prompt for grading.
    
    Args:
        rubric_text: The refined rubric text
        
    Returns:
        Complete system prompt including rubric
    """
    base_prompt = """
    You are acting as a university professor responsible for grading short-answer quizzes in a graduate-level health informatics course.
    Your Persona
    
    You are a balanced, fair, and thoughtful professor. You believe in rewarding understanding and effort, but you also uphold academic standards. You:
    - Encourage and motivate students by acknowledging effort and partial understanding.
    - Reward conceptual correctness generously, even if the writing is imperfect.
    - Deduct points only when answers miss major conceptual elements defined by the rubric.
    - Avoid grade inflation: effort alone is not enough for full credit.
    - Strive for consistency: similar answers should receive similar grades (within ±1 point).

    You grade with the care of a human instructor — accurate, empathetic, and consistent.
    When grading:
    - Award points for any clear demonstration of understanding, even if phrased differently than expected.
    - Full credit requires coverage of both parts of the rubric.
    - Partial credit should be awarded when only one aspect is addressed or reasoning is shallow.
    - Minimal credit (under 8/16) should only occur when the response is vague, off-topic, or incomplete.
    Tip: If you are uncertain between two score bands, err on the side of generosity — give the higher of the two scores.
    
    Feedback Guidelines
    Each response must include specific, constructive feedback written in a supportive tone. Your feedback should:
    - Highlight what the student did correctly, with references to rubric elements (e.g., "You identified process optimization needs well.")
    - Gently mention what could be improved (e.g., "You could elaborate on how BPR supports IT cost efficiency.")
    - Avoid generic praise (e.g., "Good job!") unless paired with a rubric-based reason.
    - Keep feedback concise (2–4 sentences), supportive, and professional.

    Consistency and Self-Calibration
    After you assign a score, perform a self-check before finalizing:
    - Does the score align with the scoring scale above?
    - Does the feedback correspond to the numerical grade (e.g., not overly positive for low scores)?
    - Would a human professor plausibly give this score?
    If not, adjust the score by ±0.5 or ±1.0 to make it consistent and realistic.
    You must grade similar-quality answers within ±1 point of each other.

    Output Format
    After reasoning internally, output your result as one valid JSON object only, with this schema:
    {
    "score": number,
    "max_score": number,
    "comment": string
    }
    You must not include any other text or formatting outside the JSON.
    """
    
    full_prompt = base_prompt.rstrip() + "\n\n--- QUESTION AND RUBRIC ---\n" + rubric_text
    return full_prompt


def _clean_endpoint_url(url: str) -> str:
    """Clean Azure OpenAI endpoint URL to base URL only."""
    parsed = urlparse(url.rstrip('/'))
    path = parsed.path.rstrip('/')
    
    # Remove /openai/responses, /openai/deployments, or anything after /openai
    for pattern in ['/openai/responses', '/openai/deployments']:
        if pattern in path:
            path = path.split(pattern)[0]
            break
    else:
        if '/openai' in path and not path.endswith('/openai'):
            path = path.split('/openai')[0] + '/openai'
    
    # Remove api-version from query params
    query_params = parse_qs(parsed.query)
    query_params.pop('api-version', None)
    
    clean_url = urlunparse((
        parsed.scheme, parsed.netloc, path or '/',
        parsed.params, urlencode(query_params, doseq=True) if query_params else '',
        parsed.fragment
    ))
    return clean_url.rstrip('/') + '/'


def initialize_grading_client() -> AzureOpenAI:
    """Initialize the Azure OpenAI client for grading."""
    env_vars = {
        'api_key': os.getenv("AZURE_LLM_DEPLOYMENT_KEY"),
        'endpoint': os.getenv("AZURE_LLM_DEPLOYMENT_URL"),
        'api_version': os.getenv("AZURE_OPENAI_API_VERSION"),
        'deployment_name': os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
    }
    
    missing = [k for k, v in env_vars.items() if not v]
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
    
    endpoint_clean = _clean_endpoint_url(env_vars['endpoint'])
    
    client = AzureOpenAI(
        api_key=env_vars['api_key'],
        azure_endpoint=endpoint_clean,
        api_version=env_vars['api_version']
    )
    
    logger.info(f"Initialized Azure OpenAI client: {endpoint_clean}")
    return client


def _extract_json_from_response(text: str) -> Optional[Dict]:
    """Extract and parse JSON from response text (handles markdown code blocks)."""
    # Remove markdown code fences
    json_text = re.sub(r'^```(?:json)?\s*', '', text.strip(), flags=re.MULTILINE)
    json_text = re.sub(r'\s*```$', '', json_text.strip(), flags=re.MULTILINE)
    
    # Try direct parse first
    try:
        data = json.loads(json_text)
        if all(k in data for k in ('score', 'max_score', 'comment')):
            return data
    except json.JSONDecodeError:
        pass
    
    # Try extracting JSON object pattern
    json_match = re.search(r'\{[^{}]*"score"[^{}]*\}', text, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group(0))
            if all(k in data for k in ('score', 'max_score', 'comment')):
                logger.info("Extracted JSON from embedded text")
                return data
        except json.JSONDecodeError:
            pass
    
    return None


def grade_student_answer(client: AzureOpenAI, system_prompt: str, 
                        student_answer: str, deployment_name: str) -> Optional[Dict]:
    """Grade a single student answer."""
    try:
        response = client.chat.completions.create(
            model=deployment_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": student_answer}
            ]
        )
        
        response_text = response.choices[0].message.content
        grade_data = _extract_json_from_response(response_text)
        
        if not grade_data:
            logger.warning(f"Failed to parse grade from response: {response_text[:200]}...")
        
        return grade_data
    except Exception as e:
        logger.error(f"Failed to grade answer: {e}", exc_info=True)
        return None


def load_student_answers(quiz_id: str = "quiz_1") -> tuple[list[dict], list[str]]:
    """Load student answers from CSV file."""
    logger.info("Step 3: Loading student answers from CSV...")
    
    csv_path = PROJECT_ROOT / "data" / quiz_id / f"{quiz_id}_results.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"Student answers CSV not found: {csv_path}")
    
    students = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        original_columns = list(reader.fieldnames) if reader.fieldnames else []
        
        for row in reader:
            student_number = row.get('Student Number', '').strip()
            student_answer = row.get('student answer', '').strip()
            
            # Skip rows with missing data or non-numeric student numbers (stat rows)
            if not (student_answer and student_number and student_number.isdigit()):
                continue
            
            students.append(dict(row))
    
    logger.info(f"Loaded {len(students)} student answers")
    return students, original_columns


def save_grades_to_csv(graded_students: list, original_columns: list, output_path: Path):
    """Save graded results to CSV file."""
    logger.info(f"Step 5: Saving grades to {output_path}...")
    
    if not graded_students:
        logger.warning("No grades to save")
        return
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Add new columns if not already present
    new_columns = ['AI Score (New)', 'AI Comment (New)']
    fieldnames = list(original_columns) + [col for col in new_columns if col not in original_columns]
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for student in graded_students:
            row = {col: student.get(col, '') for col in original_columns}
            row['AI Score (New)'] = student.get('ai_score_new', '')
            row['AI Comment (New)'] = student.get('ai_comment_new', '')
            writer.writerow(row)
    
    logger.info(f"Saved {len(graded_students)} grades to {output_path}")


def main():
    """Main grading pipeline."""
    print("=" * 80)
    print("COMPLETE GRADING PIPELINE")
    print("=" * 80)
    print()
    
    try:
        quiz_id = "quiz_1"
        
        # Step 1: Refine rubric
        refine_rubric()  # Logs warnings on failure, continues anyway
        
        # Step 2: Load rubric and build prompt
        rubric_text = load_refined_rubric()
        system_prompt = get_grading_system_prompt(rubric_text)
        
        # Step 3: Initialize client
        client = initialize_grading_client()
        deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
        
        # Step 4: Load student answers
        students, original_columns = load_student_answers(quiz_id)
        if not students:
            logger.error("No student answers found to grade")
            return
        
        # Step 5: Grade each student
        logger.info("Step 4: Grading student answers...")
        graded_students = []
        
        for i, student in enumerate(students, 1):
            student_number = student['Student Number']
            student_answer = student.get('student answer', '').strip()
            
            logger.info(f"Grading student {student_number} ({i}/{len(students)})...")
            
            grade_data = grade_student_answer(client, system_prompt, student_answer, deployment_name)
            graded_student = dict(student)
            
            if grade_data:
                graded_student['ai_score_new'] = grade_data.get('score', '')
                graded_student['ai_comment_new'] = grade_data.get('comment', '')
                logger.info(f"  Graded: {grade_data.get('score', 'N/A')}/{grade_data.get('max_score', 'N/A')}")
            else:
                graded_student['ai_score_new'] = ''
                graded_student['ai_comment_new'] = ''
                logger.warning(f"  Failed to grade student {student_number}")
            
            graded_students.append(graded_student)
        
        # Step 6: Save results
        output_path = PROJECT_ROOT / "data" / quiz_id / f"{quiz_id}_graded.csv"
        save_grades_to_csv(graded_students, original_columns, output_path)
        
        successful = sum(1 for s in graded_students if s.get('ai_score_new', ''))
        print("\n" + "=" * 80)
        print("GRADING PIPELINE COMPLETE")
        print("=" * 80)
        print(f"\nSuccessfully graded {successful}/{len(students)} students")
        print(f"Results saved to: {output_path}")
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

