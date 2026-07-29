# data_loader.py 
"""
Загрузка и валидация Excel-файлов
"""

import pandas as pd
import streamlit as st

# Обязательные колонки
REQUIRED_COLUMNS = [
    "Портал", "ACC", "Менеджер", "РП", "Тип проекта (р/бр/неполевой)",
    "CritID", "FinishTime", "CritStatus", "SetName", "SetCode",
    "ClientName", "ClientID", "Client_Account_Manager", "BranchName",
    "BranchFullname", "BranchCode", "BranchID", "Address", "CityName",
    "RegionName согласно распределения АСС", "RegionName",
    "Тайный покупатель Fullname", "Тайный покупатель ID",
    "Тайный покупатель Username", "CritID", "Проекты", "Тариф",
    "Копирайт", "Проезд", "Компенсация за покупку", "Penalty",
    "Бонус", "ВСЕГО"
]


def load_excel(file):
    """
    Загружает Excel-файл в DataFrame
    
    Args:
        file: загруженный файл из st.file_uploader
        
    Returns:
        tuple: (DataFrame, error_message)
        - Если успешно: (df, None)
        - Если ошибка: (None, error_message)
    """
    try:
        df = pd.read_excel(file, engine='openpyxl')
        return df, None
    except Exception as e:
        return None, f"Ошибка загрузки файла: {str(e)}"


def validate_columns(df):
    """
    Проверяет наличие всех обязательных колонок
    
    Args:
        df: DataFrame для проверки
        
    Returns:
        tuple: (is_valid, error_message, missing_columns)
        - is_valid: True если все колонки есть
        - error_message: сообщение об ошибке или None
        - missing_columns: список отсутствующих колонок или None
    """
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    
    if missing:
        return False, f"Отсутствуют колонки: {', '.join(missing)}", missing
    
    return True, None, None