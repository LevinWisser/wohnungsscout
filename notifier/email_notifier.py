import math
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from config import (
    EMAIL_ENABLED,
    SMTP_SERVER,
    SMTP_PORT,
    EMAIL_SENDER,
    EMAIL_PASSWORD,
    EMAIL_RECIPIENT,
    MAX_INSERATE_PRO_EMAIL,
)


def _baue_email_html(inserate: list, teil: int, gesamt_teile: int) -> str:
    """Erstellt den HTML-Body der Benachrichtigungs-E-Mail."""
    zeilen = []
    for ins in inserate:
        zeilen.append(f"""
        <div style="border:1px solid #ddd; border-radius:8px; padding:15px; margin:10px 0; font-family:sans-serif;">
            <h3 style="margin:0 0 8px 0; color:#2c3e50;">
                <a href="{ins['url']}" style="text-decoration:none; color:#2980b9;">{ins['titel']}</a>
            </h3>
            <table style="font-size:14px; color:#555;">
                <tr><td style="padding:2px 12px 2px 0;"><b>Preis:</b></td><td>{ins['preis']}</td></tr>
                <tr><td style="padding:2px 12px 2px 0;"><b>Zimmer:</b></td><td>{ins['zimmer'] or 'k.A.'}</td></tr>
                <tr><td style="padding:2px 12px 2px 0;"><b>Größe:</b></td><td>{ins['groesse'] or 'k.A.'}</td></tr>
                <tr><td style="padding:2px 12px 2px 0;"><b>Ort:</b></td><td>{ins['ort']}</td></tr>
                <tr><td style="padding:2px 12px 2px 0;"><b>Quelle:</b></td><td>{ins['plattform']}</td></tr>
            </table>
        </div>
        """)

    teil_hinweis = f" ({teil}/{gesamt_teile})" if gesamt_teile > 1 else ""
    inhalt = "\n".join(zeilen)
    return f"""
    <html><body>
        <h2 style="font-family:sans-serif; color:#2c3e50;">
            🏠 {len(inserate)} neue Wohnungsinserate gefunden{teil_hinweis}
        </h2>
        {inhalt}
        <p style="font-family:sans-serif; font-size:12px; color:#aaa; margin-top:20px;">
            Wohnungsscout – automatische Benachrichtigung
        </p>
    </body></html>
    """


def _sende_email(inserate: list, teil: int, gesamt_teile: int):
    """Sendet eine einzelne E-Mail."""
    teil_hinweis = f" ({teil}/{gesamt_teile})" if gesamt_teile > 1 else ""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Wohnungsscout: {len(inserate)} neue Inserate in Diez & Umgebung{teil_hinweis}"
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECIPIENT

    html_body = _baue_email_html(inserate, teil, gesamt_teile)
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD.replace(" ", ""))
        server.sendmail(EMAIL_SENDER, EMAIL_RECIPIENT, msg.as_string())


def sende_benachrichtigung(inserate: list):
    """
    Sendet E-Mail(s) mit den neuen Inseraten.
    Bei mehr als MAX_INSERATE_PRO_EMAIL werden mehrere E-Mails verschickt.
    """
    if not EMAIL_ENABLED or not inserate:
        return

    if not EMAIL_PASSWORD:
        print("  [Email] Kein Passwort konfiguriert – E-Mail wird nicht gesendet.")
        print("  [Email] Bitte EMAIL_PASSWORD in config.py setzen (Gmail App-Passwort).")
        return

    # In Blöcke aufteilen
    bloecke = [
        inserate[i:i + MAX_INSERATE_PRO_EMAIL]
        for i in range(0, len(inserate), MAX_INSERATE_PRO_EMAIL)
    ]
    gesamt_teile = len(bloecke)

    for i, block in enumerate(bloecke, start=1):
        try:
            _sende_email(block, i, gesamt_teile)
            print(f"  [Email] E-Mail {i}/{gesamt_teile} gesendet ({len(block)} Inserate).")
        except Exception as e:
            print(f"  [Email] Fehler bei E-Mail {i}/{gesamt_teile}: {e}")
