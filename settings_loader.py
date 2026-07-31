# ==================== settings_loader.py ====================
"""
Загрузка справочников для настроек
"""

import pandas as pd
import json
import os
from datetime import datetime

# Путь для хранения JSON
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)


def save_to_json(name, data):
    """
    Сохраняет данные в JSON-файл
    """
    filepath = os.path.join(DATA_DIR, f"{name}.json")
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_from_json(name):
    """
    Загружает данные из JSON-файла
    """
    filepath = os.path.join(DATA_DIR, f"{name}.json")
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def load_region_type(file):
    """
    Загружает справочник Регион-ДВ
    
    Ожидаемая структура:
    Lo | ДВ
    ДВ | Обычная
    AA | Сложная
    """
    try:
        df = pd.read_excel(file, engine='openpyxl')
        
        # Проверяем наличие колонок
        if 'Lo' not in df.columns or 'ДВ' not in df.columns:
            return {
                'status': 'error',
                'message': "Файл должен содержать колонки 'Lo' и 'ДВ'"
            }
        
        # Оставляем только нужные колонки
        df = df[['Lo', 'ДВ']].copy()
        
        # Очищаем от пустых строк
        df = df.dropna(subset=['Lo', 'ДВ'])
        
        # Проверяем допустимые значения
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
        
        # Проверяем наличие колонок
        if 'Имя проекта' not in df.columns or 'Мотивация' not in df.columns:
            return {
                'status': 'error',
                'message': "Файл должен содержать колонки 'Имя проекта' и 'Мотивация'"
            }
        
        # Оставляем только нужные колонки
        df = df[['Имя проекта', 'Мотивация']].copy()
        
        # Очищаем от пустых строк
        df = df.dropna(subset=['Имя проекта', 'Мотивация'])
        
        # Проверяем допустимые значения (только 1)
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
