# Wohnungsscout – Dokumentation

## Was ist das?

Wohnungsscout ist ein automatischer Immobilien-Beobachter für die Region **Diez und Umgebung** (Görgeshausen, Nentershausen, Hambach, Aull). Das Script durchsucht Wohnungsplattformen nach passenden Inseraten, filtert nach konfigurierten Kriterien und schickt eine E-Mail-Benachrichtigung wenn neue Inserate auftauchen.

Das Ziel: Immer informiert sein ohne täglich selbst suchen zu müssen – ideal für eine mittel- bis langfristige Wohnungssuche in einer Region mit überschaubarem Angebot.

Das Script läuft auf einem **Raspberry Pi** und wird dort über einen **Cron Job alle 30 Minuten** automatisch ausgeführt.

---

## Projektstruktur

```
wohnungsscout/
├── main.py                   # Einstiegspunkt – wird vom Cron Job aufgerufen
├── config.py                 # Alle Einstellungen (Suchgebiet, Filter, E-Mail)
├── requirements.txt          # Python-Abhängigkeiten
├── documentation.md          # Diese Datei
│
├── scraper/
│   ├── __init__.py
│   └── kleinanzeigen.py      # Scraper für kleinanzeigen.de
│
├── notifier/
│   ├── __init__.py
│   └── email_notifier.py     # E-Mail-Benachrichtigung via Gmail SMTP
│
├── database/
│   ├── __init__.py
│   └── db.py                 # SQLite-Datenbank (speichert gesehene Inserate)
│
└── data/
    └── inserate.db           # Wird automatisch erstellt (nicht ins Git!)
```

---

## Wie es funktioniert (Ablauf)

1. `main.py` wird aufgerufen (manuell oder per Cron Job)
2. Die SQLite-Datenbank wird initialisiert (beim ersten Start automatisch erstellt)
3. `kleinanzeigen.py` baut für jeden konfigurierten Ort eine Such-URL und ruft die Seite ab
4. Der HTML-Inhalt wird mit BeautifulSoup geparst – Titel, Preis, Zimmer, Größe, URL werden extrahiert
5. Inserate die nicht den Filtern entsprechen (zu wenig Zimmer, zu klein) werden aussortiert
6. Jedes verbleibende Inserat wird mit der Datenbank abgeglichen: Ist die ID schon bekannt?
7. Nur **neue** Inserate werden in der Datenbank gespeichert
8. Gibt es neue Inserate, wird eine **HTML-E-Mail** an die konfigurierte Adresse geschickt
9. Gibt es nichts Neues, passiert nichts – kein Spam

---

## Einrichtung

### 1. Abhängigkeiten installieren

```bash
pip install -r requirements.txt
```

### 2. config.py anpassen

Die wichtigsten Einstellungen:

| Variable | Bedeutung | Standard |
|---|---|---|
| `SEARCH_LOCATIONS` | Orte die durchsucht werden | Diez + 4 Umgebungsorte |
| `MIN_ROOMS` | Mindestanzahl Zimmer | 3 |
| `MIN_SIZE_SQM` | Mindestfläche in m² | 60 |
| `MAX_RENT_EUR` | Maximale Miete (0 = aus) | 0 |
| `EMAIL_PASSWORD` | Gmail App-Passwort | leer – muss gesetzt werden! |

### 3. Gmail App-Passwort einrichten

Da Gmail normale Passwörter für externe Scripts nicht erlaubt, braucht man ein **App-Passwort**:

1. Google-Konto → Sicherheit → 2-Faktor-Authentifizierung aktivieren (falls noch nicht)
2. Google-Konto → Sicherheit → App-Passwörter → Neues App-Passwort erstellen
3. Das generierte 16-stellige Passwort in `config.py` bei `EMAIL_PASSWORD` eintragen

### 4. Test-Lauf

```bash
python main.py
```

---

## Raspberry Pi – Einrichtung

### Dateien übertragen

```bash
# Vom PC aus (SCP):
scp -r wohnungsscout/ pi@<IP-DES-PI>:~/wohnungsscout/

# Oder per Git (empfohlen):
git clone <repo-url> ~/wohnungsscout
```

### Python-Abhängigkeiten auf dem Pi installieren

```bash
cd ~/wohnungsscout
pip3 install -r requirements.txt
```

### Cron Job einrichten (alle 30 Minuten)

```bash
crontab -e
```

Folgende Zeile einfügen:

```
*/30 * * * * cd /home/pi/wohnungsscout && python3 main.py >> logs/wohnungsscout.log 2>&1
```

Das Logs-Verzeichnis vorher anlegen:

```bash
mkdir -p ~/wohnungsscout/logs
```

### Cron Job testen

```bash
# Manuell testen:
cd ~/wohnungsscout && python3 main.py

# Log beobachten:
tail -f ~/wohnungsscout/logs/wohnungsscout.log
```

---

## Technologie-Entscheidungen

| Entscheidung | Begründung |
|---|---|
| **Kleinanzeigen.de als erste Plattform** | Einfachste HTML-Struktur, kein JavaScript-Rendering nötig, viele Privatanbieter im ländlichen Raum |
| **SQLite statt CSV/JSON** | Atomare Schreiboperationen (kein Datenverlust bei Abbruch), einfache ID-Abfragen, kein externer Datenbankserver nötig |
| **Gmail SMTP** | Kein eigener Mailserver nötig, zuverlässig, kostenlos |
| **Keine externen Scheduler-Bibliotheken** | Cron auf dem Pi übernimmt das Scheduling – das Script muss nur einmal laufen und sich dann beenden |
| **requests + BeautifulSoup** | Leichtgewichtig, ausreichend für statische Seiten, gut dokumentiert |
| **lxml als Parser** | Schneller und robuster als der eingebaute html.parser |

---

## Geplante Erweiterungen

- [ ] Scraper für ImmoScout24 (zweite Plattform)
- [ ] Scraper für Immowelt
- [ ] Telegram-Benachrichtigung als Alternative zu E-Mail
- [ ] Tägliche Zusammenfassungs-E-Mail mit allen bisher gefundenen Inseraten
- [ ] Preisstatistiken (Durchschnittsmiete pro Ort)
