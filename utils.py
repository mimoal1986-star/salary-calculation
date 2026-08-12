# ==================== utils.py ====================
"""
Вспомогательные функции
"""

import pandas as pd


def normalize_text(text):
    """
    Приводит строку к нормализованному виду:
    - убирает пробелы по краям
    - приводит к нижнему регистру
    """
    if pd.isna(text):
        return ""
    return str(text).strip().lower()


def is_empty_value(value):
    """
    Проверяет, является ли значение пустым
    
    Возвращает True если:
    - None, NaN
    - пустая строка ''
    - '-', '0', 'nan', 'none', 'null', 'нет', ' ', '—', '–'
    """
    if pd.isna(value):
        return True
    val = str(value).strip().lower()
    empty_values = ['', '-', '0', 'nan', 'none', 'null', 'нет', ' ', '—', '–']
    return val in empty_values


def format_project_type(value):
    """
    Форматирует тип проекта с большой буквы
    """
    if not value:
        return "Не определен"
    
    mapping = {
        "ротационный": "Ротационный",
        "безротационный": "Безротационный",
        "мултон": "Мултон",
        "опросы": "Опросы",
        "мониторинги": "Мониторинги"
    }
    
    val_lower = str(value).strip().lower()
    return mapping.get(val_lower, "Не определен")
