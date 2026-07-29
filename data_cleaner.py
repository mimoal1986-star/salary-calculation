"""
Логика очистки данных
"""

import pandas as pd
import numpy as np
from utils import normalize_text

# Разрешенные менеджеры (проверяем по колонке ACC)
ALLOWED_MANAGERS = [
    "Аблязимова Екатерина",
    "Герасимова Светлана",
    "Карлышева Алиса",
    "Механошина Елена",
    "Солодникова Виктория",
    "Шавлюк Юлия",
    "Воронин Евгений",
    "Яцевич Максим",
    "Голдакова Светлана"
]

# Словарь замен для колонки ACC
ACC_REPLACEMENTS = {
    "Koordinator57": "Яцевич Максим",
    "Koordinator26": "Голдакова Светлана",
    "Koordinator63": "Воронин Евгений"
}


def clean_data(df):
    """
    Основная функция очистки данных
    Возвращает: (cleaned_df, deleted_df)
    """
    # Создаем копию для работы
    working_df = df.copy()
    
    # Добавляем колонку для отслеживания причины удаления
    working_df['Причина_удаления'] = ""
    
    deleted_rows = []
    
    # ============ ПРЕДВАРИТЕЛЬНАЯ ОБРАБОТКА: замены в колонке ACC ============
    working_df['ACC'] = working_df['ACC'].replace(ACC_REPLACEMENTS)
    
    # ============ ШАГ 1: Фильтрация по менеджерам (колонка ACC) ============
    # Векторизованная фильтрация
    allowed_lower = [normalize_text(m) for m in ALLOWED_MANAGERS]
    acc_normalized = working_df['ACC'].astype(str).str.strip().str.lower()
    manager_mask = acc_normalized.isin(allowed_lower)
    
    # Собираем удаленные
    deleted = working_df[~manager_mask].copy()
    if not deleted.empty:
        deleted['Причина_удаления'] = "Менеджер не в списке"
        deleted_rows.append(deleted)
    
    # Оставляем только разрешенных
    working_df = working_df[manager_mask].copy()
    
    # ============ ШАГ 2: Стандартизация типов проекта (векторизовано) ============
    if not working_df.empty:
        # Подготавливаем данные
        project_type_norm = working_df['Тип проекта (р/бр/неполевой)'].astype(str).str.strip().str.lower()
        client_name_norm = working_df['ClientName'].astype(str).str.strip().str.lower()
        original_values = working_df['Тип проекта (р/бр/неполевой)']
        
        # Создаем условия для каждого типа
        conditions = [
            # Шаг 1: Мултон
            client_name_norm == "мултон",
            # Шаг 2: Мониторинги
            project_type_norm.str.contains("монитор", na=False),
            # Шаг 3: Опросы
            project_type_norm.str.contains("опрос", na=False),
            # Шаг 4: Ротационный (есть "ротац", нет "без")
            (project_type_norm.str.contains("ротац", na=False)) & 
            (~project_type_norm.str.contains("без", na=False)),
            # Шаг 5: Безротационный (есть "ротац" и есть "без")
            (project_type_norm.str.contains("ротац", na=False)) & 
            (project_type_norm.str.contains("без", na=False))
        ]
        
        # Соответствующие значения
        choices = [
            "Мултон",
            "Мониторинги",
            "Опросы",
            "Ротационный",
            "Безротационный"
        ]
        
        # Применяем векторизованное присвоение
        # Если ни одно условие не подошло - оставляем исходное значение
        default = original_values
        working_df['Тип проекта (р/бр/неполевой)'] = np.select(
            conditions, 
            choices, 
            default=default
        )
        
        # Определяем, какие строки были НЕ определены
        valid_types = ["Мултон", "Мониторинги", "Опросы", "Ротационный", "Безротационный"]
        invalid_type_mask = ~working_df['Тип проекта (р/бр/неполевой)'].isin(valid_types)
        
        deleted = working_df[invalid_type_mask].copy()
        if not deleted.empty:
            deleted['Причина_удаления'] = "Некорректный тип проекта"
            deleted_rows.append(deleted)
        
        working_df = working_df[~invalid_type_mask].copy()
    
    # ============ ШАГ 3: Фильтрация по столбцу "Проекты" (векторизовано) ============
    if not working_df.empty:
        # Векторизованная замена "холост" на "_SINGLE"
        projects = working_df['Проекты'].astype(str)
        projects_clean = projects.str.strip()
        
        # Создаем маску для "холост"
        holost_mask = projects_clean.str.lower().str.contains("холост", na=False)
        working_df['Проекты'] = np.where(holost_mask, "_SINGLE", projects)
        
        # Векторизованная фильтрация проектов, начинающихся с "_" (кроме "_SINGLE")
        projects_str = working_df['Проекты'].astype(str)
        project_mask = projects_str.str.startswith('_') & (projects_str != '_SINGLE')
        
        deleted = working_df[project_mask].copy()
        if not deleted.empty:
            deleted['Причина_удаления'] = "Проект начинается с _"
            deleted_rows.append(deleted)
        
        working_df = working_df[~project_mask].copy()
    
    # ============ ШАГ 4: Фильтрация по ClientName и ВСЕГО (векторизовано) ============
    if not working_df.empty:
        # Векторизованная фильтрация
        client_norm = working_df['ClientName'].astype(str).str.strip().str.lower()
        tambov_mask = (client_norm == "тамбовский бекон") & (working_df['ВСЕГО'] == 0)
        
        deleted = working_df[tambov_mask].copy()
        if not deleted.empty:
            deleted['Причина_удаления'] = "Тамбовский бекон с ВСЕГО=0"
            deleted_rows.append(deleted)
        
        working_df = working_df[~tambov_mask].copy()
    
    # ============ ФОРМИРУЕМ РЕЗУЛЬТАТ ============
    # Очищенный файл (удаляем колонку Причина_удаления)
    if not working_df.empty and 'Причина_удаления' in working_df.columns:
        cleaned_df = working_df.drop(columns=['Причина_удаления'])
    else:
        cleaned_df = working_df
    
    # Удаленные строки
    if deleted_rows:
        deleted_df = pd.concat(deleted_rows, ignore_index=True)
    else:
        # Создаем пустой DataFrame с правильными колонками
        all_columns = df.columns.tolist() + ['Причина_удаления']
        deleted_df = pd.DataFrame(columns=all_columns)
    
    return cleaned_df, deleted_df
