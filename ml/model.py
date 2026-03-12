import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import joblib
import json
import os

MODEL_PATH = "ml/model.pkl"
DATA_PATH = "data/materi.json"

def load_materi():
    with open(DATA_PATH, 'r') as f:
        return json.load(f)

def train_model():
    materi_list = load_materi()
    
    # Mapping
    pendidikan_map = {'1':0, '2':1, '3':2, '4':3, '5':4, '6':5}
    format_map = {'video':0, 'artikel':1, 'infografis':2, 'campuran':3}
    topik_set = list(set(m['category'] for m in materi_list if m.get('category')))
    topik_map = {cat: i for i, cat in enumerate(topik_set)}
    type_map = {'video':0, 'artikel':1, 'infografis':2}
    
    def generate_synthetic_data(n_users=2000):
        data = []
        for _ in range(n_users):
            usia = np.random.randint(15, 60)
            pendidikan = str(np.random.choice(list(pendidikan_map.keys())))
            gender = np.random.choice(['L', 'P'])
            pretest_score = np.random.randint(0, 16)
            preferensi_format = np.random.choice(list(format_map.keys()))
            preferensi_topik = np.random.choice(list(topik_map.keys()))
            
            for materi in materi_list:
                m_type = materi['type']
                m_category = materi.get('category', 'unknown')
                if m_category not in topik_map:
                    continue
                
                relevan = 0
                if preferensi_format == 'campuran' or m_type == preferensi_format:
                    relevan += 1
                if m_category == preferensi_topik:
                    relevan += 1
                if pretest_score > 10 and m_type == 'artikel':
                    relevan += 1
                elif pretest_score < 5 and m_type == 'video':
                    relevan += 1
                if np.random.rand() < 0.1:
                    relevan = 1 - relevan
                
                label = 1 if relevan >= 2 else 0
                
                row = [
                    usia,
                    pendidikan_map[pendidikan],
                    1 if gender=='L' else 0,
                    pretest_score,
                    format_map[preferensi_format],
                    topik_map[preferensi_topik],
                    type_map[m_type],
                    topik_map[m_category]
                ]
                data.append(row + [label])
        
        columns = ['usia', 'pendidikan', 'gender', 'pretest', 'pref_format', 'pref_topik', 'm_type', 'm_category', 'label']
        df = pd.DataFrame(data, columns=columns)
        return df
    
    df = generate_synthetic_data(3000)
    X = df.drop('label', axis=1)
    y = df['label']
    
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X, y)
    
    joblib.dump({
        'model': model,
        'pendidikan_map': pendidikan_map,
        'format_map': format_map,
        'topik_map': topik_map,
        'type_map': type_map
    }, MODEL_PATH)
    print(f"Model saved to {MODEL_PATH}")

def load_model():
    return joblib.load(MODEL_PATH)

if __name__ == "__main__":
    train_model()