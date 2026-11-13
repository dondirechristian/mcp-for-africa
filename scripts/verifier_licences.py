"""Échoue si une dépendance de production est sous licence à réciprocité (copyleft).

Article 6 du règlement CADEV : les composants « à réciprocité (notamment GPL,
AGPL, LGPL) » rendent le projet irrecevable. Par prudence on refuse aussi le
copyleft faible (MPL, EPL, CDDL, EUPL…).

À lancer dans un environnement qui ne contient que requirements.txt :
    python scripts/verifier_licences.py
"""
import json
import re
import subprocess
import sys

A_RECIPROCITE = re.compile(
    r"\b(A?GPL|LGPL|GNU|MPL|Mozilla Public|EPL|Eclipse Public|CDDL|EUPL|OSL|CPL|"
    r"Common Public|CeCILL|SSPL|Sleepycat|copyleft)", re.I)
# Outils de l'environnement de vérification, absents de l'application.
OUTILS = {"pip", "setuptools", "wheel", "pip-licenses", "prettytable", "wcwidth", "tomli"}


def main() -> int:
    sortie = subprocess.run([sys.executable, "-m", "piplicenses", "--from=mixed", "--format=json"],
                            capture_output=True, text=True, check=True).stdout
    paquets = [p for p in json.loads(sortie) if p["Name"].lower() not in OUTILS]
    fautifs = [p for p in paquets if A_RECIPROCITE.search(p["License"])]
    for p in fautifs:
        print(f"REFUSÉ : {p['Name']} {p['Version']} — {p['License']}")
    if not fautifs:
        print(f"Licences : {len(paquets)} dépendances, toutes permissives.")
    return 1 if fautifs else 0


if __name__ == "__main__":
    sys.exit(main())
