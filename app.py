# ==================== app.py ====================
"""
Оркестратор - главный файл приложения
"""

import streamlit as st
import pandas as pd

from data_loader import load_excel, validate_columns
from data_cleaner import clean_data
from report_generator import create_cleaned_excel, create_deleted_excel, get_filename

# ==================== НАСТРОЙКА СТРАНИЦЫ ====================
st.set_page_config(
    page_title="Очистка данных - Массив итоги месяца",
    page_icon="🧹",
    layout="wide"
)

st.title("🧹 Очистка данных 'Массив итоги месяца'")
st.markdown("---")

# ==================== ИНИЦИАЛИЗАЦИЯ СЕССИИ ====================
if 'cleaned_df' not in st.session_state:
    st.session_state.cleaned_df = None
if 'deleted_df' not in st.session_state:
    st.session_state.deleted_df = None
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
if 'file_uploaded' not in st.session_state:
    st.session_state.file_uploaded = False

# ==================== ОСНОВНАЯ ОБЛАСТЬ ====================

# Загрузка файла
uploaded_file = st.file_uploader(
    "📁 Загрузите Excel-файл 'Массив итоги месяца'",
    type=['xlsx', 'xls'],
    help="Файл должен содержать все обязательные колонки"
)

# Если загружен новый файл - сбрасываем состояние
if uploaded_file is not None:
    # Проверяем, изменился ли файл
    if not st.session_state.file_uploaded or st.session_state.original_df is None:
        st.session_state.is_cleaned = False
        st.session_state.cleaned_df = None
        st.session_state.deleted_df = None
        st.session_state.file_uploaded = True

if uploaded_file is not None:
    # Загрузка файла (только если изменился)
    if st.session_state.original_df is None:
        with st.spinner("Загрузка файла..."):
            df, error = load_excel(uploaded_file)
            
            if error:
                st.error(f"❌ {error}")
                st.stop()
            
            # Валидация колонок
            is_valid, error_msg, missing = validate_columns(df)
            
            if not is_valid:
                st.error(f"❌ {error_msg}")
                st.stop()
            
            st.session_state.original_df = df
            st.session_state.total_rows = len(df)
    
    df = st.session_state.original_df
    
    # Показываем информацию о файле
    col1, col2 = st.columns(2)
    with col1:
        st.metric("📊 Всего строк", st.session_state.total_rows)
    with col2:
        st.metric("✅ Все колонки", "Присутствуют")
    
    st.markdown("---")
    
    # Кнопка запуска очистки
    if st.button("🚀 Запустить очистку", type="primary", use_container_width=True):
        with st.spinner("Выполняется очистка данных..."):
            try:
                cleaned_df, deleted_df = clean_data(df)
                
                st.session_state.cleaned_df = cleaned_df
                st.session_state.deleted_df = deleted_df
                st.session_state.is_cleaned = True
                st.session_state.cleaned_rows = len(cleaned_df)
                st.session_state.deleted_rows = len(deleted_df)
                
                st.success("✅ Очистка завершена!")
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Ошибка при очистке данных: {str(e)}")
                st.exception(e)
    
    # ==================== ОТОБРАЖЕНИЕ РЕЗУЛЬТАТОВ (если есть) ====================
    if st.session_state.is_cleaned:
        cleaned_df = st.session_state.cleaned_df
        deleted_df = st.session_state.deleted_df
        total_rows = st.session_state.total_rows
        cleaned_rows = st.session_state.cleaned_rows
        deleted_rows = st.session_state.deleted_rows
        
        # Показываем статистику
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📊 Исходно строк", total_rows)
        with col2:
            st.metric("✅ Очищено строк", cleaned_rows, delta=cleaned_rows - total_rows)
        with col3:
            st.metric("🗑️ Удалено строк", deleted_rows, delta=-deleted_rows)
        
        st.markdown("---")
        
        # Таблица с удаленными строками (если есть)
        if deleted_rows > 0:
            st.subheader("🗑️ Удаленные строки")
            st.info(f"Удалено {deleted_rows} строк(и)")
            
            if 'Причина_удаления' in deleted_df.columns:
                reason_counts = deleted_df['Причина_удаления'].value_counts()
                num_reasons = len(reason_counts)
                cols = st.columns(min(num_reasons, 4))
                
                for idx, (reason, count) in enumerate(reason_counts.items()):
                    with cols[idx % 4]:
                        st.metric(reason, count)
            
            def make_arrow_compatible(df_to_convert):
                df_copy = df_to_convert.copy()
                for col in df_copy.columns:
                    if df_copy[col].dtype == 'object':
                        df_copy[col] = df_copy[col].astype(str)
                return df_copy
            
            with st.expander("Показать удаленные строки (первые 10)"):
                display_df = make_arrow_compatible(deleted_df.head(10))
                st.dataframe(display_df, use_container_width=True)
            
            if deleted_rows > 10:
                with st.expander("Показать все удаленные строки"):
                    display_all_df = make_arrow_compatible(deleted_df)
                    st.dataframe(display_all_df, use_container_width=True)
        else:
            st.success("🎉 Нет удаленных строк! Все данные прошли очистку.")
        
        st.markdown("---")
        
        # Выгрузка файлов
        st.subheader("📥 Скачать результаты")
        
        col1, col2 = st.columns(2)
        
        with col1:
            cleaned_excel = create_cleaned_excel(cleaned_df)
            cleaned_filename = get_filename("Массив_итоги_месяца", "очищенный")
            
            st.download_button(
                label="📥 Скачать очищенный файл",
                data=cleaned_excel,
                file_name=cleaned_filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key="download_cleaned"
            )
        
        with col2:
            if deleted_rows > 0:
                deleted_excel = create_deleted_excel(deleted_df)
                deleted_filename = get_filename("Массив_итоги_месяца", "удаленный")
                
                st.download_button(
                    label="📥 Скачать удаленные строки",
                    data=deleted_excel,
                    file_name=deleted_filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    key="download_deleted"
                )
            else:
                st.info("📭 Нет удаленных строк для скачивания")
        
        st.markdown("---")
        st.info("🔄 Чтобы обработать другой файл, загрузите его заново")

else:
    st.info("👈 Загрузите Excel-файл для начала работы")
    
    with st.expander("📋 Ожидаемая структура файла"):
        st.write("Файл должен содержать следующие колонки:")
        cols = [
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
        
        col1, col2, col3, col4 = st.columns(4)
        for i, col in enumerate(cols):
            if i % 4 == 0:
                col1.write(f"• {col}")
            elif i % 4 == 1:
                col2.write(f"• {col}")
            elif i % 4 == 2:
                col3.write(f"• {col}")
            else:
                col4.write(f"• {col}")
    
    with st.expander("📌 Правила очистки"):
        st.markdown("""
        **1. Фильтрация по менеджерам**
        - Оставляем только 9 разрешенных менеджеров (проверка по колонке ACC)
        - Остальные удаляются
        
        **2. Стандартизация типов проекта** (по порядку):
        - Если ClientName = "Мултон" → **Мултон**
        - Если в "Тип проекта" есть "монитор" → **Мониторинги**
        - Если в "Тип проекта" есть "опрос" → **Опросы**
        - Если в "Тип проекта" есть "ротац" без "без" → **Ротационный**
        - Если в "Тип проекта" есть "ротац" и "без" → **Безротационный**
        - Остальные → удаляются (в колонке остается исходное значение)
        
        **3. Фильтрация по проектам**
        - Все что содержит "холост" → заменяется на "_SINGLE"
        - Удаляются все проекты, начинающиеся с "_" (кроме "_SINGLE")
        
        **4. Фильтрация по ClientName**
        - "Тамбовский бекон" с "ВСЕГО" = 0 → удаляются
        """)
