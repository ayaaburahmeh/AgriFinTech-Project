import os
import json
import re
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai
from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
import firebase_admin
from firebase_admin import credentials, firestore

app = FastAPI()

# ── إعدادات CORS ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── تحديد المسارات (بناءً على صورة المستودع) ──
# CURRENT_DIR سيكون مسار مجلد backend
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# ROOT_DIR هو المجلد الرئيسي للمشروع
ROOT_DIR = os.path.dirname(CURRENT_DIR)

# مسار ملف Firebase (موجود في الـ Root)
FIREBASE_KEY_PATH = os.path.join(ROOT_DIR, "firebase_key.json")

# مسار قاعدة بيانات Chroma (موجودة في مجلد database في الـ Root)
DB_PATH = os.path.join(ROOT_DIR, "database", "chroma_db")

# ── إعدادات Google Gemini ──
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

# ── إعدادات Firebase ──
if not firebase_admin._apps:
    cred = credentials.Certificate(FIREBASE_KEY_PATH)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ── إعدادات ChromaDB ──
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
vector_db = Chroma(persist_directory=DB_PATH, embedding_function=embeddings)

# ── دالة استخراج البيانات من النص ──
def extract_decision_data(report_text: str):
    approval_rate = 0
    decision = "غير محدد"
    suggested_amount = 0

    # 1. استخراج النسبة المئوية من النص
    rate_match = re.search(r'نسبة الموافقة[^:]*:\s*(\d+)\s*%', report_text)
    if rate_match:
        approval_rate = int(rate_match.group(1))

    # 2. تحديد القرار بناءً على المنطق الرقمي (قواعدك الجديدة)
    if approval_rate < 60:
        decision = "مرفوض"
    elif approval_rate >= 80:
        decision = "موافق"
    else:
        decision = "موافق بشروط"

    # 3. استخراج المبلغ المناسب
    amount_match = re.search(r'المبلغ المناسب[^:]*:\s*([\d,]+)', report_text)
    if amount_match:
        suggested_amount = int(amount_match.group(1).replace(",", ""))
    
    # تصحيح إضافي: إذا كان القرار "مرفوض" برمجياً، نلغي المبلغ المقترح
    if decision == "مرفوض":
        suggested_amount = 0

    return approval_rate, decision, suggested_amount

# ── دالة RAG لتجميع السياق ──
def get_all_data(f_name, c_name, city, area, loan, exp):
    results = vector_db.similarity_search(f"إرشادات زراعة {c_name} في الأردن", k=2)
    context = "\n".join([res.page_content for res in results])
    return {
        "اسم_المزارع": f_name,
        "المحصول": c_name,
        "المدينة": city,
        "مساحة_الأرض_دونم": area,
        "القرض_المطلوب_دينار": loan,
        "سنوات_الخبرة": exp,
        "سياق_من_الكتب": context[:500]
    }

class FarmerRequest(BaseModel):
    farmer_name: str
    crop_name: str
    city_name: str
    land_area: int
    loan_amount: int
    experience_years: int

# ── الـ Endpoint الرئيسي ──
@app.post("/analyze")
async def analyze(data: FarmerRequest):
    bundle = get_all_data(
        data.farmer_name,
        data.crop_name,
        data.city_name,
        data.land_area,
        data.loan_amount,
        data.experience_years
    )

    prompt = f"""
أنت مستشار مالي زراعي أردني خبير، لبيب وحريص، تحكي بلهجة أردنية أصيلة ودافئة.
وظيفتك تقييم مخاطر البنك بصدق وحماية المزارع من الديون العالية التي قد تسبب تعثره.

بيانات الطلب الحالية:
- المزارع: {bundle['اسم_المزارع']}
- المحصول: {bundle['المحصول']} | المنطقة: {bundle['المدينة']}
- المساحة: {bundle['مساحة_الأرض_دونم']} دونم
- القرض المطلوب: {bundle['القرض_المطلوب_دينار']} دينار أردني
- الخبرة: {bundle['سنوات_الخبرة']} سنوات
- المعلومات الفنية المتوفرة: {bundle['سياق_من_الكتب']}

قواعد اتخاذ القرار (صارمة جداً):
1. (النسبة المالية): القرض المنطقي لا يتجاوز 500 دينار لكل دونم واحد لمحاصيل الخضروات. المزارع طلب {bundle['القرض_المطلوب_دينار']} لـ {bundle['مساحة_الأرض_دونم']} دونم، قارن هذا بالمنطق؛ إذا كان مبالغاً فيه جداً، يجب الرفض أو تقليل المبلغ بشدة.
2. (شرط الخبرة): إذا كانت الخبرة أقل من سنتين والمبلغ المطلوب يتجاوز 5,000 دينار، القرار يجب أن يكون "مرفوض" أو "موافق بشروط" بمبلغ رمزي (مثلاً 1000-2000 دينار).
3. (التوافق الجغرافي): إذا كان المحصول لا يناسب المنطقة، ارفض الطلب فوراً.

اكتب الرد بالترتيب التالي وبدون مقدمات:

نسبة الموافقة على القرض: [النسبة]%
قراري: [موافق / موافق بشروط / مرفوض]
المبلغ المناسب: [المبلغ الرقمي فقط] دينار أردني

ليش قررت هيك:
- (اربط الخبرة بالمساحة وبالمبلغ بلهجة أردنية حكيمة)

اللي لازم تنتبه له:
- (توصيات تقنية تخص {bundle['المحصول']} من واقع السياق المتوفر)

نصيحتي الك:
- (نصيحة إنسانية ومهنية بلهجة أردنية)

قواعد إضافية:
- ممنوع ذكر أي مصطلحات تقنية (AI، نظام، كود).
- ابدأ فوراً بكلمة "نسبة الموافقة".
"""

    model = genai.GenerativeModel('gemini-2.5-flash')
    response = model.generate_content(prompt)
    report_text = response.text

    approval_rate, decision, suggested_amount = extract_decision_data(report_text)

    doc_data = {
        "farmer_name": data.farmer_name,
        "crop_name": data.crop_name,
        "city_name": data.city_name,
        "land_area": data.land_area,
        "loan_amount": data.loan_amount,
        "experience_years": data.experience_years,
        "report": report_text,
        "approval_rate": approval_rate,
        "decision": decision,
        "suggested_amount": suggested_amount,
        "status": "pending",
        "timestamp": datetime.utcnow().isoformat(),
    }
    db.collection("loan_requests").add(doc_data)

    return {"report": report_text}
