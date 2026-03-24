import re
import math
import time
import requests
from bs4 import BeautifulSoup
from config import (
    REQUEST_DELAY_SECONDS,
    USER_AGENT,
    MIN_ROOMS,
    MIN_SIZE_SQM,
    MAX_RENT_EUR,
    SEARCH_RADIUS_KM,
    DIEZ_LOCATION_CODE,
)


# Kleinanzeigen.de URL-Aufbau:
# c203       = Kategorie "Wohnung mieten"
# l19222     = Ortscode für Diez (Rheinland-Pfalz)
# r{radius}  = Umkreis in km
# seite:{n}  = Seitennummer (kommt zwischen Ort und Kategorie-Code)
_LOCATION_SLUG = f"c203{DIEZ_LOCATION_CODE}r{SEARCH_RADIUS_KM}"
BASE_URL = f"https://www.kleinanzeigen.de/s-wohnung-mieten/diez/{_LOCATION_SLUG}"
PAGE_URL = f"https://www.kleinanzeigen.de/s-wohnung-mieten/diez/seite:{{page}}/{_LOCATION_SLUG}"
RESULTS_PER_PAGE = 25

HEADERS = {"User-Agent": USER_AGENT}


def _extrahiere_zahl(text: str) -> float:
    """Zieht die erste Zahl aus einem String (z.B. '117,64 m²' → 117.64)."""
    if not text:
        return 0.0
    bereinigt = text.replace(".", "").replace(",", ".")
    match = re.search(r"\d+\.?\d*", bereinigt)
    return float(match.group()) if match else 0.0


def _parse_tags(tags_text: str) -> tuple:
    """
    Parst den Tags-Absatz (z.B. '117,64 m² · 3 Zi.') in Größe und Zimmeranzahl.
    Gibt (groesse_str, zimmer_str) zurück.
    """
    groesse = ""
    zimmer = ""

    if not tags_text:
        return groesse, zimmer

    teile = [t.strip() for t in re.split(r"[·•|]", tags_text) if t.strip()]

    for teil in teile:
        if "m²" in teil or "qm" in teil.lower():
            groesse = teil
        elif re.search(r"\d", teil) and re.search(r"[Zz]i", teil):
            zimmer = teil

    return groesse, zimmer


def _passt_zu_filtern(inserat: dict) -> bool:
    """Prüft ob ein Inserat den konfigurierten Filtern entspricht."""
    if MIN_ROOMS > 0 and inserat.get("zimmer"):
        zimmer_zahl = _extrahiere_zahl(inserat["zimmer"])
        if zimmer_zahl > 0 and zimmer_zahl < MIN_ROOMS:
            return False

    if MIN_SIZE_SQM > 0 and inserat.get("groesse"):
        groesse_zahl = _extrahiere_zahl(inserat["groesse"])
        if groesse_zahl > 0 and groesse_zahl < MIN_SIZE_SQM:
            return False

    if MAX_RENT_EUR > 0 and inserat.get("preis"):
        preis_zahl = _extrahiere_zahl(inserat["preis"])
        if preis_zahl > 0 and preis_zahl > MAX_RENT_EUR:
            return False

    return True


def _hole_gesamtanzahl(soup: BeautifulSoup) -> int:
    """Liest die Gesamtanzahl der Ergebnisse aus dem H1-Tag."""
    h1 = soup.find("h1")
    if not h1:
        return 0
    match = re.search(r"von ([\d.]+)", h1.get_text())
    if match:
        return int(match.group(1).replace(".", ""))
    return 0


def _parse_seite(html: str) -> list:
    """Parst eine Suchergebnisseite und gibt eine Liste von Inseraten zurück."""
    soup = BeautifulSoup(html, "lxml")
    inserate = []

    artikel_liste = soup.find_all("article", class_="aditem")

    for artikel in artikel_liste:
        try:
            inserat_id = artikel.get("data-adid", "")
            if not inserat_id:
                continue

            # Titel und URL
            titel_tag = artikel.find("a", class_="ellipsis")
            if not titel_tag:
                continue
            titel = titel_tag.get_text(strip=True)
            url = "https://www.kleinanzeigen.de" + titel_tag.get("href", "")

            # Preis
            preis_tag = artikel.find(
                "p", class_="aditem-main--middle--price-shipping--price"
            )
            preis = preis_tag.get_text(strip=True) if preis_tag else "k.A."

            # Größe und Zimmer aus dem Tags-Absatz
            tags_tag = artikel.find("p", class_="aditem-main--middle--tags")
            tags_text = tags_tag.get_text(" · ", strip=True) if tags_tag else ""
            groesse, zimmer = _parse_tags(tags_text)

            # Standort – Whitespace bereinigen, Entfernung in Klammern erhalten
            ort_tag = artikel.find("div", class_="aditem-main--top--left")
            if ort_tag:
                ort_teile = [t.strip() for t in ort_tag.get_text().split("\n") if t.strip()]
                ort = " ".join(ort_teile)
            else:
                ort = ""

            inserat = {
                "id": inserat_id,
                "titel": titel,
                "preis": preis,
                "ort": ort,
                "groesse": groesse,
                "zimmer": zimmer,
                "url": url,
                "plattform": "kleinanzeigen.de",
            }

            if _passt_zu_filtern(inserat):
                inserate.append(inserat)

        except Exception:
            continue

    return inserate, soup


def suche_inserate() -> list:
    """
    Durchsucht Kleinanzeigen.de nach Mietwohnungen im Umkreis von Diez.
    Bestimmt die genaue Seitenanzahl aus dem ersten Request und iteriert nur
    über die tatsächlichen Ergebnisseiten – keine falschen Nationaltreffer.
    """
    alle = []

    # Erste Seite abrufen und Gesamtanzahl ermitteln
    try:
        response = requests.get(BASE_URL, headers=HEADERS, timeout=15)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"  Fehler beim ersten Request: {e}")
        return []

    inserate, soup = _parse_seite(response.text)
    alle.extend(inserate)

    gesamt = _hole_gesamtanzahl(soup)
    max_seiten = math.ceil(gesamt / RESULTS_PER_PAGE) if gesamt else 1
    print(f"  Seite 1/{max_seiten}: {len(inserate)} passende Inserate ({gesamt} gesamt im Umkreis)")

    # Weitere Seiten abrufen
    for seite in range(2, max_seiten + 1):
        time.sleep(REQUEST_DELAY_SECONDS)
        url = PAGE_URL.format(page=seite)

        try:
            response = requests.get(url, headers=HEADERS, timeout=15)
            response.raise_for_status()
            inserate, _ = _parse_seite(response.text)
            alle.extend(inserate)
            print(f"  Seite {seite}/{max_seiten}: {len(inserate)} passende Inserate")
        except requests.RequestException as e:
            print(f"  Seite {seite}: Fehler – {e}")
            break

    return alle
