# ==================== data_cleaner.py ====================
"""
Логика очистки данных и заполнения колонок
"""

import pandas as pd
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

# Словарь переименования колонок
COLUMN_RENAME_MAP = {
    "ACC": "ASM",
    "ЭМ": "RS",
    "логин эм": "Логин RS"
}


def clean_data(df):
    """
    Основная функция очистки данных
    Возвращает: (cleaned_df, deleted_df)
    """
    # Создаем копию для работы
    working_df = df.copy()
    
    # ============ ДОБАВЛЕНИЕ НОВЫХ КОЛОНОК ============
    # 1. Добавляем колонку "сцеп" в начало (перед Портал)
    working_df.insert(0, 'сцеп', working_df['ClientName'].astype(str) + '&' + working_df['BranchName'].astype(str))
    
    # 2. Находим позицию колонки "ЭМ" (она уже есть в файле после ВСЕГО)
    em_col_index = working_df.columns.get_loc('ЭМ')
    
    # 3. Добавляем колонки после "ЭМ"
    new_columns_after_total = [
        'логин эм',
        'проектная мотивация',
        'ЧТО-ТО',
        'Тип квоты',
        'отдельная мотивация',
        'квота',
        'закрытие',
        'коэффициент',
        'ставка',
        'зп эм',
        'надбавка за квоту',
        'надбавка на анкету',
        'рекрут',
        'рекрут на анкету',
        'корректировка',
        'корректировка на анкету',
        'корректировка холостых',
        'Итого затраты на эм'
    ]
    
    # Вставляем колонки по одной, начиная с позиции после ЭМ
    for i, col_name in enumerate(new_columns_after_total):
        working_df.insert(em_col_index + 1 + i, col_name, '')
    
    # Добавляем колонку для отслеживания причины удаления
    working_df['Причина_удаления'] = ""
    
    deleted_rows = []
    
    # ============ ПРЕДВАРИТЕЛЬНАЯ ОБРАБОТКА: замены в колонке ACC ============
    working_df['ACC'] = working_df['ACC'].replace(ACC_REPLACEMENTS)
    
    # ============ ШАГ 1: Фильтрация по менеджерам (колонка ACC) ============
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
    
    # ============ ШАГ 2: Стандартизация типов проекта ============
    if not working_df.empty:
        def standardize_project_type(row):
            project_type = normalize_text(row['Тип проекта (р/бр/неполевой)'])
            client_name = normalize_text(row['ClientName'])
            original_value = row['Тип проекта (р/бр/неполевой)']
            
            # Шаг 1: Мултон
            if client_name == "мултон":
                return "Мултон"
            
            # Шаг 2: Мониторинги
            if "монитор" in project_type:
                return "Мониторинги"
            
            # Шаг 3: Опросы
            if "опрос" in project_type:
                return "Опросы"
            
            # Шаг 4: Ротационный (есть "ротац", нет "б")
            if "ротац" in project_type:
                if "б" not in project_type:
                    return "Ротационный"
                else:
                    return "Безротационный"
            
            # Шаг 6: Не определен - возвращаем ИСХОДНОЕ значение
            return original_value
        
        # Применяем стандартизацию
        working_df['Тип проекта (р/бр/неполевой)'] = working_df.apply(
            standardize_project_type, axis=1
        )
        
        # Определяем, какие строки были НЕ определены
        valid_types = ["Мултон", "Мониторинги", "Опросы", "Ротационный", "Безротационный"]
        invalid_type_mask = ~working_df['Тип проекта (р/бр/неполевой)'].isin(valid_types)
        
        deleted = working_df[invalid_type_mask].copy()
        if not deleted.empty:
            deleted['Причина_удаления'] = "Некорректный тип проекта"
            deleted_rows.append(deleted)
        
        working_df = working_df[~invalid_type_mask].copy()
    
    # ============ ШАГ 3: Фильтрация по столбцу "Проекты" ============
    if not working_df.empty:
        def process_project(value):
            if pd.isna(value):
                return value
            
            val_str = str(value)
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
    if not working_df.empty:
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
    # Удаляем колонку Причина_удаления из очищенного
    if not working_df.empty and 'Причина_удаления' in working_df.columns:
        cleaned_df = working_df.drop(columns=['Причина_удаления'])
    else:
        cleaned_df = working_df
    
    # Переименовываем колонки в очищенном
    cleaned_df = cleaned_df.rename(columns=COLUMN_RENAME_MAP)
    
    # Удаленные строки
    if deleted_rows:
        deleted_df = pd.concat(deleted_rows, ignore_index=True)
        # Переименовываем колонки в удаленном
        deleted_df = deleted_df.rename(columns=COLUMN_RENAME_MAP)
    else:
        all_columns = df.columns.tolist() + ['Причина_удаления']
        # Переименовываем колонки для пустого DataFrame
        all_columns_renamed = [COLUMN_RENAME_MAP.get(col, col) for col in all_columns]
        deleted_df = pd.DataFrame(columns=all_columns_renamed)
    
    return cleaned_df, deleted_df


def fill_rs_and_em(cleaned_df, projects_df, name_login_df):
    """
    Заполняет колонки Логин RS и RS (бывшая ЭМ)
    
    Args:
        cleaned_df: очищенный массив (DataFrame) - уже с переименованными колонками
        projects_df: справочник "Проекты вне чеккера" (DataFrame)
        name_login_df: справочник "Имя-логин" (DataFrame)
    
    Returns:
        DataFrame с заполненными колонками
    """
    df = cleaned_df.copy()
    
    # ============ ШАГ 1: Заполнение Логин RS из "Проекты вне чеккера" ============
    if projects_df is not None and not projects_df.empty:
        # Создаем словарь для быстрого поиска
        project_dict = {}
        for _, row in projects_df.iterrows():
            key = (str(row['номер локации']).strip(), str(row['Код проекта']).strip())
            project_dict[key] = str(row['логин ЭМ кто назначил']).strip()
        
        # Заполняем Логин RS
        def get_login_rs(row):
            key = (str(row['BranchID']).strip(), str(row['SetCode']).strip())
            return project_dict.get(key, row['Логин RS'])
        
        df['Логин RS'] = df.apply(get_login_rs, axis=1)
    
    # ============ ШАГ 2: Дозаполнение Логин RS через RS (если пусто) ============
    if name_login_df is not None and not name_login_df.empty:
        # Создаем два словаря:
        # 1. логин эм → ЭМ (полное имя)
        # 2. ЭМ (полное имя) → логин эм (обратный поиск)
        login_to_name = {}
        name_to_login = {}
        for _, row in name_login_df.iterrows():
            login = str(row['логин эм']).strip()
            name = str(row['ЭМ']).strip()
            login_to_name[login] = name
            name_to_login[name] = login
        
        # Дозаполняем Логин RS через RS
        def fill_login_rs(row):
            login_rs = str(row['Логин RS']).strip()
            rs_value = str(row['RS']).strip()
            
            # Если Логин RS пустой и RS заполнена
            if login_rs == '' and rs_value != '':
                # Ищем RS (полное имя) в словаре name_to_login
                if rs_value in name_to_login:
                    return name_to_login[rs_value]
            
            return row['Логин RS']
        
        df['Логин RS'] = df.apply(fill_login_rs, axis=1)
        
        # ============ ШАГ 3: Заполнение RS (бывшая ЭМ) ============
        def get_rs(row):
            rs_value = str(row['RS']).strip()
            login_rs = str(row['Логин RS']).strip()
            
            # Проверяем, что RS пустая или содержит - / 0 / koordinator
            if rs_value == '' or rs_value == '-' or rs_value == '0' or 'koordinator' in rs_value.lower():
                # Ищем в словаре по логин rs
                if login_rs in login_to_name:
                    return login_to_name[login_rs]
            
            return row['RS']
        
        df['RS'] = df.apply(get_rs, axis=1)
    
    return df
