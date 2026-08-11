# ==================== app.py ====================
import streamlit as st
import pandas as pd
from datetime import datetime

from data_loader import load_excel, validate_columns, clear_cache
from data_cleaner import (
    clean_data,
    fill_rs_and_em,
    fill_project_motivation,
    fill_region_type,
    fill_separate_motivation,
    fill_quota,
    fill_closing_coefficient_rate_salary,
    fill_recruit_adjustments
)
from report_generator import create_cleaned_excel, create_deleted_excel, get_filename
from settings_loader import (
    load_region_type,
    load_project_motivation,
    load_name_login,
    save_to_json_github,
    load_from_json_github
)

# ==================== НАСТРОЙКА СТРАНИЦЫ ====================
st.set_page_config(
    page_title="Расчет ЗП",
    page_icon="💰",
    layout="wide"
)

st.title("💰 Расчет ЗП")

# ==================== ИНИЦИАЛИЗАЦИЯ СЕССИИ ====================
DEFAULT_STATE = {
    'cleaned_excel': None,
    'deleted_excel': None,
    'is_cleaned': False,
    'original_df': None,
    'total_rows': 0,
    'cleaned_rows': 0,
    'deleted_rows': 0,
    'columns_valid': False,
    'zp_shtrafy_df': None,
    'zp_shtrafy_time': None,
    'projects_outside_checker_df': None,
    'projects_outside_checker_time': None,
    'hvosty_df': None,
    'hvosty_time': None,
    'name_login_df': None
}

for key, default_value in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = default_value

# ==================== ЗАГРУЗКА СПРАВОЧНИКОВ ИЗ GITHUB ====================
# Загружаем справочник "Имя-логин" из GitHub при старте
name_login_data = load_from_json_github('name_login')
if name_login_data is not None:
    st.session_state.name_login_df = pd.DataFrame(name_login_data['data'])

# ==================== СОЗДАНИЕ ВКЛАДОК ====================
tab1, tab2 = st.tabs(["📊 Основная", "⚙️ Настройки"])

# ==================== ВКЛАДКА 1: ОСНОВНАЯ ====================
with tab1:
    st.markdown("---")
    
    # Загрузка файла
    uploaded_file = st.file_uploader(
        "📁 Загрузите Excel-файл 'Массив итоги месяца'",
        type=['xlsx', 'xls'],
        key="main_file"
    )
    
    # ==================== ЗАГРУЗКА ФАЙЛА ====================
    if uploaded_file is not None:
        # Загружаем файл (только один раз)
        if st.session_state.original_df is None:
            with st.spinner("Загрузка файла..."):
                df, error = load_excel(uploaded_file)
                if error:
                    st.error(f"❌ {error}")
                    st.stop()
                
                is_valid, error_msg, _ = validate_columns(df)
                if not is_valid:
                    st.error(f"❌ {error_msg}")
                    st.session_state.columns_valid = False
                    st.stop()
                else:
                    st.session_state.columns_valid = True
                
                st.session_state.original_df = df
                st.session_state.total_rows = len(df)
                st.session_state.is_cleaned = False
        
        df = st.session_state.original_df
    
    # ==================== СТАТИСТИКА (ВСЕГДА ВИДНА) ====================
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📊 Всего строк", st.session_state.total_rows)
    with col2:
        status = "✅ Присутствуют" if st.session_state.columns_valid else "❌ Отсутствуют"
        st.metric("📋 Все колонки", status)
    with col3:
        deleted = st.session_state.deleted_rows if st.session_state.is_cleaned else 0
        st.metric("🗑️ Удалено строк", deleted)
    
    # ==================== ИНДИКАТОР ТЕКУЩЕГО ФАЙЛА ====================
    if st.session_state.original_df is not None and uploaded_file is not None:
        st.caption(f"📄 Текущий файл: **{uploaded_file.name}** ({st.session_state.total_rows} строк)")
    
    st.markdown("---")
    
    # ==================== ДОПОЛНИТЕЛЬНЫЕ ЗАГРУЗЧИКИ (ВСЕГДА ВИДНЫ) ====================
    st.subheader("📁 Дополнительные справочники")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.caption("ЗП_штрафы")
        zp_file = st.file_uploader(
            "Загрузите файл",
            type=['xlsx', 'xls'],
            key="zp_shtrafy",
            label_visibility="collapsed"
        )
        
        # ==================== СТАТУС С ПРЕДУПРЕЖДЕНИЕМ О ПЕРЕЗАПИСИ ====================
        if st.session_state.zp_shtrafy_df is not None:
            st.success(f"✅ Загружено: {len(st.session_state.zp_shtrafy_df)} записей")
            if st.session_state.zp_shtrafy_time:
                st.caption(f"🕐 {st.session_state.zp_shtrafy_time}")
            if zp_file is not None:
                st.warning("⚠️ Новый файл перезапишет текущий справочник")
        else:
            st.info("📎 Файл не загружен")
        
        if zp_file is not None:
            with st.spinner("Загрузка ЗП_штрафы..."):
                try:
                    df_shtrafy = pd.read_excel(zp_file, engine='openpyxl')
                    st.session_state.zp_shtrafy_df = df_shtrafy
                    st.session_state.zp_shtrafy_time = datetime.now().strftime("%d.%m.%Y %H:%M")
                    st.toast(f"✅ Загружено {len(df_shtrafy)} записей", icon="✅")
                except Exception as e:
                    st.toast(f"❌ Ошибка: {str(e)}", icon="❌")
    
    with col2:
        st.caption("Проекты вне чеккера")
        projects_file = st.file_uploader(
            "Загрузите файл",
            type=['xlsx', 'xls'],
            key="projects_outside_checker",
            label_visibility="collapsed"
        )
        
        if st.session_state.projects_outside_checker_df is not None:
            st.success(f"✅ Загружено: {len(st.session_state.projects_outside_checker_df)} записей")
            if st.session_state.projects_outside_checker_time:
                st.caption(f"🕐 {st.session_state.projects_outside_checker_time}")
            if projects_file is not None:
                st.warning("⚠️ Новый файл перезапишет текущий справочник")
        else:
            st.info("📎 Файл не загружен")
        
        if projects_file is not None:
            with st.spinner("Загрузка Проекты вне чеккера..."):
                try:
                    df_projects = pd.read_excel(projects_file, engine='openpyxl')
                    st.session_state.projects_outside_checker_df = df_projects
                    st.session_state.projects_outside_checker_time = datetime.now().strftime("%d.%m.%Y %H:%M")
                    st.toast(f"✅ Загружено {len(df_projects)} записей", icon="✅")
                except Exception as e:
                    st.toast(f"❌ Ошибка: {str(e)}", icon="❌")
    
    with col3:
        st.caption("Хвосты")
        hvosty_file = st.file_uploader(
            "Загрузите файл",
            type=['xlsx', 'xls'],
            key="hvosty",
            label_visibility="collapsed"
        )
        
        if st.session_state.hvosty_df is not None:
            st.success(f"✅ Загружено: {len(st.session_state.hvosty_df)} записей")
            if st.session_state.hvosty_time:
                st.caption(f"🕐 {st.session_state.hvosty_time}")
            if hvosty_file is not None:
                st.warning("⚠️ Новый файл перезапишет текущий справочник")
        else:
            st.info("📎 Файл не загружен")
        
        if hvosty_file is not None:
            with st.spinner("Загрузка Хвосты..."):
                try:
                    df_hvosty = pd.read_excel(hvosty_file, engine='openpyxl')
                    st.session_state.hvosty_df = df_hvosty
                    st.session_state.hvosty_time = datetime.now().strftime("%d.%m.%Y %H:%M")
                    st.toast(f"✅ Загружено {len(df_hvosty)} записей", icon="✅")
                except Exception as e:
                    st.toast(f"❌ Ошибка: {str(e)}", icon="❌")
    
    st.markdown("---")
    
    # ==================== КНОПКА СБРОСА ====================
    if st.button("🗑️ Сбросить все данные", use_container_width=True):
        # 1. Очищаем кэш загрузки
        clear_cache()
        
        # 2. Сбрасываем все переменные session_state
        for key in list(DEFAULT_STATE.keys()):
            st.session_state[key] = DEFAULT_STATE[key]
        
        st.success("✅ Все данные и кэш очищены")
        st.rerun()
    
    st.markdown("---")
    
    # ==================== КНОПКА ЗАПУСКА ====================
    # Кнопка активна только если загружен основной файл
    if st.session_state.original_df is not None:
        if st.button("🚀 Запустить расчет", type="primary", use_container_width=True):
            with st.spinner("Выполняется расчет..."):
                try:
                    df = st.session_state.original_df
                    
                    # Прогресс-бар
                    progress_bar = st.progress(0, text="Начинаем расчет...")
                    
                    # Шаг 1: Очистка данных
                    progress_bar.progress(10, text="Очистка данных...")
                    cleaned_df, deleted_df = clean_data(df)
                    
                    # Шаг 2: Заполнение Логин RS и RS (бывшая ЭМ)
                    progress_bar.progress(25, text="Заполнение Логин RS и RS...")
                    if st.session_state.projects_outside_checker_df is not None:
                        cleaned_df = fill_rs_and_em(
                            cleaned_df,
                            st.session_state.projects_outside_checker_df,
                            st.session_state.name_login_df
                        )
                    
                    # Шаг 3: Заполнение Проектная мотивация
                    progress_bar.progress(35, text="Заполнение Проектная мотивация...")
                    project_motivation_data = load_from_json_github('project_motivation')
                    if project_motivation_data is not None:
                        project_motivation_df = pd.DataFrame(project_motivation_data['data'])
                        cleaned_df, invalid_projects = fill_project_motivation(cleaned_df, project_motivation_df)
                        if invalid_projects:
                            st.warning(f"⚠️ Проекты с мотивацией ≠ 1: {', '.join(invalid_projects)}")
                    
                    # Шаг 4: Заполнение Тип квоты (Регион-Тип)
                    progress_bar.progress(45, text="Заполнение Тип квоты...")
                    region_type_data = load_from_json_github('region_type')
                    if region_type_data is not None:
                        region_type_df = pd.DataFrame(region_type_data['data'])
                        cleaned_df, invalid_regions = fill_region_type(cleaned_df, region_type_df)
                        if invalid_regions:
                            st.warning(f"⚠️ Регионы не найдены в справочнике: {', '.join(invalid_regions)}")
                    
                    # Шаг 5: Заполнение отдельная мотивация = ЧТО-ТО - ВСЕГО
                    progress_bar.progress(55, text="Заполнение отдельная мотивация...")
                    cleaned_df = fill_separate_motivation(cleaned_df)
                    
                    # Шаг 6: Заполнение квота = количество записей по Логин RS
                    progress_bar.progress(65, text="Заполнение квота...")
                    cleaned_df = fill_quota(cleaned_df)

                    # Шаг 7: Заполнение закрытие, коэффициент, ставка, зп эм, надбавка за квоту, надбавка на анкету
                    progress_bar.progress(75, text="Расчет закрытия, коэффициента, ставки...")
                    cleaned_df = fill_closing_coefficient_rate_salary(cleaned_df, st.session_state.hvosty_df)
                    
                    # Шаг 8: Заполнение рекрут, рекрут на анкету, корректировка, корректировка на анкету, корректировка холостых, Итого затраты на эм
                    progress_bar.progress(90, text="Расчет рекрута и корректировок...")
                    cleaned_df = fill_recruit_adjustments(cleaned_df, st.session_state.zp_shtrafy_df)
                    
                    # Шаг 9: Округление всех дробных чисел до 2 знаков
                    progress_bar.progress(95, text="Округление...")
                    cleaned_df = cleaned_df.round(2)

                    # Сохранение результатов
                    progress_bar.progress(100, text="Сохранение результатов...")
                    st.session_state.cleaned_excel = create_cleaned_excel(cleaned_df)
                    if not deleted_df.empty:
                        st.session_state.deleted_excel = create_deleted_excel(deleted_df)
                    else:
                        st.session_state.deleted_excel = None
                    
                    st.session_state.is_cleaned = True
                    st.session_state.cleaned_rows = len(cleaned_df)
                    st.session_state.deleted_rows = len(deleted_df)
                    
                    # Убираем прогресс-бар после завершения
                    progress_bar.empty()
                    
                    st.toast("✅ Расчет завершен!", icon="✅")
                    
                except Exception as e:
                    st.toast(f"❌ Ошибка: {str(e)}", icon="❌")
                    st.exception(e)
    else:
        st.button("🚀 Запустить расчет", type="primary", use_container_width=True, disabled=True)
        st.caption("⚠️ Сначала загрузите основной файл")
    
    # ==================== СКАЧИВАНИЕ ====================
    if st.session_state.is_cleaned:
        st.markdown("---")
        st.subheader("📥 Скачать результаты")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.session_state.cleaned_excel is not None:
                st.download_button(
                    label="📥 Скачать очищенный файл",
                    data=st.session_state.cleaned_excel,
                    file_name=get_filename("Массив_итоги_месяца", "очищенный"),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    key="download_cleaned"
                )
        
        with col2:
            if st.session_state.deleted_excel is not None:
                st.download_button(
                    label="📥 Скачать удаленные строки",
                    data=st.session_state.deleted_excel,
                    file_name=get_filename("Массив_итоги_месяца", "удаленный"),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    key="download_deleted"
                )
            else:
                st.info("📭 Нет удаленных строк")
        
        st.markdown("---")
        st.caption("🔄 Чтобы обработать другой файл, загрузите его заново")

# ==================== ВКЛАДКА 2: НАСТРОЙКИ ====================
with tab2:
    st.markdown("---")
    st.subheader("⚙️ Настройки справочников")
    
    # ==================== 2.1 РЕГИОН-ТИП ====================
    st.markdown("#### 📁 Регион-Тип")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        region_file = st.file_uploader(
            "Загрузите Excel-файл 'Регион-Тип'",
            type=['xlsx', 'xls'],
            key="region_type"
        )
    
    with col2:
        try:
            region_data = load_from_json_github('region_type')
            if region_data is not None:
                st.caption(f"📅 Последняя загрузка: {region_data.get('last_upload', 'неизвестно')}")
        except Exception as e:
            st.caption("⚠️ Не удалось загрузить из GitHub")
    
    if region_file is not None:
        with st.spinner("Загрузка справочника..."):
            result = load_region_type(region_file)
            
            if result['status'] == 'error':
                st.error(f"❌ {result['message']}")
            else:
                st.success(f"✅ Загружено {len(result['data'])} записей")
                
                if result.get('invalid') is not None and not result['invalid'].empty:
                    st.warning("⚠️ Обнаружены некорректные значения:")
                    st.dataframe(result['invalid'], use_container_width=True)
                else:
                    st.info("✅ Все значения корректны")
                
                st.dataframe(result['data'], use_container_width=True)
                
                if st.button("💾 Сохранить в GitHub", key="save_region_github"):
                    try:
                        save_to_json_github('region_type', {
                            'data': result['data'].to_dict('records'),
                            'last_upload': result['last_upload']
                        })
                        st.toast("✅ Справочник 'Регион-Тип' сохранен в GitHub!", icon="✅")
                    except Exception as e:
                        st.toast(f"❌ Ошибка сохранения в GitHub: {str(e)}", icon="❌")
    
    st.markdown("---")
    
    # ==================== 2.2 ПРОЕКТ-МОТИВАЦИЯ ====================
    st.markdown("#### 📁 Проект-Мотивация")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        project_file = st.file_uploader(
            "Загрузите Excel-файл 'Проект-Мотивация'",
            type=['xlsx', 'xls'],
            key="project_motivation"
        )
    
    with col2:
        try:
            project_data = load_from_json_github('project_motivation')
            if project_data is not None:
                st.caption(f"📅 Последняя загрузка: {project_data.get('last_upload', 'неизвестно')}")
        except Exception as e:
            st.caption("⚠️ Не удалось загрузить из GitHub")
    
    if project_file is not None:
        with st.spinner("Загрузка справочника..."):
            result = load_project_motivation(project_file)
            
            if result['status'] == 'error':
                st.error(f"❌ {result['message']}")
            else:
                st.success(f"✅ Загружено {len(result['data'])} записей")
                
                if result.get('invalid') is not None and not result['invalid'].empty:
                    st.warning("⚠️ Обнаружены некорректные значения:")
                    st.dataframe(result['invalid'], use_container_width=True)
                else:
                    st.info("✅ Все значения корректны")
                
                st.dataframe(result['data'], use_container_width=True)
                
                if st.button("💾 Сохранить в GitHub", key="save_project_github"):
                    try:
                        save_to_json_github('project_motivation', {
                            'data': result['data'].to_dict('records'),
                            'last_upload': result['last_upload']
                        })
                        st.toast("✅ Справочник 'Проект-Мотивация' сохранен в GitHub!", icon="✅")
                    except Exception as e:
                        st.toast(f"❌ Ошибка сохранения в GitHub: {str(e)}", icon="❌")
    
    st.markdown("---")
    
    # ==================== 2.3 ИМЯ-ЛОГИН ====================
    st.markdown("#### 📁 Имя-логин")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        name_login_file = st.file_uploader(
            "Загрузите Excel-файл 'Имя-логин'",
            type=['xlsx', 'xls'],
            key="name_login"
        )
    
    with col2:
        try:
            name_login_data = load_from_json_github('name_login')
            if name_login_data is not None:
                st.caption(f"📅 Последняя загрузка: {name_login_data.get('last_upload', 'неизвестно')}")
        except Exception as e:
            st.caption("⚠️ Не удалось загрузить из GitHub")
    
    if name_login_file is not None:
        with st.spinner("Загрузка справочника..."):
            result = load_name_login(name_login_file)
            
            if result['status'] == 'error':
                st.error(f"❌ {result['message']}")
            else:
                st.success(f"✅ Загружено {len(result['data'])} записей")
                
                if result.get('removed_duplicates', 0) > 0:
                    st.warning(f"⚠️ Удалено полных дубликатов: {result['removed_duplicates']}")
                
                if result.get('invalid') is not None and not result['invalid'].empty:
                    with st.expander("🔍 Показать удаленные дубликаты"):
                        st.dataframe(result['invalid'], use_container_width=True)
                else:
                    st.info("✅ Полных дубликатов не обнаружено")
                
                st.dataframe(result['data'], use_container_width=True)
                
                if st.button("💾 Сохранить в GitHub", key="save_name_login"):
                    try:
                        save_to_json_github('name_login', {
                            'data': result['data'].to_dict('records'),
                            'last_upload': result['last_upload']
                        })
                        st.toast("✅ Справочник 'Имя-логин' сохранен в GitHub!", icon="✅")
                    except Exception as e:
                        st.toast(f"❌ Ошибка сохранения в GitHub: {str(e)}", icon="❌")
