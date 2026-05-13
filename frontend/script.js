const API_URL = "https://ayaaburahmeh-agrifintech-project.hf.space/analyze";

let currentStep = 0;
const steps = document.querySelectorAll(".form-step");
const dots = document.querySelectorAll(".step-dot");
const progressBar = document.getElementById("progressBar");

// تحديث خطوات النموذج (المؤشر العلوي)
function updateStep() {
  steps.forEach((step, index) => {
    step.classList.toggle("active-step", index === currentStep);
  });

  dots.forEach((dot, index) => {
    dot.classList.toggle("active-dot", index <= currentStep);
  });

  progressBar.style.width = `${((currentStep + 1) / steps.length) * 100}%`;
}

function nextStep() {
  if (currentStep < steps.length - 1) {
    currentStep++;
    updateStep();
  }
}

function prevStep() {
  if (currentStep > 0) {
    currentStep--;
    updateStep();
  }
}

// تنقلات الصفحات
function openLoansPage() {
  document.getElementById("homePage").style.display = "none";
  document.getElementById("loansPage").classList.remove("hidden");
  document.getElementById("farmerLoanPage").classList.add("hidden");
  window.scrollTo(0, 0);
}

function openFarmerLoan() {
  document.getElementById("homePage").style.display = "none";
  document.getElementById("loansPage").classList.add("hidden");
  document.getElementById("farmerLoanPage").classList.remove("hidden");
  window.scrollTo(0, 0);
  currentStep = 0;
  updateStep();
}

function goHome() {
  document.getElementById("homePage").style.display = "block";
  document.getElementById("loansPage").classList.add("hidden");
  document.getElementById("farmerLoanPage").classList.add("hidden");
  window.scrollTo(0, 0);
}

// معالجة إرسال النموذج والذكاء الاصطناعي
document.getElementById("loanForm").addEventListener("submit", async function (e) {
  e.preventDefault();

  const resultContainer = document.getElementById("result");
  const reportBox = document.getElementById("detailedReport");
  const statusResult = document.getElementById("statusResult");
  const suggestedAmount = document.getElementById("suggestedAmount");
  const riskLevel = document.getElementById("riskLevel");
  const riskText = document.getElementById("riskText");

  // إظهار لوحة النتائج وتجهيزها بـ "تحميل"
  resultContainer.classList.remove("hidden");
  reportBox.innerHTML = "جاري تحليل البيانات عبر المستشار الذكي... يرجى الانتظار.";
  statusResult.innerText = "جاري التحليل...";
  
  // تمرير الشاشة للنتائج بسلاسة
  window.scrollTo({
    top: resultContainer.offsetTop - 100,
    behavior: 'smooth'
  });

  const data = {
    farmer_name: document.getElementById("farmer_name").value,
    crop_name: document.getElementById("crop_name").value,
    city_name: document.getElementById("city_name").value,
    land_area: Number(document.getElementById("land_area").value),
    loan_amount: Number(document.getElementById("loan_amount").value),
    experience_years: Number(document.getElementById("experience_years").value)
  };

  try {
    const response = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data)
    });

    const output = await response.json();
    const fullReport = output.report || output.result || output.message || "تم إصدار التقرير.";

    // 1. عرض التقرير الكامل في قسم التحليل التفصيلي
    reportBox.innerHTML = fullReport;

    // 2. تحديث بطاقات لوحة التحكم
    statusResult.innerText = "تم التحليل";
    suggestedAmount.innerText = data.loan_amount.toLocaleString();

    // 3. حساب منطقي بسيط لمؤشر المخاطر (Logic-based UI)
    // ملاحظة: يمكن تعديل هذا الجزء ليأخذ قيمته مباشرة من الـ AI إذا كان الـ API يرسل "risk_score"
    let riskScore = 0;
    
    // مثال لمنطق تقييم: كلما زادت الخبرة قلت المخاطر
    if (data.experience_years < 2) riskScore = 80;
    else if (data.experience_years < 5) riskScore = 50;
    else riskScore = 20;

    // تحديث شكل المؤشر
    riskLevel.style.width = riskScore + "%";
    
    if (riskScore <= 30) {
        riskLevel.style.background = "linear-gradient(to left, #4CAF50, #8BC34A)";
        riskText.innerText = "مخاطر منخفضة ✅";
    } else if (riskScore <= 60) {
        riskLevel.style.background = "linear-gradient(to left, #FF9800, #FFC107)";
        riskText.innerText = "مخاطر متوسطة ⚠️";
    } else {
        riskLevel.style.background = "linear-gradient(to left, #F44336, #E91E63)";
        riskText.innerText = "مخاطر عالية ❗";
    }

  } catch (error) {
    reportBox.innerHTML = "حدث خطأ أثناء الاتصال بالمستشار الذكي. يرجى التحقق من اتصالك بالإنترنت أو حالة الخادم.";
    statusResult.innerText = "فشل التحليل";
  }
});

// تهيئة الخطوة الأولى عند التحميل
updateStep();
