"""
ImmoScout24-Scraper via HTML (kein API-Key nötig)

IS24 rendert Suchergebnisse serverseitig (SSR) – die Listings sind direkt
im HTML enthalten, entweder als eingebettetes JSON oder als article-Elemente.

Konfiguration in config.py:
  IMMOSCOUT_LOCATION_SLUG  z.B. "rheinland-pfalz/diez"
  IMMOSCOUT_ENABLED        True/False

Suchfilter werden aus den bestehenden Werten übernommen:
  MIN_ROOMS, MIN_SIZE_SQM, MAX_RENT_EUR
"""

import re
import json
import time
import requests
from bs4 import BeautifulSoup
from config import (
    IMMOSCOUT_LOCATION_SLUG,
    MIN_ROOMS,
    MIN_SIZE_SQM,
    MAX_RENT_EUR,
    REQUEST_DELAY_SECONDS,
    USER_AGENT,
)

_BASE_URL = "https://www.immobilienscout24.de/Suche/de/{slug}/wohnung-mieten"
_EXPOSE_URL = "https://www.immobilienscout24.de/expose/{id}"

_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


def suche_inserate() -> list:
    """
    Sucht Mietwohnungen auf ImmoScout24 via HTML-Scraping.
    Gibt eine Liste von Inseraten zurück (gleiche Struktur wie kleinanzeigen.py).
    """
    if not IMMOSCOUT_LOCATION_SLUG:
        print("  ImmoScout24: Kein Location-Slug konfiguriert – überspringe.")
        return []

    url = _BASE_URL.format(slug=IMMOSCOUT_LOCATION_SLUG)
    params = _build_params(page=1)

    try:
        response = requests.get(url, params=params, headers=_HEADERS, timeout=15)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"  ImmoScout24: Fehler beim Request – {e}")
        return []

    inserate = _parse_seite(response.text)
    print(f"  ImmoScout24: {len(inserate)} passende Inserate gefunden")
    return inserate


def _build_params(page: int) -> dict:
    """Baut die URL-Parameter für die IS24-Suche."""
    params = {}
    if page > 1:
        params["pagenumber"] = page
    if MIN_ROOMS > 0:
        params["numberofrooms"] = f"{float(MIN_ROOMS):.1f}-"
    if MIN_SIZE_SQM > 0:
        params["livingspace"] = f"{float(MIN_SIZE_SQM):.1f}-"
    if MAX_RENT_EUR > 0:
        params["price"] = f"-{float(MAX_RENT_EUR):.1f}"
    return params


def _parse_seite(html: str) -> list:
    """
    Versucht zuerst, eingebettetes JSON aus dem Script-Tag zu lesen.
    Fällt auf HTML-Parsing zurück falls das nicht klappt.
    """
    inserate = _extrahiere_aus_json(html)
    if inserate is not None:
        return inserate
    return _extrahiere_aus_html(html)


def _extrahiere_aus_json(html: str) -> list | None:
    """
    IS24 bettet Suchergebnisse als JSON in die SSR-Seite ein.
    Gibt None zurück wenn kein JSON gefunden wurde (→ HTML-Fallback).
    """
    # IS24 speichert Listings in einem <script>-Tag als JSON-Array mit "resultlistEntry"-Objekten
    match = re.search(
        r'"resultlistEntries"\s*:\s*\[\s*\{[^}]*"resultlistEntry"\s*:\s*(\[.+?\])\s*\}',
        html,
        re.DOTALL,
    )
    if not match:
        return None

    try:
        entries = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None

    inserate = []
    for entry in entries:
        try:
            inserat_id = str(entry.get("@id", ""))
            if not inserat_id:
                continue

            re_data = entry.get("resultlistRealEstate", {})
            inserat = _baue_inserat(inserat_id, re_data)
            if inserat:
                inserate.append(inserat)
        except Exception:
            continue

    return inserate


def _extrahiere_aus_html(html: str) -> list:
    """
    HTML-Fallback: parst <article data-obid="...">-Elemente direkt.
    IS24 rendert die Listing-Karten serverseitig.
    """
    soup = BeautifulSoup(html, "lxml")
    inserate = []

    for artikel in soup.find_all("article", attrs={"data-obid": True}):
        try:
            inserat_id = artikel["data-obid"]

            # Titel (verschiedene IS24-Versionen nutzen unterschiedliche Tags)
            titel_tag = (
                artikel.find("h5")
                or artikel.find(attrs={"data-testid": re.compile(r"result-list-entry.*title", re.I)})
            )
            titel = titel_tag.get_text(strip=True) if titel_tag else "Kein Titel"

            # Preis – Suche nach Zahl gefolgt von € im Artikel
            preis = _suche_text(artikel, r"([\d.,]+)\s*€")
            preis = f"{preis} €" if preis else "k.A."

            # Zimmer – Suche nach "X Zi." Muster
            zimmer_match = re.search(r"([\d,]+)\s*Zi\.", artikel.get_text())
            zimmer = f"{zimmer_match.group(1)} Zi." if zimmer_match else ""

            # Größe – Suche nach "X m²" Muster
            groesse_match = re.search(r"([\d,.]+)\s*m²", artikel.get_text())
            groesse = f"{groesse_match.group(1)} m²" if groesse_match else ""

            # Ort
            ort_tag = artikel.find(attrs={"data-testid": re.compile(r".*address.*", re.I)})
            if not ort_tag:
                ort_tag = artikel.find(class_=re.compile(r"address|location|ort", re.I))
            ort = ort_tag.get_text(strip=True) if ort_tag else ""

            inserate.append({
                "id": f"immoscout_{inserat_id}",
                "titel": titel,
                "preis": preis,
                "ort": ort,
                "groesse": groesse,
                "zimmer": zimmer,
                "url": _EXPOSE_URL.format(id=inserat_id),
                "plattform": "ImmoScout24",
            })
        except Exception:
            continue

    if not inserate:
        print("  ImmoScout24: Keine Listings im HTML gefunden – IS24 hat evtl. geblockt oder die Seitenstruktur hat sich geändert.")

    return inserate


def _baue_inserat(inserat_id: str, re_data: dict) -> dict | None:
    """Baut ein Inserat-Dict aus IS24 JSON-Daten."""
    titel = re_data.get("title", "Kein Titel")

    preis_val = re_data.get("price", {}).get("value")
    preis = f"{preis_val:.0f} €" if preis_val is not None else "k.A."

    zimmer_val = re_data.get("numberOfRooms")
    if zimmer_val is not None:
        if zimmer_val == int(zimmer_val):
            zimmer = f"{int(zimmer_val)} Zi."
        else:
            zimmer = f"{zimmer_val:.1f} Zi.".replace(".", ",")
    else:
        zimmer = ""

    groesse_val = re_data.get("livingSpace")
    groesse = f"{groesse_val:.0f} m²" if groesse_val is not None else ""

    adresse = re_data.get("address", {})
    stadt = adresse.get("city", "")
    stadtteil = adresse.get("quarter", "")
    ort = f"{stadt}, {stadtteil}" if stadtteil else stadt

    return {
        "id": f"immoscout_{inserat_id}",
        "titel": titel,
        "preis": preis,
        "ort": ort,
        "groesse": groesse,
        "zimmer": zimmer,
        "url": _EXPOSE_URL.format(id=inserat_id),
        "plattform": "ImmoScout24",
    }


def _suche_text(tag, pattern: str) -> str | None:
    """Sucht per Regex im Text-Inhalt eines BS4-Tags."""
    text = tag.get_text()
    match = re.search(pattern, text.replace(".", "").replace(",", "."))
    return match.group(1) if match else None
