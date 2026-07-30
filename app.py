# ==================== app.py ====================
import streamlit as st
import pandas as pd

from data_loader import load_excel, validate_columns
from data_cleaner import clean_data
from report_generator import create_cleaned_excel, create_deleted_excel, get_filename

# ==================== НАСТРОЙКА СТРАНИЦЫ ====================
st.set_page_config(
    page_title="Расчет ЗП",
    page_icon="💰",
    layout="wide"
)

st.title("💰 Расчет ЗП")
st.markdown("---")

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

# ==================== ЗАГРУЗКА ФАЙЛА ====================
uploaded_file = st.file_uploader(
    "📁 Загрузите Excel-файл",
    type=['xlsx', 'xls']
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
    
    # ==================== СТАТИСТИКА ====================
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
    
    # ==================== КНОПКА ЗАПУСКА ====================
    if st.button("🚀 Запустить расчет", type="primary", use_container_width=True):
        with st.spinner("Выполняется расчет..."):
            try:
                cleaned_df, deleted_df = clean_data(df)
                
                # Сохраняем Excel-файлы в сессию
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

else:
    st.info("👆 Загрузите Excel-файл для начала работы")
