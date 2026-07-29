#  app.py 


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

# ==================== БОКОВАЯ ПАНЕЛЬ ====================
with st.sidebar:
    st.header("📁 Загрузка файла")
    
    uploaded_file = st.file_uploader(
        "Загрузите Excel-файл 'Массив итоги месяца'",
        type=['xlsx', 'xls'],
        help="Файл должен содержать все обязательные колонки"
    )
    
    st.markdown("---")
    st.caption("Допустимые менеджеры:")
    for manager in [
        "Аблязимова Екатерина",
        "Герасимова Светлана",
        "Карлышева Алиса",
        "Механошина Елена",
        "Солодникова Виктория",
        "Шавлюк Юлия",
        "Воронин Евгений",
        "Яцевич Максим",
        "Голдакова Светлана"
    ]:
        st.caption(f"• {manager}")
    
    st.markdown("---")
    st.caption("📌 Типы проектов:")
    st.caption("• Мултон (по ClientName)")
    st.caption("• Мониторинги (поиск 'монитор')")
    st.caption("• Опросы (поиск 'опрос')")
    st.caption("• Ротационный (поиск 'ротац' без 'без')")
    st.caption("• Безротационный (поиск 'ротац' и 'без')")

# ==================== ОСНОВНАЯ ОБЛАСТЬ ====================
if uploaded_file is not None:
    # Загрузка файла
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
    
    # Показываем информацию о файле
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📊 Всего строк", len(df))
    with col2:
        st.metric("📋 Всего колонок", len(df.columns))
    with col3:
        st.metric("✅ Все колонки", "Присутствуют" if is_valid else "❌")
    
    st.markdown("---")
    
    # Кнопка запуска очистки
    if st.button("🚀 Запустить очистку", type="primary", use_container_width=True):
        with st.spinner("Выполняется очистка данных..."):
            try:
                # Очистка
                cleaned_df, deleted_df = clean_data(df)
                
                # Статистика
                total_rows = len(df)
                cleaned_rows = len(cleaned_df)
                deleted_rows = len(deleted_df)
                
                st.success("✅ Очистка завершена!")
                
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
                    
                    # Группировка по причинам
                    if 'Причина_удаления' in deleted_df.columns:
                        reason_counts = deleted_df['Причина_удаления'].value_counts()
                        
                        # Создаем колонки для статистики по причинам
                        num_reasons = len(reason_counts)
                        cols = st.columns(min(num_reasons, 4))
                        
                        for idx, (reason, count) in enumerate(reason_counts.items()):
                            with cols[idx % 4]:
                                st.metric(reason, count)
                    
                    # Показываем первые 10 удаленных строк
                    with st.expander("Показать удаленные строки (первые 10)"):
                        st.dataframe(deleted_df.head(10), use_container_width=True)
                    
                    # Показываем все удаленные строки (опционально)
                    if deleted_rows > 10:
                        with st.expander("Показать все удаленные строки"):
                            st.dataframe(deleted_df, use_container_width=True)
                else:
                    st.success("🎉 Нет удаленных строк! Все данные прошли очистку.")
                
                st.markdown("---")
                
                # Выгрузка файлов
                st.subheader("📥 Скачать результаты")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # Создаем очищенный файл
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
                        # Создаем файл с удаленными
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
                
                # Возможность загрузить новый файл
                st.markdown("---")
                st.info("🔄 Чтобы обработать другой файл, загрузите его заново в боковой панели")
                
            except Exception as e:
                st.error(f"❌ Ошибка при очистке данных: {str(e)}")
                st.exception(e)

else:
    st.info("👈 Загрузите Excel-файл в боковой панели для начала работы")
    
    # Показываем пример структуры
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
        
        # Разбиваем на 4 колонки для красивого отображения
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
    
    # Показываем информацию о правилах очистки
    with st.expander("📌 Правила очистки"):
        st.markdown("""
        **1. Фильтрация по менеджерам**
        - Оставляем только 9 разрешенных менеджеров
        - Остальные удаляются
        
        **2. Стандартизация типов проекта** (по порядку):
        - Если ClientName = "Мултон" → **Мултон**
        - Если в "Тип проекта" есть "монитор" → **Мониторинги**
        - Если в "Тип проекта" есть "опрос" → **Опросы**
        - Если в "Тип проекта" есть "ротац" без "без" → **Ротационный**
        - Если в "Тип проекта" есть "ротац" и "без" → **Безротационный**
        - Остальные → **Не определен** (удаляются)
        
        **3. Фильтрация по проектам**
        - Все что содержит "холост" → заменяется на "_SINGLE"
        - Удаляются все проекты, начинающиеся с "_" (кроме "_SINGLE")
        
        **4. Фильтрация по ClientName**
        - "Тамбовский бекон" с "ВСЕГО" = 0 → удаляются
        """)