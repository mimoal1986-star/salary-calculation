# ==================== app.py ====================
import streamlit as st
import pandas as pd

from data_loader import load_excel, validate_columns
from data_cleaner import clean_data
from report_generator import create_cleaned_excel, create_deleted_excel, get_filename
from settings_loader import load_region_type, load_project_motivation, save_to_json, load_from_json

# ==================== НАСТРОЙКА СТРАНИЦЫ ====================
st.set_page_config(
    page_title="Расчет ЗП",
    page_icon="💰",
    layout="wide"
)

st.title("💰 Расчет ЗП")

# ==================== ИНИЦИАЛИЗАЦИЯ СЕССИИ ====================
if 'cleaned_excel' not in st.session_state:
    st.session_state.cleaned_excel = None
if 'deleted_excel' not in st.session_state:
    st.session_state.deleted_excel = None
if 'is_cleaned' not in st.session_state:
    st.session_state.is_cleaned = False
if 'original_df' not in st.session_state:
    st.session_state.original_df = None
if 'total_rows' not in st.session_state:
    st.session_state.total_rows = 0
if 'cleaned_rows' not in st.session_state:
    st.session_state.cleaned_rows = 0
if 'deleted_rows' not in st.session_state:
    st.session_state.deleted_rows = 0
if 'columns_valid' not in st.session_state:
    st.session_state.columns_valid = False

# Для дополнительных справочников
if 'zp_shtrafy_df' not in st.session_state:
    st.session_state.zp_shtrafy_df = None
if 'name_login_rs_df' not in st.session_state:
    st.session_state.name_login_rs_df = None
if 'hvosty_df' not in st.session_state:
    st.session_state.hvosty_df = None

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
        
        # Статистика
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📊 Всего строк", st.session_state.total_rows)
        with col2:
            status = "✅ Присутствуют" if st.session_state.columns_valid else "❌ Отсутствуют"
            st.metric("📋 Все колонки", status)
        with col3:
            deleted = st.session_state.deleted_rows if st.session_state.is_cleaned else 0
            st.metric("🗑️ Удалено строк", deleted)
        
        st.markdown("---")
        
        # Кнопка запуска
        if st.button("🚀 Запустить расчет", type="primary", use_container_width=True):
            with st.spinner("Выполняется расчет..."):
                try:
                    cleaned_df, deleted_df = clean_data(df)
                    
                    st.session_state.cleaned_excel = create_cleaned_excel(cleaned_df)
                    if not deleted_df.empty:
                        st.session_state.deleted_excel = create_deleted_excel(deleted_df)
                    else:
                        st.session_state.deleted_excel = None
                    
                    st.session_state.is_cleaned = True
                    st.session_state.cleaned_rows = len(cleaned_df)
                    st.session_state.deleted_rows = len(deleted_df)
                    
                    st.success("✅ Расчет завершен!")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Ошибка: {str(e)}")
                    st.exception(e)
        
        # Скачивание
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
    
    else:
        st.info("👆 Загрузите Excel-файл для начала работы")
    
    st.markdown("---")
    
    # ==================== ДОПОЛНИТЕЛЬНЫЕ ЗАГРУЗЧИКИ ====================
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
        if zp_file is not None:
            with st.spinner("Загрузка ЗП_штрафы..."):
                try:
                    df_shtrafy = pd.read_excel(zp_file, engine='openpyxl')
                    st.session_state.zp_shtrafy_df = df_shtrafy
                    st.success(f"✅ Загружено {len(df_shtrafy)} записей")
                except Exception as e:
                    st.error(f"❌ Ошибка: {str(e)}")
    
    with col2:
        st.caption("Имя-Логин RS")
        login_file = st.file_uploader(
            "Загрузите файл",
            type=['xlsx', 'xls'],
            key="name_login_rs",
            label_visibility="collapsed"
        )
        if login_file is not None:
            with st.spinner("Загрузка Имя-Логин RS..."):
                try:
                    df_login = pd.read_excel(login_file, engine='openpyxl')
                    st.session_state.name_login_rs_df = df_login
                    st.success(f"✅ Загружено {len(df_login)} записей")
                except Exception as e:
                    st.error(f"❌ Ошибка: {str(e)}")
    
    with col3:
        st.caption("Хвосты")
        hvosty_file = st.file_uploader(
            "Загрузите файл",
            type=['xlsx', 'xls'],
            key="hvosty",
            label_visibility="collapsed"
        )
        if hvosty_file is not None:
            with st.spinner("Загрузка Хвосты..."):
                try:
                    df_hvosty = pd.read_excel(hvosty_file, engine='openpyxl')
                    st.session_state.hvosty_df = df_hvosty
                    st.success(f"✅ Загружено {len(df_hvosty)} записей")
                except Exception as e:
                    st.error(f"❌ Ошибка: {str(e)}")


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
        # Загружаем из GitHub
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
                
                # Кнопка "Сохранить в GitHub"
                if st.button("💾 Сохранить Регион-Тип в GitHub", key="save_region"):
                    try:
                        save_to_json_github('region_type', {
                            'data': result['data'].to_dict('records'),
                            'last_upload': result['last_upload']
                        })
                        st.success("✅ Справочник 'Регион-Тип' сохранен в GitHub!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Ошибка сохранения: {str(e)}")
    
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
                
                # Кнопка "Сохранить в GitHub"
                if st.button("💾 Сохранить Проект-Мотивация в GitHub", key="save_project"):
                    try:
                        save_to_json_github('project_motivation', {
                            'data': result['data'].to_dict('records'),
                            'last_upload': result['last_upload']
                        })
                        st.success("✅ Справочник 'Проект-Мотивация' сохранен в GitHub!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Ошибка сохранения: {str(e)}")
