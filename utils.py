# utils.py

import pandas as pd

def normalize_text(text):
    if pd.isna(text):
        return ""
    return str(text).strip().lower()


def format_project_type(value):
    if not value:
        return "Не определен"
    
    mapping = {
        "ротационный": "Ротационный",
        "безротационный": "Безротационный",
        "мултон": "Мултон",
        "опросы": "Опросы",
        "мониторинги": "Мониторинги"
    }
    
    val_lower = str(value).strip().lower()
    return mapping.get(val_lower, "Не определен")