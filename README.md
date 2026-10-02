<div align="center">

# ⚡ TutorForge AI

[![React](https://img.shields.io/badge/React-18.2-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev/)
[![Next.js](https://img.shields.io/badge/Next.js-14-000000?style=for-the-badge&logo=next.js&logoColor=white)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)

**An interactive, AI-powered tutoring platform featuring a dynamic Concept Map visualization.**

</div>

## Overview
TutorForge AI is an advanced intelligent tutoring system that builds an adaptive concept map for learners, tracking mastery in real-time.

## Features
- **Interactive Concept Map:** Visualize relationships between topics with React Flow.
- **AI Tutor:** Conversational AI that leverages Gemini for intelligent tutoring.
- **Dynamic Mastery Tracking:** Concepts update from "Not Started" to "Mastered".

## Getting Started

### Prerequisites
- Node.js (v18+)
- Python 3.10+

### Backend Setup
1. `cd backend`
2. `python -m venv .venv`
3. `source .venv/bin/activate` (or `.venv\Scripts\activate` on Windows)
4. `pip install -r requirements.txt`
5. Copy `.env.example` to `.env` and configure your `GEMINI_API_KEY`.
6. Run the server: `python -m uvicorn main:app --reload`

### Frontend Setup
1. `cd frontend`
2. `npm install`
3. `npm run dev`
