# Wohnungsscout

Automatischer Immobilien-Beobachter für die Region **Diez und Umgebung** (Rheinland-Pfalz). Durchsucht Kleinanzeigen.de im 15km-Umkreis nach Mietwohnungen und schickt eine E-Mail-Benachrichtigung sobald neue Inserate auftauchen.

Läuft auf einem Raspberry Pi als Cron Job – vollständig automatisch, 24/7.

---

## Features

- Sucht stündlich nach neuen Inseraten im konfigurierten Umkreis
- Filtert nach Zimmeranzahl und Mindestgröße
- Speichert gesehene Inserate in einer lokalen Datenbank – jedes Inserat kommt nur einmal
- Sendet HTML-E-Mails mit direkten Links zu den Inseraten
- Bei vielen neuen Inseraten werden automatisch mehrere übersichtliche Mails verschickt

---

## Schnellstart

```bash
git clone https://github.com/LevinWisser/wohnungsscout.git
cd wohnungsscout
pip3 install -r requirements.txt
cp config.example.py config.py
# config.py öffnen und EMAIL_PASSWORD eintragen
python3 main.py
```

---

## Konfiguration

Alle Einstellungen in `config.py` (wird aus `config.example.py` erstellt):

| Variable | Bedeutung | Standard |
|---|---|---|
| `SEARCH_RADIUS_KM` | Suchradius ab Diez in km | `15` |
| `MIN_ROOMS` | Mindestanzahl Zimmer | `3` |
| `MIN_SIZE_SQM` | Mindestfläche in m² | `60` |
| `MAX_RENT_EUR` | Maximale Miete (0 = kein Filter) | `0` |
| `EMAIL_PASSWORD` | Gmail App-Passwort | – |
| `MAX_INSERATE_PRO_EMAIL` | Max. Inserate pro E-Mail | `10` |

### Gmail App-Passwort einrichten

1. [myaccount.google.com/security](https://myaccount.google.com/security) → 2-Schritt-Verifizierung aktivieren
2. [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) → neues App-Passwort erstellen
3. Das 16-stellige Passwort in `config.py` eintragen (Leerzeichen sind OK)

---

## Raspberry Pi – Cron Job

```bash
mkdir -p logs
crontab -e
```

Eintrag für stündliche Ausführung zwischen 8 und 18 Uhr:

```
0 8-18 * * * cd /home/pi/wohnungsscout && python3 main.py >> logs/wohnungsscout.log 2>&1
```

Updates einspielen:

```bash
git pull
```

---

## Projektstruktur

```
wohnungsscout/
├── main.py                 # Einstiegspunkt
├── config.py               # Einstellungen (nicht im Git)
├── config.example.py       # Vorlage für config.py
├── requirements.txt
├── scraper/
│   └── kleinanzeigen.py    # Scraper für kleinanzeigen.de
├── notifier/
│   └── email_notifier.py   # E-Mail-Benachrichtigung
└── database/
    └── db.py               # SQLite-Datenbank
```

Ausführliche Dokumentation: [documentation.md](documentation.md)
