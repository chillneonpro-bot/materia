#!/bin/zsh
set -e
cd -- "$(dirname -- "$0")"

for candidate in python3.13 python3.12 python3.11 python3; do
  if command -v "$candidate" >/dev/null 2>&1; then
    if "$candidate" -c 'import sys; raise SystemExit(not ((3, 11) <= sys.version_info[:2] <= (3, 13)))' >/dev/null 2>&1; then
      exec "$candidate" launcher.py
    fi
  fi
done

echo "Python 3.11, 3.12 ou 3.13 est nécessaire."
echo "Installez-le depuis https://www.python.org/downloads/ puis relancez ce fichier."
read "?Appuyez sur Entrée pour fermer."
exit 1
