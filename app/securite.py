"""Mots de passe, jeton CSRF, limitation des tentatives de connexion."""
import base64
import hashlib
import hmac
import secrets
import time
from collections import defaultdict, deque

_N, _R, _P = 2**14, 8, 1


def hacher(mdp: str) -> str:
    sel = secrets.token_bytes(16)
    h = hashlib.scrypt(mdp.encode(), salt=sel, n=_N, r=_R, p=_P, dklen=32)
    return "scrypt${}${}".format(base64.b64encode(sel).decode(), base64.b64encode(h).decode())


def verifier(mdp: str, stocke: str) -> bool:
    try:
        algo, sel, h = stocke.split("$")
        if algo != "scrypt":
            return False
        calcule = hashlib.scrypt(mdp.encode(), salt=base64.b64decode(sel), n=_N, r=_R, p=_P, dklen=32)
        return hmac.compare_digest(calcule, base64.b64decode(h))
    except (ValueError, TypeError):
        return False


def jeton_csrf(session: dict) -> str:
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(24)
    return session["csrf"]


def csrf_valide(session: dict, recu: str | None) -> bool:
    attendu = session.get("csrf")
    return bool(attendu and recu and hmac.compare_digest(attendu, recu))


class Limiteur:
    """Fenêtre glissante en mémoire : suffisant pour une instance unique."""

    def __init__(self, maximum: int, fenetre_s: int):
        self.maximum, self.fenetre = maximum, fenetre_s
        self._traces: dict[str, deque] = defaultdict(deque)

    def autorise(self, cle: str) -> bool:
        t = time.monotonic()
        q = self._traces[cle]
        while q and t - q[0] > self.fenetre:
            q.popleft()
        if len(q) >= self.maximum:
            return False
        q.append(t)
        return True
