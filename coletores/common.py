from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import BinaryIO
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


USER_AGENT = "Dados-ANAC-Dashboard/1.0 (+https://github.com/EdsonCesariUnivesp/Dados_ANAC)"


@dataclass(frozen=True)
class DownloadMetadata:
    source_url: str
    collected_at_utc: str
    sha256: str
    size_bytes: int
    status: str


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _copy_response(response: BinaryIO, destination: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with destination.open("wb") as output:
        while chunk := response.read(1024 * 1024):
            output.write(chunk)
            digest.update(chunk)
            size += len(chunk)
        output.flush()
        os.fsync(output.fileno())
    return digest.hexdigest(), size


def download_file(
    *,
    url: str,
    destination: Path,
    allowed_url_prefix: str,
    force: bool = False,
    retries: int = 4,
    timeout_seconds: int = 90,
) -> DownloadMetadata:
    """Baixa um arquivo de modo atômico e registra sua proveniência.

    O destino é decidido pelo coletor, nunca por conteúdo retornado pela origem.
    """
    if not url.startswith(allowed_url_prefix):
        raise ValueError("URL fora da origem permitida.")

    destination = destination.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    metadata_path = destination.with_suffix(destination.suffix + ".metadata.json")

    if destination.is_file() and metadata_path.is_file() and not force:
        stored = json.loads(metadata_path.read_text(encoding="utf-8"))
        current_hash = sha256_file(destination)
        if current_hash == stored.get("sha256"):
            return DownloadMetadata(**{**stored, "status": "unchanged"})

    temporary = destination.with_suffix(destination.suffix + ".part")
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/csv,*/*;q=0.8"})
    last_error: Exception | None = None

    for attempt in range(retries):
        try:
            with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310 - allowlist acima
                digest, size = _copy_response(response, temporary)
            if size == 0:
                raise ValueError("A origem retornou um arquivo vazio.")
            temporary.replace(destination)
            metadata = DownloadMetadata(
                source_url=url,
                collected_at_utc=datetime.now(UTC).isoformat(),
                sha256=digest,
                size_bytes=size,
                status="downloaded",
            )
            metadata_path.write_text(
                json.dumps(asdict(metadata), ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            return metadata
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
            last_error = exc
            temporary.unlink(missing_ok=True)
            if attempt + 1 < retries:
                time.sleep(min(2**attempt, 30))

    raise RuntimeError(f"Falha ao baixar {url}: {last_error}") from last_error
