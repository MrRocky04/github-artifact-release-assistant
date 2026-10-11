"""Question definitions and the editable question store.

The original command-line questionnaire is now data driven so the web UI can
add and remove questions.  The wording, order and follow-up logic of the
default questions are unchanged.

Sections
    artifact    Artifact information
    release     Release information
    internal    Purpose of the artifact -> Internal Testing
    personal    Purpose of the artifact -> Personal Testing
    production  Purpose of the artifact -> Production

Question types
    text    free text
    binary  Yes / No / Skip   (stored as "1" / "0" / "" for report_generator)
"""

import json
import re
import threading
import uuid
from typing import Optional

from config import DEFAULT_SOURCE_BRANCH, QUESTIONS_FILE

SECTIONS = [
    {"id": "artifact", "title": "Artifact information", "group": "Artifact information"},
    {"id": "release", "title": "Release information", "group": "Release information"},
    {"id": "internal", "title": "Internal testing", "group": "Purpose of the artifact"},
    {"id": "personal", "title": "Personal testing", "group": "Purpose of the artifact"},
    {"id": "production", "title": "Production", "group": "Purpose of the artifact"},
]
SECTION_IDS = {s["id"] for s in SECTIONS}

# purpose number used by report_generator ("1"/"2"/"3") -> section id
PURPOSES = {
    "1": {"section": "internal", "name": "Internal Testing"},
    "2": {"section": "personal", "name": "Personal Testing"},
    "3": {"section": "production", "name": "Production"},
}

_lock = threading.Lock()


def _q(key, section, label, qtype="text", required=False, default=None,
       locked=False, depends_on=None):
    return {
        "key": key, "section": section, "label": label, "type": qtype,
        "required": required, "default": default, "builtin": True,
        "locked": locked, "depends_on": depends_on,
    }


def _dep(key):
    return {"key": key, "value": "1"}


def default_questions() -> list[dict]:
    q = _q
    return [
        # ---- Artifact information ---------------------------------------
        q("current_version", "artifact", "What is the current artifact version", required=True, locked=True),
        q("previous_version", "artifact", "What was the previous artifact version, if applicable"),
        q("repository", "artifact", "Which GitHub repository contains the SDK/Artifact release (OWNER/REPO)",
          required=True, locked=True),
        q("source_branch", "artifact", "Which source branch is associated with this SDK release",
          required=True, default=DEFAULT_SOURCE_BRANCH, locked=True),
        q("is_new_release", "artifact", "Is this information for a new SDK release", "binary"),
        q("is_update", "artifact", "Is this an update to information for an existing SDK version", "binary"),
        q("artifact_notes", "artifact", "Is there any additional artifact information you want to record (optional)"),

        # ---- Release information ----------------------------------------
        q("release_reason", "release", "Why was this SDK release created"),
        q("new_features", "release", "What new features or capabilities were introduced in this release"),
        q("bugs_fixed", "release", "What bugs or defects were fixed in this release"),
        q("modified_functionality", "release", "Was any existing SDK functionality changed or modified", "binary"),
        q("known_issues", "release", "Are there any known issues or limitations that consumers should be aware of"),
        q("breaking_changes", "release", "Does this release introduce any breaking changes", "binary"),
        q("migration_steps", "release", "Are there any migration steps consumers need to follow"),
        q("prerequisites", "release", "Are there any prerequisites or configuration requirements consumers need to know about"),
        q("recommended_over_previous", "release", "Is this version recommended over the previous version for its intended use", "binary"),
        q("release_notes", "release", "Is there any additional release information you want to record (optional)"),

        # ---- Internal testing --------------------------------------------
        q("code_review", "internal", "Has the SDK code been reviewed before this artifact is used for internal testing", "binary"),
        q("code_reviewer", "internal", "Who reviewed the SDK changes or artifact", depends_on=_dep("code_review")),
        q("qa_testing", "internal", "Has QA testing been completed for the SDK changes included in this artifact", "binary"),
        q("regression_testing", "internal", "Has regression testing been completed to check existing SDK functionality", "binary"),
        q("unit_testing", "internal", "Has unit testing been completed for the relevant SDK changes", "binary"),
        q("integration_testing", "internal", "Has the AAR been integrated into a test or sample application", "binary"),
        q("integration_successful", "internal", "Did the SDK integrate and behave as expected in the test application", "binary"),
        q("all_tests_successful", "internal", "Were all tests relevant to this internal build successful", "binary"),
        q("failed_pending_tests", "internal", "Which tests failed or are still pending",
          depends_on={"key": "all_tests_successful", "value": "0"}),
        q("internal_testing_notes", "internal", "Is there any additional information about the internal testing of this artifact (optional)"),

        # ---- Personal testing --------------------------------------------
        q("personally_tested", "personal", "Have you personally tested this artifact for the intended SDK functionality", "binary"),
        q("artifact_imported", "personal", "Was the AAR imported successfully into the application used for testing", "binary"),
        q("required_functionality_tested", "personal", "Was the functionality you are evaluating tested successfully", "binary"),
        q("integration_testing", "personal", "Was the AAR integrated into an application as part of your testing", "binary"),
        q("integration_successful", "personal", "Did the SDK behave as expected after integration into the application", "binary"),
        q("target_environment_tested", "personal", "Was the artifact tested in the target Android, device, or runtime environment", "binary"),
        q("known_problems", "personal", "Did you encounter any known problems while personally testing this artifact", "binary"),
        q("known_problem_details", "personal", "Please describe the known problems encountered during testing",
          depends_on=_dep("known_problems")),
        q("experimental_use", "personal", "Is this artifact mainly intended for experimentation or personal evaluation rather than production use", "binary"),
        q("personal_testing_notes", "personal", "Is there any additional information about your personal testing of this artifact (optional)"),

        # ---- Production ---------------------------------------------------
        q("code_review", "production", "Has the SDK code been reviewed before this artifact is considered for production use", "binary"),
        q("code_reviewer", "production", "Who reviewed the SDK changes or artifact", depends_on=_dep("code_review")),
        q("qa_testing", "production", "Has QA testing been completed for the release", "binary"),
        q("unit_testing", "production", "Has unit testing been completed for the relevant SDK changes", "binary"),
        q("regression_testing", "production", "Has regression testing been completed to verify existing functionality", "binary"),
        q("integration_testing", "production", "Has the artifact been integrated into an application for release validation", "binary"),
        q("integration_successful", "production", "Did the SDK integrate and behave as expected in the release validation application", "binary"),
        q("all_tests_successful", "production", "Were all required tests successful for this release", "binary"),
        q("failed_pending_tests", "production", "Which tests failed or are still pending",
          depends_on={"key": "all_tests_successful", "value": "0"}),
        q("backward_compatible", "production", "Is this release backward compatible with the previous SDK version where compatibility is expected", "binary"),
        q("dependency_changes", "production", "Does this release introduce any dependency changes that consumers should know about", "binary"),
        q("deployment_approved", "production", "Has this release been approved for deployment or consumer use", "binary"),
        q("approved_by", "production", "Who approved the release for deployment or consumer use",
          depends_on=_dep("deployment_approved")),
        q("production_recommended", "production", "Is this artifact recommended for production use", "binary"),
        q("final_artifact_verified", "production", "Has the final AAR been verified as the intended build for this release", "binary"),
        q("production_testing_notes", "production", "Is there any additional information about production validation or readiness (optional)"),
    ]


# Questions of the separate "Upload Artifact" operation (not editable).
UPLOAD_QUESTIONS = [
    {"key": "deployment_environment", "label": "Which deployment environment is this artifact being uploaded for (optional)",
     "type": "text", "required": False},
    {"key": "upload_notes", "label": "Is there any additional information about this artifact upload (optional)",
     "type": "text", "required": False},
]


# --------------------------------------------------------------------------
# Ids
#
# The same answer key (e.g. "code_review") is used in more than one section,
# exactly like the original code, because report_generator reads answers by
# key.  The unique id of a question is therefore "<section>:<key>".
# --------------------------------------------------------------------------
def _with_ids(questions: list[dict]) -> list[dict]:
    for item in questions:
        item["id"] = f'{item["section"]}:{item["key"]}'
    return questions


def _save(questions: list[dict]) -> None:
    QUESTIONS_FILE.write_text(json.dumps({"questions": questions}, indent=2), encoding="utf-8")


def _load() -> list[dict]:
    if QUESTIONS_FILE.exists():
        try:
            data = json.loads(QUESTIONS_FILE.read_text(encoding="utf-8"))
            items = data.get("questions")
            if isinstance(items, list) and items:
                return _with_ids(items)
        except (OSError, json.JSONDecodeError):
            pass
    items = _with_ids(default_questions())
    _save(items)
    return items


def list_questions() -> list[dict]:
    with _lock:
        return _load()


def questions_for_section(section: str) -> list[dict]:
    return [item for item in list_questions() if item["section"] == section]


def add_question(section: str, label: str, qtype: str, required: bool) -> dict:
    label = (label or "").strip()
    if section not in SECTION_IDS:
        raise ValueError("Please choose a valid section for the question.")
    if not label:
        raise ValueError("The question text cannot be empty.")
    if len(label) > 300:
        raise ValueError("The question text is too long (300 characters maximum).")
    if qtype not in {"text", "binary"}:
        raise ValueError("The answer type must be text or Yes/No.")

    with _lock:
        items = _load()
        if any(i["section"] == section and i["label"].lower() == label.lower() for i in items):
            raise ValueError("This question already exists in the selected section.")
        key = f"custom_{uuid.uuid4().hex[:8]}"
        item = {
            "key": key, "section": section, "label": label, "type": qtype,
            "required": bool(required), "default": None, "builtin": False,
            "locked": False, "depends_on": None, "id": f"{section}:{key}",
        }
        items.append(item)
        _save(items)
        return item


def delete_question(question_id: str) -> list[str]:
    """Delete a question and any follow-up questions that depend on it.

    Returns the ids of every removed question.
    """
    with _lock:
        items = _load()
        target = next((i for i in items if i["id"] == question_id), None)
        if target is None:
            raise KeyError("Question not found.")
        if target.get("locked"):
            raise ValueError(
                "This question is needed to create the branch, release and pull request, so it cannot be removed.")
        removed = {target["id"]}
        # follow-up questions are only meaningful together with their parent
        for i in items:
            dep = i.get("depends_on")
            if dep and i["section"] == target["section"] and dep["key"] == target["key"]:
                removed.add(i["id"])
        items = [i for i in items if i["id"] not in removed]
        _save(items)
        return sorted(removed)


def reset_questions() -> None:
    with _lock:
        _save(_with_ids(default_questions()))


# --------------------------------------------------------------------------
# Answer helpers
# --------------------------------------------------------------------------
def is_visible(question: dict, answers: dict) -> bool:
    dep = question.get("depends_on")
    return not dep or answers.get(dep["key"]) == dep["value"]


def normalize_repository(repository: str) -> str:
    """Accept a Windows-style backslash and normalize it to GitHub OWNER/REPO."""
    return repository.strip().replace("\\", "/")


_REPO_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9_.-]+$")


def valid_repository(repository: str) -> bool:
    return bool(_REPO_RE.match(repository))


def validate_answers(answers: dict, sections: list[str]) -> dict[str, str]:
    """Return {question id: error message} for the given sections."""
    errors: dict[str, str] = {}
    for item in list_questions():
        if item["section"] not in sections or not is_visible(item, answers):
            continue
        value = str(answers.get(item["key"], "") or "").strip()
        if item["type"] == "binary" and value not in {"", "0", "1"}:
            errors[item["id"]] = "Please choose Yes, No or Skip."
        elif item["required"] and not value:
            errors[item["id"]] = "This question is required."
        elif item["key"] == "repository" and value and not valid_repository(normalize_repository(value)):
            errors[item["id"]] = "Please enter the repository in OWNER/REPO format."
    return errors


def custom_answers(answers: dict, sections: list[str]) -> dict[str, list[tuple[str, str]]]:
    """Collect answers to user-added questions: {section: [(label, value), ...]}."""
    out: dict[str, list[tuple[str, str]]] = {}
    for item in list_questions():
        if item["builtin"] or item["section"] not in sections:
            continue
        value = str(answers.get(item["key"], "") or "").strip()
        if value:
            out.setdefault(item["section"], []).append((item["label"], value))
    return out
