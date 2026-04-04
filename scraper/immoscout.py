"""
ImmoScout24-Scraper via Playwright (headless Chromium)

IS24 blockiert einfache HTTP-Requests mit CloudFront WAF.
Playwright startet einen echten (headless) Chrome-Browser und umgeht das.

Einmaliges Setup auf dem Pi:
  pip install playwright
  playwright install chromium

Konfiguration in config.py:
  IMMOSCOUT_LOCATION_SLUG  z.B. "rheinland-pfalz/diez"
  IMMOSCOUT_ENABLED        True/False

Suchfilter werden aus den bestehenden Werten übernommen:
  MIN_ROOMS, MIN_SIZE_SQM, MAX_RENT_EUR
"""

import re
import json
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from bs4 import BeautifulSoup
from config import (
    IMMOSCOUT_LOCATION_SLUG,
    MIN_ROOMS,
    MIN_SIZE_SQM,
    MAX_RENT_EUR,
)

_BASE_URL = "https://www.immobilienscout24.de/Suche/de/{slug}/wohnung-mieten"
_EXPOSE_URL = "https://www.immobilienscout24.de/expose/{id}"


def suche_inserate() -> list:
    """
    Sucht Mietwohnungen auf ImmoScout24 via Playwright.
    Gibt eine Liste von Inseraten zurück (gleiche Struktur wie kleinanzeigen.py).
    """
    if not IMMOSCOUT_LOCATION_SLUG:
        print("  ImmoScout24: Kein Location-Slug konfiguriert – überspringe.")
        return []

    url = _BASE_URL.format(slug=IMMOSCOUT_LOCATION_SLUG)
    params = _build_params()
    if params:
        query = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{url}?{query}"

    try:
        html = _lade_seite(url)
    except Exception as e:
        print(f"  ImmoScout24: Fehler beim Laden – {e}")
        return []

    inserate = _parse_seite(html)
    print(f"  ImmoScout24: {len(inserate)} passende Inserate gefunden")
    return inserate


def _lade_seite(url: str) -> str:
    """Öffnet die Seite mit Playwright und gibt das gerenderte HTML zurück."""
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            locale="de-DE",
            user_agent=(
                "Mozilla/5.0 (X11; Linux aarch64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            # Kurz warten bis Listings gerendert sind
            page.wait_for_selector("article[data-obid]", timeout=10000)
        except PlaywrightTimeout:
            pass  # Seite teilweise geladen – trotzdem parsen

        html = page.content()
        browser.close()

    return html


def _build_params() -> dict:
    """Baut die URL-Parameter für die IS24-Suche."""
    params = {}
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
    Fällt auf HTML-Parsing der gerenderten article-Elemente zurück.
    """
    inserate = _extrahiere_aus_json(html)
    if inserate is not None:
        return inserate
    return _extrahiere_aus_html(html)


def _extrahiere_aus_json(html: str) -> list | None:
    """IS24 bettet Suchergebnisse manchmal als JSON in Script-Tags ein."""
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
            inserat = _baue_inserat_aus_json(inserat_id, entry.get("resultlistRealEstate", {}))
            if inserat:
                inserate.append(inserat)
        except Exception:
            continue

    return inserate


def _extrahiere_aus_html(html: str) -> list:
    """Parst gerenderte <article data-obid="...">-Elemente."""
    soup = BeautifulSoup(html, "lxml")
    inserate = []

    for artikel in soup.find_all("article", attrs={"data-obid": True}):
        try:
            inserat_id = artikel["data-obid"]
            text = artikel.get_text(" ", strip=True)

            titel_tag = artikel.find("h5") or artikel.find(["h2", "h3", "h4"])
            titel = titel_tag.get_text(strip=True) if titel_tag else "Kein Titel"

            preis_match = re.search(r"([\d.]+(?:,\d+)?)\s*€", text)
            preis = f"{preis_match.group(1)} €" if preis_match else "k.A."

            zimmer_match = re.search(r"([\d,]+)\s*Zi\.", text)
            zimmer = f"{zimmer_match.group(1)} Zi." if zimmer_match else ""

            groesse_match = re.search(r"([\d,.]+)\s*m²", text)
            groesse = f"{groesse_match.group(1)} m²" if groesse_match else ""

            ort_tag = (
                artikel.find(attrs={"data-testid": re.compile(r"address", re.I)})
                or artikel.find(class_=re.compile(r"address|location", re.I))
            )
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
        print("  ImmoScout24: Keine Listings gefunden – evtl. CAPTCHA oder geändertes Seitenlayout.")

    return inserate


def _baue_inserat_aus_json(inserat_id: str, re_data: dict) -> dict | None:
    """Baut ein Inserat-Dict aus IS24 JSON-Daten."""
    titel = re_data.get("title", "Kein Titel")

    preis_val = re_data.get("price", {}).get("value")
    preis = f"{preis_val:.0f} €" if preis_val is not None else "k.A."

    zimmer_val = re_data.get("numberOfRooms")
    if zimmer_val is not None:
        zimmer = f"{int(zimmer_val)} Zi." if zimmer_val == int(zimmer_val) else f"{zimmer_val:.1f} Zi.".replace(".", ",")
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
