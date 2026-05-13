# 🇯🇴 AgriFinTech Jordan: AI-Driven Credit Intelligence
> **Revolutionizing Agricultural Finance through Generative AI, RAG, and Real-Time Data Fusion.**

---

## 📈 The Challenge: Bridging Jordan's "Data Gap"
Despite agriculture contributing **~7.2% to Jordan's GDP**, nearly **70% of agricultural loan applications are rejected**. 
Small-scale farmers in regions like **Al-Ghor, Mafraq, and Irbid** operate in a "data vacuum," lacking formal credit records. This creates **Information Asymmetry**, leading traditional banks to perceive agricultural lending as high-risk.

## 💡 The Solution
**AgriFinTech Jordan** is an intelligent decision-support system that transforms raw agricultural variables into verifiable **Credit Intelligence Reports**. By merging real-time environmental data with localized expertise, we provide financial institutions with a **Probability of Default (PD)** assessment in seconds—reducing evaluation time from **21 days to <10 seconds**.

---

## 🧠 Technical Architecture & "Secret Sauce"

### 1. RAG Framework (Retrieval-Augmented Generation)
Unlike generic LLMs, our system utilizes a dedicated RAG Pipeline to eliminate AI hallucinations:
* **Knowledge Base:** A vectorized repository of **13.5MB** of specialized Jordanian agricultural textbooks and crop guidelines.
* **Vector Store:** Powered by **ChromaDB** for high-speed semantic retrieval.
* **Contextual Grounding:** Ensures every recommendation is rooted in Jordanian soil requirements and regional crop cycles.

### 2. Multi-Source Data Fusion
Our engine orchestrates a "fusion" of three critical intelligence layers:
* **Farmer Persona:** Qualitative data including experience, land area, and historical success.
* **Soil Intelligence (ISRIC API):** Real-time pH levels, clay content, and bulk density based on precise geo-coordinates.
* **Climate Intelligence (Open-Meteo API):** Historical and real-time weather patterns (Temp, Humidity, Rainfall).

### 3. Reasoning Engine
Utilizing **Google Gemini 1.5 Pro** as the core synthesizer to transform multi-dimensional data into a single, objective credit score.

---

## 🛠️ Tech Stack & Infrastructure

| Layer | Technology |
| :--- | :--- |
| **Language** | Python 3.10+ |
| **AI Engine** | Google Gemini 1.5 Pro |
| **Orchestration** | LangChain (RAG Pipeline Management) |
| **Vector DB** | ChromaDB (Embeddings: `all-MiniLM-L6-v2`) |
| **Backend** | FastAPI (High-performance Asynchronous API) |
| **Frontend** | HTML5 / TailwindCSS (Hosted on Netlify) |
| **Database** | Firebase Firestore (Real-time Persistence) |
| **Deployment** | Docker / Hugging Face Spaces |

---

## 🚀 Key Features
* **Automated Credit Scoring:** Instant approval/rejection probability calculation.
* **Localized Advisory:** Reports generated in **Jordanian Arabic** to build trust and provide actionable insights for farmers.
* **Institutional Transparency:** Provides "The Why" behind every decision, explaining risk factors to bank officers.
* **Bank Dashboard (MVP):** A real-time interface for loan officers to manage, filter, and approve AI-generated reports.

---

## ⚙️ Installation & Setup

1.  **Source Acquisition:** `git clone https://github.com/ayaaburahmeh/AgriFinTech-Project.git`
2.  **Environment Preparation:** Create a virtual environment and install dependencies:  
    `pip install -r requirements.txt`
3.  **Security Configuration:** Add your `GEMINI_API_KEY` and Firebase service account credentials to your environment variables (`.env`).
4.  **Service Initialization:** `uvicorn backend.main:app --reload`
5.  **Frontend Deployment:** Deploy the `frontend/` directory to Netlify and point the API endpoint to your hosted backend.

---

## 📈 Impact & Vision
* **Financial Inclusion:** Shifting lending from "intuition-based" to "data-driven."
* **National Vision:** Supporting the **Jordan National Vision 2025** for food security.
* **Scalability:** A modular architecture ready to expand to other MENA regions.

---

## 👩‍💻 The Team
* **Aya Abu Rahmeh:** Backend Development, AI Engineering, RAG Integration, & Cloud Architecture.
* **Ruaa:** Frontend Design & Bank Dashboard UI/UX.

---
**AgriFinTech Jordan** | *Empowering the Kingdom's Farmers with Data.*
