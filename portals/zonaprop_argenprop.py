"""FLIPAS — Scrapers ZonaProp y Argenprop"""
import time,json
from datetime import datetime,timezone
try:
    import cloudscraper
    _s=cloudscraper.create_scraper()
    def get(url,**kw): return _s.get(url,**kw)
except:
    import requests
    def get(url,**kw): return requests.get(url,**kw)
from bs4 import BeautifulSoup

HDRS={"User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36","Accept-Language":"es-AR,es;q=0.9"}

ZP_BARRIOS=["saavedra","nunez","coghlan","belgrano","colegiales","palermo-hollywood","palermo-soho","palermo","las-canitas","belgrano-r","belgrano-c"]
ZP_MAP={"saavedra":"Saavedra","nunez":"Núñez","coghlan":"Coghlan","belgrano":"Belgrano","colegiales":"Colegiales","palermo-hollywood":"Palermo Hollywood","palermo-soho":"Palermo Soho","palermo":"Palermo","las-canitas":"Las Cañitas","belgrano-r":"Belgrano R","belgrano-c":"Belgrano C"}
AP_BARRIOS=["saavedra","nunez","coghlan","belgrano","colegiales","palermo","palermo-hollywood","palermo-soho","las-canitas"]
AP_MAP={"saavedra":"Saavedra","nunez":"Núñez","coghlan":"Coghlan","belgrano":"Belgrano","colegiales":"Colegiales","palermo":"Palermo","palermo-hollywood":"Palermo Hollywood","palermo-soho":"Palermo Soho","las-canitas":"Las Cañitas"}

def parse_dates(s):
    if not s: return False,9999
    try:
        d=datetime.fromisoformat(s.replace("Z","+00:00"))
        h=(datetime.now(timezone.utc)-d).total_seconds()/3600
        return h<48,round(h,1)
    except: return False,9999

def scrape_portal(url,barrio,bmap,ptype,prefix):
    try:
        r=get(url,headers=HDRS,timeout=15); r.raise_for_status()
    except Exception as e: print(f"[{prefix}] Error {url}: {e}"); return []
    soup=BeautifulSoup(r.text,"html.parser")
    script=soup.find("script",{"id":"__NEXT_DATA__"})
    if not script: return []
    try:
        data=json.loads(script.string)
        pp=data.get("props",{}).get("pageProps",{})
        items=(pp.get("searchResult",{}).get("listings",[]) or
               pp.get("listings",[]) or
               pp.get("data",{}).get("items",[]))
    except: return []
    results=[]
    for item in items:
        listing=item.get("listing",item)
        try:
            po=(listing.get("priceOperationTypes") or [{}])[0]
            pr=(po.get("prices") or [{}])[0]
            price=float(pr.get("amount",0) or 0)
            if pr.get("currency","USD")!="USD": continue
            sf=listing.get("surfaces",{}) if "surfaces" in listing else listing
            tot=float(sf.get("totalSurface",0) or sf.get("total",0) or 0)
            cov=float(sf.get("roofedSurface",0) or sf.get("roofed",0) or 0)
            semi=float(sf.get("semiRoofedSurface",0) or sf.get("semiRoofed",0) or 0)
            desc2=max(0,tot-cov-semi)
            title=listing.get("title",""); desc_txt=listing.get("description","")
            combined=(title+" "+desc_txt).lower()
            pub=listing.get("publicationDate",listing.get("createdAt",""))
            is_new,hours_ago=parse_dates(pub)
            link=listing.get("permalink","")
            if link and not link.startswith("http"):
                link=f"https://www.{'zonaprop.com.ar' if prefix=='ZP' else 'argenprop.com'}{link}"
            results.append({
                "id":f"{prefix}-{listing.get('globalId',listing.get('id',''))}",
                "source":{"ZP":"Zonaprop","AP":"Argenprop"}[prefix],
                "type":ptype,"barrio":bmap.get(barrio,barrio),
                "address":listing.get("address",""),"title":title,
                "description":desc_txt[:400],"m2_covered":cov,"m2_semi":semi,
                "m2_uncovered":desc2,"m2_total":tot,"ambientes":listing.get("rooms"),
                "price_usd":price,"has_cochera":"cochera" in combined,"has_patio":"patio" in combined,
                "has_terraza":"terraza" in combined,"has_balcon":"balcón" in combined or "balcon" in combined,
                "expensas_ars":float(listing.get("expenses",0) or 0),
                "floor":listing.get("floor"),"url":link,"image_url":"",
                "date_created":pub,"is_new":is_new,"hours_ago":hours_ago,"features_raw":combined,
            })
        except: pass
    return results

def scrape_zonaprop():
    print("[ZP] Iniciando..."); results=[]; seen=set()
    for b in ZP_BARRIOS:
        for slug,ptype in [("ph","PH"),("departamentos","Departamento")]:
            url=f"https://www.zonaprop.com.ar/{slug}-venta-{b}-mas-de-50-m2.html?orden=fecha-bajada"
            for item in scrape_portal(url,b,ZP_MAP,ptype,"ZP"):
                if item["id"] not in seen: seen.add(item["id"]); results.append(item)
            time.sleep(2)
    print(f"[ZP] Total: {len(results)}"); return results

def scrape_argenprop():
    print("[AP] Iniciando..."); results=[]; seen=set()
    for b in AP_BARRIOS:
        for slug,ptype in [("ph","PH"),("departamento","Departamento")]:
            url=f"https://www.argenprop.com/{slug}/venta/{b}?orden=fecha_desc"
            for item in scrape_portal(url,b,AP_MAP,ptype,"AP"):
                if item["id"] not in seen: seen.add(item["id"]); results.append(item)
            time.sleep(2)
    print(f"[AP] Total: {len(results)}"); return results
