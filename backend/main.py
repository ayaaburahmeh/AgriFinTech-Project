import os
import json
import re
import requests
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Google Gemini ──────────────────────────────────────────────────────────────
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

# ── Firebase ───────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIREBASE_KEY_PATH = os.path.join(BASE_DIR, "firebase_key.json")

if not firebase_admin._apps:
    cred = credentials.Certificate(FIREBASE_KEY_PATH)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ── ChromaDB ───────────────────────────────────────────────────────────────────
DB_PATH = os.path.join(BASE_DIR, "database", "chroma_db")
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
vector_db = Chroma(persist_directory=DB_PATH, embedding_function=embeddings)


# ── استخراج النسبة والقرار من نص التقرير ──────────────────────────────────────
def extract_decision_data(report_text: str):
    approval_rate = 0
    decision = "غير محدد"
    suggested_amount = 0

    match = re.search(r'نسبة الموافقة[^:]*:\s*(\d+)\s*%', report_text)
    if match:
        approval_rate = int(match.group(1))

    if "موافق بشروط" in report_text:
        decision = "موافق بشروط"
    elif "مرفوض" in report_text:
        decision = "مرفوض"
    elif "موافق" in report_text:
        decision = "موافق"

    match2 = re.search(r'المبلغ المناسب[^:]*:\s*([\d,]+)', report_text)
    if match2:
        suggested_amount = int(match2.group(1).replace(",", ""))

    return approval_rate, decision, suggested_amount


# ── RAG + تجميع البيانات ───────────────────────────────────────────────────────
def get_all_data(f_name, c_name, city, area, loan, exp):
    results = vector_db.similarity_search(f"إرشادات زراعة {c_name}", k=2)
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
أنت مستشار مالي زراعي أردني خبير، تحكي بلهجة أردنية أصيلة ودافئة (مثل لهجة كبارنا المزارعين). 
وظيفتك تقييم طلب القرض وتقديم تقرير "لوحة تحكم" احترافية وإنسانية بنفس الوقت.

معلومات المزارع الحالية:
- الاسم: {bundle['اسم_المزارع']}
- المحصول: {bundle['المحصول']}
- المنطقة: {bundle['المدينة']}
- المساحة: {bundle['مساحة_الأرض_دونم']} دونم
- القرض المطلوب: {bundle['القرض_المطلوب_دينار']} دينار
- الخبرة: {bundle['سنوات_الخبرة']} سنوات
- المعلومات الفنية المتوفرة: {bundle['سياق_من_الكتب']}

اكتب الرد بالترتيب التالي وبدون مقدمات:

نسبة الموافقة على القرض: [اكتب النسبة هنا]%
قراري: [موافق / موافق بشروط / مرفوض]
المبلغ المناسب: [حدد المبلغ] دينار أردني

ليش قررت هيك:
- (اربط الخبرة بالمساحة وبالمحصول المذكور {bundle['المحصول']})
- (تحدث عن جدوى المحصول في منطقة {bundle['المدينة']})

اللي لازم تنتبه له:
- (نقاط تقنية بخصوص المحصول {bundle['المحصول']} حصراً)
- (تنبيه بخصوص إدارة المبلغ)

نصيحتي الك:
(استخدم المعلومات من "المعلومات الفنية المتوفرة" بشرط ربطها بذكاء بمحصول {bundle['المحصول']}. إذا كانت المعلومات عن زيتون والمحصول عنب، ركز في نصيحتك على الجودة العامة والاهتمام بالأرض كما يُهتم بالزيتون، بلهجة أردنية حميمة).

قواعد صارمة:
1. ممنوع نهائياً ذكر كلمات تقنية مثل (ذكاء اصطناعي، نموذج، بيانات، نظام).
2. الرد يبدأ فوراً بـ "نسبة الموافقة" ولا يضع أي جمل ترحيبية قبلها.
3. تأكد أن النصيحة موجهة لمزارع {bundle['المحصول']} ولا تخلط بين المحاصيل بشكل يشتت المزارع.
4. اجعل التقرير يبدو كأنه صادر من ابن بلد لبيب وخبير.
"""
    model = genai.GenerativeModel('gemini-2.5-flash')
    response = model.generate_content(prompt)
    report_text = response.text

    approval_rate, decision, suggested_amount = extract_decision_data(report_text)

    doc = {
        "farmer_name":      data.farmer_name,
        "crop_name":        data.crop_name,
        "city_name":        data.city_name,
        "land_area":        data.land_area,
        "loan_amount":      data.loan_amount,
        "experience_years": data.experience_years,
        "report":           report_text,
        "approval_rate":    approval_rate,
        "decision":         decision,
        "suggested_amount": suggested_amount,
        "status":           "pending",       # البنك يغيرها لاحقاً
        "timestamp":        datetime.utcnow().isoformat(),
    }
    db.collection("loan_requests").add(doc)

    return {"report": report_text}
