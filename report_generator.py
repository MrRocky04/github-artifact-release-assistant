"""README and Pull Request content generation."""

SECTION_START_TEMPLATE = "<!-- ARTIFACT-RELEASE: {artifact}@{version} START -->"
SECTION_END_TEMPLATE = "<!-- ARTIFACT-RELEASE: {artifact}@{version} END -->"


def _display_value(value):
    if value is None or value == "":
        return None
    if value == "1":
        return "Yes"
    if value == "0":
        return "No"
    return str(value)


def _add_field(lines: list[str], label: str, value) -> None:
    display = _display_value(value)
    if display is not None:
        lines.append(f"**{label}:** {display}")


def _optional(lines: list[str], label: str, value) -> None:
    display = _display_value(value)
    if display is not None:
        lines.append(f"**{label}:**")
        lines.append("")
        lines.append(display)
        lines.append("")


def _add_custom(lines: list[str], answers: dict, section: str) -> None:
    """Append answers to user-added questions that belong to the given section."""
    for label, value in answers.get("custom", {}).get(section, []):
        _add_field(lines, label, value)


def generate_release_record(answers: dict) -> str:
    artifact = answers["artifact_name"]
    version = answers["current_version"]
    lines = [
        SECTION_START_TEMPLATE.format(artifact=artifact, version=version),
        f"## SDK / Artifact Release Information — {artifact} ({version})",
        "",
    ]

    for label, key in [
        ("Artifact Name", "artifact_name"),
        ("Current Version", "current_version"),
        ("Previous Version", "previous_version"),
        ("GitHub Repository", "repository"),
        ("Source Branch", "source_branch"),
        ("Testing / Usage Purpose", "testing_purpose_name"),
    ]:
        _add_field(lines, label, answers.get(key))
    _add_custom(lines, answers, "artifact")

    lines += ["", "### Release Information", ""]
    for label, key in [
        ("Reason for Release", "release_reason"),
        ("New Features / Capabilities", "new_features"),
        ("Bugs Fixed", "bugs_fixed"),
        ("Existing Functionality Modified", "modified_functionality"),
        ("Known Issues / Limitations", "known_issues"),
        ("Breaking Changes", "breaking_changes"),
        ("Recommended Over Previous Version", "recommended_over_previous"),
    ]:
        _add_field(lines, label, answers.get(key))
    _add_custom(lines, answers, "release")
    _optional(lines, "Migration Steps", answers.get("migration_steps"))
    _optional(lines, "Prerequisites / Configuration Requirements", answers.get("prerequisites"))
    _optional(lines, "Additional Release Information", answers.get("release_notes"))

    purpose = answers.get("testing_purpose")
    if purpose == "1":
        lines += ["### Internal Testing", ""]
        for label, key in [
            ("Code Review Completed", "code_review"),
            ("Code Reviewer", "code_reviewer"),
            ("QA Testing Completed", "qa_testing"),
            ("Regression Testing Completed", "regression_testing"),
            ("Unit Testing Completed", "unit_testing"),
            ("Integration Testing Completed", "integration_testing"),
            ("Integration Successful", "integration_successful"),
            ("All Required Tests Successful", "all_tests_successful"),
        ]:
            _add_field(lines, label, answers.get(key))
        _add_custom(lines, answers, "internal")
        _optional(lines, "Failed / Pending Tests", answers.get("failed_pending_tests"))
        _optional(lines, "Additional Internal Testing Information", answers.get("internal_testing_notes"))
    elif purpose == "2":
        lines += ["### Personal Testing", ""]
        for label, key in [
            ("Personally Tested", "personally_tested"),
            ("Artifact Imported Successfully", "artifact_imported"),
            ("Required Functionality Tested", "required_functionality_tested"),
            ("Integration Testing Completed", "integration_testing"),
            ("Integration Successful", "integration_successful"),
            ("Target Environment Tested", "target_environment_tested"),
            ("Known Problems Encountered", "known_problems"),
        ]:
            _add_field(lines, label, answers.get(key))
        _add_custom(lines, answers, "personal")
        _optional(lines, "Known Problem Details", answers.get("known_problem_details"))
        _add_field(lines, "Primarily Experimental / Evaluation Use", answers.get("experimental_use"))
        _optional(lines, "Additional Personal Testing Information", answers.get("personal_testing_notes"))
    elif purpose == "3":
        lines += ["### Production Readiness", ""]
        for label, key in [
            ("Code Review Completed", "code_review"),
            ("Code Reviewer", "code_reviewer"),
            ("QA Testing Completed", "qa_testing"),
            ("Unit Testing Completed", "unit_testing"),
            ("Regression Testing Completed", "regression_testing"),
            ("Integration Testing Completed", "integration_testing"),
            ("Integration Successful", "integration_successful"),
            ("All Required Tests Successful", "all_tests_successful"),
            ("Backward Compatible", "backward_compatible"),
            ("Dependency Changes", "dependency_changes"),
            ("Deployment Approved", "deployment_approved"),
            ("Approved By", "approved_by"),
            ("Recommended for Production", "production_recommended"),
            ("Final Artifact Verified", "final_artifact_verified"),
        ]:
            _add_field(lines, label, answers.get(key))
        _add_custom(lines, answers, "production")
        _optional(lines, "Failed / Pending Tests", answers.get("failed_pending_tests"))
        _optional(lines, "Additional Production Validation Information", answers.get("production_testing_notes"))

    _optional(lines, "Additional Artifact Information", answers.get("artifact_notes"))
    lines.append(SECTION_END_TEMPLATE.format(artifact=artifact, version=version))
    return "\n".join(lines).strip() + "\n"


def update_readme(readme_text: str, answers: dict) -> tuple[str, bool, str]:
    """Insert or replace the marked release section in an existing README."""
    section = generate_release_record(answers)
    artifact = answers["artifact_name"]
    version = answers["current_version"]
    start = SECTION_START_TEMPLATE.format(artifact=artifact, version=version)
    end = SECTION_END_TEMPLATE.format(artifact=artifact, version=version)

    start_index = readme_text.find(start)
    if start_index >= 0:
        end_index = readme_text.find(end, start_index)
        if end_index < 0:
            raise ValueError("Found the release section start marker, but not its end marker.")
        end_index += len(end)
        replacement = readme_text[:start_index] + section.rstrip("\n") + readme_text[end_index:]
    else:
        separator = "\n" if readme_text.endswith("\n") else "\n\n"
        replacement = readme_text + separator + section

    return replacement, replacement != readme_text, section


def _summary_lines(answers: dict) -> list[str]:
    lines = []
    record = generate_release_record(answers).strip()
    if record:
        lines.append(record)
    return lines


def generate_pr_body(answers: dict, branch: str, base_branch: str) -> str:
    lines = [
        "## SDK / Artifact Release Information",
        "",
        f"**Artifact:** `{answers['artifact_name']}`",
        f"**Version:** `{answers['current_version']}`",
        f"**Source branch:** `{answers['source_branch']}`",
        f"**PR branch:** `{branch}`",
        f"**Base branch:** `{base_branch}`",
        "",
        "The questionnaire responses below are also recorded in the repository README.md so Git can track future changes.",
        "",
        "### Questionnaire Details",
        "",
    ]
    lines.extend(_summary_lines(answers))
    return "\n".join(lines).rstrip() + "\n"


def generate_answer_summary(answers: dict) -> str:
    """Return only answers the developer actually supplied; skipped values are omitted."""
    record = generate_release_record(answers).strip()
    if not record:
        return "No questionnaire information was supplied."
    return record
