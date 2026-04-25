from pathlib import Path

from llm_wiki.git import find_latest_managed_commit, get_git_status, is_git_repo, revert_commit
from llm_wiki.models import UndoResult


def undo_last_ingest(root: Path) -> UndoResult:
    if not is_git_repo(root):
        return UndoResult(ok=False, message="Workspace is not a git-backed llm-wiki workspace.")

    status = get_git_status(root)
    if status.dirty:
        return UndoResult(ok=False, message="Undo blocked: workspace has uncommitted changes.")

    commit = find_latest_managed_commit(root, "ingest")
    if commit is None:
        return UndoResult(ok=False, message="No LLM-Wiki ingest commit found to undo.")

    message = "\n\n".join(
        [
            "undo: revert latest llm-wiki ingest",
            f"Reverts: {commit}",
            "LLM-Wiki-Action: undo",
        ]
    )
    result = revert_commit(root, commit, message)
    if not result.committed:
        return UndoResult(ok=False, message=result.message)
    return UndoResult(ok=True, message=f"Reverted ingest commit {commit}.", commit_hash=result.commit_hash)
