"""Cross-platform first-run launcher for macOS, Windows and Linux."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
REQUIREMENTS = ROOT / "requirements-lock.txt"
STAMP = VENV / ".materia-requirements.sha256"


def _venv_python() -> Path:
    return VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _requirements_digest() -> str:
    return hashlib.sha256(REQUIREMENTS.read_bytes()).hexdigest()


def _run(command: list[str]) -> None:
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> int:
    if not (3, 11) <= sys.version_info[:2] <= (3, 13):
        print("Materia nécessite Python 3.11, 3.12 ou 3.13.")
        print("Téléchargement : https://www.python.org/downloads/")
        return 2

    if not REQUIREMENTS.exists():
        print("Le fichier requirements-lock.txt est introuvable.")
        return 2

    python = _venv_python()
    if not python.exists():
        print("Création de l'environnement Materia…")
        _run([sys.executable, "-m", "venv", str(VENV)])

    digest = _requirements_digest()
    installed = STAMP.read_text(encoding="utf-8").strip() if STAMP.exists() else ""
    if installed != digest:
        print("Installation ou mise à jour des composants…")
        _run([str(python), "-m", "pip", "install", "--upgrade", "pip"])
        _run([str(python), "-m", "pip", "install", "-r", str(REQUIREMENTS)])
        STAMP.write_text(digest, encoding="utf-8")

    env = os.environ.copy()
    env.setdefault("MATERIA_HOST", "127.0.0.1")
    env.setdefault("MATERIA_PORT", "8087")
    env.setdefault("MATERIA_SHOW_BROWSER", "1")
    print(f"Materia démarre sur http://{env['MATERIA_HOST']}:{env['MATERIA_PORT']}")
    print("Fermez cette fenêtre ou utilisez Ctrl+C pour arrêter le logiciel.")
    return subprocess.call([str(python), str(ROOT / "main.py")], cwd=ROOT, env=env)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print(f"L'installation a échoué (code {exc.returncode}).")
        print("Vérifiez votre connexion Internet puis relancez Materia.")
        raise SystemExit(exc.returncode)
