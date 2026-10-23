from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import unicodedata
from datetime import UTC, datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REQUIRED_COLUMNS = {
    "empresa_sigla",
    "ano",
    "mes",
    "aeroporto_de_origem_sigla",
    "aeroporto_de_destino_sigla",
    "natureza",
    "grupo_de_voo",
    "passageiros_pagos",
    "passageiros_gratis",
    "decolagens",
    "assentos",
}


def canonical_header(value: str) -> str:
    text = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
    return text


def _detect_encoding(path: Path) -> str:
    sample = path.read_bytes()[:65536]
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            sample.decode(encoding)
            return encoding
        except UnicodeDecodeError:
            continue
    raise ValueError("Encoding não reconhecido para o arquivo estatístico.")


def normalize_statistics(source: Path, destination: Path) -> dict[str, object]:
    source = source.resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    destination = destination.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    encoding = _detect_encoding(source)
    digest = hashlib.sha256()
    row_count = 0

    with source.open("rb") as raw:
        for chunk in iter(lambda: raw.read(1024 * 1024), b""):
            digest.update(chunk)

    with source.open("r", encoding=encoding, newline="") as input_file:
        reader = csv.DictReader(input_file, delimiter=";")
        if not reader.fieldnames:
            raise ValueError("CSV sem cabeçalho.")
        mapping = {name: canonical_header(name) for name in reader.fieldnames}
        missing = REQUIRED_COLUMNS - set(mapping.values())
        if missing:
            raise ValueError(f"Schema incompatível; colunas ausentes: {sorted(missing)}")
        source_by_target = {target: source_name for source_name, target in mapping.items()}
        with temporary.open("w", encoding="utf-8", newline="") as output_file:
            writer = csv.DictWriter(output_file, fieldnames=sorted(REQUIRED_COLUMNS))
            writer.writeheader()
            for row in reader:
                writer.writerow({target: row.get(source_by_target[target], "") for target in sorted(REQUIRED_COLUMNS)})
                row_count += 1
            output_file.flush()
            os.fsync(output_file.fileno())
    temporary.replace(destination)
    metadata = {
        "imported_at_utc": datetime.now(UTC).isoformat(),
        "source_sha256": digest.hexdigest(),
        "source_size_bytes": source.stat().st_size,
        "rows": row_count,
        "encoding": encoding,
        "provenance": "Arquivo oficial ANAC fornecido localmente; URL não inferida.",
    }
    destination.with_suffix(destination.suffix + ".metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return metadata


def main() -> int:
    parser = argparse.ArgumentParser(description="Importa o CSV oficial de Dados Estatísticos da ANAC.")
    parser.add_argument("--source-file", type=Path, required=True)
    parser.add_argument(
        "--output-file",
        type=Path,
        default=PROJECT_ROOT / "data" / "staging" / "anac_statistics.csv",
    )
    args = parser.parse_args()
    print(json.dumps(normalize_statistics(args.source_file, args.output_file), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
