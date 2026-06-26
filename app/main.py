import logging
import socket
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import quote

import uvicorn
from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette import status

from .config import get_settings
from .file_ops import (
    FileDropError,
    delete_path,
    list_directory,
    parent_web_path,
    relative_web_path,
    resolve_safe_path,
    unique_destination,
)

BASE_DIR = Path(__file__).resolve().parent
settings = get_settings()


def local_ip_address() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return "no disponible"


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    logging.getLogger("uvicorn.error").info("IP de esta PC: %s", local_ip_address())
    yield


app = FastAPI(title="Local CRT FileDrop", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


def browse_url(raw_path: str = "", message: str | None = None, error: str | None = None) -> str:
    clean_path = raw_path.strip("/")
    base = "/" if not clean_path else f"/browse/{quote(clean_path, safe='/')}"
    params = []
    if message:
        params.append(f"message={quote(message)}")
    if error:
        params.append(f"error={quote(error)}")
    return f"{base}?{'&'.join(params)}" if params else base


def action_url(prefix: str, raw_path: str = "") -> str:
    clean_path = raw_path.strip("/")
    return f"/{prefix}" if not clean_path else f"/{prefix}/{quote(clean_path, safe='/')}"


def render_index(request: Request, raw_path: str = ""):
    try:
        entries = list_directory(settings.shared_root, raw_path)
        current_path = relative_web_path(settings.shared_root, resolve_safe_path(settings.shared_root, raw_path))
        parent_path = parent_web_path(settings.shared_root, raw_path)
        error = request.query_params.get("error")
    except FileDropError as exc:
        entries = []
        current_path = ""
        parent_path = None
        error = str(exc)

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "title": "TRANFERSISTEM",
            "entries": entries,
            "current_path": current_path,
            "parent_path": parent_path,
            "message": request.query_params.get("message"),
            "error": error,
            "delete_enabled": settings.delete_enabled,
            "max_upload_size_mb": settings.max_upload_size_mb,
            "browse_url": browse_url,
            "download_url": lambda path: action_url("download", path),
            "upload_url": lambda path: action_url("upload", path),
            "delete_url": lambda path: action_url("delete", path),
        },
    )


@app.get("/")
async def index(request: Request):
    return render_index(request)


@app.get("/browse")
@app.get("/browse/{path:path}")
async def browse(request: Request, path: str = ""):
    return render_index(request, path)


@app.get("/download/{path:path}")
async def download(path: str):
    try:
        target = resolve_safe_path(settings.shared_root, path)
        if not target.exists() or not target.is_file():
            raise FileDropError("El archivo solicitado no existe.")
    except FileDropError as exc:
        return RedirectResponse(browse_url(error=str(exc)), status_code=status.HTTP_303_SEE_OTHER)

    return FileResponse(target, filename=target.name)


@app.post("/upload")
@app.post("/upload/{path:path}")
async def upload(file: UploadFile = File(...), path: str = ""):
    try:
        directory = resolve_safe_path(settings.shared_root, path)
        if not directory.is_dir():
            raise FileDropError("La ruta actual no es una carpeta.")

        destination = unique_destination(directory, file.filename or "")
        bytes_written = 0

        with destination.open("wb") as output:
            while chunk := await file.read(1024 * 1024):
                bytes_written += len(chunk)
                if bytes_written > settings.max_upload_size_bytes:
                    output.close()
                    destination.unlink(missing_ok=True)
                    raise FileDropError(f"El archivo supera el límite de {settings.max_upload_size_mb} MB.")
                output.write(chunk)

        message = f"Archivo subido como {destination.name}."
        return RedirectResponse(browse_url(path, message=message), status_code=status.HTTP_303_SEE_OTHER)
    except FileDropError as exc:
        return RedirectResponse(browse_url(path, error=str(exc)), status_code=status.HTTP_303_SEE_OTHER)
    finally:
        await file.close()


@app.post("/delete/{path:path}")
async def delete(path: str):
    try:
        parent = parent_web_path(settings.shared_root, path) or ""
        delete_path(settings.shared_root, path, settings.delete_enabled)
        return RedirectResponse(browse_url(parent, message="Elemento borrado."), status_code=status.HTTP_303_SEE_OTHER)
    except FileDropError as exc:
        return RedirectResponse(browse_url(error=str(exc)), status_code=status.HTTP_303_SEE_OTHER)


if __name__ == "__main__":
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=True)
