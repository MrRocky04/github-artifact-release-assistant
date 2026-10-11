"""Release workflow used by the web UI.

This is the logic that used to live in the interactive part of main.py.  The
steps, their order and every GitHub operation (all through ``git`` and the
GitHub CLI ``gh``) are unchanged - only ``print``/``input`` was replaced by
return values so the website can show the result.
"""

import threading
from pathlib import Path

from github_cli import (
    check_authentication,
    checkout_existing_branch,
    checkout_new_branch,
    commit_and_push,
    copy_artifact_into_repo,
    create_pull_request,
    create_release_tag,
    discard_changes,
    ensure_repository_clone,
    find_open_pr,
    get_last_error,
    git_diff,
    git_fetch,
    git_status,
    git_worktree_clean,
    read_file,
    release_exists,
    remote_branch_exists,
    remote_branch_exists_local,
    run_command,
    tag_exists,
    write_file,
)
from questions import (
    PURPOSES,
    custom_answers,
    list_questions,
    normalize_repository,
    validate_answers,
)
from report_generator import generate_answer_summary, generate_pr_body, update_readme

_lock = threading.Lock()
_pending: dict = {}          # the change that is waiting for the user's confirmation


class WorkflowError(Exception):
    """An error that can be shown to the user as-is."""


# --------------------------------------------------------------------------
def _artifact_size(path: Path) -> str:
    size_mb = path.stat().st_size / (1024 * 1024)
    return f"{size_mb:.2f} MB"


def _cli_error(default: str) -> str:
    detail = get_last_error()
    return f"{default}\n{detail}" if detail else default


def _valid_ref(repo_path: Path, name: str) -> bool:
    if not name or name.startswith("-") or " " in name:
        return False
    return run_command(["git", "check-ref-format", "--branch", name], cwd=repo_path) is not None


def default_pr_title(answers: dict) -> str:
    return f"SDK Release - {answers['artifact_name']} {answers['current_version']}"


def _build_release_notes(answers: dict, branch: str) -> str:
    lines = [
        f"Artifact: {answers['artifact_name']}",
        f"Version: {answers['current_version']}",
        f"Release branch: {branch}",
        f"Source branch: {answers['source_branch']}",
    ]
    if answers.get("artifact_notes"):
        lines.extend(["", answers["artifact_notes"]])
    return "\n".join(lines)


def _normalise(payload: dict, artifact: dict) -> dict:
    """Build the same ``answers`` dict the CLI produced."""
    action = payload.get("action")
    if action not in {"release", "upload"}:
        raise WorkflowError("Unknown action.")

    raw = payload.get("answers") or {}
    answers = {k: (str(v).strip() if v is not None else "") for k, v in raw.items()}
    answers["artifact_name"] = artifact["name"]
    answers["artifact_path"] = artifact["path"]
    answers["repository"] = normalize_repository(answers.get("repository", ""))

    sections = ["artifact"]
    if action == "release":
        purpose = answers.get("testing_purpose", "")
        if purpose not in PURPOSES:
            raise WorkflowError("Please select the purpose of the artifact.")
        answers["testing_purpose_name"] = PURPOSES[purpose]["name"]
        sections += ["release", PURPOSES[purpose]["section"]]

    errors = validate_answers(answers, sections)
    if errors:
        raise WorkflowError("Some required questions are not answered correctly.")

    version = answers["current_version"]
    if version.startswith("-") or any(ch.isspace() for ch in version):
        raise WorkflowError("The artifact version cannot contain spaces or start with '-'.")

    answers["custom"] = custom_answers(answers, sections)
    return answers


# --------------------------------------------------------------------------
# Public API used by server.py
# --------------------------------------------------------------------------
def status() -> dict:
    import shutil
    gh = shutil.which("gh") is not None
    git = shutil.which("git") is not None
    return {
        "gh_installed": gh,
        "git_installed": git,
        "authenticated": bool(gh and check_authentication()),
    }


def summary(payload: dict, artifact: dict) -> dict:
    """'Questionnaire answer verification' - what will be written to the README / PR."""
    answers = _normalise(payload, artifact)
    return {"text": generate_answer_summary(answers)}


def prepare(payload: dict, artifact: dict) -> dict:
    """Clone/refresh the repository, pick the branch and stage the changes for review."""
    with _lock:
        _discard_pending()
        answers = _normalise(payload, artifact)
        action = payload["action"]
        repository = answers["repository"]

        if not check_authentication():
            raise WorkflowError("GitHub CLI authentication is required. Run: gh auth login")

        repo_path = ensure_repository_clone(repository)
        if repo_path is None:
            raise WorkflowError(_cli_error("Unable to prepare a local repository workspace."))

        if not git_worktree_clean(repo_path):
            what = "uploading an artifact" if action == "upload" else "using the questionnaire workflow"
            raise WorkflowError(
                f"The local repository workspace has uncommitted changes. Clean it before {what}.")

        if not git_fetch(repo_path):
            raise WorkflowError(_cli_error("Unable to refresh the repository branches."))

        source_branch = answers["source_branch"]
        branch_mode = payload.get("branch_mode")
        branch = (payload.get("branch_name") or "").strip()
        if branch_mode not in {"new", "existing"}:
            raise WorkflowError("Please choose how to handle the release branch.")
        if not branch:
            raise WorkflowError("Please enter the branch name.")
        if not _valid_ref(repo_path, branch) or not _valid_ref(repo_path, source_branch):
            raise WorkflowError("The branch name is not valid.")
        if branch == source_branch:
            raise WorkflowError("The release branch cannot be the same as the source/base branch.")

        if branch_mode == "new":
            if remote_branch_exists(repository, branch) or remote_branch_exists_local(repo_path, branch):
                raise WorkflowError(
                    f"Branch '{branch}' already exists. Choose the existing-branch option instead.")
            if not checkout_new_branch(repo_path, source_branch, branch):
                raise WorkflowError(_cli_error(f"Unable to create branch '{branch}'."))
        else:
            if not remote_branch_exists(repository, branch):
                raise WorkflowError(f"The branch '{branch}' does not exist on the remote repository.")
            # A new PR is always created, and GitHub allows one open PR per head/base pair.
            existing_pr = find_open_pr(repository, branch, source_branch)
            if existing_pr:
                raise WorkflowError(
                    f"Branch '{branch}' already has open Pull Request #{existing_pr['number']}. "
                    "Use a different branch for a new Pull Request.")
            if not checkout_existing_branch(repo_path, branch):
                raise WorkflowError(_cli_error(f"Unable to checkout existing branch '{branch}'."))

        artifact_path = Path(answers["artifact_path"])
        answers["file_size"] = _artifact_size(artifact_path)

        _, artifact_changed, artifact_message = copy_artifact_into_repo(
            repo_path, artifact_path, artifact_path.name)

        readme_changed = False
        readme_section = ""
        if action == "release":
            readme_before = read_file(repo_path, "README.md")
            try:
                readme_after, readme_changed, readme_section = update_readme(readme_before, answers)
            except ValueError as exc:
                discard_changes(repo_path, [artifact_path.name])
                raise WorkflowError(f"Unable to update README.md safely: {exc}")
            if readme_changed:
                write_file(repo_path, "README.md", readme_after)

        review = {
            "action": action,
            "branch": branch,
            "branch_mode": branch_mode,
            "source_branch": source_branch,
            "repository": repository,
            "artifact_name": artifact_path.name,
            "version": answers["current_version"],
            "size": answers["file_size"],
            "artifact_message": artifact_message,
            "artifact_changed": artifact_changed,
            "readme_changed": readme_changed,
            "readme_section": readme_section if readme_changed else "",
            "default_pr_title": default_pr_title(answers) if action == "release" else "",
            "status": git_status(repo_path),
            "readme_diff": git_diff(repo_path) if readme_changed else "",
            "no_changes": not (artifact_changed or readme_changed),
        }
        if review["no_changes"]:
            review["message"] = (
                "No Git changes were produced. Nothing to commit or release."
                if action == "release"
                else "No new Git change is required. The same AAR is already present in the branch.")
            return review

        paths = [artifact_path.name] + (["README.md"] if readme_changed else [])
        _pending.clear()
        _pending.update({
            "repo_path": repo_path, "answers": answers, "branch": branch,
            "paths": paths, "action": action,
            "artifact_changed": artifact_changed, "readme_changed": readme_changed,
        })
        return review


def confirm(payload: dict) -> dict:
    """Commit, push and (for the questionnaire workflow) create the release/tag and PR."""
    with _lock:
        if not _pending:
            raise WorkflowError("There is nothing waiting for confirmation. Please review the changes again.")
        p = dict(_pending)
        answers, repo_path, branch = p["answers"], p["repo_path"], p["branch"]
        repository = answers["repository"]
        steps: list[dict] = []

        def step(label, ok, detail=""):
            steps.append({"label": label, "ok": ok, "detail": detail})
            return ok

        artifact_name = Path(answers["artifact_path"]).name

        if p["action"] == "upload":
            message = f"Add artifact {artifact_name} {answers['current_version']}"
            if not commit_and_push(repo_path, branch, message, p["paths"]):
                step("Commit and push", False, _cli_error("Artifact commit/push failed."))
                return {"ok": False, "steps": steps}
            _pending.clear()
            step("Artifact added to the release branch and pushed", True, f"Branch: {branch}")
            step("GitHub Release / Pull Request", True,
                 "Not created - the upload-only operation does not create them.")
            return {"ok": True, "steps": steps, "branch": branch}

        # ---- questionnaire / release workflow --------------------------------
        message = (f"Add release information for {answers['artifact_name']} "
                   f"{answers['current_version']}")
        if not p["readme_changed"] and p["artifact_changed"]:
            message = (f"Update artifact {answers['artifact_name']} "
                       f"{answers['current_version']}")

        if not commit_and_push(repo_path, branch, message, p["paths"]):
            step("Commit and push", False,
                 _cli_error("Commit/push failed. No release/tag or Pull Request was created."))
            return {"ok": False, "steps": steps}
        _pending.clear()
        step("Changes committed and pushed", True, f"Branch: {branch}")

        version = answers["current_version"]
        already = release_exists(repository, version) or tag_exists(repository, version)
        if not create_release_tag(
            repository=repository,
            version=version,
            target_branch=branch,
            notes=_build_release_notes(answers, branch),
            aar_path=answers["artifact_path"],
        ):
            step("GitHub release / tag", False,
                 _cli_error("The branch was pushed, but the release/tag could not be created."))
            return {"ok": False, "steps": steps}
        if already:
            step("GitHub release / tag", True,
                 f"'{version}' already exists - it was not recreated or moved.")
        else:
            step("GitHub release / tag", True, f"Release '{version}' created with the AAR attached.")

        title = (payload.get("pr_title") or "").strip() or default_pr_title(answers)
        body = generate_pr_body(answers, branch, answers["source_branch"])
        created = create_pull_request(
            repository=repository, branch=branch,
            base_branch=answers["source_branch"], title=title, body=body)
        if created:
            step("Pull Request", True, created)
            return {"ok": True, "steps": steps, "pr_url": created, "branch": branch}
        step("Pull Request", False, _cli_error(
            "The artifact/README commit and release/tag were created, but Pull Request creation failed."))
        return {"ok": False, "steps": steps}


def cancel() -> dict:
    with _lock:
        _discard_pending()
    return {"ok": True}


def _discard_pending() -> None:
    if _pending:
        discard_changes(_pending["repo_path"], _pending["paths"])
        _pending.clear()
