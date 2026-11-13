"""Modèles et accès à la base (PostgreSQL en production, SQLite en local)."""
import os
from datetime import datetime, timezone

from sqlalchemy import (Boolean, DateTime, ForeignKey, Integer, String, Text,
                        UniqueConstraint, create_engine)
from sqlalchemy.orm import (DeclarativeBase, Mapped, Session, mapped_column,
                            relationship, sessionmaker)


def maintenant() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def url_base() -> str:
    url = os.environ.get("DATABASE_URL", "sqlite:///./mcp_for_africa.db")
    # Les hébergeurs donnent souvent postgres:// ou postgresql:// ; on impose
    # le pilote pg8000 (licence BSD) : psycopg est sous LGPL, refusé par la CADEV.
    for prefixe in ("postgres://", "postgresql://"):
        if url.startswith(prefixe):
            url = "postgresql+pg8000://" + url[len(prefixe):]
    return url


def _creer_moteur(url: str):
    if url.startswith("sqlite"):
        return create_engine(url, connect_args={"check_same_thread": False})
    args = {}
    if os.environ.get("DATABASE_SSL", "").lower() in ("1", "true", "oui", "require"):
        import ssl
        contexte = ssl.create_default_context()
        if os.environ.get("DATABASE_SSL_VERIFY", "1") in ("0", "false", "non"):
            contexte.check_hostname = False
            contexte.verify_mode = ssl.CERT_NONE
        args["ssl_context"] = contexte
    return create_engine(url, pool_pre_ping=True, pool_recycle=1800, connect_args=args)


moteur = _creer_moteur(url_base())
FabriqueSession = sessionmaker(bind=moteur, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Dev(Base):
    __tablename__ = "devs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pseudo: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(200), unique=True)
    mdp: Mapped[str] = mapped_column(String(300))
    pays: Mapped[str] = mapped_column(String(2), default="")
    bio: Mapped[str] = mapped_column(Text, default="")
    github: Mapped[str] = mapped_column(String(80), default="")
    cree_le: Mapped[datetime] = mapped_column(DateTime, default=maintenant)


class Connecteur(Base):
    __tablename__ = "connecteurs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    nom: Mapped[str] = mapped_column(String(80))
    resume: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    installation: Mapped[str] = mapped_column(Text, default="")
    categorie: Mapped[str] = mapped_column(String(40), index=True)
    type: Mapped[str] = mapped_column(String(40))
    langage: Mapped[str] = mapped_column(String(40), default="")
    # Codes pays encadrés de virgules (",BF,CI,") : filtre simple par LIKE.
    pays: Mapped[str] = mapped_column(String(400), default="")
    service: Mapped[str] = mapped_column(String(120), default="")
    depot_url: Mapped[str] = mapped_column(String(300), default="")
    doc_url: Mapped[str] = mapped_column(String(300), default="")
    auteur_id: Mapped[int] = mapped_column(ForeignKey("devs.id"))
    cree_le: Mapped[datetime] = mapped_column(DateTime, default=maintenant)
    modifie_le: Mapped[datetime] = mapped_column(DateTime, default=maintenant)
    # Relevé automatique du dépôt GitHub.
    gh_licence: Mapped[str] = mapped_column(String(60), default="")
    gh_etoiles: Mapped[int] = mapped_column(Integer, default=0)
    gh_dernier_push: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    gh_ci: Mapped[str] = mapped_column(String(20), default="")
    gh_archive: Mapped[bool] = mapped_column(Boolean, default=False)
    gh_verifie_le: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    gh_erreur: Mapped[str] = mapped_column(String(200), default="")

    auteur: Mapped[Dev] = relationship()

    @property
    def codes_pays(self) -> list[str]:
        return [c for c in self.pays.strip(",").split(",") if c]


class Essai(Base):
    """« Je l'ai essayé » : le témoignage d'un dev, dans son pays, à une date."""
    __tablename__ = "essais"
    __table_args__ = (UniqueConstraint("connecteur_id", "dev_id"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    connecteur_id: Mapped[int] = mapped_column(ForeignKey("connecteurs.id", ondelete="CASCADE"), index=True)
    dev_id: Mapped[int] = mapped_column(ForeignKey("devs.id"))
    marche: Mapped[bool] = mapped_column(Boolean)
    pays: Mapped[str] = mapped_column(String(2), default="")
    note: Mapped[str] = mapped_column(String(500), default="")
    le: Mapped[datetime] = mapped_column(DateTime, default=maintenant)

    dev: Mapped[Dev] = relationship()
    connecteur: Mapped[Connecteur] = relationship()


class Contributeur(Base):
    __tablename__ = "contributeurs"
    __table_args__ = (UniqueConstraint("connecteur_id", "dev_id"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    connecteur_id: Mapped[int] = mapped_column(ForeignKey("connecteurs.id", ondelete="CASCADE"), index=True)
    dev_id: Mapped[int] = mapped_column(ForeignKey("devs.id"))
    role: Mapped[str] = mapped_column(String(200), default="")
    le: Mapped[datetime] = mapped_column(DateTime, default=maintenant)

    dev: Mapped[Dev] = relationship()


class Demande(Base):
    __tablename__ = "demandes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    titre: Mapped[str] = mapped_column(String(140))
    description: Mapped[str] = mapped_column(Text, default="")
    categorie: Mapped[str] = mapped_column(String(40))
    pays: Mapped[str] = mapped_column(String(400), default="")
    auteur_id: Mapped[int] = mapped_column(ForeignKey("devs.id"))
    statut: Mapped[str] = mapped_column(String(20), default="ouverte")  # ouverte | en-cours | resolue
    preneur_id: Mapped[int | None] = mapped_column(ForeignKey("devs.id"), nullable=True)
    connecteur_id: Mapped[int | None] = mapped_column(ForeignKey("connecteurs.id", ondelete="SET NULL"), nullable=True)
    cree_le: Mapped[datetime] = mapped_column(DateTime, default=maintenant)

    auteur: Mapped[Dev] = relationship(foreign_keys=[auteur_id])
    preneur: Mapped[Dev | None] = relationship(foreign_keys=[preneur_id])
    connecteur: Mapped[Connecteur | None] = relationship()

    @property
    def codes_pays(self) -> list[str]:
        return [c for c in self.pays.strip(",").split(",") if c]


class Soutien(Base):
    """« Moi aussi j'en ai besoin » sur une demande."""
    __tablename__ = "soutiens"
    __table_args__ = (UniqueConstraint("demande_id", "dev_id"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    demande_id: Mapped[int] = mapped_column(ForeignKey("demandes.id", ondelete="CASCADE"), index=True)
    dev_id: Mapped[int] = mapped_column(ForeignKey("devs.id"))
    le: Mapped[datetime] = mapped_column(DateTime, default=maintenant)


class Message(Base):
    """Fil de discussion sous un connecteur ou une demande."""
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cible: Mapped[str] = mapped_column(String(12), index=True)  # connecteur | demande
    cible_id: Mapped[int] = mapped_column(Integer, index=True)
    dev_id: Mapped[int] = mapped_column(ForeignKey("devs.id"))
    texte: Mapped[str] = mapped_column(Text)
    le: Mapped[datetime] = mapped_column(DateTime, default=maintenant)

    dev: Mapped[Dev] = relationship()


def creer_tables() -> None:
    Base.metadata.create_all(moteur)


def session() -> Session:
    return FabriqueSession()
