"""Entrega de archivos pensada para PDF grandes.

- Acepta peticiones por rangos (Range): el visor del navegador muestra la primera
  página sin esperar a descargar todo el archivo.
- ETag y caché privada: al volver a abrir el mismo archivo el navegador no lo descarga de nuevo.
"""

import os
import re

from django.http import FileResponse, HttpResponse, StreamingHttpResponse

RANGE_RE = re.compile(r"bytes=(\d*)-(\d*)$")
CHUNK = 256 * 1024


def _etag(artifact, size):
    return f'"{artifact.pk}-{size}-{int(artifact.updated_at.timestamp()) if artifact.updated_at else 0}"'


def _read_range(handle, start, length):
    handle.seek(start)
    remaining = length
    try:
        while remaining > 0:
            data = handle.read(min(CHUNK, remaining))
            if not data:
                break
            remaining -= len(data)
            yield data
    finally:
        handle.close()


def serve_artifact(request, artifact, content_type, inline=True):
    size = artifact.file.size
    etag = _etag(artifact, size)
    disposition = "inline" if inline else "attachment"
    filename = os.path.basename(artifact.original_name or "archivo")
    headers = {
        "ETag": etag,
        "Accept-Ranges": "bytes",
        "Cache-Control": "private, max-age=3600",
        "Content-Disposition": f'{disposition}; filename="{filename}"',
    }

    if request.headers.get("If-None-Match") == etag:
        response = HttpResponse(status=304)
        for key in ("ETag", "Cache-Control"):
            response[key] = headers[key]
        return response

    match = RANGE_RE.match(request.headers.get("Range", "").strip())
    if match and size:
        first, last = match.groups()
        if first == "":
            start = max(0, size - int(last or 0))
            end = size - 1
        else:
            start = int(first)
            end = min(int(last), size - 1) if last else size - 1
        if start >= size or start > end:
            response = HttpResponse(status=416)
            response["Content-Range"] = f"bytes */{size}"
            return response
        length = end - start + 1
        response = StreamingHttpResponse(
            _read_range(artifact.file.open("rb"), start, length), status=206, content_type=content_type
        )
        response["Content-Length"] = str(length)
        response["Content-Range"] = f"bytes {start}-{end}/{size}"
        for key, value in headers.items():
            response[key] = value
        return response

    response = FileResponse(artifact.file.open("rb"), content_type=content_type, as_attachment=not inline, filename=filename)
    for key, value in headers.items():
        response[key] = value
    return response
