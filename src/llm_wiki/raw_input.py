from pathlib import Path
import mimetypes

from llm_wiki.models import RawInput


TEXT_EXTENSIONS = {".md", ".txt", ".html", ".json", ".csv"}
FILE_EXTENSIONS = {".pdf"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}
MIME_FALLBACKS = {
    ".md": "text/markdown",
    ".txt": "text/plain",
    ".html": "text/html",
    ".json": "application/json",
    ".csv": "text/csv",
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}


def build_raw_input(root: Path, raw_path: Path) -> RawInput:
    try:
        relative = raw_path.relative_to(root)
    except ValueError:
        return _error(root, raw_path, "Raw file must be inside the active workspace.")

    if not relative.parts or relative.parts[0] != "raw":
        return _error(root, raw_path, "Raw file must be under raw/.")
    if not raw_path.is_file():
        return _error(root, raw_path, f"Raw file not found: {relative.as_posix()}")

    suffix = raw_path.suffix.lower()
    mime_type = _guess_mime_type(raw_path)
    if suffix in TEXT_EXTENSIONS:
        try:
            text = raw_path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            return _error(root, raw_path, f"Raw text file must be UTF-8: {exc}")
        return RawInput(
            ok=True,
            root=root,
            path=raw_path,
            relative_path=relative.as_posix(),
            mime_type=mime_type,
            kind="text",
            text=text,
        )
    if suffix in FILE_EXTENSIONS:
        return RawInput(
            ok=True,
            root=root,
            path=raw_path,
            relative_path=relative.as_posix(),
            mime_type=mime_type,
            kind="file",
        )
    if suffix in IMAGE_EXTENSIONS:
        return RawInput(
            ok=True,
            root=root,
            path=raw_path,
            relative_path=relative.as_posix(),
            mime_type=mime_type,
            kind="image",
        )

    return _error(root, raw_path, f"Unsupported raw file type: {suffix or '(none)'}")


def _guess_mime_type(path: Path) -> str:
    return mimetypes.guess_type(path.name)[0] or MIME_FALLBACKS.get(path.suffix.lower(), "application/octet-stream")


def _error(root: Path, path: Path, message: str) -> RawInput:
    return RawInput(
        ok=False,
        root=root,
        path=path,
        relative_path="",
        mime_type="",
        kind="unsupported",
        message=message,
    )
