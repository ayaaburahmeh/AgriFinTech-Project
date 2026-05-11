import os
import json
import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

GOOGLE_API_KEY = "AIzaSyAVxyE49x8sdKRt8NAZo73WKFuV1XA6ZGY"
genai.configure(api_key=GOOGLE_API_KEY)

# استخدام مسارات نسبية مرنة
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "database", "chroma_db")
DATA_PATH = os.path.join(BASE_DIR, "data", "crops_data.json")

embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
vector_db = Chroma(persist_directory=DB_PATH, embedding_function=embeddings)

JORDAN_CITIES = {
    "إربد": {"lat": 32.55, "lon": 35.85},
    "الأغوار الشمالية": {"lat": 32.45, "lon": 35.60},
    "الأغوار الوسطى": {"lat": 32.19, "lon": 35.61},
    "المفرق": {"lat": 32.34, "lon": 36.20},
    "عمان": {"lat": 31.95, "lon": 35.91},
    "الكرك": {"lat": 31.18, "lon": 35.70},
}

def get_soil(lat, lon):
    try:
        url = f"https://rest.isric.org/soilgrids/v2.0/properties/query?lon={lon}&lat={lat}&property=phh2o&property=clay&depth=0-5cm&value=mean"
        response = requests.get(url, timeout=10).json()
        layers = response.get('properties', {}).get('layers', [])
        soil_results = {"حموضة_التربة": 7.5, "نسبة_الطين_بالمئة": 30.0, "وصف_التربة": "قاعدية طينية (نموذجية للأردن)"}
        for layer in layers:
            name = layer.get('name')
            try:
                val = layer['depths'][0]['values']['mean'] / 10
                if name == 'phh2o': soil_results["حموضة_التربة"] = val
                if name == 'clay': soil_results["نسبة_الطين_بالمئة"] = val
            except: continue
        if soil_results["حموضة_التربة"] >= 7: soil_results["وصف_التربة"] = "قاعدية طينية (نموذجية للأردن)"
        else: soil_results["وصف_التربة"] = "تربة حامضية"
        return soil_results
    except:
        return {"حموضة_التربة": 7.5, "نسبة_الطين_بالمئة": 30.0, "وصف_التربة": "قاعدية طينية (متوسط)"}

def get_all_data(f_name, c_name, city, area, loan, exp):
    loc = JORDAN_CITIES.get(city)
    if not loc: return None
    
    with open(DATA_PATH, 'r', encoding='utf-8') as f:
        crops = json.load(f)
    crop_info = crops.get(c_name, {})
    
    w_url = f"https://api.open-meteo.com/v1/forecast?latitude={loc['lat']}&longitude={loc['lon']}&daily=temperature_2m_max&timezone=Asia/Amman"
    temp = requests.get(w_url).json()["daily"]["temperature_2m_max"][0]
    
    results = vector_db.similarity_search(f"إرشادات زراعة {c_name}", k=3)
    context = "\n".join([res.page_content for res in results])

    return {
        "اسم_المزارع": f_name, "محصول": c_name, "مدينة": city, "مساحة_الأرض": area,
        "مبلغ_القرض": loan, "سنوات_الخبرة": exp, "سعر_السوق_دينار": crop_info.get("متوسط_السعر_دينار"),
        "الحرارة_الحالية": temp, "بيانات_التربة": get_soil(loc['lat'], loc['lon']), "توصية_النظام": context[:500]
    }

class FarmerRequest(BaseModel):
    farmer_name: str
    crop_name: str
    city_name: str
    land_area: int
    loan_amount: int
    experience_years: int

@app.post("/analyze")
async def analyze(data: FarmerRequest):
    bundle = get_all_data(data.farmer_name, data.crop_name, data.city_name, data.land_area, data.loan_amount, data.experience_years)
    
    model = genai.GenerativeModel('gemini-1.5-flash')
    # البرومبت الأردني اللي اتفقنا عليه
    prompt = f"""
    أنت مستشار زراعي أردني خبير. حلل هذه البيانات للمزارع {bundle['اسم_المزارع']}:
    {json.dumps(bundle, ensure_ascii=False)}
    اكتب تقرير بلهجة أردنية بيضاء يتضمن الجدوى، نصيحة ري، وتقييم لمخاطرة القرض.
    """
    
    response = model.generate_content(prompt)
    return {"report": response.text}
