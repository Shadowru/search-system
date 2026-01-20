import re
import pymorphy2
import ftfy
import pandas as pd

morph = pymorphy2.MorphAnalyzer()

STOP_WORDS = {
            'система', 'сервис', 'продукт', 'приложение', 'веб', 'для', 'на', 'в', 'и', 
            'или', 'по', 'с', 'от', 'как', 'это', 'предназначен', 'автоматизации', 
            'обеспечения', 'реализации', 'функций', 'процессов', 'аис', 'гис', 'егис'
        }

SYNONYMS = {
            "сад": "доу дошкольное",
            "садик": "доу дошкольное",
            "школа": "оу сош общее образование",
            "колледж": "спо профтех",
            "вуз": "впо высшее",
            "кружок": "удо дополнительное",
            "секция": "удо дополнительное",
            "еда": "питание",
            "проход": "скуд турникет",
            "ученик": "обучающийся учащийся",
        }

def fix_encoding(text):
    if pd.isna(text):
        return ""
    return ftfy.fix_text(str(text))

def preprocess_text(text, expand_synonyms=True):
    if not text: return ""
    text = str(text).lower()
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'[^\w\s]', ' ', text)
    
    words = text.split()
    result_words = []
    
    for word in words:
        if word in STOP_WORDS or len(word) < 2: continue
        
        parses = morph.parse(word)
        normal_form = parses[0].normal_form 
        normal_forms = set(p.normal_form for p in parses)
        
        synonyms_found = []
        for nf in normal_forms:
            if nf in SYNONYMS:
                synonyms_found.append(SYNONYMS[nf])
        
        if expand_synonyms and synonyms_found:
            result_words.extend(synonyms_found)
        else:
            result_words.append(normal_form)
            
    return " ".join(list(dict.fromkeys(result_words)))