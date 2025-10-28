import os
import re
import math
import json
import pandas as pd
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from openai import AzureOpenAI
from dotenv import load_dotenv 

load_dotenv()

# ===========================
# CONFIGURATION
# ===========================
XLSX_PATH = "CS 549 Autograder Quiz 1.xlsx"

# Rubric sheet and columns
RUBRIC_SHEET = "Quiz 1 Rubric"
RUBRIC_ID_COL = "ID"
RUBRIC_RULE_COL = "Basic-Rule (Criterion)"
RUBRIC_POINTS_COL = "SS (Points)"
RUBRIC_LA_COL = "Levels of Achievement (la)"  # "[desc == ls][desc == ls]..."

# Answers sheet and columns
ANSWERS_SHEET = "Quiz 1 Answers"
STUDENT_ID_COL = "Student Number"
STUDENT_ANSWER_COL = "Student Answer"

# Scoring + LLM behavior
ROUNDING_MODE = "round"   # 'round' | 'floor' | 'ceil'
TEMPERATURE = 0.2         # keep low for consistency
LENIENT_PERSONA = True    # slightly encourages partial credit

# Azure OpenAI client (use env vars if available)
AZURE_OPENAI_ENDPOINT=os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY=os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_DEPLOYMENT=os.getenv("AZURE_OPENAI_DEPLOYMENT")
AZURE_OPENAI_API_VERSION=os.getenv("AZURE_OPENAI_API_VERSION")


# ===========================
# RUBRIC PARSING
# ===========================
FULLWIDTH_OPEN = "［"
FULLWIDTH_CLOSE = "］"
BRACKETED_ITEM = re.compile(r"\[(.*?)\]", re.DOTALL)

def _to_float01(token: str) -> float:
    s = str(token).strip()
    if s.endswith("%"):
        return float(s[:-1].strip()) / 100.0
    return float(s)

def parse_la_cell(cell: Any) -> List[Dict[str, Any]]:
    """
    Parse a cell containing level descriptors in compact form:
      [Excellent, clear linkage to EHR == 1.0][Reasonable linkage == 0.5][Vague/incorrect == 0.0]
    Also supports full-width brackets and a fallback format:
      Excellent == 1.0 | Partial == 0.5 | Poor == 0
    Returns a list of { "description": str, "ls": float }.
    """
    if cell is None or (isinstance(cell, float) and math.isnan(cell)):
        return []

    s = str(cell).strip().replace(FULLWIDTH_OPEN, "[").replace(FULLWIDTH_CLOSE, "]")
    items: List[Dict[str, Any]] = []

    # Preferred: bracketed blocks
    blocks = BRACKETED_ITEM.findall(s)
    if blocks:
        for inner in blocks:
            parts = inner.split("==", 1)
            if len(parts) == 2:
                desc, ls = parts[0].strip(), parts[1].strip()
            else:
                desc, ls = inner.strip(), "1.0"
            try:
                items.append({"description": desc, "ls": _to_float01(ls)})
            except ValueError:
                items.append({"description": desc, "ls": 0.0})
        return items

    # Fallback: split on '|' or ';', each piece must contain '=='
    for part in re.split(r"[|;]\s*", s):
        if "==" in part:
            desc, ls = part.split("==", 1)
            desc, ls = desc.strip(), ls.strip()
            try:
                items.append({"description": desc, "ls": _to_float01(ls)})
            except ValueError:
                items.append({"description": desc, "ls": 0.0})

    return items

@dataclass
class Criterion:
    id: Any
    basic_rule: str
    max_points: float
    levels: List[Dict[str, Any]]  # list of {"description": str, "ls": float}

@dataclass
class Rubric:
    criteria: List[Criterion]
    total_points: float

def load_rubric(xlsx_path: str) -> Rubric:
    df = pd.read_excel(xlsx_path, sheet_name=RUBRIC_SHEET, engine="openpyxl")
    # ensure numeric points
    df[RUBRIC_POINTS_COL] = pd.to_numeric(df[RUBRIC_POINTS_COL], errors="coerce").fillna(0)

    criteria: List[Criterion] = []
    for _, row in df.iterrows():
        levels = parse_la_cell(row[RUBRIC_LA_COL])
        if not levels:
            # default to a single "excellent" level if none provided
            levels = [{"description": "(no explicit level provided)", "ls": 1.0}]
        crit = Criterion(
            id=row[RUBRIC_ID_COL],
            basic_rule=str(row[RUBRIC_RULE_COL]).strip(),
            max_points=float(row[RUBRIC_POINTS_COL]),
            levels=levels
        )
        criteria.append(crit)

    total_points = float(sum(c.max_points for c in criteria))
    return Rubric(criteria=criteria, total_points=total_points)


# ===========================
# AZURE OPENAI CLIENT + PROMPTS
# ===========================
client = AzureOpenAI(
    api_key=AZURE_OPENAI_API_KEY,
    api_version=AZURE_OPENAI_API_VERSION,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
)

SYSTEM_ROLE = f"""
You are a university professor grading ONE rubric criterion for ONE student answer.

Persona:
- Lenient and encouraging; award partial credit whenever reasonable.
- Grade this single criterion independently (ignore other criteria).
- Return STRICT JSON only.

RATAS targets:
- SP ∈ [0,1]: coverage of the Basic-Rule.
- LQAP ∈ [0,1]: quality alignment within the chosen Level description.
- la_index: 0-based index of the best-matching Level.

Scoring:
- raw = SP * LQAP * ls * max_points
- points = integer via {ROUNDING_MODE} (cap to [0, max_points])

Return only:
{{
  "sp": number,
  "lqap": number,
  "la_index": integer,
  "points": integer,
  "max_points": integer,
  "rationale": string
}}
"""

def build_criterion_prompt(criterion: Criterion, student_answer: str) -> str:
    persona_hint = ("Reward effort and partial understanding. If the answer shows a kernel of understanding, "
                    "prefer higher SP/LQAP values.") if LENIENT_PERSONA else ""
    levels_block = "\n".join([f"- [{i}] ls={lvl['ls']}: {lvl['description']}" for i, lvl in enumerate(criterion.levels)])
    if not levels_block:
        levels_block = "- [0] ls=1.0: (no explicit level provided)"

    return f"""
        {persona_hint}

        BASIC-RULE (Criterion):
        {criterion.basic_rule}

        MAX POINTS:
        {criterion.max_points}

        LEVELS:
        {levels_block}

        STUDENT ANSWER:
        {student_answer}

        Return JSON only.
        """

def ask_llm_for_criterion(criterion: Criterion, student_answer: str) -> Dict[str, Any]:
    user_prompt = build_criterion_prompt(criterion, student_answer)

    resp = client.chat.completions.create(
        model=AZURE_OPENAI_DEPLOYMENT,
        temperature=TEMPERATURE,
        messages=[
            {"role": "system", "content": SYSTEM_ROLE},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
    )
    content = resp.choices[0].message.content

    # try JSON
    try:
        data = json.loads(content)
    except Exception:
        # best-effort JSON extraction
        m = re.search(r"\{.*\}", content, flags=re.DOTALL)
        if not m:
            # fallback zero
            return {
                "sp": 0.0,
                "lqap": 0.0,
                "la_index": 0,
                "points": 0,
                "max_points": int(round(criterion.max_points)),
                "rationale": "Failed to parse model JSON; assigning 0."
            }
        data = json.loads(m.group(0))

    # sanitize values and recompute integer points from formula
    sp = float(max(0.0, min(1.0, data.get("sp", 0.0))))
    lqap = float(max(0.0, min(1.0, data.get("lqap", 0.0))))
    la_index = int(data.get("la_index", 0))
    la_index = max(0, min(la_index, max(0, len(criterion.levels) - 1)))
    ls = float(criterion.levels[la_index]["ls"] if criterion.levels else 1.0)

    raw = sp * lqap * ls * float(criterion.max_points)
    if ROUNDING_MODE == "floor":
        points = math.floor(raw)
    elif ROUNDING_MODE == "ceil":
        points = math.ceil(raw)
    else:
        points = int(round(raw))
    points = max(0, min(points, int(round(criterion.max_points))))

    return {
        "sp": sp,
        "lqap": lqap,
        "la_index": la_index,
        "points": points,
        "max_points": int(round(criterion.max_points)),
        "rationale": str(data.get("rationale", "")).strip()[:500],
    }


# ===========================
# MAIN GRADING PIPELINE
# ===========================
def grade_all_students() -> pd.DataFrame:
    rubric = load_rubric(XLSX_PATH)
    ans_df = pd.read_excel(XLSX_PATH, sheet_name=ANSWERS_SHEET, engine="openpyxl")

    # Ensure necessary columns exist
    missing = [c for c in [STUDENT_ID_COL, STUDENT_ANSWER_COL] if c not in ans_df.columns]
    if missing:
        raise ValueError(f"Missing columns in answers sheet: {missing}. Found: {list(ans_df.columns)}")

    results_rows = []

    for _, row in ans_df.iterrows():
        student_id = str(row.get(STUDENT_ID_COL, "")).strip()
        answer = str(row.get(STUDENT_ANSWER_COL, "")).strip()

        total_points = 0
        max_points = 0

        # Grade each rubric row independently
        for crit in rubric.criteria:
            r = ask_llm_for_criterion(crit, answer)
            
            # Print detailed model outputs
            # print(f"\n  Criterion {crit.id}:")
            # print(f"    SP: {r['sp']:.3f}")
            # print(f"    LQAP: {r['lqap']:.3f}")
            # print(f"    la_index: {r['la_index']}")
            # print(f"    Rationale: {r['rationale']}")
            # print(f"    Points: {r['points']}/{r['max_points']}")
            
            total_points += r["points"]
            max_points += r["max_points"]

        results_rows.append({
            "Student Number": student_id,
            "Score": total_points,
            "Max Score": max_points
        })

        print(f"{student_id}: {total_points}/{max_points}")

    out_df = pd.DataFrame(results_rows)
    out_csv = "quiz1_scores.csv"
    out_df.to_csv(out_csv, index=False)
    print(f"\nSaved results to {out_csv}")
    return out_df


if __name__ == "__main__":
    # Basic env guardrails
    if "YOUR-RESOURCE" in AZURE_OPENAI_ENDPOINT or AZURE_OPENAI_API_KEY == "YOUR_API_KEY":
        print("WARNING: Set your Azure OpenAI env vars before running:")
        print("  AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_API_VERSION, AZURE_OPENAI_DEPLOYMENT")
    grade_all_students()
