# -*- coding: utf-8 -*-
import os

class Config:
    DEBUG = True
    SECRET_KEY = "super-secret-key"

    SESSION_TIMEOUT_HOURS = 2
    PDF_DPI = 200

    # рџ“‚ 1. РћРїСЂРµРґРµР»РµРЅРёРµ Р±Р°Р·РѕРІРѕРіРѕ РїСѓС‚Рё (Р”РћР›Р–РќРћ РР”РўР РџР•Р Р•Р” Р”Р РЈР“РРњР РџРЈРўРЇРњР)
    # BASE_DIR - СЌС‚Рѕ Р°Р±СЃРѕР»СЋС‚РЅС‹Р№ РїСѓС‚СЊ Рє РїР°РїРєРµ pdftest_app
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    # рџ“‚ 2. РќР°СЃС‚СЂРѕР№РєР° РІСЃРµС… РїСѓС‚РµР№ (РёСЃРїРѕР»СЊР·СѓРµРј Р°Р±СЃРѕР»СЋС‚РЅС‹Рµ РїСѓС‚Рё)
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    TEMPLATES_FOLDER = os.path.join(BASE_DIR, "templates_json")
    STATIC_FOLDER = os.path.join(BASE_DIR, "static")
    # рџ”‘ РљР РРўРР§Р•РЎРљР Р’РђР–РќРђРЇ РЎРўР РћРљРђ: РїР°РїРєР° РґР»СЏ РєР»СЋС‡РµР№ Р°РІС‚РѕСЂРёР·Р°С†РёРё
    CREDENTIALS_FOLDER = os.path.join(BASE_DIR, "credentials") 

    # Google Sheets API
    GOOGLE_SHEETS_SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]

    # рџ”‘ СЃСЃС‹Р»РєР° РЅР° Google Sheets
    USERS_SHEET_URL = "https://docs.google.com/spreadsheets/d/1yI_73HFTwXFuG2-2nwxqodoGCM0gDC6uDDp16t3aLa8/edit?gid=0#gid=0"

    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}


    @staticmethod
    def create_directories():
        """РЎРѕР·РґР°РµС‚ РІСЃРµ РЅРµРѕР±С…РѕРґРёРјС‹Рµ РїР°РїРєРё, РµСЃР»Рё РѕРЅРё РЅРµ СЃСѓС‰РµСЃС‚РІСѓСЋС‚."""
        import os
        for folder in [
            Config.UPLOAD_FOLDER,  
            Config.TEMPLATES_FOLDER,  
            Config.STATIC_FOLDER,
            Config.CREDENTIALS_FOLDER # <--- Р”РѕР±Р°РІР»РµРЅРЅР°СЏ РїР°РїРєР° РґР»СЏ РєР»СЋС‡РµР№
            # РџР°РїРєР° templates РЅРµ РЅСѓР¶РЅР°, С‚Р°Рє РєР°Рє Flask РёС‰РµС‚ РµРµ СЃР°Рј РІ РєРѕСЂРЅРµ РїСЂРѕРµРєС‚Р°
        ]:
            # exist_ok=True РїСЂРµРґРѕС‚РІСЂР°С‰Р°РµС‚ РѕС€РёР±РєСѓ, РµСЃР»Рё РїР°РїРєР° СѓР¶Рµ РµСЃС‚СЊ
            os.makedirs(folder, exist_ok=True)