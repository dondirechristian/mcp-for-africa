"""Échoue si une dépendance installée est sous GPL, AGPL ou LGPL (article 6 du règlement CADEV).

    python scripts/verifier_licences.py
"""
import json
import re
import subprocess
import sys

INTERDITES = re.compile(r"\b(A?GPL|LGPL|GNU (Affero |Lesser )?General Public)", re.I)
# Paquets d'outillage absents de l'image de production.
IGNORES = {"pip", "setuptools", "wheel", "pip-licenses", "prettytable", "wcwidth",
           "pytest", "iniconfig", "pluggy", "pygments", "colorama"}


def main() -> int:
    sortie = subprocess.run([sys.executable, "-m", "piplicenses", "--from=mixed", "--format=json"],
                            capture_output=True, text=True, check=True).stdout
    fautifs = [p for p in json.loads(sortie)
               if p["Name"].lower() not in IGNORES and INTERDITES.search(p["License"])]
    for p in fautifs:
        print(f"INTERDIT : {p['Name']} {p['Version']} — {p['License']}")
    if not fautifs:
        print("Licences : aucune dépendance GPL, AGPL ou LGPL.")
    return 1 if fautifs else 0


if __name__ == "__main__":
    sys.exit(main())
