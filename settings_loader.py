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
    Сохраняет данные в JSON-файл в GitHub репозиторий через API
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
    
    # Кодируем данные в base64
    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    encoded = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')
    
    # Проверяем, существует ли файл
    response = requests.get(url, headers=headers)
    
    payload = {
        "message": f"Update {name}.json",
        "content": encoded,
        "branch": "main"
    }
    
    # Если файл существует, берем его SHA
    if response.status_code == 200:
        sha = response.json().get('sha')
        if sha:
            payload["sha"] = sha
    
    # Отправляем запрос на создание/обновление файла
    response = requests.put(url, headers=headers, json=payload)
    
    if response.status_code in [200, 201]:
        return True
    else:
        raise Exception(f"Ошибка сохранения: {response.status_code} - {response.text}")


def load_from_json_github(name):
    """
    Загружает данные из JSON-файла из GitHub репозитория
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


def save_to_json(name, data):
    """
    Сохраняет данные в JSON-файл (локально, для совместимости)
    """
    filepath = f"{name}.json"
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_from_json(name):
    """
    Загружает данные из JSON-файла (локально, для совместимости)
    """
    filepath = f"{name}.json"
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
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
    Имя проекта | Мотивация
    05.2026_Ёбидоёби | 1
    """
    try:
        df = pd.read_excel(file, engine='openpyxl')
        
        if 'Имя проекта' not in df.columns or 'Мотивация' not in df.columns:
            return {
                'status': 'error',
                'message': "Файл должен содержать колонки 'Имя проекта' и 'Мотивация'"
            }
        
        df = df[['Имя проекта', 'Мотивация']].copy()
        df = df.dropna(subset=['Имя проекта', 'Мотивация'])
        
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
