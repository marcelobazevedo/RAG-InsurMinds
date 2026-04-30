import argparse
import shutil
from pathlib import Path

from rag.ingest.truncate_data import truncate_table

PROJECT_ROOT = Path(__file__).resolve().parents[2]

CACHE_DIR_NAMES = {"__pycache__", ".pytest_cache", ".mypy_cache"}
SKIP_DIR_NAMES = {".git", ".venv"}


def remove_local_caches() -> list[Path]:
    removed = []
    for path in PROJECT_ROOT.rglob("*"):
        if not path.is_dir():
            continue
        if any(part in SKIP_DIR_NAMES for part in path.parts):
            continue
        if path.name in CACHE_DIR_NAMES:
            shutil.rmtree(path)
            removed.append(path)
    return removed


def reset_project_state(remove_caches: bool = True) -> None:
    print("[reset] Truncando tabela 'dados'...")
    truncate_table()

    if remove_caches:
        removed_caches = remove_local_caches()
        if removed_caches:
            print("[reset] Caches removidos:")
            for path in removed_caches:
                print(f"  - {path.relative_to(PROJECT_ROOT)}")
        else:
            print("[reset] Nenhum cache local para remover.")

    print("[reset] Projeto resetado com sucesso.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Trunca a base vetorial e remove artefatos regeneráveis do projeto."
    )
    parser.add_argument(
        "--keep-caches",
        action="store_true",
        help="Mantém caches locais como __pycache__ e .pytest_cache.",
    )
    args = parser.parse_args()

    reset_project_state(
        remove_caches=not args.keep_caches,
    )
