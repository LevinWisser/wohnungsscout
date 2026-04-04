"""
ImmoScout24-Scraper via offizielle REST API (OAuth 1.0a)

Voraussetzungen:
  1. Kostenlosen Developer-Account anlegen: https://developer.immobilienscout24.de
  2. App registrieren → Consumer Key + Consumer Secret erhalten
  3. Keys in config.py eintragen (IMMOSCOUT_CONSUMER_KEY, IMMOSCOUT_CONSUMER_SECRET)

GeoCode-ID für deine Suchregion ermitteln:
  Rufe folgende URL auf (kein API-Key nötig):
  https://rest.immobilienscout24.de/restapi/api/gis/v1.0/geoautocomplete/de/Diez
  → suche im JSON nach "id" für den passenden Eintrag (z.B. Diez, Rheinland-Pfalz)
  → diesen Wert als IMMOSCOUT_GEO_CODE_ID in config.py eintragen
"""

from requests_oauthlib import OAuth1Session
from config import (
    IMMOSCOUT_CONSUMER_KEY,
    IMMOSCOUT_CONSUMER_SECRET,
    IMMOSCOUT_GEO_CODE_ID,
    MIN_ROOMS,
    MIN_SIZE_SQM,
    MAX_RENT_EUR,
)

_SEARCH_URL = "https://rest.immobilienscout24.de/restapi/api/search/v1.0/search/region"
_EXPOSE_URL = "https://www.immobilienscout24.de/expose/{id}"


def suche_inserate() -> list:
    """
    Sucht Mietwohnungen auf ImmoScout24 via REST API.
    Gibt eine Liste von Inseraten zurück (gleiche Struktur wie kleinanzeigen.py).
    """
    if not IMMOSCOUT_CONSUMER_KEY or not IMMOSCOUT_CONSUMER_SECRET:
        print("  ImmoScout24: Kein API-Key konfiguriert – überspringe.")
        return []

    if not IMMOSCOUT_GEO_CODE_ID:
        print("  ImmoScout24: Keine GeoCode-ID konfiguriert – überspringe.")
        return []

    session = OAuth1Session(IMMOSCOUT_CONSUMER_KEY, IMMOSCOUT_CONSUMER_SECRET)

    params = {
        "geocodeid": IMMOSCOUT_GEO_CODE_ID,
        "realestatetype": "apartmentrent",
        "pagesize": 100,
        "pagenumber": 1,
    }
    if MIN_ROOMS > 0:
        params["numberofrooms.min"] = MIN_ROOMS
    if MIN_SIZE_SQM > 0:
        params["livingspace.min"] = MIN_SIZE_SQM
    if MAX_RENT_EUR > 0:
        params["price.max"] = MAX_RENT_EUR

    try:
        response = session.get(
            _SEARCH_URL,
            params=params,
            headers={"Accept": "application/json"},
            timeout=15,
        )
        response.raise_for_status()
    except Exception as e:
        print(f"  ImmoScout24: API-Fehler – {e}")
        return []

    inserate = _parse_response(response.json())
    print(f"  ImmoScout24: {len(inserate)} passende Inserate gefunden")
    return inserate


def _parse_response(data: dict) -> list:
    """Parst die JSON-Antwort der ImmoScout24 Search API."""
    inserate = []

    try:
        resultlist = data.get("resultlist.resultlist", {})
        entries_container = resultlist.get("resultlistEntries", [{}])
        entries = entries_container[0].get("resultlistEntry", []) if entries_container else []
    except (KeyError, IndexError, AttributeError):
        print("  ImmoScout24: Unerwartetes Antwortformat")
        return []

    for entry in entries:
        try:
            inserat_id = str(entry.get("@id", ""))
            if not inserat_id:
                continue

            re_data = entry.get("resultlistRealEstate", {})

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

    return inserate
