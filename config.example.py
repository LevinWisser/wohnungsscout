# ============================================================
# KONFIGURATION – hier alles anpassen bevor du das Script startest
# ============================================================

# --- Suchregion ---
# Kleinanzeigen.de Ortscode für Diez (Rheinland-Pfalz)
# Dieser Code ist fest hinterlegt – nicht ändern
DIEZ_LOCATION_CODE = "l19222"

# Umkreis in km ab Diez (deckt Görgeshausen, Nentershausen, Hambach, Aull ab)
# 10 km: nur nahe Umgebung
# 15 km: schließt Limburg-Randgebiete ein
SEARCH_RADIUS_KM = 15

# --- Filter ---
MIN_ROOMS = 3          # Mindestanzahl Zimmer (0 = kein Filter)
MIN_SIZE_SQM = 60      # Mindestfläche in qm (0 = kein Filter)
MAX_RENT_EUR = 0       # Maximale Miete in € (0 = kein Filter)

# --- Benachrichtigung (E-Mail) ---
EMAIL_ENABLED = True
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_SENDER = "wisserlevin@gmail.com"      # Deine Gmail-Adresse
EMAIL_PASSWORD = ""                          # App-Passwort (nicht dein normales Passwort!)
EMAIL_RECIPIENT = "wisserlevin@gmail.com"   # Wohin die Benachrichtigung geht
MAX_INSERATE_PRO_EMAIL = 10                 # Max. Inserate pro E-Mail (Rest kommt in Folge-Mails)

# --- Datenbank ---
DB_PATH = "data/inserate.db"

# --- Scraper-Verhalten ---
REQUEST_DELAY_SECONDS = 2   # Pause zwischen Seiten-Requests (bitte nicht unter 1)
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)
