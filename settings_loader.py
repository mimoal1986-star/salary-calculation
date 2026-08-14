# ==================== settings_loader.py ====================
"""
Загрузка справочников для настроек
"""

import pandas as pd
import json
import os
import requests
import base64
import streamlit as st
from datetime import datetime


def save_to_json_github(name, data):
    """
    Сохраняет данные в GitHub репозиторий через API
    """
    token = st.secrets.get("GITHUB_TOKEN")
    username = st.secrets.get("GITHUB_USERNAME")
    repo = st.secrets.get("GITHUB_REPO")
    
    if not token:
        raise Exception("GITHUB_TOKEN не найден в secrets")
    if not username or not repo:
        raise Exception("GITHUB_USERNAME или GITHUB_REPO не найдены в secrets")
    
    path = f"{name}.json"
    url = f"https://api.github.com/repos/{username}/{repo}/contents/{path}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    encoded = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')
    
    response = requests.get(url, headers=headers)
    
    payload = {
        "message": f"Update {name}.json",
        "content": encoded,
        "branch": "main"
    }
    
    if response.status_code == 200:
        sha = response.json().get('sha')
        if sha:
            payload["sha"] = sha
    
    response = requests.put(url, headers=headers, json=payload)
    
    if response.status_code in [200, 201]:
        return True
    else:
        raise Exception(f"Ошибка сохранения: {response.status_code} - {response.text}")


def load_from_json_github(name):
    """
    Загружает данные из JSON из GitHub
    """
    token = st.secrets.get("GITHUB_TOKEN")
    username = st.secrets.get("GITHUB_USERNAME")
    repo = st.secrets.get("GITHUB_REPO")
    
    if not token:
        return None
    
    path = f"{name}.json"
    url = f"https://api.github.com/repos/{username}/{repo}/contents/{path}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        content = response.json().get('content', '')
        if content:
            decoded = base64.b64decode(content).decode('utf-8')
            return json.loads(decoded)
    return None


def load_region_type(file):
    """
    Загружает справочник Регион-Тип
    
    Ожидаемая структура:
    Lo | ДВ
    ДВ | Обычная
    AA | Сложная
    """
    try:
        df = pd.read_excel(file, engine='openpyxl')
        
        if 'Lo' not in df.columns or 'ДВ' not in df.columns:
            return {
                'status': 'error',
                'message': "Файл должен содержать колонки 'Lo' и 'ДВ'"
            }
        
        df = df[['Lo', 'ДВ']].copy()
        df = df.dropna(subset=['Lo', 'ДВ'])
        
        valid_types = ['Обычная', 'Сложная']
        invalid = df[~df['ДВ'].isin(valid_types)]
        
        return {
            'status': 'success',
            'data': df,
            'invalid': invalid if not invalid.empty else None,
            'last_upload': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f"Ошибка загрузки: {str(e)}"
        }


def load_project_motivation(file):
    """
    Загружает справочник Проект-Мотивация
    
    Ожидаемая структура:
    Имя клиента | Мотивация
    Ёбидоёби | 1
    """
    try:
        df = pd.read_excel(file, engine='openpyxl')
        
        if 'Имя клиента' not in df.columns or 'Мотивация' not in df.columns:
            return {
                'status': 'error',
                'message': "Файл должен содержать колонки 'Имя клиента' и 'Мотивация'"
            }
        df = df[['Имя клиента', 'Мотивация']].copy()

        df = df.dropna(subset=['Имя клиента', 'Мотивация'])
        
        invalid = df[df['Мотивация'] != 1]
        
        return {
            'status': 'success',
            'data': df,
            'invalid': invalid if not invalid.empty else None,
            'last_upload': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f"Ошибка загрузки: {str(e)}"
        }


def load_name_login(file):
    """
    Загружает справочник Имя-логин
    
    Ожидаемая структура:
    логин эм | ЭМ
    Koordinator10 | Екатерина Алексеевна Митюшкина
    """
    try:
        df = pd.read_excel(file, engine='openpyxl')
        
        if 'логин эм' not in df.columns or 'ЭМ' not in df.columns:
            return {
                'status': 'error',
                'message': "Файл должен содержать колонки 'логин эм' и 'ЭМ'"
            }
        
        df = df[['логин эм', 'ЭМ']].copy()
        df = df.dropna(subset=['логин эм', 'ЭМ'])
        
        # Находим полные дубликаты (совпадают и логин, и ФИО)
        duplicates = df[df.duplicated(subset=['логин эм', 'ЭМ'], keep=False)]
        duplicate_count = len(duplicates) if not duplicates.empty else 0
        
        # Удаляем полные дубликаты, оставляя первое вхождение
        df_clean = df.drop_duplicates(subset=['логин эм', 'ЭМ'], keep='first')
        removed_count = len(df) - len(df_clean)
        
        return {
            'status': 'success',
            'data': df_clean,
            'invalid': duplicates if not duplicates.empty else None,
            'last_upload': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'removed_duplicates': removed_count,
            'duplicate_count': duplicate_count
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f"Ошибка загрузки: {str(e)}"
        }


def load_distribution(file):
    try:
        df = pd.read_excel(file, engine='openpyxl')
        
        if df.empty:
            return {'status': 'error', 'message': "Файл пуст"}
        
        # ============ 1. Маппинг по регионам ============
        region_mapping = {}
        
        region_col = None
        for col in df.columns:
            if str(col).strip() == 'регион':
                region_col = col
                break
        
        login_col = None
        for col in df.columns:
            if str(col).strip() == 'логин RS':
                login_col = col
                break
        
        if region_col is not None and login_col is not None:
            for _, row in df.iterrows():
                region = str(row[region_col]).strip()
                login = str(row[login_col]).strip()
                
                if region and region not in ['nan', 'None', '']:
                    if login and login not in ['nan', 'None', '']:
                        region_mapping[region] = login
        
        # ============ 2. Маппинг по Москве ============
        moscow_mapping = {}
        moscow_client_col = None
        moscow_login_col = None
        
        for col in df.columns:
            if str(col).strip() == 'Москва':
                moscow_client_col = col
                break
        
        if moscow_client_col is not None:
            for col in df.columns:
                if str(col).strip() == 'логин RS' and col != login_col:
                    moscow_login_col = col
                    break
            
            if moscow_login_col is None:
                moscow_login_col = login_col
        
        if moscow_client_col is not None and moscow_login_col is not None:
            for _, row in df.iterrows():
                client = str(row[moscow_client_col]).strip()
                login = str(row[moscow_login_col]).strip()
                
                if client and client not in ['nan', 'None', '']:
                    if login and login not in ['nan', 'None', '']:
                        moscow_mapping[client] = login
        
        # ============ 3. Маппинг по Санкт-Петербургу ============
        spb_mapping = {}
        spb_client_col = None
        spb_login_col = None
        
        for col in df.columns:
            if str(col).strip() == 'распределение по Питеру':
                spb_client_col = col
                break
        
        if spb_client_col is not None:
            for col in df.columns:
                if str(col).strip() == 'логин RS' and col != login_col and col != moscow_login_col:
                    spb_login_col = col
                    break
            
            if spb_login_col is None:
                spb_login_col = login_col
        
        if spb_client_col is not None and spb_login_col is not None:
            for _, row in df.iterrows():
                client = str(row[spb_client_col]).strip()
                login = str(row[spb_login_col]).strip()
                
                if client and client not in ['nan', 'None', '']:
                    if login and login not in ['nan', 'None', '']:
                        spb_mapping[client] = login
        
        return {
            'status': 'success',
            'data': {
                'region_mapping': region_mapping,
                'spb_mapping': spb_mapping,
                'moscow_mapping': moscow_mapping
            },
            'last_upload': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'stats': {
                'regions': len(region_mapping),
                'spb': len(spb_mapping),
                'moscow': len(moscow_mapping)
            }
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f"Ошибка загрузки: {str(e)}"
        }

def load_multon(file):
    """
    Загружает справочник Мултон
    
    Ожидаемая структура:
    Номер анкеты с ПО | ... | логин ЭМ кто назначил | Проектная
    """
    try:
        df = pd.read_excel(file, engine='openpyxl')
        
        if df.empty:
            return {
                'status': 'error',
                'message': "Файл пуст"
            }
        
        # Проверяем наличие обязательных колонок
        required_cols = ['Номер анкеты с ПО', 'логин ЭМ кто назначил', 'Проектная']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            return {
                'status': 'error',
                'message': f"Отсутствуют колонки: {', '.join(missing_cols)}"
            }
        
        # Оставляем только нужные колонки
        df = df[['Номер анкеты с ПО', 'логин ЭМ кто назначил', 'Проектная']].copy()
        
        # Очищаем от пустых строк
        df = df.dropna(subset=['Номер анкеты с ПО', 'логин ЭМ кто назначил'])
        
        # Приводим номер анкеты к строке
        df['Номер анкеты с ПО'] = df['Номер анкеты с ПО'].astype(str).str.strip()
        df['логин ЭМ кто назначил'] = df['логин ЭМ кто назначил'].astype(str).str.strip()
        df['Проектная'] = pd.to_numeric(df['Проектная'], errors='coerce').fillna(0)
        
        return {
            'status': 'success',
            'data': df,
            'last_upload': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'stats': {
                'rows': len(df)
            }
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f"Ошибка загрузки: {str(e)}"
        }
