# report_generator.py
"""
Формирование Excel-файлов для выгрузки
"""

import pandas as pd
import io
from datetime import datetime


def create_cleaned_excel(df):
    """
    Создает Excel-файл с очищенными данными
    
    Args:
        df: DataFrame с очищенными данными
        
    Returns:
        BytesIO: Excel-файл в памяти
    """
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Очищенные данные')
    
    output.seek(0)
    return output


def create_deleted_excel(df):
    """
    Создает Excel-файл с удаленными строками
    
    Args:
        df: DataFrame с удаленными строками
        
    Returns:
        BytesIO: Excel-файл в памяти
    """
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Удаленные строки')
    
    output.seek(0)
    return output


def get_filename(base_name, suffix):
    """
    Формирует имя файла с датой
    
    Args:
        base_name: базовое имя файла
        suffix: суффикс (очищенный/удаленный)
        
    Returns:
        str: имя файла с датой
    """
    date_str = datetime.now().strftime("%Y-%m-%d")
    return f"{base_name}_{suffix}_{date_str}.xlsx"