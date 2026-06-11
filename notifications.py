"""FLIPAS — Notificaciones por email y Telegram"""
import smtplib,os,requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from config import NOTIFICATION_CONFIG

EMOJI={"urgente":"🔴","oportunidad":"🟠","negociable":"🟡"}
LABEL={"urgente":"ATACAR URGENTE","oportunidad":"OPORTUNIDAD","negociable":"NEGOCIABLE"}

def fmt(p):
    emoji=EMOJI.get(p["alert_level"],"⚪")
    outdoor=[x for x in ["🌿 patio"if p.get("has_patio") else "","🌇 terraza"if p.get("has_terraza") else "","🏠 balcón"if p.get("has_balcon") else ""] if x]
    return (f'{emoji} {LABEL[p["alert_level"]]}{"  🆕 NUEVA" if p.get("is_new") else ""}\n'
            f'📍 {p.get("barrio")} · {p.get("type")}\n'
            f'🏠 {(p.get("address") or p.get("title",""))[:60]}\n'
            f'📐 {p.get("m2_total",0):.0f}m² tot ({p.get("m2_weighted",0):.0f}m² pond.)\n'
            f'💰 USD {p.get("price_usd",0):,.0f} → USD/m² pond.: {p.get("usd_per_m2",0):,.0f}\n'
            f'{"🚗 Cochera incluida\n" if p.get("has_cochera") else ""}'
            f'{"  ".join(outdoor)+"\n" if outdoor else ""}'
            f'🔗 {p.get("url","")}')

def send_email(props):
    cfg=NOTIFICATION_CONFIG
    if not cfg.get("email_enabled") or not props: return
    pw=os.environ.get("SMTP_PASSWORD","")
    if not pw: return
    urg=[p for p in props if p["alert_level"]=="urgente"]
    subj=(f'🔴 FLIPAS: {len(urg)} URGENTE — {len(props)} total' if urg
          else f'🟠 FLIPAS: {len(props)} oportunidad(es)')
    rows="".join(f'<tr style="background:{"#FFEBEE"if p["alert_level"]=="urgente" else "#FFF8E1"if p["alert_level"]=="oportunidad" else "#F3F8FF"}"><td style="padding:10px">{EMOJI[p["alert_level"]]}</td><td style="padding:10px"><strong>{p.get("barrio")} · {p.get("type")}</strong><br><small>{(p.get("address") or p.get("title",""))[:50]}</small></td><td style="padding:10px;text-align:right"><strong>USD {p.get("price_usd",0):,.0f}</strong><br><span style="color:#C62828;font-weight:700">${p.get("usd_per_m2",0):,.0f}/m²</span></td><td style="padding:10px"><a href="{p.get("url","")}" style="background:#263238;color:#fff;padding:5px 10px;border-radius:4px;text-decoration:none">Ver</a></td></tr>' for p in props)
    html=f'<html><body style="font-family:Arial"><div style="background:#263238;padding:16px"><span style="color:#D4AF37;font-size:18px;font-weight:700">FLIPAS</span></div><table style="width:100%;border-collapse:collapse">{rows}</table></body></html>'
    msg=MIMEMultipart("alternative"); msg["Subject"]=subj
    msg["From"]=cfg["email_from"]; msg["To"]=", ".join(cfg["email_to"])
    msg.attach(MIMEText(html,"html"))
    try:
        with smtplib.SMTP(cfg["smtp_host"],cfg["smtp_port"]) as s:
            s.starttls(); s.login(cfg["email_from"],pw)
            s.sendmail(cfg["email_from"],cfg["email_to"],msg.as_string())
        print(f"[EMAIL] Enviado: {len(props)} oportunidades")
    except Exception as e: print(f"[EMAIL] Error: {e}")

def send_telegram(props):
    cfg=NOTIFICATION_CONFIG
    if not cfg.get("telegram_enabled") or not props: return
    token=os.environ.get("TELEGRAM_BOT_TOKEN","")
    chat=os.environ.get("TELEGRAM_CHAT_ID","")
    if not token or not chat: return
    for p in sorted(props,key=lambda x:{"urgente":0,"oportunidad":1,"negociable":2}.get(x["alert_level"],3))[:10]:
        try:
            requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id":chat,"text":fmt(p)},timeout=10)
        except Exception as e: print(f"[TG] Error: {e}")
    print(f"[TELEGRAM] {len(props)} alertas enviadas")

def notify_new_opportunities(props):
    if not props: return
    s=sorted(props,key=lambda x:({"urgente":0,"oportunidad":1,"negociable":2}.get(x.get("alert_level"),3),-x.get("score",0)))
    send_email(s); send_telegram(s)