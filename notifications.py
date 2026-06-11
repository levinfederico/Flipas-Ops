"""FLIPAS — Notificaciones por email y Telegram"""
import smtplib, os, requests, time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from config import NOTIFICATION_CONFIG

EMOJI = {"urgente": "🔴", "oportunidad": "🟠", "negociable": "🟡"}
LABEL = {"urgente": "ATACAR URGENTE", "oportunidad": "OPORTUNIDAD", "negociable": "NEGOCIABLE"}


def fmt(p):
    """Formatea una propiedad para Telegram (texto plano)."""
    emoji = EMOJI.get(p["alert_level"], "⚪")
    new_tag = "  🆕 NUEVA" if p.get("is_new") else ""

    outdoor = []
    if p.get("has_patio"):   outdoor.append("🌿 patio")
    if p.get("has_terraza"): outdoor.append("🌇 terraza")
    if p.get("has_balcon"):  outdoor.append("🏠 balcón")

    cochera_line = "🚗 Cochera incluida\n" if p.get("has_cochera") else ""
    outdoor_line = "  ".join(outdoor) + "\n" if outdoor else ""

    return (
        f'{emoji} {LABEL[p["alert_level"]]}{new_tag}\n'
        f'📍 {p.get("barrio")} · {p.get("type")}\n'
        f'🏠 {(p.get("address") or p.get("title", ""))[:60]}\n'
        f'📐 {p.get("m2_total", 0):.0f}m² tot '
        f'({p.get("m2_weighted", 0):.0f}m² pond.)\n'
        f'💰 USD {p.get("price_usd", 0):,.0f} '
        f'→ USD/m² pond.: {p.get("usd_per_m2", 0):,.0f}\n'
        + cochera_line
        + outdoor_line
        + f'🔗 {p.get("url", "")}'
    )


def build_email_html(props):
    """HTML del email de alerta."""
    BG = {"urgente": "#FFEBEE", "oportunidad": "#FFF8E1", "negociable": "#F3F8FF"}
    rows = ""
    for p in props:
        bg = BG.get(p["alert_level"], "#fff")
        new_badge = ""
        if p.get("is_new"):
            new_badge = '<span style="background:#1565C0;color:#fff;font-size:10px;padding:2px 6px;border-radius:10px;margin-left:6px">NUEVA</span>'
        cochera_txt = " 🚗" if p.get("has_cochera") else ""
        rows += (
            f'<tr style="background:{bg}">'
            f'<td style="padding:10px 12px;font-size:16px">{EMOJI.get(p["alert_level"],"")}</td>'
            f'<td style="padding:10px 12px">'
            f'<strong>{LABEL.get(p["alert_level"],"")} {cochera_txt}</strong>{new_badge}<br>'
            f'<span style="color:#555;font-size:13px">{p.get("barrio")} · {p.get("type")}</span><br>'
            f'<span style="font-size:12px;color:#777">'
            f'{(p.get("address") or p.get("title",""))[:55]}</span></td>'
            f'<td style="padding:10px 12px;text-align:right">'
            f'<strong>USD {p.get("price_usd",0):,.0f}</strong><br>'
            f'<span style="color:#C62828;font-weight:700;font-size:13px">'
            f'USD {p.get("usd_per_m2",0):,.0f}/m² pond.</span></td>'
            f'<td style="padding:10px 12px;text-align:center;font-size:12px;color:#555">'
            f'{p.get("m2_total",0):.0f}m²<br>Score: {p.get("score",0)}/100</td>'
            f'<td style="padding:10px 12px">'
            f'<a href="{p.get("url","")}" target="_blank" '
            f'style="background:#263238;color:#fff;padding:6px 12px;border-radius:4px;'
            f'text-decoration:none;font-size:12px">Ver aviso</a></td>'
            f'</tr>'
        )

    urgente_count = sum(1 for p in props if p["alert_level"] == "urgente")
    total_txt = f"{len(props)} oportunidad{'es' if len(props) > 1 else ''} detectada{'s' if len(props) > 1 else ''}"
    urgente_txt = f" — {urgente_count} 🔴 URGENTE" if urgente_count else ""
    fecha = datetime.now().strftime("%d/%m/%Y %H:%M")

    return (
        "<html><body style='font-family:Arial,sans-serif;max-width:700px;margin:0 auto'>"
        "<div style='background:#263238;padding:16px 20px;border-radius:6px 6px 0 0'>"
        "<span style='color:#D4AF37;font-size:18px;font-weight:700'>FLIPAS</span>"
        "<span style='color:#90A4AE;font-size:11px;margin-left:8px'>REAL ESTATE</span>"
        f"<span style='color:#fff;float:right;font-size:14px'>{total_txt}{urgente_txt}</span>"
        "</div>"
        "<table style='width:100%;border-collapse:collapse;border:1px solid #ECEFF1'>"
        "<thead><tr style='background:#607D8B;color:#fff'>"
        "<th style='padding:8px 12px'></th>"
        "<th style='padding:8px 12px;text-align:left'>Propiedad</th>"
        "<th style='padding:8px 12px;text-align:right'>Precio</th>"
        "<th style='padding:8px 12px;text-align:center'>M²</th>"
        "<th style='padding:8px 12px'>Link</th>"
        "</tr></thead>"
        f"<tbody>{rows}</tbody></table>"
        f"<div style='background:#F6F8FA;padding:10px 16px;font-size:11px;color:#90A4AE;"
        f"text-align:center;border-radius:0 0 6px 6px'>"
        f"Flipas Real Estate · {fecha} · USD/m² sobre m² ponderados. Cochera deducida del precio.</div>"
        "</body></html>"
    )


def send_email(props):
    """Envía email de alerta via Gmail SMTP."""
    cfg = NOTIFICATION_CONFIG
    if not cfg.get("email_enabled") or not props:
        return False

    smtp_pass = os.environ.get("SMTP_PASSWORD", "")
    if not smtp_pass:
        print("[EMAIL] Sin SMTP_PASSWORD — saltando")
        return False

    urg = [p for p in props if p["alert_level"] == "urgente"]
    if urg:
        subject = f"🔴 FLIPAS: {len(urg)} URGENTE — {len(props)} total"
    else:
        subject = f"🟠 FLIPAS: {len(props)} oportunidad(es) detectada(s)"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = cfg["email_from"]
    msg["To"]      = ", ".join(cfg["email_to"])
    msg.attach(MIMEText(build_email_html(props), "html"))

    try:
        with smtplib.SMTP(cfg["smtp_host"], cfg["smtp_port"]) as server:
            server.starttls()
            server.login(cfg["email_from"], smtp_pass)
            server.sendmail(cfg["email_from"], cfg["email_to"], msg.as_string())
        print(f"[EMAIL] Enviado: {len(props)} oportunidades")
        return True
    except Exception as e:
        print(f"[EMAIL] Error: {e}")
        return False


def send_telegram(props):
    """Envía alertas via Telegram Bot."""
    cfg = NOTIFICATION_CONFIG
    if not cfg.get("telegram_enabled") or not props:
        return False

    token   = os.environ.get("TELEGRAM_BOT_TOKEN", cfg.get("telegram_bot_token", ""))
    chat_id = os.environ.get("TELEGRAM_CHAT_ID",   cfg.get("telegram_chat_id",   ""))

    if not token or not chat_id:
        print("[TELEGRAM] Token o chat_id no configurados — saltando")
        return False

    ordered = sorted(
        props,
        key=lambda x: (
            {"urgente": 0, "oportunidad": 1, "negociable": 2}.get(x["alert_level"], 3),
            -x.get("score", 0),
        )
    )

    for p in ordered[:10]:
        try:
            resp = requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": fmt(p)},
                timeout=10,
            )
            if not resp.ok:
                print(f"[TELEGRAM] Error: {resp.text[:100]}")
            time.sleep(0.5)
        except Exception as e:
            print(f"[TELEGRAM] Error: {e}")

    print(f"[TELEGRAM] {len(ordered[:10])} alertas enviadas")
    return True


def notify_new_opportunities(props):
    """Dispara email + Telegram para oportunidades nuevas."""
    if not props:
        print("[NOTIFY] Sin oportunidades nuevas")
        return

    sorted_props = sorted(
        props,
        key=lambda x: (
            {"urgente": 0, "oportunidad": 1, "negociable": 2}.get(x.get("alert_level"), 3),
            -x.get("score", 0),
        )
    )
    print(f"[NOTIFY] Enviando alertas: {len(sorted_props)} oportunidades")
    send_email(sorted_props)
    send_telegram(sorted_props)
