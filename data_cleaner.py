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


def fill_project_motivation(cleaned_df, project_motivation_df):
    """
    Заполняет колонку Проектная мотивация
    
    Args:
        cleaned_df: очищенный массив (DataFrame)
        project_motivation_df: справочник "Проект-Мотивация" (DataFrame)
    
    Returns:
        DataFrame с заполненной колонкой Проектная мотивация
        и список проектов с ошибками
    """
    df = cleaned_df.copy()
    invalid_projects = []
    
    if project_motivation_df is not None and not project_motivation_df.empty:
        # Создаем словарь: Имя проекта → Мотивация
        motivation_dict = {}
        for _, row in project_motivation_df.iterrows():
            project_name = str(row['Имя проекта']).strip()
            motivation = row['Мотивация']
            
            # Проверяем, что мотивация = 1
            if motivation != 1:
                invalid_projects.append(project_name)
            
            motivation_dict[project_name] = motivation
        
        # Заполняем Проектная мотивация
        def get_motivation(row):
            project = str(row['Проекты']).strip()
            return motivation_dict.get(project, 0)
        
        df['проектная мотивация'] = df.apply(get_motivation, axis=1)
    
    return df, invalid_projects


def fill_region_type(cleaned_df, region_type_df):
    """
    Заполняет колонку Тип квоты из справочника Регион-Тип
    
    Args:
        cleaned_df: очищенный массив (DataFrame)
        region_type_df: справочник "Регион-Тип" (DataFrame)
    
    Returns:
        DataFrame с заполненной колонкой Тип квоты
        и список регионов с ошибками
    """
    df = cleaned_df.copy()
    invalid_regions = []
    
    if region_type_df is not None and not region_type_df.empty:
        # Создаем словарь: Lo → ДВ (Тип)
        region_dict = {}
        for _, row in region_type_df.iterrows():
            lo = str(row['Lo']).strip()
            region_type = str(row['ДВ']).strip()
            region_dict[lo] = region_type
        
        # Заполняем Тип квоты
        def get_region_type(row):
            region = str(row['RegionName согласно распределения АСС']).strip()
            return region_dict.get(region, '')
        
        df['Тип квоты'] = df.apply(get_region_type, axis=1)
        
        # Находим регионы, которых нет в справочнике
        all_regions = df['RegionName согласно распределения АСС'].astype(str).str.strip().unique()
        missing_regions = [r for r in all_regions if r and r not in region_dict]
        if missing_regions:
            invalid_regions = missing_regions
    
    return df, invalid_regions

def fill_separate_motivation(cleaned_df):
    """
    Заполняет колонку отдельная мотивация
    
    Логика:
    - Если проектная мотивация = 1 → отдельная мотивация = ЧТО-ТО - ВСЕГО
    - Иначе → отдельная мотивация = пусто
    """
    df = cleaned_df.copy()
    
    # Преобразуем колонки в числа
    df['ЧТО-ТО'] = pd.to_numeric(df['ЧТО-ТО'], errors='coerce').fillna(0)
    df['ВСЕГО'] = pd.to_numeric(df['ВСЕГО'], errors='coerce').fillna(0)
    df['проектная мотивация'] = pd.to_numeric(df['проектная мотивация'], errors='coerce').fillna(0)
    
    # Если проектная мотивация = 1 → ЧТО-ТО - ВСЕГО, иначе пусто
    df['отдельная мотивация'] = df.apply(
        lambda row: row['ЧТО-ТО'] - row['ВСЕГО'] if row['проектная мотивация'] == 1 else '',
        axis=1
    )
    
    return df

def fill_quota(cleaned_df):
    """
    Заполняет колонку квота = количество записей по каждому Логин RS
    """
    df = cleaned_df.copy()
    
    # Считаем количество записей по каждому Логин RS
    quota_counts = df.groupby('Логин RS').size().to_dict()
    
    # Заполняем квоту
    df['квота'] = df['Логин RS'].map(quota_counts).fillna(0).astype(int)
    
    return df

def fill_closing_coefficient_rate_salary(cleaned_df, hvosty_df):
    """
    Заполняет колонки: закрытие, коэффициент, ставка, зп эм,
    надбавка за квоту, надбавка на анкету
    
    Args:
        cleaned_df: очищенный массив (DataFrame)
        hvosty_df: справочник "Хвосты" (DataFrame)
    
    Returns:
        DataFrame с заполненными колонками
    """
    df = cleaned_df.copy()
    
    # ============ 1. Считаем Хвосты по каждому Логин RS ============
    hvosty_counts = {}
    if hvosty_df is not None and not hvosty_df.empty:
        # Считаем количество хвостов по колонке 'эм'
        hvosty_counts = hvosty_df.groupby('эм').size().to_dict()
    
    # Добавляем колонку с количеством хвостов для каждого Логин RS
    df['хвосты_count'] = df['Логин RS'].map(hvosty_counts).fillna(0).astype(int)
    
    # ============ 2. Закрытие ============
    # Закрытие = Квота / (Квота + Хвосты)
    df['закрытие'] = df.apply(
        lambda row: row['квота'] / (row['квота'] + row['хвосты_count']) 
        if (row['квота'] + row['хвосты_count']) > 0 else 0,
        axis=1
    )
    # Округляем до 3 знаков и преобразуем в проценты для отображения
    df['закрытие_процент'] = (df['закрытие'] * 100).round(2)
    
    # ============ 3. Коэффициент ============
    def get_coefficient(closing):
        if closing >= 1.0:
            return 1.0
        elif closing >= 0.99:
            return 0.8
        else:
            return 0.45
    
    df['коэффициент'] = df['закрытие'].apply(get_coefficient)
    
    # ============ 4. Ставка ============
    def get_rate(row):
        region_type = str(row['Тип квоты']).strip()
        project_type = str(row['Тип проекта (р/бр/неполевой)']).strip()
        
        # Определяем тип проекта (ротационный/безротационный)
        is_rotational = 'ротационный' in project_type.lower()
        
        # Определяем тип региона
        is_complex = 'сложная' in region_type.lower()
        
        if is_complex:
            if is_rotational:
                return 150  # Сложная + Ротация
            else:
                return 85   # Сложная + Без ротации
        else:  # Обычная
            if is_rotational:
                return 90   # Обычная + Ротация
            else:
                return 50   # Обычная + Без ротации
    
    df['ставка'] = df.apply(get_rate, axis=1)
    
    # ============ 5. зп эм = ставка * коэффициент ============
    df['зп эм'] = df['ставка'] * df['коэффициент']
    
    # ============ 6. надбавка за квоту ============
    def get_bonus(quota):
        if quota >= 550:
            return 12000
        elif quota >= 350:
            return 8000
        else:
            return 0
    
    df['надбавка за квоту'] = df['квота'].apply(get_bonus)
    
    # ============ 7. надбавка на анкету ============
    # Считаем количество строк с проектная мотивация = 1 по каждому Логин RS
    motivation_1_counts = df[df['проектная мотивация'] == 1].groupby('Логин RS').size().to_dict()
    df['мотивация_1_count'] = df['Логин RS'].map(motivation_1_counts).fillna(0).astype(int)
    
    # Надбавка на анкету = надбавка за квоту / (квота - кол-во строк с проектная мотивация = 1)
    df['надбавка на анкету'] = df.apply(
        lambda row: row['надбавка за квоту'] / (row['квота'] - row['мотивация_1_count'])
        if (row['квота'] - row['мотивация_1_count']) > 0 else 0,
        axis=1
    )
    
    # Удаляем вспомогательные колонки
    df = df.drop(columns=['хвосты_count', 'закрытие_процент', 'мотивация_1_count'])
    
    return df

def fill_recruit_adjustments(cleaned_df, zp_shtrafy_df):
    """
    Заполняет колонки: рекрут, рекрут на анкету, корректировка,
    корректировка на анкету, корректировка холостых, Итого затраты на эм
    
    Args:
        cleaned_df: очищенный массив (DataFrame)
        zp_shtrafy_df: справочник "ЗП_штрафы" (DataFrame)
    
    Returns:
        DataFrame с заполненными колонками
    """
    df = cleaned_df.copy()
    
    # Считаем количество строк с проектная мотивация = 1 по каждому Логин RS
    motivation_1_counts = df[df['проектная мотивация'] == 1].groupby('Логин RS').size().to_dict()
    df['мотивация_1_count'] = df['Логин RS'].map(motivation_1_counts).fillna(0).astype(int)
    
    # Знаменатель для рекрут на анкету и корректировка на анкету
    df['denominator'] = df['квота'] - df['мотивация_1_count']
    df['denominator'] = df['denominator'].apply(lambda x: x if x > 0 else 1)  # Защита от деления на 0
    
    # ============ 1. Рекрут ============
    if zp_shtrafy_df is not None and not zp_shtrafy_df.empty:
        # Считаем количество записей по логин эм в ЗП_штрафы
        recruit_counts = zp_shtrafy_df.groupby('логин эм').size().to_dict()
        
        # Рекрут = COUNT * 300
        df['рекрут'] = df['Логин RS'].map(recruit_counts).fillna(0).astype(int) * 300
    else:
        df['рекрут'] = 0
    
    # ============ 2. Рекрут на анкету ============
    df['рекрут на анкету'] = df.apply(
        lambda row: row['рекрут'] / row['denominator'] if row['denominator'] > 0 else 0,
        axis=1
    )
    
    # ============ 3. Корректировка ============
    if zp_shtrafy_df is not None and not zp_shtrafy_df.empty:
        # Суммируем штраф/премия по логин эм ЧЕКЕР
        adjustment_sums = zp_shtrafy_df.groupby('логин эм ЧЕКЕР')['штраф/премия'].sum().to_dict()
        
        df['корректировка'] = df['Логин RS'].map(adjustment_sums).fillna(0)
    else:
        df['корректировка'] = 0
    
    # ============ 4. Корректировка на анкету ============
    df['корректировка на анкету'] = df.apply(
        lambda row: row['корректировка'] / row['denominator'] if row['denominator'] > 0 else 0,
        axis=1
    )
    
    # ============ 5. Корректировка холостых ============
    df['корректировка холостых'] = df.apply(
        lambda row: -row['зп эм'] / 2 if str(row['Проекты']).strip() == '_SINGLE' else '',
        axis=1
    )
    
    # ============ 6. Итого затраты на эм ============
    # Преобразуем все в числа для суммирования
    cols_to_sum = ['зп эм', 'надбавка на анкету', 'рекрут на анкету', 'корректировка на анкету', 'корректировка холостых']
    for col in cols_to_sum:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    df['Итого затраты на эм'] = df[cols_to_sum].sum(axis=1)
    
    # Удаляем вспомогательные колонки
    df = df.drop(columns=['мотивация_1_count', 'denominator'])
    
    return df
