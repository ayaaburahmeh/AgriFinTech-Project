# استخدام نسخة بايثون مستقرة
FROM python:3.10-slim

# إعداد مجلد العمل
WORKDIR /code

# نسخ ملف المكتبات وتثبيتها
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# نسخ كل ملفات المشروع
COPY . .

# تشغيل التطبيق باستخدام Uvicorn على بورت 7860 (البورت الخاص بـ Hugging Face)
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7860"]
