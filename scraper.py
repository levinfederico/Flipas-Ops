"""FLIPAS REAL ESTATE — Scraper principal"""
import json,sys
from datetime import datetime,timezone
from config import DATA_JSON_PATH,SEEN_IDS_PATH,SHEETS_CONFIG
from filter_engine import filter_property
from notifications import notify_new_opportunities

def load_seen():
    try:
        with open(SEEN_IDS_PATH) as f: return set(json.load(f))
    except: return set()

def save_seen(ids):
    with open(SEEN_IDS_PATH,"w") as f: json.dump(list(ids)[-10000:],f)

def save_json(props):
    out={"updated_at":datetime.now(timezone.utc).isoformat(),
         "properties":sorted(props,key=lambda x:({"urgente":0,"oportunidad":1,"negociable":2}.get(x.get("alert_level"),3),-x.get("score",0)))}
    with open(DATA_JSON_PATH,"w",encoding="utf-8") as f:
        json.dump(out,f,ensure_ascii=False,indent=2,default=str)
    print(f"[MAIN] data.json: {len(props)} oportunidades")

def push_sheets(new_props):
    if not SHEETS_CONFIG.get("enabled") or not new_props: return
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        creds=Credentials.from_service_account_file(SHEETS_CONFIG["credentials_file"],
            scopes=["https://www.googleapis.com/auth/spreadsheets"])
        gc=gspread.authorize(creds)
        ws=gc.open_by_key(SHEETS_CONFIG["spreadsheet_id"]).worksheet(SHEETS_CONFIG["sheet_name"])
        hdrs=["Fecha","ID","Fuente","Tipo","Barrio","Dirección","M² cub","M² semi","M² desc","M² tot","M² pond","Amb","Precio USD","Precio efectivo","USD/m²","Nivel","Score","Cochera","Patio","Terraza","Balcón","Expensas","Nueva","Horas pub.","URL"]
        if not ws.get_all_values(): ws.insert_row(hdrs,1)
        rows=[[datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
               p.get("id"),p.get("source"),p.get("type"),p.get("barrio"),
               (p.get("address") or p.get("title",""))[:50],
               p.get("m2_covered",0),p.get("m2_semi",0),p.get("m2_uncovered",0),
               p.get("m2_total",0),p.get("m2_weighted",0),p.get("ambientes",""),
               p.get("price_usd",0),p.get("effective_price",0),p.get("usd_per_m2",0),
               p.get("alert_level","").upper(),p.get("score",0),
               "Sí"if p.get("has_cochera") else "No",
               "Sí"if p.get("has_patio") else "No",
               "Sí"if p.get("has_terraza") else "No",
               "Sí"if p.get("has_balcon") else "No",
               p.get("expensas_ars",0),"Sí"if p.get("is_new") else "No",
               p.get("hours_ago",""),p.get("url","")] for p in new_props]
        if rows: ws.append_rows(rows,value_input_option="USER_ENTERED")
        print(f"[SHEETS] {len(rows)} filas agregadas")
    except Exception as e: print(f"[SHEETS] Error: {e}")

def fake_data():
    return [
        {"id":"ZP-001","source":"Zonaprop","type":"PH","barrio":"Núñez","address":"Av. Balbín 3200","title":"PH 3 amb sin expensas terraza","m2_covered":64,"m2_semi":5,"m2_uncovered":33,"m2_total":102,"ambientes":3,"price_usd":90000,"has_cochera":False,"has_patio":False,"has_terraza":True,"has_balcon":True,"expensas_ars":0,"is_new":True,"hours_ago":1.2,"url":"https://zonaprop.com.ar","image_url":"","date_created":"","floor":None,"features_raw":"terraza balcon"},
        {"id":"ML-002","source":"MercadoLibre","type":"PH","barrio":"Saavedra","address":"Conde 3150","title":"PH 3 amb con cochera y terraza","m2_covered":64,"m2_semi":0,"m2_uncovered":41,"m2_total":105,"ambientes":3,"price_usd":155000,"has_cochera":True,"has_patio":False,"has_terraza":True,"has_balcon":True,"expensas_ars":0,"is_new":True,"hours_ago":3.5,"url":"https://mercadolibre.com.ar","image_url":"","date_created":"","floor":None,"features_raw":"terraza cochera"},
        {"id":"RM-003","source":"Remax","type":"Departamento","barrio":"Belgrano","address":"Mendoza 2300","title":"Depto 3 amb excelente estado cochera","m2_covered":78,"m2_semi":9,"m2_uncovered":0,"m2_total":87,"ambientes":3,"price_usd":119000,"has_cochera":True,"has_patio":False,"has_terraza":False,"has_balcon":True,"expensas_ars":95000,"is_new":False,"hours_ago":31,"url":"https://remax.com.ar","image_url":"","date_created":"","floor":3,"features_raw":"balcon cochera"},
    ]

def run(test=False,ml_only=False):
    print(f"\n{'='*50}\nFLIPAS SCRAPER — {datetime.now().strftime('%d/%m/%Y %H:%M')}\n{'='*50}")
    seen=load_seen()
    all_raw=[]
    if test:
        filtered=[r for p in fake_data() if (r:=filter_property(p))]
        new_props=filtered
    else:
        from portals.mercadolibre import scrape_mercadolibre
        all_raw.extend(scrape_mercadolibre())
        if not ml_only:
            from portals.zonaprop_argenprop import scrape_zonaprop,scrape_argenprop
            all_raw.extend(scrape_zonaprop())
            all_raw.extend(scrape_argenprop())
        print(f"[MAIN] Crudos: {len(all_raw)}")
        filtered=[r for p in all_raw if (r:=filter_property(p))]
        new_props=[p for p in filtered if p["id"] not in seen]
    print(f"[MAIN] Filtrados: {len(filtered)} | Nuevos: {len(new_props)}")
    for lvl,emoji in [("urgente","🔴"),("oportunidad","🟠"),("negociable","🟡")]:
        print(f"  {emoji} {lvl}: {sum(1 for p in filtered if p.get('alert_level')==lvl)}")
    save_json(filtered)
    if new_props and not test: push_sheets(new_props)
    if new_props: notify_new_opportunities(new_props)
    if not test:
        seen.update(p["id"] for p in filtered)
        save_seen(seen)
    print("[MAIN] ✅ Completado")
    return filtered

if __name__=="__main__":
    run(test="--test" in sys.argv,ml_only="--ml-only" in sys.argv)