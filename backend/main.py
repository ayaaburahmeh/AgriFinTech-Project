import os
import json
import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

# إعداد المسارات
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "database", "chroma_db")
DATA_PATH = os.path.join(BASE_DIR, "data", "crops_data.json")

# الحل السحري: نستخدم Embeddings جوجل (كود خفيف جداً لا يحتاج RAM)
embeddings = GoogleGenerativeAIEmbeddings(
    model="models/text-embedding-004", 
    google_api_key=GOOGLE_API_KEY
)

# تحميل قاعدة البيانات (ستعمل الآن لأننا سحبنا المعالجة للسحاب)
vector_db = Chroma(persist_directory=DB_PATH, embedding_function=embeddings)

def get_all_data(f_name, c_name, city, area, loan, exp):
    # (كود جلب بيانات الطقس والتربة كما هو في نسختك السابقة)
    # ... 
    
    # الـ RAG: البحث في قاعدة البيانات
    results = vector_db.similarity_search(f"إرشادات زراعة {c_name}", k=2)
    context = "\n".join([res.page_content for res in results])
    
    return {
        "اسم_المزارع": f_name, "محصول": c_name, "سياق_من_الكتب": context[:500]
        # أضيفي باقي الحقول هنا
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
    prompt = f"""
أنت مستشار مالي زراعي أردني خبير. حلل البيانات التالية واتخذ قرار القرض:

{json.dumps(bundle, ensure_ascii=False)}

بناءً على البيانات أعلاه، قدم تقريرك بالشكل التالي بالضبط:

**نسبة الموافقة على القرض: XX%**

**قرار القرض:** (موافق / موافق بشروط / مرفوض)

**قيمة القرض المقترحة:** X دينار أردني

**أسباب القرار:**
- السبب الأول
- السبب الثاني

**المخاطر الرئيسية:**
- الخطر الأول
- الخطر الثاني

**توصيات للمزارع:**
استخدم المعلومات من الكتب الزراعية (سياق_من_الكتب) وقدم نصيحة عملية بلهجة أردنية.

ملاحظة: النسبة تعتمد على (الخبرة + المحصول + المساحة + قيمة القرض المطلوبة).
قواعد مهمة:
- لا تذكر أي كلمة مثل: AI، ذكاء اصطناعي، نموذج، خوارزمية، نظام، بيانات، تحليل رقمي
- تكلم وكأنك إنسان بيعرف المزارع شخصياً
- استخدم كلمات أردنية مثل: يا أخي، والله، يعطيك العافية، الله يبارك
- الرد يكون دافئ وإنساني مش رسمي وجاف
"""
    
    response = model.generate_content(prompt)
    return {"report": response.text}
