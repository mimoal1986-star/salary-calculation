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
    """
    Загружает справочник Распределение
    
    Ожидаемая структура (3 таблицы горизонтально):
    Таблица 1: ФИ ASM | регион | рег 2 | ФИ RS | логин RS | статус (RS/СТАЖЕР)
    Таблица 2: распределение по Питеру | ФИ RS | логин RS | статус (RS/СТАЖЕР)
    Таблица 3: Москва | ФИ RS | логин RS | статус (RS/СТАЖЕР)
    
    Returns:
        dict: {
            'region_mapping': {'регион': 'логин RS'},
            'spb_mapping': {'распределение по Питеру': 'логин RS'},
            'moscow_mapping': {'Москва': 'логин RS'}
        }
    """
    try:
        df = pd.read_excel(file, engine='openpyxl', header=None)
        
        region_mapping = {}
        spb_mapping = {}
        moscow_mapping = {}
        
        # ============ 1. Парсим таблицу Регионов ============
        # Находим строку с заголовками "ФИ ASM" или "регион"
        header_row_idx = None
        for idx, row in df.iterrows():
            row_str = row.astype(str).str.lower().str.strip().values
            if any('фи asm' in str(val).lower() for val in row_str):
                header_row_idx = idx
                break
        
        if header_row_idx is not None:
            header_row = df.iloc[header_row_idx].astype(str).str.strip()
            
            col_region = None
            col_login_rs = None
            
            # Ищем колонки в области первой таблицы (первые 10 колонок)
            for idx in range(0, 10):
                val = str(header_row.get(idx, '')).lower()
                if 'регион' in val and 'рег 2' not in val and 'рег2' not in val:
                    col_region = idx
                if 'логин rs' in val:
                    col_login_rs = idx
            
            if col_region is not None and col_login_rs is not None:
                for idx in range(header_row_idx + 1, len(df)):
                    region = str(df.iloc[idx, col_region]).strip()
                    login = str(df.iloc[idx, col_login_rs]).strip()
                    if region and region != 'nan' and login and login != 'nan':
                        region_mapping[region] = login
        
        # ============ 2. Парсим таблицу СПб ============
        # Ищем строку с "распределение по питеру"
        header_row_idx_spb = None
        for idx, row in df.iterrows():
            row_str = row.astype(str).str.lower().str.strip().values
            if any('распределение по питеру' in str(val).lower() for val in row_str):
                header_row_idx_spb = idx
                break
        
        if header_row_idx_spb is not None:
            header_row_spb = df.iloc[header_row_idx_spb].astype(str).str.strip()
            
            col_client = None
            col_login = None
            
            # Ищем колонки в области таблицы СПб (начиная с позиции заголовка)
            for idx in range(header_row_idx_spb, header_row_idx_spb + 10):
                val = str(header_row_spb.get(idx, '')).lower()
                if 'распределение по питеру' in val:
                    col_client = idx
                if 'логин rs' in val:
                    col_login = idx
            
            if col_client is not None and col_login is not None:
                for idx in range(header_row_idx_spb + 1, len(df)):
                    client = str(df.iloc[idx, col_client]).strip()
                    login = str(df.iloc[idx, col_login]).strip()
                    if client and client != 'nan' and login and login != 'nan':
                        spb_mapping[client] = login
        
        # ============ 3. Парсим таблицу Москва ============
        # Ищем строку с "Москва"
        header_row_idx_msk = None
        for idx, row in df.iterrows():
            row_str = row.astype(str).str.lower().str.strip().values
            if any('москва' in str(val).lower() for val in row_str):
                header_row_idx_msk = idx
                break
        
        if header_row_idx_msk is not None:
            header_row_msk = df.iloc[header_row_idx_msk].astype(str).str.strip()
            
            col_client = None
            col_login = None
            
            # Ищем колонки в области таблицы Москва (начиная с позиции заголовка)
            for idx in range(header_row_idx_msk, header_row_idx_msk + 10):
                val = str(header_row_msk.get(idx, '')).lower()
                if 'москва' in val:
                    col_client = idx
                if 'логин rs' in val:
                    col_login = idx
            
            if col_client is not None and col_login is not None:
                for idx in range(header_row_idx_msk + 1, len(df)):
                    client = str(df.iloc[idx, col_client]).strip()
                    login = str(df.iloc[idx, col_login]).strip()
                    if client and client != 'nan' and login and login != 'nan':
                        moscow_mapping[client] = login
        
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
