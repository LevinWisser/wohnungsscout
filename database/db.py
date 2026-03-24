import sqlite3
import os
from config import DB_PATH


def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db():
    """Erstellt die Datenbanktabelle falls sie noch nicht existiert."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS inserate (
                id TEXT PRIMARY KEY,
                titel TEXT,
                preis TEXT,
                ort TEXT,
                groesse TEXT,
                zimmer TEXT,
                url TEXT,
                plattform TEXT,
                gefunden_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


def ist_neu(inserat_id: str) -> bool:
    """Gibt True zurück wenn das Inserat noch nicht in der Datenbank ist."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM inserate WHERE id = ?", (inserat_id,)
        ).fetchone()
        return row is None


def speichere_inserat(inserat: dict):
    """Speichert ein neues Inserat in der Datenbank."""
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO inserate (id, titel, preis, ort, groesse, zimmer, url, plattform)
            VALUES (:id, :titel, :preis, :ort, :groesse, :zimmer, :url, :plattform)
            """,
            inserat,
        )
        conn.commit()


def alle_inserate() -> list:
    """Gibt alle gespeicherten Inserate zurück."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM inserate ORDER BY gefunden_am DESC"
        ).fetchall()
        return rows
