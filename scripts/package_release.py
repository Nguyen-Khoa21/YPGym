"""Package Git-managed source and non-ignored additions; exclude private runtime data."""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import zipfile


EXCLUDED_PARTS = {
    ".git", "tmp", "node_modules", "__pycache__", ".pytest_cache", ".mypy_cache",
    ".ruff_cache", ".expo", ".vite", ".venv", "venv", "env", "dist", "build",
    "coverage", "htmlcov", "storage", "uploads", "generated", "data", "logs",
    "maildir", "mongo-data", "redis-data", "postgres_data", "redis_data",
}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".db", ".sqlite", ".sqlite3", ".pem", ".key", ".crt", ".log"}


def is_release_source(name: str) -> bool:
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or {part.lower() for part in path.parts} & EXCLUDED_PARTS:
        return False
    if path.name.startswith(".env") and path.name != ".env.example":
        return False
    return path.suffix.lower() not in EXCLUDED_SUFFIXES and not path.name.startswith(("~$", "celerybeat-schedule"))


def write_archive(root: Path, names: list[str], output: Path, revision: str) -> dict:
    root = root.resolve()
    included = sorted(set(name for name in names if is_release_source(name)
                          and (root / name).resolve().is_relative_to(root) and (root / name).is_file()))
    manifest = {"base_commit": revision, "files": []}
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name in included:
            content = (root / name).read_bytes()
            archive.writestr(name, content)
            manifest["files"].append({"path": name, "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()})
        archive.writestr("ARCHIVE-CONTENTS.json", json.dumps(manifest, indent=2))
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None:
            raise RuntimeError("Archive integrity check failed")
    return {
        "archive": str(output), "base_commit": revision, "file_count": len(included),
        "archive_bytes": output.stat().st_size, "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "excluded_candidates": sorted(set(names) - set(included)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path, help="New ZIP path outside the repository")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = args.output.resolve()
    if output.is_relative_to(root) or output.exists() or output.with_suffix(".inventory.json").exists():
        parser.error("Choose a new output path outside the repository")
    names = subprocess.check_output(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=root).decode("utf-8").split("\0")
    names = [name for name in names if name]
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    inventory = write_archive(root, names, output, revision)
    output.with_suffix(".inventory.json").write_text(json.dumps(inventory, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in inventory.items() if key != "excluded_candidates"}, indent=2))


if __name__ == "__main__":
    main()
