"""FLIPAS — Motor de filtrado y scoring"""
from config import (TARGET_BARRIOS,PH_RULES,DEPTO_RULES,
    COCHERA_VALUE,M2_WEIGHT,THRESHOLDS,MIN_M2_TOTAL,MIN_AMBIENTES,MAX_AMBIENTES)

def is_target_barrio(b):
    b=b.lower().strip()
    return any(b in t.lower() or t.lower() in b for t in TARGET_BARRIOS)

def calc_weighted_m2(cub,semi,desc):
    return cub*M2_WEIGHT["cubierto"]+semi*M2_WEIGHT["semicubierto"]+desc*M2_WEIGHT["descubierto"]

def calc_effective_price(price,ptype,cochera):
    return max(0,price-COCHERA_VALUE[ptype]) if cochera and ptype in COCHERA_VALUE else price

def get_alert_level(usd):
    if usd<THRESHOLDS["urgente"]:     return "urgente"
    if usd<THRESHOLDS["oportunidad"]: return "oportunidad"
    if usd<THRESHOLDS["negociable"]:  return "negociable"
    return None

def check_ph_rules(prop):
    combined=(prop.get("title","")+prop.get("description","")+prop.get("features_raw","")).lower()
    # Excluir si dice "1er piso por escalera"
    for kw in PH_RULES.get("exclude_if_keywords",[]):
        if kw.lower() in combined:
            return False,f"PH excluido: {kw}"
    # Requiere exterior
    if PH_RULES["requires_outdoor"]:
        has_out=any(k in combined for k in PH_RULES["outdoor_keywords"])
        if not (has_out or prop.get("has_patio") or prop.get("has_terraza") or prop.get("has_deck")):
            return False,"PH sin patio/terraza"
    return True,""

def check_depto_rules(prop):
    if DEPTO_RULES["exclude_pb"]:
        floor=prop.get("floor")
        if floor is not None and floor==0: return False,"PB excluida para deptos"
        combined=(prop.get("title","")+prop.get("description","")).lower()
        if any(k in combined for k in ["planta baja","pb ","piso 0"]): return False,"PB excluida"
    if DEPTO_RULES["exclude_interior"]:
        combined=(prop.get("title","")+prop.get("description","")).lower()
        if any(k in combined for k in [" interno"," interior"]): return False,"Interior excluido"
    return True,""

def calc_score(prop,usd,level):
    s=0
    if usd<1000:s+=35
    elif usd<1100:s+=28
    elif usd<1200:s+=20
    elif usd<1300:s+=14
    elif usd<1400:s+=8
    else:s+=3
    b=prop.get("barrio","").lower()
    t1=["palermo","colegiales","belgrano r","belgrano c","las cañitas"]
    t2=["núñez","nuñez","belgrano","coghlan"]
    if any(t in b for t in t1):s+=20
    elif any(t in b for t in t2):s+=12
    else:s+=5
    if prop.get("type")=="PH" and (prop.get("has_patio") or prop.get("has_terraza")):s+=15
    elif prop.get("type")=="PH":s+=8
    else:s+=5
    if prop.get("is_new"):s+=15
    elif prop.get("hours_ago",999)<24:s+=10
    elif prop.get("hours_ago",999)<48:s+=5
    desc=(prop.get("description","")+prop.get("title","")).lower()
    if "urgente" in desc or "oportunidad" in desc:s+=5
    if "sin expensas" in desc:s+=4
    if prop.get("has_cochera"):s+=3
    return min(100,s)

def filter_property(prop):
    if not is_target_barrio(prop.get("barrio","")): return None
    ptype=prop.get("type","")
    if ptype not in ["PH","Departamento"]: return None
    amb=prop.get("ambientes")
    if amb and (amb<MIN_AMBIENTES or amb>MAX_AMBIENTES): return None
    if ptype=="PH":
        ok,_=check_ph_rules(prop)
        if not ok: return None
    else:
        ok,_=check_depto_rules(prop)
        if not ok: return None
    cub=float(prop.get("m2_covered",0) or 0)
    semi=float(prop.get("m2_semi",0) or 0)
    desc2=float(prop.get("m2_uncovered",0) or 0)
    tot=float(prop.get("m2_total",0) or 0)
    if tot==0: tot=cub+semi+desc2
    if cub==0 and tot>0: cub=tot
    if tot<MIN_M2_TOTAL: return None
    w=calc_weighted_m2(cub,semi,desc2) or tot
    price=float(prop.get("price_usd",0) or 0)
    if price<=0: return None
    cochera=bool(prop.get("has_cochera"))
    eff=calc_effective_price(price,ptype,cochera)
    usd=eff/w
    level=get_alert_level(usd)
    if not level: return None
    score=calc_score(prop,usd,level)
    return {**prop,"m2_covered":cub,"m2_semi":semi,"m2_uncovered":desc2,
            "m2_total":tot,"m2_weighted":round(w,1),"effective_price":eff,
            "usd_per_m2":round(usd,0),"alert_level":level,"score":score}