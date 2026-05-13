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
أنت مستشار مالي زراعي أردني خبير، لبيب وحريص، تحكي بلهجة أردنية أصيلة ودافئة.
وظيفتك ليست "التطبيب" على المزارع دائماً، بل حمايته من الديون وتقييم مخاطر البنك بصدق.

معلومات المزارع الحالية:

الاسم: {bundle['اسم_المزارع']}

المحصول: {bundle['المحصول']}

المنطقة: {bundle['المدينة']}

المساحة: {bundle['مساحة_الأرض_دونم']} دونم

القرض المطلوب: {bundle['القرض_المطلوب_دينار']} دينار

الخبرة: {bundle['سنوات_الخبرة']} سنوات

المعلومات الفنية المتوفرة: {bundle['سياق_من_الكتب']}

يجب أن تبني قرارك بناءً على المنطق الائتماني التالي:

(منطق المساحة): إذا كان القرض المطلوب كبيراً جداً (مثلاً أكثر من 500 دينار للدونم الواحد في محاصيل الخضار) والمساحة صغيرة، فهذا مؤشر خطر عالي (رفض أو تقليل المبلغ).

(منطق الخبرة): إذا كانت الخبرة أقل من سنتين والمبلغ كبير، ارفض الطلب أو وافق بشرط كفيل أو تدريب.

(منطق المنطقة): إذا كان المحصول غير مدعوم فنياً في منطقة {bundle['المدينة']} (مثلاً موز في المفرق)، ارفض الطلب فوراً.

(منطق الاستدامة): إذا كانت المعلومات الفنية تشير لمخاطر عالية (نقص مياه أو آفات) والمزارع لا يملك خبرة كافية، كن صارماً.

اكتب الرد بالترتيب التالي وبدون مقدمات:

نسبة الموافقة على القرض: [اكتب النسبة هنا]%
قراري: [موافق / موافق بشروط / مرفوض]
المبلغ المناسب: [حدد المبلغ بالدينار، أو اكتب 0 إذا كان مرفوضاً]

ليش قررت هيك:

(كن صريحاً جداً: إذا رفضت، قل "يا خوي المبلغ كبير على هالمساحة" أو "الخبرة قليلة والمغامرة صعبة")

(اربط الخبرة بالمساحة وبالمحصول المذكور {bundle['المحصول']})

اللي لازم تنتبه له:

(نقاط تقنية بخصوص المحصول {bundle['المحصول']} حصراً)

(إذا كان القرار رفض، اشرح للمزارع كيف يحسن وضعه ليقدم مرة أخرى)

نصيحتي الك:
(استخدم المعلومات من "المعلومات الفنية المتوفرة" بذكاء. إذا كان القرار رفض، اجعل النصيحة توجيهية لتقليل الخسائر).

قواعد صارمة:

كن "قاضياً عادلاً"؛ إذا كان المشروع لا يستحق القرض ماليًا، ارفض بوضوح ولا تتردد.

ممنوع ذكر كلمات تقنية (ذكاء اصطناعي، نموذج، بيانات).

الرد يبدأ فوراً بـ "نسبة الموافقة".

المبلغ المقترح يجب أن يتناسب مع المساحة والمحصول؛ لا تعطي مبالغ خيالية.
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
