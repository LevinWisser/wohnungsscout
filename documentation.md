# Wohnungsscout – Dokumentation

## Was ist das?

Wohnungsscout ist ein automatischer Immobilien-Beobachter für die Region **Diez und Umgebung** (Görgeshausen, Nentershausen, Hambach, Aull). Das Script durchsucht Wohnungsplattformen nach passenden Inseraten, filtert nach konfigurierten Kriterien und schickt eine E-Mail-Benachrichtigung wenn neue Inserate auftauchen.

Das Ziel: Immer informiert sein ohne täglich selbst suchen zu müssen – ideal für eine mittel- bis langfristige Wohnungssuche in einer Region mit überschaubarem Angebot.

Das Script läuft auf einem **Raspberry Pi** und wird dort über einen **Cron Job** automatisch ausgeführt.

---

## Für Claude Code auf dem Raspberry Pi – Schnellstart

> Du liest diese Datei gerade auf dem Pi und sollst das Projekt einrichten. Hier ist genau was zu tun ist:

### Schritt 1 – Python-Abhängigkeiten installieren

```bash
pip3 install -r requirements.txt
```

### Schritt 2 – config.py anlegen

`config.py` ist nicht im Repository (enthält das E-Mail-Passwort). Kopiere die Vorlage:

```bash
cp config.example.py config.py
```

Dann in `config.py` das Gmail App-Passwort eintragen:

```python
EMAIL_PASSWORD = "xxxx xxxx xxxx xxxx"   # App-Passwort von wisserlevin@gmail.com
```

Das App-Passwort bekommt der Nutzer aus dem Google-Konto (myaccount.google.com/apppasswords).

### Schritt 3 – Test-Lauf

```bash
mkdir -p logs
python3 main.py
```

Erwartete Ausgabe beim ersten Lauf:
- Seiten 1-8 werden gescraped (~197 Inserate im Umkreis)
- Neue Inserate werden in `data/inserate.db` gespeichert
- E-Mail-Benachrichtigung wird verschickt

### Schritt 4 – Cron Job einrichten

```bash
crontab -e
```

Folgende Zeile einfügen (stündlich zwischen 8 und 18 Uhr):

```
0 8-18 * * * cd /home/pi/wohnungsscout && python3 main.py >> logs/wohnungsscout.log 2>&1
```

### Fertig. Log beobachten mit:

```bash
tail -f logs/wohnungsscout.log
```

---

## Projektstruktur

```
wohnungsscout/
├── main.py                   # Einstiegspunkt – wird vom Cron Job aufgerufen
├── config.py                 # Alle Einstellungen – NICHT im Git, muss manuell angelegt werden
├── config.example.py         # Vorlage für config.py (ohne Passwort)
├── requirements.txt          # Python-Abhängigkeiten
├── documentation.md          # Diese Datei
│
├── scraper/
│   ├── __init__.py
│   └── kleinanzeigen.py      # Scraper für kleinanzeigen.de (15km Umkreis ab Diez)
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
    └── inserate.db           # Wird automatisch erstellt (nicht im Git)
```

---

## Wie es funktioniert (Ablauf)

1. `main.py` wird aufgerufen (manuell oder per Cron Job)
2. Die SQLite-Datenbank wird initialisiert (beim ersten Start automatisch erstellt)
3. `kleinanzeigen.py` sucht Mietwohnungen im 15km-Umkreis um Diez (Ortscode `l19222`)
4. Der HTML-Inhalt wird mit BeautifulSoup geparst – Titel, Preis, Zimmer, Größe, URL werden extrahiert
5. Inserate die nicht den Filtern entsprechen (zu wenig Zimmer, zu klein) werden aussortiert
6. Jedes verbleibende Inserat wird mit der Datenbank abgeglichen: Ist die ID schon bekannt?
7. Nur **neue** Inserate werden in der Datenbank gespeichert
8. Gibt es neue Inserate, wird eine **HTML-E-Mail** verschickt – max. 10 Inserate pro Mail, bei mehr kommen Folge-Mails (1/3, 2/3, 3/3)
9. Gibt es nichts Neues, passiert nichts – kein Spam

---

## Konfiguration (config.py)

| Variable | Bedeutung | Standard |
|---|---|---|
| `DIEZ_LOCATION_CODE` | Kleinanzeigen-Ortscode für Diez | `l19222` – nicht ändern |
| `SEARCH_RADIUS_KM` | Umkreis in km | 15 |
| `MIN_ROOMS` | Mindestanzahl Zimmer | 3 |
| `MIN_SIZE_SQM` | Mindestfläche in m² | 60 |
| `MAX_RENT_EUR` | Maximale Miete (0 = kein Filter) | 0 |
| `EMAIL_PASSWORD` | Gmail App-Passwort | leer – muss gesetzt werden! |
| `MAX_INSERATE_PRO_EMAIL` | Max. Inserate pro E-Mail | 10 |

---

## Technologie-Entscheidungen

| Entscheidung | Begründung |
|---|---|
| **Kleinanzeigen.de als erste Plattform** | Einfachste HTML-Struktur, kein JavaScript-Rendering nötig, viele Privatanbieter im ländlichen Raum |
| **Radius-Suche statt Einzel-Orte** | Eine Suche mit `r15` deckt alle Zielorte ab, sauberer als 5 separate Suchen mit Deduplizierung |
| **SQLite statt CSV/JSON** | Atomare Schreiboperationen, einfache ID-Abfragen, kein externer Datenbankserver nötig |
| **Gmail SMTP** | Kein eigener Mailserver nötig, zuverlässig, kostenlos |
| **Cron statt interner Scheduler** | Script läuft einmal durch und beendet sich – einfacher, stabiler, Pi-freundlich |
| **requests + BeautifulSoup + lxml** | Leichtgewichtig, ausreichend für statische Seiten, läuft problemlos auf ARM |

---

## Geplante Erweiterungen

- [ ] Scraper für ImmoScout24 (zweite Plattform)
- [ ] Scraper für Immowelt
- [ ] Telegram-Benachrichtigung als Alternative zu E-Mail
- [ ] Preisstatistiken (Durchschnittsmiete pro Ort)
