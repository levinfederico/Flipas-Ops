"""FLIPAS — Scraper MercadoLibre via API oficial"""
import requests,time
from datetime import datetime,timezone

ML_BASE="https://api.mercadolibre.com"
ML_CATS={"PH":"MLA1472","Departamento":"MLA1473"}
HDRS={"User-Agent":"FlipasBot/1.0","Accept":"application/json"}

BARRIO_MAP={
    "saavedra":"Saavedra","núñez":"Núñez","nuñez":"Núñez","coghlan":"Coghlan",
    "belgrano":"Belgrano","colegiales":"Colegiales","palermo":"Palermo",
    "palermo hollywood":"Palermo Hollywood","palermo soho":"Palermo Soho",
    "las cañitas":"Las Cañitas","las canitas":"Las Cañitas",
    "belgrano r":"Belgrano R","belgrano c":"Belgrano C",
}

def safe_float(v):
    try: return float(v) if v else 0.0
    except: return 0.0

def get_attr(attrs,aid):
    for a in attrs:
        if a.get("id")==aid:
            return a.get("value_name") or (a.get("value_struct") or {}).get("number")
    return None

def parse_item(item,ptype):
    attrs=item.get("attributes",[])
    loc=item.get("location",{})
    barrio_raw=(loc.get("neighborhood",{}).get("name","") or
                loc.get("city_subdivision",{}).get("name",""))
    barrio=BARRIO_MAP.get(barrio_raw.lower(),barrio_raw)

    cub=safe_float(get_attr(attrs,"COVERED_AREA"))
    tot=safe_float(get_attr(attrs,"TOTAL_AREA"))
    semi=safe_float(get_attr(attrs,"SEMI_COVERED_AREA"))
    desc=max(0.0,tot-cub-semi)

    try: amb=int(get_attr(attrs,"ROOMS") or 0) or None
    except: amb=None

    price=item.get("price",0) or 0
    if item.get("currency_id","USD")!="USD": price=0

    garage=get_attr(attrs,"PARKING_LOTS")
    cochera=bool(garage and int(garage)>0 if garage else False)

    title=item.get("title","")
    combined=title.lower()
    has_patio="patio" in combined
    has_terraza="terraza" in combined
    has_balcon="balcón" in combined or "balcon" in combined

    pub=item.get("date_created","")
    is_new=False; hours_ago=9999
    if pub:
        try:
            d=datetime.fromisoformat(pub.replace("Z","+00:00"))
            h=(datetime.now(timezone.utc)-d).total_seconds()/3600
            hours_ago=h; is_new=h<48
        except: pass

    return {
        "id":f"ML-{item.get('id','')}","source":"MercadoLibre","type":ptype,
        "barrio":barrio,"address":loc.get("address_line",""),"title":title,
        "description":"","m2_covered":cub,"m2_semi":semi,"m2_uncovered":desc,
        "m2_total":tot,"ambientes":amb,"price_usd":price,"has_cochera":cochera,
        "has_patio":has_patio,"has_terraza":has_terraza,"has_balcon":has_balcon,
        "expensas_ars":0,"floor":None,"url":item.get("permalink",""),
        "image_url":item.get("thumbnail",""),"date_created":pub,
        "is_new":is_new,"hours_ago":round(hours_ago,1),"features_raw":combined,
    }

def scrape_mercadolibre():
    print("[ML] Iniciando..."); results=[]; seen=set()
    for ptype in ["PH","Departamento"]:
        for off in range(0,200,50):
            try:
                r=requests.get(f"{ML_BASE}/sites/MLA/search",
                    params={"category":ML_CATS[ptype],"state":"TUxBUENBUGw3M2JR",
                            "city":"TUxBQ0NBUGZlZG1l","sort":"date_desc","limit":50,"offset":off},
                    headers=HDRS,timeout=15)
                r.raise_for_status(); items=r.json().get("results",[])
            except Exception as e: print(f"[ML] Error: {e}"); break
            if not items: break
            for item in items:
                iid=item.get("id")
                if iid in seen: continue
                seen.add(iid); results.append(parse_item(item,ptype))
            time.sleep(0.5)
        print(f"[ML] {ptype}: {sum(1 for r in results if r['type']==ptype)}")
    print(f"[ML] Total: {len(results)}"); return results
