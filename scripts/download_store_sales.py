from __future__ import annotations

import argparse
import os
from pathlib import Path
from zipfile import ZipFile

COMPETITION = "store-sales-time-series-forecasting"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "raw"
REQUIRED_FILES = ("train.csv", "stores.csv")
EXPECTED_FILES = (
    "train.csv",
    "test.csv",
    "stores.csv",
    "transactions.csv",
    "oil.csv",
    "holidays_events.csv",
    "sample_submission.csv",
)


def main() -> None:
    args = _parse_args()
    _load_dotenv(args.env_file)

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    _assert_credentials_available()

    from kaggle.api.kaggle_api_extended import KaggleApi

    api = KaggleApi()
    api.authenticate()
    api.competition_download_files(
        COMPETITION,
        path=output_dir,
        force=args.force,
        quiet=False,
    )

    _extract_archives(output_dir)
    _assert_required_files(output_dir)

    print(f"Dados reais extraidos em: {output_dir}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Baixa os dados reais da competição Kaggle Store Sales."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Pasta onde os CSVs serão salvos. Padrão: data/raw.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Baixa novamente mesmo se os arquivos já existirem.",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=PROJECT_ROOT / ".env",
        help="Arquivo .env com KAGGLE_API_TOKEN. Padrão: .env na raiz do projeto.",
    )
    return parser.parse_args()


def _load_dotenv(env_file: Path) -> None:
    if not env_file.exists():
        return

    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        if key.startswith("export "):
            key = key.removeprefix("export ").strip()

        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _assert_credentials_available() -> None:
    if os.getenv("KAGGLE_API_TOKEN"):
        return
    if os.getenv("KAGGLE_USERNAME") and os.getenv("KAGGLE_KEY"):
        return

    kaggle_home = Path.home() / ".kaggle"
    credential_paths = (
        kaggle_home / "access_token",
        kaggle_home / "access_token.txt",
        kaggle_home / "kaggle.json",
    )
    if any(path.exists() for path in credential_paths):
        return

    raise SystemExit(
        "Credencial Kaggle não encontrada. Configure KAGGLE_API_TOKEN ou crie "
        "~/.kaggle/access_token antes de executar este script."
    )


def _extract_archives(output_dir: Path) -> None:
    for archive in output_dir.glob("*.zip"):
        with ZipFile(archive) as zipped:
            zipped.extractall(output_dir)
        archive.unlink()


def _assert_required_files(output_dir: Path) -> None:
    missing = [filename for filename in REQUIRED_FILES if not (output_dir / filename).exists()]
    if missing:
        missing_text = ", ".join(missing)
        raise SystemExit(f"Download incompleto. Arquivos obrigatórios ausentes: {missing_text}")

    available = [filename for filename in EXPECTED_FILES if (output_dir / filename).exists()]
    print("Arquivos disponíveis:")
    for filename in available:
        print(f"- {filename}")


if __name__ == "__main__":
    main()
