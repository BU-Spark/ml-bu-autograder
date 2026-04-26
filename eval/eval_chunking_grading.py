"""
Evaluate chunking strategies for RAG grading: compare AI grades to professor grades.
Uses HTML lectures as context, Quiz 1 Excel for student answers + human scores.

API keys (env vars): OPENAI_API_KEY
"""

from pathlib import Path
import argparse
import json
import os
import re
import sys
import warnings
import requests

# ---------------------------------------------------------------------------
# Few-shot calibration examples: real professor-graded student answers.
#
# Data provenance and leakage status:
#   quiz_1  — sourced from FALL 2024 semester (24fallmetcs581_m1 Quiz 1.xlsx,
#             question 13). Evaluated on FALL 2025 data → zero overlap possible.
#             Max score differs (14 vs 16) but conceptual depth anchoring holds.
#   quiz_2  — sourced from FALL 2025 (same file as eval). Leakage guard in
#             run_eval() removes any overlapping rows before grading. No older
#             semester has the same RCM question.
#   quiz_3  — sourced from FALL 2025 (same file as eval). Leakage guard applied.
#             No older semester has the same PI requirements question.
#   quiz_4  — sourced from FALL 2025 (same file as eval). Leakage guard applied.
#             No older semester quiz data found for this question.
# ---------------------------------------------------------------------------
FEW_SHOT_EXAMPLES: dict[str, dict] = {
    "quiz_1": {
        # SOURCE: fall 2024 (24fallmetcs581_m1 Quiz 1.xlsx, question 13)
        # LEAKAGE RISK: none — different semester from eval data (fall 2025)
        "max_points": 14,  # fall 2024 scale; rubric anchoring is conceptual not absolute
        "question": "Why do we need to do Business Process Re-engineering as a part of implementing an EHR?",
        "bad": {
            "score": 12,
            "answer": (
                "since BPR shows and indicates the currents data, it shows any errors, duplication or "
                "discrepancies. This will help starting the EHR with clean and more efficient system and "
                "reduce the errors. In addition, defining the process step by step and all the details "
                "involved make it easier and faster to implement the EHR. while conducting BPR, areas of "
                "improvment can easily be defined and solved before implementing EHR. Also, areas that can "
                "improve patients communication and satisfaction can be determined and easily implemented "
                "while establising the system. any extra steps can be defineds and removed to make health "
                "care delivery faster. lastly, to have BPR will save effort, time and cost while "
                "implementing EHR since it will make it easier to identify all cost that can be saved, "
                "steps that can be removed and time that can be reducesd"
            ),
        },
        "neutral": {
            "score": 13,
            "answer": (
                "One benefit of an Enterprise Architecture (EA) is it manages complexity by organizing the "
                "business' current investments and supports maximizing its returns. This is a benefit because "
                "it makes use of its existing business and IT resources, which allows for reduced risk for "
                "future investment. Mapping out the EA assists in making decisions regarding IT solutions and "
                "infrastructure, and whether to buy, make, or out-source them."
            ),
        },
        "good": {
            "score": 14,
            "answer": (
                "Performing a business re-engineering process and implementing EHR can reap many benefits for "
                "the organization and the patients. Re-engineering is streamlining a current state to improve "
                "the ease and efficiency. In order to provide the best care and service to patients, "
                "organizations should make the business of healthcare as clear and concise as possible. "
                "Implementing structured EHR models can save time and money, improve clinical outcomes, "
                "foster trust and confidence in the system for patients and staff, and ensure transparency "
                "throughout the healthcare organization. Outlining the steps needed to complete EHR processes "
                "and involving the key players is essential to building a strong and enduring system. You need "
                "to identify how things are being done currently, both in reality and perception, and then "
                "develop clear, measurable, and accountable steps in an organized manner to incorporate into "
                "the EHR."
            ),
        },
    },
    "quiz_2": {
        "max_points": 15,
        "question": "Describe how one function of HIS revenue cycle management functionality increases a provider's revenue.",
        "bad": {
            "score": 6,
            "answer": (
                "Based on common hospital financial performance, many providers face high levels of bad debt. "
                "HIS revenue cycle management helps reduce this by quickly analyzing and visualizing financial "
                "data that support better decision-making. This improves cash flow and overall revenue efficiency."
            ),
        },
        "neutral": {
            "score": 10,
            "answer": (
                "One function of HIS revenue cycle management is automated claim submission to insurance "
                "companies. This process reduces errors and speeds up claim handling. Providers receive "
                "reimbursements faster and face fewer denials, which directly increases revenue. This system "
                "also lowers administrative costs and allows staff to focus more on patient care."
            ),
        },
        "good": {
            "score": 12,
            "answer": (
                "Eligibility and benefits verification is an important part of HIS revenue cycle management. "
                "The method cuts down on claim denials and makes sure providers are paid on time for eligible "
                "treatments by checking a patient's insurance coverage before services are given. This boosts "
                "revenues by reducing the amount of money lost from claims that are denied and speeding up "
                "cash flow."
            ),
        },
    },
    "quiz_3": {
        "max_points": 16,
        "question": "What is one goal of the federal government Promoting Interoperability (PI) requirements and why is it important?",
        "bad": {
            "score": 10,
            "answer": (
                "In my view, the essence of the PI program is to accelerate the improvement of overall "
                "healthcare quality through the effective use of technology. Its main goal is to maximize "
                "the potential of existing digital tools to benefit public health and enhance the efficiency "
                "of care delivery. However, misuse or failure of technology can lead to serious consequences, "
                "such as patient data breaches. Therefore, strong federal regulation and oversight are "
                "essential to ensure that innovation in health IT truly improves care while protecting "
                "patient privacy and safety."
            ),
        },
        "neutral": {
            "score": 14,
            "answer": (
                "The federal Promoting Interoperability (PI) requirements are all about making it easier for "
                "different healthcare providers and systems to share health information smoothly. This matters "
                "because when patients see multiple doctors or visit different clinics, their care team needs "
                "a full, accurate picture of their medical history to make smart treatment choices. Without "
                "this, critical details like medications, allergies, lab results, or past diagnoses might not "
                "be available, which can lead to serious mistakes, unnecessary tests, or disjointed care. By "
                "ensuring EHR systems use standard formats and protocols to share data, PI helps get the right "
                "info to the right doctor at the right time. This boosts patient safety, cuts down on costs, "
                "and improves the quality of care across the board."
            ),
        },
        "good": {
            "score": 16,
            "answer": (
                "Engaging patients and families through a patient portal is one of the Promoting "
                "Interoperability requirements. By offering a patient portal like MyChart to patients, health "
                "systems can directly engage patients in their care by giving them immediate access to lab "
                "results, procedure results, progress notes, After Visit Summaries, and active medication "
                "prescriptions. Patient portals also allow patients to directly communicate with providers "
                "through secure messaging and offer direct scheduling workflows. Through direct engagement of "
                "patients and families in their care, improved outcomes are common as patients are more likely "
                "to follow through on treatment plans, medication regimens, frequent lab testing, and "
                "preventative care like annual physicals and mammograms."
            ),
        },
    },
    "quiz_4": {
        "max_points": 16,
        "question": (
            "Select one of the following two HIS / EHR Technical Infrastructure Requirement areas and "
            "describe why it is important for an HIS / EHR."
        ),
        "bad": {
            "score": 6,
            "answer": (
                "Data security and privacy are critical components of a Health Information System (HIS) or "
                "Electronic Health Record (EHR) because they guard against misuse, breaches, and unauthorized "
                "access to sensitive patient data. The confidentiality and integrity of health data are "
                "preserved by making sure that robust encryption, access controls, and authentication "
                "procedures are in place. Organizations are also protected from fines and penalties by "
                "adhering to regulations such as HIPAA. Furthermore, preserving patient trust is crucial "
                "because when patients are certain that their data is safe, they are more inclined to divulge "
                "accurate information. All things considered, robust data security and privacy procedures are "
                "essential to the dependability and effectiveness of any HIS or EHR system."
            ),
        },
        "neutral": {
            "score": 12,
            "answer": (
                "In distributed EHR infrastructure, the system components and data are shared across multiple "
                "healthcare facilities like hospitals, laboratories, and clinics. This distributed "
                "infrastructure improves availability, redundancy, and fault tolerance, thus helping in smooth "
                "functioning of healthcare operations by minimizing hardware failures. This also facilitates "
                "interoperability and thus improves patient care. Therefore, distributed HIS/EHR ensures "
                "availability of the right information at the right time, reducing delays and improving "
                "overall patient care."
            ),
        },
        "good": {
            "score": 16,
            "answer": (
                "Data Management is one of the most important parts of any HIS or EHR system because "
                "healthcare providers deal with so much patient information every day. Having a solid data "
                "management setup helps make sure records are accurate, organized, and easy to find when "
                "needed. It also helps doctors and staff make better decisions since they can rely on complete "
                "and up-to-date data. Without good data management, mistakes in patient care, billing, or "
                "reporting can happen easily. Overall, it keeps the system running smoothly, supports patient "
                "safety, and helps meet privacy and security requirements."
            ),
        },
    },
    # ------------------------------------------------------------------
    # Assignments 1–4: description-based calibration (submissions are
    # PDFs/PPTXs/XLSXs, not short text). Each tier describes what a
    # real professor-graded submission at that score level looked like,
    # drawn from the 24fall rubric feedback and Spring 2026 examples.
    # ------------------------------------------------------------------
    "assignment_1": {
        "max_points": 100,
        "question": (
            "Workflow & BPR Assignment: Create a redesigned workflow diagram for Virginia Women's Center "
            "(VWC) EHR implementation using swimlanes, decision points, and branching. Include a table "
            "mapping data, people, EHR capabilities, and benefits for each step. Identify critical "
            "deployment issues."
        ),
        "bad": {
            "score": 75,
            "answer": (
                "[LOW EXAMPLE — described from professor feedback, score 75/100]\n"
                "The submission lacked the required workflow diagram showing decision points, branching, "
                "or repetitive steps. It did not include a specific section detailing the critical issues "
                "for deployment, though the benefits section implied some redesign consideration. "
                "The provided table mapped some required components (data, people, EHR capabilities, "
                "benefits) for the general scheduling process, but key required elements were missing. "
                "The material was professionally presented but lacked the specific deliverables of the "
                "assignment."
            ),
        },
        "neutral": {
            "score": 89,
            "answer": (
                "[NEUTRAL EXAMPLE — described from professor feedback, score 89/100]\n"
                "The workflow diagram showed a good BPR model with swimlanes but was missing some "
                "connections to the patient. The critical deployment issues covered some aspects but "
                "lacked sufficient depth. The table mapped data, people, EHR functionality, and "
                "benefits adequately but some steps were under-specified. Overall the workflow "
                "demonstrated understanding of BPR redesign principles but needed more decision "
                "points and more complete coverage of EHR capabilities at each step."
            ),
        },
        "good": {
            "score": 100,
            "answer": (
                "[HIGH EXAMPLE — described from professor feedback, score 100/100]\n"
                "The workflow diagram was highly detailed, included all required BPR elements, and was "
                "logically structured with comprehensive swimlanes, clear decision points, and a "
                "full closed-loop process. The analysis identified a comprehensive set of critical "
                "deployment issues including interoperability, exception handling, and user adoption. "
                "Key information, people, and EHR capabilities were thoroughly and accurately mapped "
                "to each step of the redesigned workflow. The assignment was well-presented, clear, "
                "and demonstrated excellent organization and quality throughout."
            ),
        },
    },
    "assignment_2": {
        "max_points": 100,
        "question": (
            "EHR Functional Requirements Worksheet: Identify key EHR functions for Virginia Women's "
            "Center (VWC), explain why each is important, and describe how each relates to VWC's "
            "operational needs, government requirements (MIPS/QPP/PI), and the HL7 EHR functional model."
        ),
        "bad": {
            "score": 70,
            "answer": (
                "[LOW EXAMPLE — described from professor feedback, score 70/100]\n"
                "The student identified EHR functions but did not select specific examples from the "
                "case study or explain how the functions directly contribute to improving healthcare "
                "outcomes, workflow efficiency, or patient experience. CPOE — the most important "
                "functionality highlighted in the VWC case study — was missing. The importance "
                "column was used incorrectly (not a 1-4 rating scale as instructed). Relationships "
                "between the functions and government requirements (MIPS/QPP/PI) were not provided "
                "as required. The worksheet showed a surface-level understanding without connecting "
                "functions to VWC's specific context."
            ),
        },
        "neutral": {
            "score": 88,
            "answer": (
                "[NEUTRAL EXAMPLE — described from professor feedback, score 88/100]\n"
                "The student identified relevant EHR functions and provided justifications, but the "
                "functions could have been elaborated with specific details from the VWC case study. "
                "For example, the student noted interoperability and scheduling but did not cite "
                "that CPOE is listed as the 'most important functionality in use' at VWC. Connections "
                "to government requirements were stated generically (e.g., 'meets PI/MIPS goals') "
                "without elaborating how specific functions align with specific program requirements. "
                "The worksheet showed good understanding overall but lacked the depth needed for full "
                "credit."
            ),
        },
        "good": {
            "score": 100,
            "answer": (
                "[HIGH EXAMPLE — described from professor feedback, score 100/100]\n"
                "The student identified highly relevant EHR functions with a great level of detail for "
                "each, selecting functions that directly meet VWC's requirements and backing selections "
                "with specific references to the case study. References to the VWC case study "
                "effectively emphasized the importance of each function in relation to VWC's specific "
                "needs (e.g., CPOE as most important, reduction from 3 FTEs to 1.25 FTEs for charge "
                "entry). Government requirement connections (MIPS/QPP/PI) were specific and well "
                "explained. The HL7 EHR functional model was appropriately referenced. Justifications "
                "consistently connected functions to VWC's operational needs."
            ),
        },
    },
    "assignment_3": {
        "max_points": 100,
        "question": (
            "HIS/EHR Business Functional Requirements: Design and document the technical infrastructure "
            "for VWC's EHR system, including architectural design choices (cloud/on-premises/hybrid), "
            "infrastructure components (servers, storage, networking, devices), security/data management, "
            "and service level requirements."
        ),
        "bad": {
            "score": 84,
            "answer": (
                "[LOW EXAMPLE — described from professor feedback, score 84/100]\n"
                "The submission identified an architectural design but did not explain the rationale "
                "for that choice or discuss benefits of virtualization (e.g., reduced hardware costs "
                "via multiple virtual desktops/servers). End-user devices (laptops, PCs, mobile devices) "
                "were not represented in the diagram. Dedicated server types (application, database, "
                "PACS, SAN, LDAP, Citrix) were not fully accounted for. The security section only "
                "included firewalls without explaining their role — data management, firewall placement, "
                "and network topology were underspecified. Service level requirements were present but "
                "lacked depth."
            ),
        },
        "neutral": {
            "score": 90,
            "answer": (
                "[NEUTRAL EXAMPLE — described from professor feedback, score 90/100]\n"
                "The submission described a hybrid infrastructure combining centralized cloud resources "
                "with on-premises devices at VWC Headquarters, but the rationale for this choice needed "
                "more elaboration (e.g., data redundancy, scalability, secure local access). Router, "
                "switches, and firewall placement between each site and the cloud was not clearly shown. "
                "Data management was mentioned but not detailed — how data is collected, stored, and "
                "processed across sites was underspecified. Performance requirements were touched upon "
                "but specific methods (load balancing, failover) were not described."
            ),
        },
        "good": {
            "score": 98,
            "answer": (
                "[HIGH EXAMPLE — described from professor feedback, score 98/100]\n"
                "The submission showed comprehensive understanding of infrastructure architectural "
                "design choices with clear rationale. All major infrastructure components (user devices, "
                "application servers, database servers, PACS, SAN, LDAP, Citrix) were included and "
                "correctly located (on-premises vs. cloud). Security was addressed with firewalls, "
                "access controls, and data encryption. Service level requirements were well-specified. "
                "Performance methods were described (e.g., load balancing to distribute network traffic, "
                "preventing resource bottlenecks). Third-party reporting and EHR help desk/IT support "
                "were considered. Only minor improvements suggested (elaborating on virtualization "
                "benefits)."
            ),
        },
    },
    "assignment_4": {
        "max_points": 100,
        "question": (
            "Technical Infrastructure Diagram & Interoperability Memo: Create a technical infrastructure "
            "diagram for VWC's EHR deployment and write a memo covering interoperability requirements "
            "(QPP/MIPS/PI), technical interoperability standards (HL7 v2, HL7 CDA, HL7 FHIR, HIE "
            "architectures), key success factors, and a critique of GenAI-generated responses."
        ),
        "bad": {
            "score": 83,
            "answer": (
                "[LOW EXAMPLE — described from professor feedback, score 83/100]\n"
                "The memo was missing several HIE functionalities, key success factors (technical, "
                "policy, organizational, and financial), and business requirements. The interoperability "
                "requirements section did not fully cover QPP/MIPS/PI goals or explain the different "
                "HIE architectures (centralized, federated, hybrid). The GenAI critique section "
                "focused on lack of depth but did not address other common GenAI concerns such as "
                "redundancy, hallucinations, or the human-AI complementarity angle. Technical "
                "standards (HL7 v2, CDA, FHIR) were referenced but usage at VWC was not clearly "
                "explained."
            ),
        },
        "neutral": {
            "score": 90,
            "answer": (
                "[NEUTRAL EXAMPLE — described from professor feedback, score 90/100]\n"
                "The memo covered interoperability requirements and most HIE functionalities, but "
                "some key success factors and business requirements were missing. Technical standards "
                "(HL7 v2, CDA, FHIR) were discussed with some explanation of how they would be used "
                "at VWC. The GenAI critique described the prompting process and noted key issues with "
                "GenAI responses but did not explore the full range of concerns (beyond lack of depth). "
                "The memo demonstrated solid understanding of interoperability concepts and how VWC "
                "would benefit from HIE participation."
            ),
        },
        "good": {
            "score": 97,
            "answer": (
                "[HIGH EXAMPLE — described from professor feedback, score 97/100]\n"
                "The memo comprehensively covered HIS/EHR interoperability requirements (QPP/MIPS/PI), "
                "information exchange across all stakeholders (providers, patients, government, labs, "
                "pharmacies, HIEs), and technical standards (HL7 v2, CDA, FHIR, APIs). HIE architectures "
                "(centralized, federated, hybrid) were explained with rationale for VWC's choices. "
                "Key success factors across technical, policy, organizational, and financial dimensions "
                "were addressed. The GenAI critique was thorough and insightful — it highlighted both "
                "benefits and drawbacks of GenAI, addressed how humans and AI could complement each "
                "other, and investigated nuances between different AI systems for efficient, high-quality "
                "results."
            ),
        },
    },
}


def _infer_assignment_id(rubric_path: Path | None, excel_path: Path | None) -> str | None:
    """
    Infer the assignment ID (e.g. 'quiz_1') from the rubric or Excel path.
    Used to look up few-shot calibration examples automatically.
    """
    for path in [rubric_path, excel_path]:
        if path is None:
            continue
        s = str(path).lower()
        for key in FEW_SHOT_EXAMPLES:
            # match 'quiz_1', 'quiz1', 'quiz 1', 'quiz-1'
            norm = re.sub(r"[_\s-]", "", key)  # e.g. 'quiz1'
            if norm in re.sub(r"[_\s-]", "", s):
                return key
    return None


def build_few_shot_block(assignment_id: str | None) -> str:
    """
    Return a formatted few-shot calibration block for the given assignment.
    Returns an empty string if no examples are registered for the assignment.
    """
    if assignment_id is None or assignment_id not in FEW_SHOT_EXAMPLES:
        return ""
    ex = FEW_SHOT_EXAMPLES[assignment_id]
    max_pts = ex["max_points"]
    lines = [
        "CALIBRATION EXAMPLES (real professor-graded answers — use these to anchor your scoring):",
    ]
    for tier, label in [("bad", "LOW"), ("neutral", "NEUTRAL"), ("good", "HIGH")]:
        entry = ex[tier]
        lines.append(
            f"\n[{label} EXAMPLE — Professor Score: {entry['score']}/{max_pts}]\n{entry['answer']}"
        )
    return "\n".join(lines)


# Column names in Excel - exact or partial match (script also tries contains "answer"/"score")
EXCEL_ANSWER_COLS = [
    "Student Answer",
    "Answer",
    "Response",
    "student_answer",
    "answer",
    "Why do we need to do Business Process Re-engineering as a part of implementing an EHR?",  # Quiz 1 long header
]
EXCEL_PROF_COLS = [
    "Human Score",
    "Professor Score",
    "Instructor Score",
    "Human Grade",
    "Prof Score",
    "human_score",
    "Score",
    "Grade",
]

BASE_DIR = Path(__file__).parent.resolve()
DATA_DIR = BASE_DIR / "fall 2025 cs 581 quiz and assignment data"
LECTURES_DIR = BASE_DIR / "Spring 2026" / "Lectures [html versions]"
RUBRIC_PATH = DATA_DIR / "New Refined Rubrics" / "quiz_1" / "quiz_1.json"
EXCEL_PATH = DATA_DIR / "Quiz 1" / "CS 581 Quiz 1 AI vs Human Anonymized.xlsx"


def _infer_module_and_topic_from_path(path: Path) -> tuple[str | None, str | None]:
    """
    Heuristic inference of module and topic from a lecture path.
    Mirrors the logic in html_lecture_ingest so eval sees similar metadata.
    """
    parts = list(path.parts)
    module = None
    topic = None

    for p in parts:
        m = re.search(r"module[_\s-]*([0-9]+)", p, flags=re.IGNORECASE)
        if m:
            module = f"module{m.group(1)}"
            break

    if module:
        for i, p in enumerate(parts):
            m = re.search(r"module[_\s-]*([0-9]+)", p, flags=re.IGNORECASE)
            if m and i + 1 < len(parts) - 1:
                topic_seg = parts[i + 1]
                topic = re.sub(r"\s+", "_", Path(topic_seg).stem)
                break

    return module, topic


def _first_match(df, candidates, default=None):
    """Return first column name that exists in df (exact or startswith), or default."""
    for c in candidates:
        if c in df.columns:
            return c
        for col in df.columns:
            if col.strip().startswith(c.strip()) or (c.strip() and c.strip() in col):
                return col
    return default


def _first_match_contains(df, *keywords):
    """Return first column whose name contains any of the keywords (case-insensitive)."""
    for col in df.columns:
        lower = str(col).lower()
        if any(kw.lower() in lower for kw in keywords):
            return col
    return None


def load_eval_data(
    excel_path: Path,
    answer_col: str | None = None,
    prof_col: str | None = None,
    sheet_name: str | None = None,
):
    """Load student answers and professor grades from Excel."""
    import pandas as pd

    xl = pd.ExcelFile(excel_path)

    # If a specific sheet is requested (e.g. 'Student Submission'), only use that
    if sheet_name is not None:
        if sheet_name not in xl.sheet_names:
            raise ValueError(f"Sheet '{sheet_name}' not found. Available: {xl.sheet_names}")
        df = pd.read_excel(excel_path, sheet_name=sheet_name)
        answer_col = answer_col or _first_match(df, EXCEL_ANSWER_COLS) or _first_match_contains(
            df, "answer", "response", "why do we need"
        )
        prof_col = prof_col or _first_match(df, EXCEL_PROF_COLS) or _first_match_contains(
            df, "human", "score", "grade", "prof", "instructor"
        )
    else:
        df = None
        for sheet in xl.sheet_names:
            _df = pd.read_excel(excel_path, sheet_name=sheet)
            _answer = answer_col or _first_match(_df, EXCEL_ANSWER_COLS) or _first_match_contains(
                _df, "answer", "response", "why do we need"
            )
            _prof = prof_col or _first_match(_df, EXCEL_PROF_COLS) or _first_match_contains(
                _df, "human", "score", "grade", "prof", "instructor"
            )
            if _answer and _prof:
                df = _df
                answer_col = _answer
                prof_col = _prof
                break
        if df is None:
            df = pd.read_excel(excel_path, sheet_name=0)
            answer_col = answer_col or _first_match(df, EXCEL_ANSWER_COLS) or _first_match_contains(
                df, "answer", "response", "why do we need"
            )
            prof_col = prof_col or _first_match(df, EXCEL_PROF_COLS) or _first_match_contains(
                df, "human", "score", "grade", "prof", "instructor"
            )

    if not answer_col:
        raise ValueError(
            f"Could not find answer column. Columns: {df.columns.tolist()}. "
            "Set answer_col explicitly."
        )
    if not prof_col:
        raise ValueError(
            f"Could not find professor score column. Sheets: {xl.sheet_names}. Columns on first sheet: {df.columns.tolist()}. "
            "Use a sheet that has both student answers and human scores, or set prof_col explicitly."
        )

    rows = []
    for _, r in df.iterrows():
        ans = r.get(answer_col)
        prof = r.get(prof_col)
        if pd.isna(ans) or str(ans).strip() == "":
            continue
        prof_score = None
        if not pd.isna(prof):
            # Scores may appear as "12" or "12 / 14" etc. Extract the first number.
            m = re.search(r"[\d.]+", str(prof))
            if m:
                try:
                    prof_score = float(m.group())
                except (TypeError, ValueError):
                    prof_score = None
        # Guard against clearly invalid scores (e.g. years like 2025)
        if prof_score is not None and prof_score > 100:
            prof_score = None
        if prof_score is None:
            continue
        rows.append({"answer": str(ans).strip(), "prof_score": prof_score})
    return rows


def load_rubric(path: Path) -> str:
    """Build grading rubric string from quiz JSON."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    parts = [data.get("overall_instructor_guidelines", "")]
    for sr in data.get("sub_rubrics", []):
        parts.append(sr.get("instructor_guideline", ""))
        for gc in sr.get("grading_criteria", []):
            parts.append(f"- {gc.get('criteria_id', '')}: {gc.get('criteria', '')}")
    return "\n\n".join(p for p in parts if p)


def load_rubric_from_excel(excel_path: Path, sheet_name: str = "Question Details", question_label: str | None = None) -> str:
    """
    Build a rubric string from an Excel sheet (e.g. 24fallmetcs581_m1 Quiz 1.xlsx, 'Question Details' tab).
    If question_label is provided (e.g. 'Question 13'), we try to extract only rows mentioning that;
    otherwise we join all non-empty rows.
    """
    import pandas as pd

    try:
        df = pd.read_excel(excel_path, sheet_name=sheet_name)
    except Exception as exc:
        raise ValueError(f"Failed to read rubric sheet '{sheet_name}' from {excel_path}: {exc}")

    df = df.fillna("")

    def row_to_text(row) -> str:
        cells = [str(v).strip() for v in row.values if str(v).strip()]
        return " ".join(cells)

    parts: list[str] = []

    if question_label:
        mask = df.apply(
            lambda r: any(str(v).strip().startswith(question_label) or question_label in str(v) for v in r.values),
            axis=1,
        )
        sub = df[mask]
        for _, r in sub.iterrows():
            txt = row_to_text(r)
            if txt:
                parts.append(txt)

    if not parts:
        for _, r in df.iterrows():
            txt = row_to_text(r)
            if txt:
                parts.append(txt)

    return "\n\n".join(parts)


def build_chunks_from_lectures(root_dir: Path, strategy: str) -> list[dict]:
    """Build list of {text, metadata} chunks using given strategy."""
    from html_lecture_ingest import iter_lecture_html, extract_text_from_html
    from chunking_strategies import chunk_by_semantic, chunk_by_fixed_tokens, chunk_hybrid

    root_dir = Path(root_dir).resolve()
    # If default root has no lectures, try Spring 2026 explicitly
    candidates = [root_dir]
    if (root_dir / "Spring 2026").exists():
        candidates.append(root_dir / "Spring 2026")

    chunks = []
    for _root in candidates:
        for html_path in iter_lecture_html(str(_root)):
            try:
                text = extract_text_from_html(html_path)
            except Exception:
                continue
            if not text.strip():
                continue

            # Project-wide, we standardize on hybrid chunking.
            texts = chunk_hybrid(text, max_chars=4000, sub_chunk=800)

            module, topic = _infer_module_and_topic_from_path(Path(html_path))

            for i, t in enumerate(texts):
                chunks.append(
                    {
                        "text": t,
                        "metadata": {
                            "source": Path(html_path).name,
                            "strategy": strategy,
                            "module": module,
                            "topic": topic,
                            "abs_path": str(Path(html_path).resolve()),
                        },
                    }
                )
        if chunks:
            break
    return chunks


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """No-op: TF-IDF retrieval builds its index at query time; nothing to pre-compute."""
    return chunks


def retrieve(chunks: list[dict], query: str, k: int = 5) -> list[str]:
    """Retrieve top-k chunk texts using TF-IDF cosine similarity (no API required)."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np

    texts = [c["text"] for c in chunks]
    corpus = texts + [query]
    vec = TfidfVectorizer(stop_words="english")
    tfidf = vec.fit_transform(corpus)
    scores = cosine_similarity(tfidf[-1], tfidf[:-1]).flatten()
    top_k = np.argsort(scores)[::-1][:k]
    return [texts[i] for i in top_k]


# LLM configs: (provider, model_id, env_var)

LLM_CONFIGS = {
    "openai": ("openai", "gpt-4o-mini", "OPENAI_API_KEY"),
    "claude": ("anthropic", "claude-sonnet-4-6", "ANTHROPIC_API_KEY"),   # Claude Sonnet 4.6
    "gemini": ("google", "gemini-3.1-pro-preview", "GOOGLE_API_KEY"),    # Gemini 3 Pro
}


def grade_with_llm(
    rubric: str,
    context: str,
    student_answer: str,
    provider: str = "openai",
    model_id: str | None = None,
    few_shot_block: str = "",
) -> float | None:
    """Call LLM to grade; return numeric score or None on failure."""
    cfg = LLM_CONFIGS.get(provider)
    if not cfg:
        raise ValueError(f"Unknown provider: {provider}. Use one of: {list(LLM_CONFIGS)}")
    prov, default_model, env_var = cfg
    model_id = model_id or default_model

    api_key = os.environ.get(env_var) or (os.environ.get("GEMINI_API_KEY") if provider == "gemini" else None)
    if not api_key:
        return None

    calibration_section = (
        f"\n{few_shot_block}\n" if few_shot_block else ""
    )

    prompt = f"""You are grading a short-answer quiz question. Use ONLY the rubric and retrieved context below.

RUBRIC:
{rubric}
{calibration_section}
RETRIEVED LECTURE CONTEXT (for reference):
{context[:6000]}

STUDENT ANSWER:
{student_answer}

Respond with ONLY a single number (the score, e.g. 12 or 8.5). No explanation.
Award partial credit when appropriate: do not give 0 unless the answer is empty
or clearly off-topic relative to the rubric and context. Use the calibration
examples above to anchor your scoring to the professor's grading scale."""

    try:
        if prov == "openai":
            from openai import OpenAI
            client = OpenAI()
            resp = client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )
            content = resp.choices[0].message.content.strip()
        elif prov == "anthropic":
            # Call Anthropic Claude API directly via HTTP to avoid SDK version issues.
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }
            payload = {
                "model": model_id,
                "max_tokens": 64,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
            }
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                data=json.dumps(payload),
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()
            # New Claude Messages API: content is a list of blocks; concatenate text blocks.
            blocks = data.get("content", [])
            content_parts = [
                b.get("text", "") for b in blocks if isinstance(b, dict) and b.get("type") == "text"
            ]
            content = "".join(content_parts).strip()
        elif prov == "google":
            with warnings.catch_warnings(action="ignore", category=FutureWarning):
                import google.generativeai as genai
            genai.configure(api_key=os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY"))
            model = genai.GenerativeModel(model_id)
            resp = model.generate_content(prompt, generation_config={"temperature": 0})
            content = resp.text.strip() if resp.text else ""
        else:
            return None

        m = re.search(r"[\d.]+", content)
        return float(m.group()) if m else None
    except Exception as e:
        # Print first failure per provider so user sees API/key/model errors
        if not hasattr(grade_with_llm, "_logged"):
            grade_with_llm._logged = set()
        if provider not in grade_with_llm._logged:
            grade_with_llm._logged.add(provider)
            print(f"    [{provider}] error: {e}", flush=True)
        return None


def run_eval(
    excel_path: Path = EXCEL_PATH,
    rubric_path: Path = RUBRIC_PATH,
    lectures_root: Path = BASE_DIR,
    strategies: list[str] | None = None,
    models: list[str] | None = None,
    openai_model: str | None = None,
    max_eval: int = 15,
    k_retrieve: int = 5,
    out_path: Path | None = None,
    rubric_text: str | None = None,
    sheet_name: str | None = None,
    answer_col: str | None = None,
    prof_col: str | None = None,
    filter_module: str | None = None,
    assignment_id: str | None = None,
):
    """Run evaluation: load data, build indexes per strategy, grade with each LLM, compute MAE.

    NOTE: Project-wide we standardize on hybrid chunking only.
    Retrieval is tailored per student answer, and can optionally be restricted
    to a specific module via metadata (filter_module), e.g. 'module1'.
    """
    strategies = ["hybrid"]
    models = models or ["openai"]
    openai_model = openai_model or LLM_CONFIGS["openai"][1]

    def has_key(m):
        env_var = LLM_CONFIGS.get(m, ("", "", ""))[2]
        if m == "gemini":
            return bool(os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY"))
        return bool(os.environ.get(env_var))

    available = [m for m in models if has_key(m)]
    if not available:
        print("No LLM API keys found. Set OPENAI_API_KEY, ANTHROPIC_API_KEY, and/or GOOGLE_API_KEY.")
        return

    # Require provider packages to be importable (e.g. anthropic for Claude)
    def can_import_provider(m):
        if m == "openai":
            try:
                import openai
                return True
            except ImportError:
                return False
        if m == "claude":
            try:
                import anthropic
                return True
            except ImportError:
                return False
        if m == "gemini":
            try:
                import google.generativeai
                return True
            except ImportError:
                return False
        return True

    python_exe = sys.executable
    skipped = []
    for m in list(available):
        if not can_import_provider(m):
            available.remove(m)
            if m == "claude":
                skipped.append(f"{m} (run: {python_exe!r} -m pip install anthropic)")
            elif m == "gemini":
                skipped.append(f"{m} (run: {python_exe!r} -m pip install google-generativeai)")
            else:
                skipped.append(m)
    if skipped:
        print("Skipping (package not installed):", ", ".join(skipped))
    print(f"Using LLMs: {available}")

    if not excel_path.exists():
        print(f"Excel not found: {excel_path}")
        print("  Update EXCEL_PATH or pass --excel. Expected columns for answer: " + ", ".join(EXCEL_ANSWER_COLS[:3]))
        print("  For professor score: " + ", ".join(EXCEL_PROF_COLS[:3]))
        return

    print("Loading eval data...")
    eval_rows = load_eval_data(excel_path, answer_col=answer_col, prof_col=prof_col, sheet_name=sheet_name)

    # --- Data leakage guard ---
    # Remove any eval rows whose answer text matches a few-shot calibration example.
    # We compare the first 80 characters as a fingerprint (unique enough, avoids
    # whitespace/encoding edge cases). This ensures the model never sees the correct
    # score for an answer it was shown as a calibration example.
    _aid_for_leak_check = assignment_id or _infer_assignment_id(rubric_path, excel_path)
    _few_shot_fingerprints: set[str] = set()
    if _aid_for_leak_check and _aid_for_leak_check in FEW_SHOT_EXAMPLES:
        for tier in ("bad", "neutral", "good"):
            ex_ans = FEW_SHOT_EXAMPLES[_aid_for_leak_check].get(tier, {}).get("answer", "")
            if ex_ans:
                _few_shot_fingerprints.add(ex_ans.strip()[:80])

    if _few_shot_fingerprints:
        before = len(eval_rows)
        eval_rows = [
            r for r in eval_rows
            if r["answer"].strip()[:80] not in _few_shot_fingerprints
        ]
        removed = before - len(eval_rows)
        if removed:
            print(f"  Leakage guard: removed {removed} row(s) whose answer appears in few-shot examples.")

    eval_rows = eval_rows[:max_eval]
    print(f"  {len(eval_rows)} rows (clean, no overlap with few-shot examples)")

    print("Loading rubric...")
    rubric = rubric_text if rubric_text is not None else load_rubric(rubric_path)

    # Few-shot calibration: auto-detect assignment if not provided
    _aid = assignment_id or _infer_assignment_id(rubric_path, excel_path)
    few_shot_block = build_few_shot_block(_aid)
    if few_shot_block:
        print(f"  Few-shot calibration: {_aid} ({len(FEW_SHOT_EXAMPLES[_aid]['bad']['answer'].split()) + len(FEW_SHOT_EXAMPLES[_aid]['neutral']['answer'].split()) + len(FEW_SHOT_EXAMPLES[_aid]['good']['answer'].split())} total words across 3 examples)")
    else:
        print(f"  Few-shot calibration: none (assignment '{_aid}' not found in FEW_SHOT_EXAMPLES)")

    results = {}
    for strategy in strategies:
        print(f"\n--- Strategy: {strategy} ---")
        chunks = build_chunks_from_lectures(lectures_root, strategy)
        if not chunks:
            print(f"  No chunks for {strategy}; skipping.")
            if strategy == "semantic":
                p = Path(lectures_root).resolve()
                hint = p / "Lectures [html versions]" if (p / "Lectures [html versions]").exists() else p / "Spring 2026" / "Lectures [html versions]"
                print(f"  Hint: ensure .html or .htm lectures exist under: {hint}")
                print(f"  Or pass --lectures /path/to/parent/of/Lectures [html versions]")
            continue
        print(f"  {len(chunks)} chunks")
        chunks = embed_chunks(chunks)

        # Optionally narrow retrieval to a specific module using metadata
        if filter_module:
            narrowed = [
                c for c in chunks
                if c.get("metadata", {}).get("module") == filter_module
            ]
            if narrowed:
                print(f"  Using {len(narrowed)} chunks after module filter '{filter_module}'")
                chunks_for_retrieval = narrowed
            else:
                print(f"  Module filter '{filter_module}' matched no chunks; using all chunks.")
                chunks_for_retrieval = chunks
        else:
            chunks_for_retrieval = chunks

        for model_name in available:
            errors = []
            print(f"  [{model_name}]", flush=True)
            for i, row in enumerate(eval_rows):
                # Tailor retrieval per student answer: use the answer text as the query.
                answer_text = row["answer"]
                context_chunks = retrieve(chunks_for_retrieval, answer_text, k=k_retrieve)
                context = "\n\n---\n\n".join(context_chunks)
                model_id = openai_model if model_name == "openai" else None
                ai_score = grade_with_llm(rubric, context, row["answer"], provider=model_name, model_id=model_id, few_shot_block=few_shot_block)
                if ai_score is not None:
                    # Soft clamp: avoid hard zeros for non-empty answers unless explicitly produced.
                    if ai_score == 0.0 and str(row["answer"]).strip():
                        ai_score = 2.0
                    err = abs(ai_score - row["prof_score"])
                    errors.append(err)
                    print(f"    Row {i+1}: prof={row['prof_score']} ai={ai_score:.1f} err={err:.1f}", flush=True)
            if errors:
                mae = sum(errors) / len(errors)
                key = f"{strategy}+{model_name}"
                results[key] = {"mae": mae, "n": len(errors)}
                print(f"    MAE = {mae:.2f} (n={len(errors)})", flush=True)
            else:
                print(f"    No successful grades. Check API key and model id.", flush=True)

    print("\n=== Summary ===")
    for key, r in results.items():
        print(f"  {key}: MAE = {r['mae']:.2f}")

    if results:
        best_key = min(results, key=lambda k: results[k]["mae"])
        best_mae = results[best_key]["mae"]
        print(f"\n>>> Best: {best_key} (MAE = {best_mae:.2f})")

    # Optionally write results to a JSON file
    if out_path is not None:
        payload = {
            "results": results,
            "best": {"key": best_key, "mae": best_mae} if results else None,
            "config": {
                "strategies": strategies,
                "models": models,
                "openai_model": openai_model,
                "max_eval": max_eval,
                "k_retrieve": k_retrieve,
            },
        }
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    return results


def inspect_excel(path: Path):
    """Print Excel columns and sample rows for column mapping."""
    import pandas as pd
    df = pd.read_excel(path, sheet_name=0)
    print("Columns:", df.columns.tolist())
    print("\nFirst 2 rows (answer-like, score-like):")
    if df.empty:
        print("  (no rows in sheet)")
    else:
        for c in df.columns:
            if any(k in str(c).lower() for k in ["answer", "response", "score", "grade", "human"]):
                print(f"  {c}: {df[c].iloc[0]!r} ...")


def _parse_args():
    p = argparse.ArgumentParser(description="Evaluate chunking strategies for RAG grading.")
    p.add_argument("--inspect", action="store_true", help="Print Excel columns and exit")
    p.add_argument("--excel", default=str(EXCEL_PATH), help="Path to Quiz Excel")
    p.add_argument("--rubric", default=str(RUBRIC_PATH), help="Path to rubric JSON (ignored if --rubric-from-excel)")
    p.add_argument(
        "--rubric-from-excel",
        action="store_true",
        help="Build rubric text from the Excel file (e.g. 'Question Details' tab) instead of JSON rubric",
    )
    p.add_argument(
        "--sheet-name",
        default=None,
        help="Explicit Excel sheet name for student answers/scores (e.g. 'Student Submission')",
    )
    p.add_argument(
        "--answer-col",
        default=None,
        help="Explicit answer column name in Excel (e.g. 'question 13 answer')",
    )
    p.add_argument(
        "--prof-col",
        default=None,
        help="Explicit professor score column name in Excel (e.g. 'question 13 score')",
    )
    p.add_argument("--lectures", default=str(BASE_DIR), help="Root dir containing Lectures [html versions]")
    p.add_argument("--strategies", nargs="+", default=["semantic", "fixed", "hybrid"])
    p.add_argument("--models", nargs="+", default=["openai"],
                   help="LLMs to use: openai, claude, gemini")
    p.add_argument(
        "--filter-module",
        default=None,
        help="If set, restrict lecture retrieval to this module (e.g. 'module1') using chunk metadata.",
    )
    default_openai = LLM_CONFIGS["openai"][1]
    p.add_argument("--openai-model", default=default_openai,
                   help=f"OpenAI model id (default: {default_openai})")
    p.add_argument("--max-eval", type=int, default=15, help="Max evaluation rows")
    p.add_argument("--k", type=int, default=5, help="Retrieve top-k chunks")
    p.add_argument("--out", default="chunking_eval_results.json",
                   help="Path to write JSON results (default: chunking_eval_results.json)")
    p.add_argument(
        "--assignment-id",
        default=None,
        choices=list(FEW_SHOT_EXAMPLES.keys()),
        help=(
            "Assignment ID for few-shot calibration examples "
            f"(auto-detected from paths if omitted). One of: {list(FEW_SHOT_EXAMPLES.keys())}"
        ),
    )
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    if args.inspect:
        inspect_excel(Path(args.excel))
    else:
        rubric_override = None
        if args.rubric_from_excel:
            # For now we assume a sheet named 'Question Details' and focus on Question 13 if present.
            rubric_override = load_rubric_from_excel(
                Path(args.excel),
                sheet_name="Question Details",
                question_label="Question 13",
            )
        run_eval(
            excel_path=Path(args.excel),
            rubric_path=Path(args.rubric),
            lectures_root=Path(args.lectures),
            strategies=args.strategies,
            models=args.models,
            openai_model=args.openai_model,
            max_eval=args.max_eval,
            k_retrieve=args.k,
            out_path=Path(args.out) if args.out else None,
            rubric_text=rubric_override,
            sheet_name=args.sheet_name,
            answer_col=args.answer_col,
            prof_col=args.prof_col,
            filter_module=args.filter_module,
            assignment_id=args.assignment_id,
        )
