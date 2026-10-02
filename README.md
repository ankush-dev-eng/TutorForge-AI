<div align="center">

# TutorForge AI

[![Typing SVG](https://readme-typing-svg.herokuapp.com/?font=Fira+Code&weight=600&size=24&pause=1000&color=2D5568&center=true&vCenter=true&width=750&lines=Personalized+AI+Study+Companion;Grounded+Answers+From+Your+Own+Material;Adaptive+Assessments;Concept-Level+Mastery;Personalized+Learning+Paths;Learn+What+You+Actually+Need)](https://git.io/typing-svg)

<img src="https://capsule-render.vercel.app/api?type=waving&color=2D5568&customColorList=2D5568,A65E4B,657E68,A7864F&height=180&section=header&text=&fontSize=0" width="100%"/>

**A personalized AI learning workspace that turns textbooks, lecture slides, notes, and supported learning media into source-grounded tutoring, adaptive assessments, concept mastery, and personalized learning paths.**

**Upload your material. Ask questions. Practice. See what you actually need to learn next.**

[![Next.js](https://img.shields.io/badge/Next.js-14-2D5568?style=for-the-badge&logo=next.js&logoColor=white)](https://nextjs.org/)
[![React](https://img.shields.io/badge/React-18.2-2D5568?style=for-the-badge&logo=react&logoColor=white)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0-2D5568?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Tailwind](https://img.shields.io/badge/Tailwind-3.0-A65E4B?style=for-the-badge&logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)
[![Python](https://img.shields.io/badge/Python-3.10-657E68?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-657E68?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Gemini](https://img.shields.io/badge/Gemini-AI-A7864F?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev/)
[![SQLite](https://img.shields.io/badge/SQLite-DB-657E68?style=for-the-badge&logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![React Flow](https://img.shields.io/badge/React_Flow-UI-2D5568?style=for-the-badge)](https://reactflow.dev/)
[![Recharts](https://img.shields.io/badge/Recharts-Data-A65E4B?style=for-the-badge)](https://recharts.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

![Stars](https://img.shields.io/github/stars/ankush-dev-eng/TutorForge-AI?style=social)
![Forks](https://img.shields.io/github/forks/ankush-dev-eng/TutorForge-AI?style=social)
![Last Commit](https://img.shields.io/github/last-commit/ankush-dev-eng/TutorForge-AI?color=2D5568&style=flat-square)

</div>

---

### 🎓 What is TutorForge?

Studying usually means jumping between a textbook, lecture slides, recorded lectures, notes, and a lot of searching.

We wanted to build something that could actually connect all of that.

**TutorForge AI** turns your own learning material into a personalized study environment.

You can:

- upload your learning material
- ask questions about it
- get source-grounded answers
- see where the information came from
- practice with adaptive questions
- track concept-level mastery
- follow a personalized learning path

The core idea is:

**Material → Knowledge → Tutor → Assessment → Mastery → Recommendation**

---

### ✨ Features

<table>
<tr>
<td width="50%">

**📚 Multimodal Learning Library**

Bring together textbooks, lecture slides, notes, and supported audio/video material in one place.

**🤖 Source-Grounded AI Tutor**

Ask questions about your own material and get responses grounded in retrieved source content.

</td>
<td width="50%">

**📎 Real Source Citations**

Responses can point back to source pages, slides, or timestamps when available.

**🧠 Adaptive Assessments**

Question difficulty responds to the student's previous performance.

</td>
</tr>

<tr>
<td width="50%">

**📈 Concept-Level Mastery**

Track concepts as Mastered, Developing, Needs Review, or Not Started.

**🗺️ Personalized Learning Path**

Use current mastery to decide what the student should work on next.

</td>
<td width="50%">

**🕸️ Concept Map**

Explore relationships between course concepts while seeing current mastery.

**📊 Learning Analytics**

Track accuracy, mastery, questions answered, study activity, and learning signals.

</td>
</tr>
</table>

> **Not just an AI that answers questions — a study system that learns what you need to learn next.**

---

### 🛠️ Tech Stack

<div align="center">

| Layer | Technology |
|---|---|
| 🖥️ **Frontend** | Next.js + React + TypeScript |
| 🎨 **Styling** | Tailwind CSS |
| ✨ **Motion** | Framer Motion |
| 🐍 **Backend** | Python + FastAPI |
| 🗄️ **Database** | SQLite + SQLAlchemy |
| 🤖 **AI** | Google Gemini + Google GenAI SDK |
| 🔎 **Retrieval** | TutorForge retrieval / RAG layer |
| 🕸️ **Knowledge Graph** | React Flow |
| 📊 **Analytics** | Recharts |

</div>

---

### 🚀 Getting Started

```bash
# 1. Clone the repository
git clone https://github.com/ankush-dev-eng/TutorForge-AI.git
cd TutorForge-AI

# 2. Setup the Backend
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env       # Then add your GEMINI_API_KEY
python -m uvicorn main:app --reload --port 8000

# 3. Setup the Frontend (in a new terminal)
cd frontend
npm install
npm run dev
```

Then open `http://localhost:3000` to start exploring. ⚡

---

### 🖥️ How It Works (Under the Hood)

```mermaid
flowchart LR
    A[Upload Material] --> B[RAG / Knowledge Engine]
    B --> C{AI Core}
    C --> D[Source-Grounded Tutor]
    C --> E[Adaptive Assessments]
    D --> F[Learning State]
    E --> F
    F --> G[Concept Map & Path]
```

The system ingests multimodal content, chunks and vectorizes it, and builds a personalized knowledge graph. The AI Tutor and Assessment engines continuously interact with this graph, updating the student's mastery state in real time.

---

### 🗂️ Project Structure

```
TutorForge-AI/
├── backend/          # FastAPI, Python, GenAI SDK, SQLite
├── frontend/         # Next.js, React, Tailwind, Framer Motion
├── README.md
└── .gitignore
```

---

### 🤝 Contributing

Pull requests, issue reports, and feedback are all welcome!

1. 🍴 Fork the repo
2. 🌿 Create your feature branch (`git checkout -b feature/amazing-feature`)
3. 💾 Commit your changes
4. 📤 Push and open a PR

---

### 📄 License

Licensed under the **MIT License** — see `LICENSE` for details.

---

<div align="center">

### 💡 If you found this project helpful, drop a ⭐!

<img src="https://capsule-render.vercel.app/api?type=waving&color=2D5568&customColorList=2D5568,A65E4B,657E68,A7864F&height=100&section=footer"/>

</div>
