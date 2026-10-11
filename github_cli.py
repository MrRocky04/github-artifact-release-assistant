"""GitHub CLI and Git helpers used by the assistant."""

import json
import subprocess
from pathlib import Path

from config import REPOSITORY_WORKSPACE


_last_error = ""


def get_last_error() -> str:
    """Return the stderr text of the most recent failed command (for the web UI)."""
    return _last_error


def run_command(command, *, cwd=None, check=False):
    global _last_error
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError as exc:
        _last_error = f"Command not found: {command[0]}"
        print(f"\nCommand not found: {command[0]}")
        print(exc)
        return None

    if result.returncode != 0:
        _last_error = result.stderr.strip() or result.stdout.strip()
        if check:
            print("\nCommand failed:")
            print(" ".join(command))
            if result.stderr.strip():
                print("\nError:")
                print(result.stderr.strip())
        return None

    return result.stdout.strip()


def check_authentication() -> bool:
    return run_command(["gh", "auth", "status"]) is not None


def release_exists(repository: str, version: str) -> bool:
    return run_command(["gh", "release", "view", version, "--repo", repository]) is not None


def tag_exists(repository: str, version: str) -> bool:
    output = run_command(["gh", "api", f"repos/{repository}/git/ref/tags/{version}"])
    return output is not None


def create_release_tag(repository: str,version: str,target_branch: str,notes: str,aar_path: str,) -> bool:
    """Create a GitHub release/tag at the current tip of target_branch
    and upload the AAR as a release asset.
    Existing tags/releases are never moved or recreated.
    """
    if release_exists(repository, version) or tag_exists(repository, version):
        print(f"\nRelease/tag '{version}' already exists in {repository}.")
        print("The existing release/tag will not be recreated or moved.")
        return True

    command = [
        "gh",
        "release",
        "create",
        version,
        aar_path,
        "--repo",
        repository,
        "--title",
        version,
        "--notes",
        notes,
        "--target",
        target_branch,
    ]

    print(
        f"\nCreating GitHub release/tag '{version}' "
        f"at branch '{target_branch}'..."
    )
    print(f"Uploading artifact '{aar_path}' as a release asset...")

    return run_command(command, check=True) is not None

def repository_workspace(repository: str) -> Path:
    safe_name = repository.replace("/", "__")
    return Path(REPOSITORY_WORKSPACE) / safe_name


def ensure_repository_clone(repository: str) -> Path | None:
    path = repository_workspace(repository)
    path.parent.mkdir(parents=True, exist_ok=True)

    if (path / ".git").exists():
        remote = run_command(["git", "remote", "get-url", "origin"], cwd=path)
        if remote is None:
            print(f"Existing workspace is not a valid Git repository: {path}")
            return None
        return path

    if path.exists() and any(path.iterdir()):
        print(f"Workspace already exists and is not empty: {path}")
        return None

    result = run_command(
        ["gh", "repo", "clone", repository, str(path)],
        check=True,
    )
    return path if result is not None else None


def git_worktree_clean(repo_path: Path) -> bool:
    output = run_command(["git", "status", "--porcelain"], cwd=repo_path)
    return output == ""


def git_fetch(repo_path: Path) -> bool:
    return run_command(
        ["git", "fetch", "origin", "--prune"],
        cwd=repo_path,
        check=True,
    ) is not None


def remote_branch_exists(repository: str, branch: str) -> bool:
    return run_command(
        ["gh", "api", f"repos/{repository}/branches/{branch}"]
    ) is not None


def remote_branch_exists_local(repo_path: Path, branch: str) -> bool:
    output = run_command(
        ["git", "ls-remote", "--heads", "origin", branch],
        cwd=repo_path,
    )
    return bool(output)


def local_branch_exists(repo_path: Path, branch: str) -> bool:
    return run_command(
        ["git", "rev-parse", "--verify", branch],
        cwd=repo_path,) is not None

def checkout_existing_branch(repo_path: Path, branch: str) -> bool:
    if run_command(["git", "checkout", "-B", branch, f"origin/{branch}"],
        cwd=repo_path,
        check=True,) is None:
        return False
    return run_command(
        ["git", "pull", "--ff-only", "origin", branch],
        cwd=repo_path,
        check=True,) is not None

def checkout_new_branch(repo_path: Path, base_branch: str, new_branch: str) -> bool:
    if local_branch_exists(repo_path, new_branch) or remote_branch_exists_local(
        repo_path, new_branch):
        return False

    if run_command(["git", "checkout", base_branch], cwd=repo_path, check=True) is None:
        if run_command(
            ["git", "checkout", "-B", base_branch, f"origin/{base_branch}"],
            cwd=repo_path,
            check=True,) is None:
            return False

    if run_command(
        ["git", "pull", "--ff-only", "origin", base_branch],
        cwd=repo_path,
        check=True,) is None:
        return False

    return run_command(
        ["git", "checkout", "-b", new_branch],
        cwd=repo_path,
        check=True,) is not None


def read_file(repo_path: Path, relative_path: str) -> str:
    path = repo_path / relative_path
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def write_file(repo_path: Path, relative_path: str, content: str) -> None:
    path = repo_path / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def copy_artifact_into_repo(repo_path: Path,artifact_path: Path,destination_name: str,) -> tuple[bool, bool, str]:
    """Copy the AAR into the repository root.
    Returns (success, changed, message). Existing binary content is replaced only
    after the caller has confirmed the complete planned change.
    """
    destination = repo_path / destination_name
    source_bytes = artifact_path.read_bytes()

    if destination.exists():
        existing_bytes = destination.read_bytes()
        if existing_bytes == source_bytes:
            return True, False, "The same AAR already exists in the branch."
        destination.write_bytes(source_bytes)
        return True, True, "The existing AAR was replaced with the supplied build."

    destination.write_bytes(source_bytes)
    return True, True, "The AAR was added to the branch."


def discard_changes(repo_path: Path, paths: list[str]) -> None:
    """Undo staged/working-tree changes for paths, including a newly added (untracked) file."""
    for name in paths:
        tracked = run_command(["git", "ls-files", "--error-unmatch", "--", name], cwd=repo_path)
        if tracked is not None:
            run_command(["git", "restore", "--staged", "--worktree", "--", name], cwd=repo_path)
        else:
            target = repo_path / name
            if target.exists():
                target.unlink()


def git_diff(repo_path: Path) -> str:
    output = run_command(["git", "diff", "--", "README.md"], cwd=repo_path)
    return output or ""


def git_status(repo_path: Path) -> str:
    output = run_command(["git", "status", "--short"], cwd=repo_path)
    return output or ""


def commit_and_push(repo_path: Path,branch: str,message: str,paths: list[str],) -> bool:
    if not paths:
        return False

    if run_command(["git", "add", *paths], cwd=repo_path, check=True) is None:
        return False

    commit_result = run_command(["git", "commit", "-m", message],
        cwd=repo_path,
        check=True,)
    if commit_result is None:
        return False

    return run_command(
        ["git", "push", "-u", "origin", branch],
        cwd=repo_path,
        check=True,) is not None

def find_open_pr(repository: str, branch: str, base_branch: str | None = None):
    output = run_command([
        "gh", "pr", "list",
        "--repo", repository,
        "--head", branch,
        "--state", "open",
        "--json", "number,title,url,headRefName,baseRefName",])
    if output is None:
        return None
    try:
        prs = json.loads(output)
    except json.JSONDecodeError:
        return None

    if base_branch is None:
        return prs[0] if prs else None

    for pr in prs:
        if pr.get("baseRefName") == base_branch:
            return pr
    return None


def create_pull_request(repository: str,branch: str,base_branch: str,title: str,body: str,):
    body_file = repository_workspace(repository) / ".artifact_assistant_pr_body.md"
    body_file.write_text(body, encoding="utf-8")
    try:
        output = run_command([
            "gh", "pr", "create",
            "--repo", repository,
            "--head", branch,
            "--base", base_branch,
            "--title", title,
            "--body-file", str(body_file),
        ], check=True)
    finally:
        body_file.unlink(missing_ok=True)
    return output
