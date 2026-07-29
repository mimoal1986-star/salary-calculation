# data_cleaner.py


import pandas as pd
from utils import normalize_text

# Разрешенные менеджеры
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
    
    # ============ ШАГ 1: Фильтрация по менеджерам ============
    allowed_lower = [normalize_text(m) for m in ALLOWED_MANAGERS]
    manager_mask = working_df['Менеджер'].apply(
        lambda x: normalize_text(x) in allowed_lower
    )
    
    # Собираем удаленные
    deleted = working_df[~manager_mask].copy()
    if not deleted.empty:
        deleted['Причина_удаления'] = "Менеджер не в списке"
        deleted_rows.append(deleted)
    
    # Оставляем только разрешенных
    working_df = working_df[manager_mask].copy()
    
    # ============ ШАГ 2: Стандартизация типов проекта ============
    def standardize_project_type(row):
        project_type = normalize_text(row['Тип проекта (р/бр/неполевой)'])
        client_name = normalize_text(row['ClientName'])
        
        # Шаг 1: Мултон
        if client_name == "мултон":
            return "Мултон"
        
        # Шаг 2: Мониторинги
        if "монитор" in project_type:
            return "Мониторинги"
        
        # Шаг 3: Опросы
        if "опрос" in project_type:
            return "Опросы"
        
        # Шаг 4: Ротационный (есть "ротац", нет "без")
        if "ротац" in project_type:
            if "без" not in project_type:
                return "Ротационный"
            else:
                return "Безротационный"
        
        # Шаг 6: Не определен
        return "Не определен"
    
    # Применяем стандартизацию
    working_df['Тип проекта (р/бр/неполевой)'] = working_df.apply(
        standardize_project_type, axis=1
    )
    
    # Удаляем строки с "Не определен"
    invalid_type_mask = working_df['Тип проекта (р/бр/неполевой)'] == "Не определен"
    deleted = working_df[invalid_type_mask].copy()
    if not deleted.empty:
        deleted['Причина_удаления'] = "Некорректный тип проекта"
        deleted_rows.append(deleted)
    
    working_df = working_df[~invalid_type_mask].copy()
    
    # ============ ШАГ 3: Фильтрация по столбцу "Проекты" ============
    def process_project(value):
        if pd.isna(value):
            return value
        
        val_str = str(value)
        # Ищем "холост" (без учета регистра)
        if "холост" in val_str.lower():
            return "_SINGLE"
        return val_str
    
    working_df['Проекты'] = working_df['Проекты'].apply(process_project)
    
    # Удаляем строки, где Проекты начинается с "_" (кроме "_SINGLE")
    project_mask = working_df['Проекты'].apply(
        lambda x: str(x).startswith('_') and str(x) != '_SINGLE'
    )
    
    deleted = working_df[project_mask].copy()
    if not deleted.empty:
        deleted['Причина_удаления'] = "Проект начинается с _"
        deleted_rows.append(deleted)
    
    working_df = working_df[~project_mask].copy()
    
    # ============ ШАГ 4: Фильтрация по ClientName и ВСЕГО ============
    # Находим "Тамбовский бекон" с ВСЕГО = 0
    tambov_mask = (
        (working_df['ClientName'].apply(normalize_text) == "тамбовский бекон") &
        (working_df['ВСЕГО'] == 0)
    )
    
    deleted = working_df[tambov_mask].copy()
    if not deleted.empty:
        deleted['Причина_удаления'] = "Тамбовский бекон с ВСЕГО=0"
        deleted_rows.append(deleted)
    
    working_df = working_df[~tambov_mask].copy()
    
    # ============ ФОРМИРУЕМ РЕЗУЛЬТАТ ============
    # Очищенный файл (удаляем колонку Причина_удаления)
    if 'Причина_удаления' in working_df.columns:
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