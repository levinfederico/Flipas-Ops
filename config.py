"""FLIPAS REAL ESTATE — Configuración del agente scraper"""

PORTALS = {"mercadolibre":True,"zonaprop":True,"argenprop":True,"remax":True}

TARGET_BARRIOS = [
    "Saavedra","Núñez","Nuñez","Coghlan",
    "Belgrano","Belgrano R","Belgrano C","Barrio Chino",
    "Colegiales","Palermo","Palermo Hollywood","Palermo Soho",
    "Las Cañitas","Las Canitas",
]

PROPERTY_TYPES = ["PH","Departamento"]

PH_RULES = {
    "requires_outdoor": True,
    "outdoor_keywords": ["patio","terraza","deck","azotea","parrilla"],
    # Solo PHs con acceso desde PB (planta baja) — excluir "1er piso por escalera"
    "exclude_if_keywords": [
        "1er piso por escalera","1° piso por escalera",
        "primer piso por escalera","1 piso por escalera",
        "1er piso - por escalera","primer piso - escalera",
        "acceso por escalera piso 1",
    ],
}

DEPTO_RULES = {
    "exclude_pb":       True,   # No PB para departamentos
    "exclude_interior": True,   # No interiores
}

COCHERA_VALUE = {"PH":20_000,"Departamento":25_000}

M2_WEIGHT = {"cubierto":1.00,"semicubierto":0.50,"descubierto":0.33}

THRESHOLDS = {"urgente":1_300,"oportunidad":1_400,"negociable":1_500}

MIN_M2_TOTAL=50; MIN_AMBIENTES=2; MAX_AMBIENTES=5

NOTIFICATION_CONFIG = {
    "email_enabled":True,"smtp_host":"smtp.gmail.com","smtp_port":587,
    "email_from":"flipasre@gmail.com","email_to":["flipasre@gmail.com"],
    "telegram_enabled":True,"telegram_bot_token":"","telegram_chat_id":"",
    "notify_only_new":True,"alert_levels":["urgente","oportunidad","negociable"],
}

SHEETS_CONFIG = {
    "enabled":True,"spreadsheet_id":"",
    "credentials_file":"credentials.json","sheet_name":"Oportunidades",
}

DATA_JSON_PATH="data.json"; SEEN_IDS_PATH="seen_ids.json"