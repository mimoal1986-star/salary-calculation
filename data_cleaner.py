# ==================== data_cleaner.py ====================
"""
Логика очистки данных и заполнения колонок
"""

import pandas as pd
from utils import normalize_text, is_empty_value

# Разрешенные менеджеры (проверяем по колонке ACC)
ALLOWED_MANAGERS = [
    "Аблязимова Екатерина",
    "Герасимова Светлана",
    "Карлышева Алиса",
    "Механошина Елена",
    "Солодникова Виктория",
    "Шавлюк Юлия",
    "Кузнецова Екатерина",
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
        'зп RS',
        'надбавка за квоту',
        'надбавка на анкету',
        'рекрут',
        'рекрут на анкету',
        'корректировка',
        'корректировка на анкету',
        'корректировка холостых',
        'Итого затраты на RS'
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
            if any("опрос" in str(val).lower() for val in row.values):
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
            lambda x: str(x).startswith('_') and '_single' not in str(x).lower()
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
    """
    df = cleaned_df.copy()
    
    # ============ ШАГ 1: Заполнение Логин RS из "Проекты вне чеккера" ============
    if projects_df is not None and not projects_df.empty:
        project_dict = {}
        for _, row in projects_df.iterrows():
            key = (str(row['номер локации']).strip(), str(row['Код проекта']).strip())
            project_dict[key] = str(row['логин ЭМ кто назначил']).strip()
        
        def get_login_rs(row):
            key = (str(row['BranchID']).strip(), str(row['SetCode']).strip())
            return project_dict.get(key, row['Логин RS'])
        
        df['Логин RS'] = df.apply(get_login_rs, axis=1)
    
    # ============ ШАГ 2: Дозаполнение Логин RS через RS (если пусто) ============
    if name_login_df is not None and not name_login_df.empty:
        login_to_name = {}
        name_to_login = {}
        for _, row in name_login_df.iterrows():
            login = str(row['логин эм']).strip().lower()
            name = str(row['ЭМ']).strip()
            login_to_name[login] = name
            name_to_login[name] = login
        
        def fill_login_rs(row):
            login_rs = str(row['Логин RS']).strip()
            rs_value = str(row['RS']).strip()
            
            if is_empty_value(login_rs) and not is_empty_value(rs_value):
                if rs_value in name_to_login:
                    return name_to_login[rs_value]
            
            return row['Логин RS']
        
        df['Логин RS'] = df.apply(fill_login_rs, axis=1)
        
        # ============ ШАГ 3: Заполнение RS (бывшая ЭМ) ============
        def get_rs(row):
            rs_value = str(row['RS']).strip()
            login_rs = str(row['Логин RS']).strip()
            
            if is_empty_value(rs_value) or 'koordinator' in rs_value.lower() or 'rukovoditel' in rs_value.lower():
                if login_rs.lower() in login_to_name:
                    return login_to_name[login_rs.lower()]
            
            return row['RS']
    
        df['RS'] = df.apply(get_rs, axis=1)
    
    return df


def fill_project_motivation(cleaned_df, project_motivation_df):
    df = cleaned_df.copy()
    invalid_projects = []
    
    if project_motivation_df is not None and not project_motivation_df.empty:
        motivation_dict = {}
        for _, row in project_motivation_df.iterrows():
            client_name = str(row['Имя клиента']).strip()
            motivation = row['Мотивация']
            
            if motivation != 1:
                invalid_projects.append(client_name)
            
            motivation_dict[client_name] = motivation
        
        def get_motivation(row):
            client_name = str(row['ClientName']).strip()
            return motivation_dict.get(client_name, 0)
        
        df['проектная мотивация'] = df.apply(get_motivation, axis=1)
    
    return df, invalid_projects


def fill_region_type(cleaned_df, region_type_df):
    df = cleaned_df.copy()
    invalid_regions = []
    
    if region_type_df is not None and not region_type_df.empty:
        region_dict = {}
        for _, row in region_type_df.iterrows():
            lo = str(row['Lo']).strip()
            region_type = str(row['ДВ']).strip()
            region_dict[lo] = region_type
        
        def get_region_type(row):
            region = str(row['RegionName согласно распределения АСС']).strip()
            return region_dict.get(region, '')
        
        df['Тип квоты'] = df.apply(get_region_type, axis=1)
        
        all_regions = df['RegionName согласно распределения АСС'].astype(str).str.strip().unique()
        missing_regions = [r for r in all_regions if r and r not in region_dict]
        if missing_regions:
            invalid_regions = missing_regions
    
    return df, invalid_regions


def fill_separate_motivation(cleaned_df):
    df = cleaned_df.copy()
    
    df['ЧТО-ТО'] = pd.to_numeric(df['ЧТО-ТО'], errors='coerce').fillna(0)
    df['ВСЕГО'] = pd.to_numeric(df['ВСЕГО'], errors='coerce').fillna(0)
    df['проектная мотивация'] = pd.to_numeric(df['проектная мотивация'], errors='coerce').fillna(0)
    
    df['отдельная мотивация'] = df.apply(
        lambda row: row['ЧТО-ТО'] - row['ВСЕГО'] if row['проектная мотивация'] == 1 else '',
        axis=1
    )
    
    return df


def fill_quota(cleaned_df):
    df = cleaned_df.copy()
    
    quota_counts = df.groupby('Логин RS').size().to_dict()
    df['квота'] = df['Логин RS'].map(quota_counts).fillna(0).astype(int)
    
    return df


def fill_closing_coefficient_rate_salary(cleaned_df, hvosty_df):
    df = cleaned_df.copy()
    
    hvosty_counts = {}
    if hvosty_df is not None and not hvosty_df.empty:
        hvosty_counts = hvosty_df.groupby('эм').size().to_dict()
    
    df['хвосты_count'] = df['Логин RS'].map(hvosty_counts).fillna(0).astype(int)
    
    df['закрытие'] = df.apply(
        lambda row: (row['квота'] / (row['квота'] + row['хвосты_count']) * 100)
        if (row['квота'] + row['хвосты_count']) > 0 else 0,
        axis=1
    ).round(2)
    
    def get_coefficient(closing):
        if closing >= 100:
            return 1.0
        elif closing >= 99:
            return 0.8
        else:
            return 0.45
    
    df['коэффициент'] = df['закрытие'].apply(get_coefficient)
    
    def get_rate(row):
        region_type = str(row['Тип квоты']).strip()
        project_type = str(row['Тип проекта (р/бр/неполевой)']).strip()
        
        is_rotational = 'ротационный' in project_type.lower()
        is_complex = 'сложная' in region_type.lower()
        
        if is_complex:
            if is_rotational:
                return 150
            else:
                return 85
        else:
            if is_rotational:
                return 90
            else:
                return 50
    
    df['ставка'] = df.apply(get_rate, axis=1)
    
    df['зп RS'] = df['ставка'] * df['коэффициент']
    
    def get_bonus(quota):
        if quota >= 550:
            return 12000
        elif quota >= 350:
            return 8000
        else:
            return 0
    
    df['надбавка за квоту'] = df['квота'].apply(get_bonus)
    
    motivation_1_counts = df[df['проектная мотивация'] == 1].groupby('Логин RS').size().to_dict()
    df['мотивация_1_count'] = df['Логин RS'].map(motivation_1_counts).fillna(0).astype(int)
    
    df['надбавка на анкету'] = df.apply(
        lambda row: row['надбавка за квоту'] / (row['квота'] - row['мотивация_1_count'])
        if (row['квота'] - row['мотивация_1_count']) > 0 else 0,
        axis=1
    )
    
    df = df.drop(columns=['хвосты_count', 'мотивация_1_count'])
    
    return df


def fill_recruit_adjustments(cleaned_df, zp_shtrafy_df):
    df = cleaned_df.copy()
    
    motivation_1_counts = df[df['проектная мотивация'] == 1].groupby('Логин RS').size().to_dict()
    df['мотивация_1_count'] = df['Логин RS'].map(motivation_1_counts).fillna(0).astype(int)
    
    df['denominator'] = df['квота'] - df['мотивация_1_count']
    df['denominator'] = df['denominator'].apply(lambda x: x if x > 0 else 1)
    
    if zp_shtrafy_df is not None and not zp_shtrafy_df.empty:
        recruit_counts = zp_shtrafy_df.groupby('логин эм').size().to_dict()
        df['рекрут'] = df['Логин RS'].map(recruit_counts).fillna(0).astype(int) * 300
    else:
        df['рекрут'] = 0
    
    df['рекрут на анкету'] = df.apply(
        lambda row: row['рекрут'] / row['denominator'] if row['denominator'] > 0 else 0,
        axis=1
    )
    
    if zp_shtrafy_df is not None and not zp_shtrafy_df.empty:
        adjustment_sums = zp_shtrafy_df.groupby('логин эм ЧЕКЕР')['штраф/премия'].sum().to_dict()
        df['корректировка'] = df['Логин RS'].map(adjustment_sums).fillna(0)
    else:
        df['корректировка'] = 0
    
    df['корректировка на анкету'] = df.apply(
        lambda row: row['корректировка'] / row['denominator'] if row['denominator'] > 0 else 0,
        axis=1
    )
    
    df['корректировка холостых'] = df.apply(
        lambda row: -row['зп RS'] / 2 if str(row['Проекты']).strip() == '_SINGLE' else '',
        axis=1
    )
    
    cols_to_sum = ['зп RS', 'надбавка на анкету', 'рекрут на анкету', 'корректировка на анкету', 'корректировка холостых']
    for col in cols_to_sum:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    df['Итого затраты на RS'] = df[cols_to_sum].sum(axis=1)
    
    df = df.drop(columns=['мотивация_1_count', 'denominator'])
    
    return df


def fill_login_rs_from_distribution(cleaned_df, distribution_data):
    """
    Заполняет Логин RS из справочника "Распределение"
    
    Условие: Логин RS пустой И RS заполнена
    
    Логика:
    - Если регион = Москва → ищем по ClientName в moscow_mapping
    - Если регион = СПб → ищем по ClientName в spb_mapping
    - Если регион ≠ Москва и ≠ СПб → ищем по региону в region_mapping
    """
    df = cleaned_df.copy()
    
    if distribution_data is None:
        return df
    
    region_mapping = distribution_data.get('region_mapping', {})
    spb_mapping = distribution_data.get('spb_mapping', {})
    moscow_mapping = distribution_data.get('moscow_mapping', {})
    
    region_dict = {k.lower().strip(): v for k, v in region_mapping.items()}
    spb_dict = {k.lower().strip(): v for k, v in spb_mapping.items()}
    moscow_dict = {k.lower().strip(): v for k, v in moscow_mapping.items()}
    
    def get_login_rs(row):
        login_rs = str(row['Логин RS']).strip()
        rs_value = str(row['RS']).strip()
        region = str(row['RegionName согласно распределения АСС']).strip().lower()
        client_name = str(row['ClientName']).strip().lower()
        
        # Если Логин RS уже заполнен — пропускаем
        if not is_empty_value(login_rs):
            return row['Логин RS']
        
        # Если RS пустая — не заполняем
        if is_empty_value(rs_value):
            return row['Логин RS']
        
        # Определяем тип региона
        is_msk = any(x in region for x in ['mc', 'ms'])
        is_spb = any(x in region for x in ['ln',])
        
        if is_msk:
            # Москва — ищем по клиенту в moscow_mapping
            if client_name in moscow_dict:
                return moscow_dict[client_name]
        elif is_spb:
            # СПб — ищем по клиенту в spb_mapping
            if client_name in spb_dict:
                return spb_dict[client_name]
        else:
            # Регион — ищем по региону в region_mapping
            if region in region_dict:
                return region_dict[region]
        
        return row['Логин RS']
    
    df['Логин RS'] = df.apply(get_login_rs, axis=1)
    
    return df


def fill_rs_login_from_projects(cleaned_df, projects_df):
    """
    Заполняет Логин RS из справочника "Проекты вне чеккера"
    по сцепке SetCode + Address
    
    Условие: RS пусто И Логин RS пусто
    
    Запускать ПОСЛЕ всех обогащений!
    """
    df = cleaned_df.copy()
    
    if projects_df is None or projects_df.empty:
        return df
    
    project_dict = {}
    for _, row in projects_df.iterrows():
        code = str(row['Код проекта']).strip()
        address = str(row['адрес']).strip()
        login = str(row['логин ЭМ кто назначил']).strip()
        
        if code and address and login:
            key = (code, address)
            project_dict[key] = login
    
    def fill_row(row):
        login_rs = str(row['Логин RS']).strip()
        rs_value = str(row['RS']).strip()
        
        is_login_empty = is_empty_value(login_rs)
        is_rs_empty = is_empty_value(rs_value)
        
        # Если оба не пустые — пропускаем
        if not is_login_empty and not is_rs_empty:
            return row
        
        # Если Логин RS не пустой, но RS пустой — пропускаем (это кейс для другого обогащения)
        if not is_login_empty and is_rs_empty:
            return row
        
        # Если оба пустые — ищем в справочнике
        if is_login_empty and is_rs_empty:
            set_code = str(row['SetCode']).strip()
            address = str(row['Address']).strip()
            
            key = (set_code, address)
            if key in project_dict:
                login = project_dict[key]
                row['Логин RS'] = login
        
        return row
    
    df = df.apply(fill_row, axis=1)
    
    return df

def fill_multon(cleaned_df, multon_df):
    """
    Заполняет Логин RS и ЧТО-ТО из справочника Мултон
    
    Условие: Тип проекта = Мултон И CritID = Номер анкеты с ПО
    
    Запускать ПОСЛЕ всех обогащений!
    """
    df = cleaned_df.copy()
    
    if multon_df is None or multon_df.empty:
        return df
    
    # Создаем словарь: Номер анкеты с ПО → (логин ЭМ кто назначил, Проектная)
    multon_dict = {}
    for _, row in multon_df.iterrows():
        anketa = str(row['Номер анкеты с ПО']).strip()
        login = str(row['логин ЭМ кто назначил']).strip()
        project_motivation = row['Проектная']
        
        if anketa and login:
            multon_dict[anketa] = (login, project_motivation)
    
    def fill_row(row):
        # Проверяем, что тип проекта = Мултон
        project_type = str(row['Тип проекта (р/бр/неполевой)']).strip()
        if project_type != 'Мултон':
            return row
        
        crit_id = str(row['CritID']).strip()
        
        # Проверяем, что CritID не пустой
        if is_empty_value(crit_id):
            return row
        
        if crit_id in multon_dict:
            login, motivation = multon_dict[crit_id]
            if not is_empty_value(login):
                row['Логин RS'] = login
            row['отдельная мотивация'] = motivation
        
        return row
    
    df = df.apply(fill_row, axis=1)
    
    return df
