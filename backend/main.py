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

# ── إعدادات CORS للسماح للفرونت إند بالاتصال ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── إعدادات Google Gemini ──
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

# ── إعدادات Firebase ──
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) # تم تعديل المسار ليكون أكثر مرونة
FIREBASE_KEY_PATH = os.path.join(BASE_DIR, "firebase_key.json")

if not firebase_admin._apps:
    cred = credentials.Certificate(FIREBASE_KEY_PATH)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ── إعدادات ChromaDB (Vector Database) ──
DB_PATH = os.path.join(BASE_DIR, "database", "chroma_db")
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
vector_db = Chroma(persist_directory=DB_PATH, embedding_function=embeddings)

# ── دالة استخراج البيانات من النص (دقيقة جداً) ──
def extract_decision_data(report_text: str):
    approval_rate = 0
    decision = "غير محدد"
    suggested_amount = 0

    # 1. استخراج النسبة المئوية
    rate_match = re.search(r'نسبة الموافقة[^:]*:\s*(\d+)\s*%', report_text)
    if rate_match:
        approval_rate = int(rate_match.group(1))

    # 2. استخراج القرار (الترتيب مهم: مرفوض ثم موافق بشروط ثم موافق)
    if "مرفوض" in report_text:
        decision = "مرفوض"
    elif "موافق بشروط" in report_text:
        decision = "موافق بشروط"
    elif "موافق" in report_text:
        decision = "موافق"

    # 3. استخراج المبلغ المناسب
    amount_match = re.search(r'المبلغ المناسب[^:]*:\s*([\d,]+)', report_text)
    if amount_match:
        suggested_amount = int(amount_match.group(1).replace(",", ""))

    return approval_rate, decision, suggested_amount

# ── دالة RAG لتجميع السياق من الكتب الزراعية ──
def get_all_data(f_name, c_name, city, area, loan, exp):
    # البحث في ChromaDB عن المحصول
    results = vector_db.similarity_search(f"إرشادات زراعة {c_name} في الأردن", k=2)
    context = "\n".join([res.page_content for res in results])
    
    return {
        "اسم_المزارع": f_name,
        "المحصول": c_name,
        "المدينة": city,
        "مساحة_الأرض_دونم": area,
        "القرض_المطلوب_دينار": loan,
        "سنوات_الخبرة": exp,
        "سياق_من_الكتب": context[:500] # نأخذ أول 500 حرف للسياق
    }

# ── هيكلة البيانات القادمة من الفرونت إند ──
class FarmerRequest(BaseModel):
    farmer_name: str
    crop_name: str
    city_name: str
    land_area: int
    loan_amount: int
    experience_years: int

# ── الـ Endpoint الرئيسي للتحليل ──
@app.post("/analyze")
async def analyze(data: FarmerRequest):
    # 1. تجميع البيانات والسياق
    bundle = get_all_data(
        data.farmer_name,
        data.crop_name,
        data.city_name,
        data.land_area,
        data.loan_amount,
        data.experience_years
    )

    # 2. بناء البرومبت (Prompt Engineering)
    # ملاحظة: تم وضع القواعد الائتمانية داخل البرومبت لضبط تفكير الـ AI
    prompt = f"""
أنت مستشار مالي زراعي أردني خبير ولبيب، تحكي بلهجة أردنية أصيلة ودافئة.
وظيفتك تقييم مخاطر البنك بصدق وحماية المزارع من الديون العالية التي قد تسبب تعثره.

بيانات الطلب الحالية:
- المزارع: {bundle['اسم_المزارع']}
- المحصول: {bundle['المحصول']} | المنطقة: {bundle['المدينة']}
- المساحة: {bundle['مساحة_الأرض_دونم']} دونم
- القرض المطلوب: {bundle['القرض_المطلوب_دينار']} دينار أردني
- الخبرة: {bundle['سنوات_الخبرة']} سنوات
- المعلومات الفنية المتوفرة: {bundle['سياق_من_الكتب']}

قواعد اتخاذ القرار (صارمة جداً):
1. (النسبة المالية): إذا تجاوز القرض المطلوب مبلغ 500 دينار لكل دونم واحد في محاصيل الخضراوات، فهذا "تضخم مالي" خطير ويجب الرفض أو تقليل المبلغ بشدة.
2. (شرط الخبرة): إذا كانت الخبرة أقل من سنتين والمبلغ المطلوب يتجاوز 5,000 دينار، يجب أن يكون القرار "مرفوض" أو "موافق بشروط" بمبلغ رمزي (مثلاً 1000-2000 دينار).
3. (التوافق الجغرافي): إذا كان المحصول لا يناسب المنطقة (مثل موز في الصحراء)، ارفض الطلب فوراً.
4. (الحالة الحالية): المزارع طلب {bundle['القرض_المطلوب_دينار']} لـ {bundle['مساحة_الأرض_دونم']} دونم، قارن هذا بالمنطق؛ إذا كان مبالغاً فيه، كن حازماً في قرارك.

اكتب الرد بالترتيب التالي وبدون مقدمات:

نسبة الموافقة على القرض: [النسبة]%
قراري: [موافق / موافق بشروط / مرفوض]
المبلغ المناسب: [المبلغ الرقمي فقط] دينار أردني

ليش قررت هيك:
- (اربط الخبرة بالمساحة وبالمبلغ بلهجة أردنية حكيمة.. إذا كان المبلغ خيالي، قل للمزارع بصراحة "يا خوي هاد حمل ثقيل عليك")

اللي لازم تنتبه له:
- (توصيات تقنية تخص {bundle['المحصول']} حصراً من واقع السياق المتوفر)

نصيحتي الك:
- (نصيحة إنسانية ومهنية لمساعدة المزارع على البدء بطريقة صحيحة ومستدامة)

قواعد إضافية:
- ممنوع ذكر أي مصطلحات تقنية (AI، نظام، كود).
- ابدأ فوراً بكلمة "نسبة الموافقة".
"""

    # 3. تشغيل نموذج Gemini
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content(prompt)
    report_text = response.text

    # 4. استخراج البيانات لتخزينها في قاعدة البيانات
    approval_rate, decision, suggested_amount = extract_decision_data(report_text)

    # 5. حفظ السجل في Firebase للمتابعة لاحقاً من قبل البنك
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

    # 6. إعادة التقرير النصي للفرونت إند ليتم عرضه
    return {"report": report_text}

# ── تشغيل السيرفر (في حال التشغيل المحلي) ──
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
