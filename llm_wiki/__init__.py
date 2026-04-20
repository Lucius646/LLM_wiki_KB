from pathlib import Path


_SRC_PACKAGE = Path(__file__).resolve().parent.parent / "src" / "llm_wiki"
if _SRC_PACKAGE.is_dir():
    __path__.append(str(_SRC_PACKAGE))
