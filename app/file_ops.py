from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable


class FileDropError(Exception):
    pass


@dataclass(frozen=True)
class DirEntry:
    name: str
    rel_path: str
    is_dir: bool
    size: str
    modified: str


def normalize_web_path(raw_path: str = "") -> str:
    return raw_path.strip("/")


def ensure_inside_root(root: Path, candidate: Path) -> Path:
    root_resolved = root.resolve()
    candidate_resolved = candidate.resolve()

    if candidate_resolved == root_resolved or root_resolved in candidate_resolved.parents:
        return candidate_resolved

    raise FileDropError("Ruta no permitida: fuera del directorio compartido.")


def resolve_safe_path(root: Path, raw_path: str = "") -> Path:
    clean_path = normalize_web_path(raw_path)

    if Path(clean_path).is_absolute():
        raise FileDropError("Ruta absoluta no permitida.")

    return ensure_inside_root(root, root / clean_path)


def relative_web_path(root: Path, path: Path) -> str:
    safe_path = ensure_inside_root(root, path)
    rel = safe_path.relative_to(root.resolve())
    return "" if str(rel) == "." else rel.as_posix()


def human_size(size_bytes: int) -> str:
    units = ("B", "KB", "MB", "GB", "TB")
    value = float(size_bytes)

    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} B"
            return f"{value:.1f} {unit}"
        value /= 1024

    return f"{size_bytes} B"


def format_mtime(path: Path) -> str:
    modified = datetime.fromtimestamp(path.stat().st_mtime)
    return modified.strftime("%Y-%m-%d %H:%M:%S")


def list_directory(root: Path, raw_path: str = "") -> list[DirEntry]:
    directory = resolve_safe_path(root, raw_path)

    if not directory.exists():
        raise FileDropError("La carpeta solicitada no existe.")
    if not directory.is_dir():
        raise FileDropError("La ruta solicitada no es una carpeta.")

    entries: Iterable[Path] = directory.iterdir()
    sorted_entries = sorted(entries, key=lambda item: (not item.is_dir(), item.name.casefold()))

    result: list[DirEntry] = []
    for item in sorted_entries:
        rel_path = relative_web_path(root, item)
        is_dir = item.is_dir()
        size = "--" if is_dir else human_size(item.stat().st_size)
        result.append(
            DirEntry(
                name=item.name,
                rel_path=rel_path,
                is_dir=is_dir,
                size=size,
                modified=format_mtime(item),
            )
        )

    return result


def parent_web_path(root: Path, raw_path: str = "") -> str | None:
    current = resolve_safe_path(root, raw_path)
    root_resolved = root.resolve()

    if current == root_resolved:
        return None

    return relative_web_path(root, current.parent)


def unique_destination(directory: Path, filename: str) -> Path:
    original = Path(filename).name
    if not original or original in {".", ".."}:
        raise FileDropError("Nombre de archivo inválido.")

    candidate = directory / original
    if not candidate.exists():
        return candidate

    stem = candidate.stem
    suffix = candidate.suffix
    counter = 1

    while True:
        renamed = directory / f"{stem}_{counter}{suffix}"
        if not renamed.exists():
            return renamed
        counter += 1


def delete_path(root: Path, raw_path: str, delete_enabled: bool) -> None:
    if not delete_enabled:
        raise FileDropError("El borrado está deshabilitado por configuración.")

    target = resolve_safe_path(root, raw_path)
    if target == root.resolve():
        raise FileDropError("No se puede borrar el directorio raíz compartido.")
    if not target.exists():
        raise FileDropError("La ruta a borrar no existe.")
    if target.is_dir():
        raise FileDropError("El borrado de carpetas no está permitido. Solo se pueden borrar archivos.")

    target.unlink()
