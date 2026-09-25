from pathlib import Path
from app.models import RepositoryFile

SUPPORTED_EXTENSIONS = {
    ".py": "python",
    ".java": "java",
    ".cpp": "cpp",
    ".c": "c",
    ".h": "c",
    ".hpp": "cpp",
    ".js": "javascript",
    ".ts": "typescript",
}

# Skip generated, dependency, and version-control directories during scanning.
IGNORED_DIRECTORIES = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "node_modules",
}

def load_repository(repo_path: str):
    repo = Path(repo_path)

    files = []

    # recursively walks through everything inside the repository
    for path in repo.rglob("*"):
        # Only index source files that are directly supported by the loader.
        if not path.is_file():
            continue

        if any(part in IGNORED_DIRECTORIES for part in path.parts):
            continue

        if path.suffix not in SUPPORTED_EXTENSIONS:
            continue

        content = path.read_text(
            encoding="utf-8",
            errors="ignore"
        )

        # Store paths relative to the repository so records remain portable.
        files.append(
            RepositoryFile(
                path=str(path.relative_to(repo)),
                language=SUPPORTED_EXTENSIONS[path.suffix],
                content=content
            )
        )

    return files