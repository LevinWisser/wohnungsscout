"""
Wohnungsscout – Hauptskript
Wird vom Cron Job auf dem Raspberry Pi alle 30 Minuten aufgerufen.
"""

import sys
import os
from datetime import datetime

# Projektverzeichnis zum Python-Pfad hinzufügen (wichtig für Cron auf dem Pi)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.db import init_db, ist_neu, speichere_inserat
from scraper.kleinanzeigen import suche_inserate
from notifier.email_notifier import sende_benachrichtigung


def main():
    zeitstempel = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n[{zeitstempel}] Wohnungsscout startet...")

    # Datenbank initialisieren (erstellt Tabelle falls nötig)
    init_db()

    # Inserate von Kleinanzeigen.de holen
    print("Suche auf Kleinanzeigen.de...")
    gefundene_inserate = suche_inserate()
    print(f"Gesamt gefunden: {len(gefundene_inserate)} passende Inserate")

    # Nur wirklich neue Inserate herausfiltern
    neue_inserate = []
    for inserat in gefundene_inserate:
        if ist_neu(inserat["id"]):
            neue_inserate.append(inserat)
            speichere_inserat(inserat)

    print(f"Davon neu: {len(neue_inserate)}")

    # Benachrichtigung senden wenn es neue gibt
    if neue_inserate:
        print("Sende E-Mail-Benachrichtigung...")
        sende_benachrichtigung(neue_inserate)
    else:
        print("Keine neuen Inserate – keine Benachrichtigung nötig.")

    print("Fertig.")


if __name__ == "__main__":
    main()
