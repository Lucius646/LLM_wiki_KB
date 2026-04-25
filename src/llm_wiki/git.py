from pathlib import Path
import subprocess

from llm_wiki.models import GitCommitResult, GitStatus


def run_git(root: Path, args: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("Git is required but was not found on PATH.") from exc
    if check and result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "git command failed"
        raise RuntimeError(detail)
    return result


def ensure_git_available() -> None:
    try:
        subprocess.run(
            ["git", "--version"],
            text=True,
            capture_output=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("Git is required but was not found on PATH.") from exc


def is_git_repo(root: Path) -> bool:
    result = run_git(root, ["rev-parse", "--show-toplevel"], check=False)
    if result.returncode != 0:
        return False
    try:
        top_level = Path(result.stdout.strip()).resolve()
        return top_level == root.resolve()
    except OSError:
        return False


def init_git_repo(root: Path) -> None:
    ensure_git_available()
    root.mkdir(parents=True, exist_ok=True)
    run_git(root, ["init"])


def get_git_status(root: Path) -> GitStatus:
    result = run_git(root, ["status", "--porcelain"])
    raw_wiki_changes: list[str] = []
    other_changes: list[str] = []
    for line in result.stdout.splitlines():
        if not line:
            continue
        path_text = line[3:].replace("\\", "/")
        target = raw_wiki_changes if _is_raw_or_wiki_path(path_text) else other_changes
        target.append(path_text)
    return GitStatus(raw_wiki_changes=raw_wiki_changes, other_changes=other_changes)


def commit_paths(root: Path, paths: list[Path], message: str) -> GitCommitResult:
    if not paths:
        return GitCommitResult(committed=False, message="No paths to commit.")
    relative_paths = [_relative_git_path(root, path) for path in paths if path.exists()]
    if not relative_paths:
        return GitCommitResult(committed=False, message="No existing paths to commit.")
    run_git(root, ["add", *relative_paths])
    staged = run_git(root, ["diff", "--cached", "--quiet"], check=False)
    if staged.returncode == 0:
        return GitCommitResult(committed=False, message="No staged changes.")
    run_git(
        root,
        [
            "-c",
            "user.name=LLM Wiki",
            "-c",
            "user.email=llm-wiki@example.invalid",
            "commit",
            "--no-gpg-sign",
            "-m",
            message,
        ],
    )
    commit_hash = run_git(root, ["rev-parse", "HEAD"]).stdout.strip()
    return GitCommitResult(committed=True, commit_hash=commit_hash, message=message)


def _relative_git_path(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _is_raw_or_wiki_path(path_text: str) -> bool:
    return path_text == "raw" or path_text == "wiki" or path_text.startswith("raw/") or path_text.startswith("wiki/")
