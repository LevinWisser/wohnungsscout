"""
Immowelt-Scraper via HTML (kein API-Key nötig, kein Bot-Schutz)

Konfiguration in config.py:
  IMMOWELT_LOCATION_SLUG   Stadtname für die URL, z.B. "diez"
  IMMOWELT_SEARCH_RADIUS_KM  Umkreis in km
  IMMOWELT_ENABLED         True/False

Suchfilter werden aus den bestehenden Werten übernommen:
  MIN_ROOMS, MIN_SIZE_SQM, MAX_RENT_EUR
"""

import re
import time
import requests
from bs4 import BeautifulSoup
from config import (
    IMMOWELT_LOCATION_SLUG,
    IMMOWELT_SEARCH_RADIUS_KM,
    MIN_ROOMS,
    MIN_SIZE_SQM,
    MAX_RENT_EUR,
    USER_AGENT,
    REQUEST_DELAY_SECONDS,
)

_BASE_URL = "https://www.immowelt.de/liste/{slug}/wohnungen/mieten"
_EXPOSE_URL = "https://www.immowelt.de/expose/{id}"
_RESULTS_PER_PAGE = 20

_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "de-DE,de;q=0.9",
}


def suche_inserate() -> list:
    """
    Sucht Mietwohnungen auf Immowelt.
    Gibt eine Liste von Inseraten zurück (gleiche Struktur wie kleinanzeigen.py).
    """
    if not IMMOWELT_LOCATION_SLUG:
        print("  Immowelt: Kein Location-Slug konfiguriert – überspringe.")
        return []

    url = _BASE_URL.format(slug=IMMOWELT_LOCATION_SLUG)
    params = _build_params()
    alle = []

    try:
        response = requests.get(url, params=params, headers=_HEADERS, timeout=15)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"  Immowelt: Fehler beim Request – {e}")
        return []

    inserate, gesamt = _parse_seite(response.text)
    alle.extend(inserate)

    max_seiten = max(1, -(-gesamt // _RESULTS_PER_PAGE))  # ceiling division
    print(f"  Immowelt Seite 1/{max_seiten}: {len(inserate)} passende Inserate ({gesamt} gesamt)")

    for seite in range(2, max_seiten + 1):
        time.sleep(REQUEST_DELAY_SECONDS)
        params_seite = {**params, "cp": seite}
        try:
            response = requests.get(url, params=params_seite, headers=_HEADERS, timeout=15)
            response.raise_for_status()
            inserate, _ = _parse_seite(response.text)
            alle.extend(inserate)
            print(f"  Immowelt Seite {seite}/{max_seiten}: {len(inserate)} passende Inserate")
        except requests.RequestException as e:
            print(f"  Immowelt Seite {seite}: Fehler – {e}")
            break

    return alle


def _build_params() -> dict:
    """Baut die URL-Parameter für die Immowelt-Suche."""
    params = {"r": IMMOWELT_SEARCH_RADIUS_KM}
    if MIN_SIZE_SQM > 0:
        params["ami"] = MIN_SIZE_SQM
    if MAX_RENT_EUR > 0:
        params["mar"] = MAX_RENT_EUR
    if MIN_ROOMS > 0:
        params["mzi"] = MIN_ROOMS
    return params


def _parse_seite(html: str) -> tuple[list, int]:
    """
    Parst eine Suchergebnisseite.
    Gibt (inserate, gesamtanzahl) zurück.
    """
    soup = BeautifulSoup(html, "lxml")
    inserate = []

    # Gesamtanzahl aus der Seite lesen
    gesamt = _hole_gesamtanzahl(soup)

    karten = soup.find_all("div", attrs={"data-testid": re.compile(r"^classified-card-mfe-")})

    for karte in karten:
        try:
            # ID aus data-testid: "classified-card-mfe-26WN92G4D16I" → "26WN92G4D16I"
            testid = karte.get("data-testid", "")
            expose_id = testid.replace("classified-card-mfe-", "").lower()
            if not expose_id:
                continue

            # URL aus dem <a>-Tag
            expose_a = karte.find("a", href=re.compile(r"/expose/"))
            if not expose_a:
                continue
            expose_url = expose_a["href"]
            if not expose_url.startswith("http"):
                expose_url = "https://www.immowelt.de" + expose_url

            text = karte.get_text(" ", strip=True)

            # Preis – sucht "1.234 € Kaltmiete" oder "1234 € Kaltmiete"
            preis_m = re.search(r"([\d.]+)\s*€\s*Kaltmiete", text)
            preis = f"{preis_m.group(1).replace('.', '')} €" if preis_m else "k.A."

            # Zimmer – sucht "3 Zimmer" oder "2,5 Zimmer"
            zimmer_m = re.search(r"([\d,]+)\s*Zimmer", text)
            zimmer = f"{zimmer_m.group(1)} Zi." if zimmer_m else ""

            # Größe – sucht "75 m²"
            groesse_m = re.search(r"([\d,]+)\s*m²", text)
            groesse = f"{groesse_m.group(1)} m²" if groesse_m else ""

            # Ort – sucht "Stadtname (PLZ)"
            ort_m = re.search(r"([\w\s\-]+\(\d{5}\))", text)
            ort = ort_m.group(1).strip() if ort_m else ""

            # Titel aus dem ersten Link-Text oder h2/h3
            titel_tag = karte.find(["h2", "h3"]) or expose_a
            titel = titel_tag.get_text(strip=True) if titel_tag else "Kein Titel"

            inserat = {
                "id": f"immowelt_{expose_id}",
                "titel": titel,
                "preis": preis,
                "ort": ort,
                "groesse": groesse,
                "zimmer": zimmer,
                "url": expose_url,
                "plattform": "Immowelt",
            }

            if _passt_zu_filtern(inserat):
                inserate.append(inserat)

        except Exception:
            continue

    return inserate, gesamt


def _hole_gesamtanzahl(soup: BeautifulSoup) -> int:
    """Liest die Gesamtanzahl der Suchergebnisse aus der Seite."""
    # Immowelt zeigt z.B. "30 Wohnungen" oder "über 100 Wohnungen" in einem heading
    for tag in soup.find_all(["h1", "h2", "span"], string=re.compile(r"\d+")):
        m = re.search(r"(\d+)", tag.get_text())
        if m:
            return int(m.group(1))
    return _RESULTS_PER_PAGE  # Fallback: nur eine Seite


def _extrahiere_zahl(text: str) -> float:
    """Zieht die erste Zahl aus einem String ('2,5 Zi.' → 2.5)."""
    if not text:
        return 0.0
    bereinigt = text.replace(".", "").replace(",", ".")
    match = re.search(r"\d+\.?\d*", bereinigt)
    return float(match.group()) if match else 0.0


def _passt_zu_filtern(inserat: dict) -> bool:
    """Nachgelagerte Filterprüfung (URL-Filter von Immowelt sind nicht immer exakt)."""
    if MIN_ROOMS > 0 and inserat.get("zimmer"):
        if 0 < _extrahiere_zahl(inserat["zimmer"]) < MIN_ROOMS:
            return False
    if MIN_SIZE_SQM > 0 and inserat.get("groesse"):
        if 0 < _extrahiere_zahl(inserat["groesse"]) < MIN_SIZE_SQM:
            return False
    if MAX_RENT_EUR > 0 and inserat.get("preis"):
        if 0 < _extrahiere_zahl(inserat["preis"]) > MAX_RENT_EUR:
            return False
    return True
