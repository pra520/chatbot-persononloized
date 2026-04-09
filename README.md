# PersonaBot — AI Document Chatbot

> A production-ready, SaaS-level personalized AI chatbot that lets you upload PDFs and CSVs and chat with your data using cutting-edge AI.

---

## ✨ Features

| Feature | Description |
|---|---|
| 📄 Document AI | Upload PDF, CSV, XLSX, TXT — chat with your data |
| 🧠 Smart Memory | Remembers last 8 conversation turns |
| 🎨 Premium UI | Dark glassmorphism, animated, responsive |
| ⚡ Fast Backend | Flask + OpenRouter API integration |
| 🔒 Session Isolation | Multiple users, separate contexts |
| 🎛️ Configurable | Change bot name, role, business per client |

---

## 🚀 Quick Start

### 1. Run Setup
```
setup.bat
```

### 2. Add Your API Key
Open `backend/.env` and replace:
```
OPENROUTER_API_KEY=your_openrouter_api_key_here
```
with your actual key from [openrouter.ai/keys](https://openrouter.ai/keys)

### 3. Start the App
```
start.bat
```

### 4. Open Browser
Go to: [http://localhost:5000](http://localhost:5000)

---

## 📁 Project Structure

```
person/
├── backend/
│   ├── app.py                    # Flask server + routes
│   ├── requirements.txt          # Python dependencies
│   ├── .env.example              # Config template
│   └── services/
│       ├── ai_engine.py          # OpenRouter + prompt engineering
│       ├── file_processor.py     # PDF/CSV/XLSX extraction
│       ├── memory_manager.py     # Conversation memory
│       └── context_store.py      # Document context storage
├── frontend/
│   ├── index.html                # Main UI
│   ├── style.css                 # Premium dark theme
│   └── app.js                   # Frontend logic
├── setup.bat                     # One-click setup
├── start.bat                     # Start server
└── README.md
```

---

## 🎛️ Customize Per Client

Edit `backend/.env`:

```env
BOT_NAME=Acme Assistant
BOT_TAGLINE=Your Smart Business AI
BOT_ROLE=customer support agent for an e-commerce company
BUSINESS_NAME=Acme Corp
WELCOME_MESSAGE=Hi! I'm Acme's AI. Upload our product catalog and ask anything!
PRIMARY_COLOR=#FF6B35
```

---

## 🌐 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/health` | Server health check |
| GET | `/api/config` | Get bot configuration |
| POST | `/api/chat` | Send a message |
| POST | `/api/upload` | Upload a document |
| GET | `/api/documents` | List uploaded documents |
| DELETE | `/api/documents/<name>` | Remove a document |
| POST | `/api/reset` | Clear session |

---

## 💰 Selling This System

**Target Price**: ₹15,000 – ₹50,000 per client

**What to show during demo:**
1. Upload a business PDF/catalog → AI answers instantly
2. Multi-turn memory — reference previous answers
3. Mobile responsive — works on all devices
4. Customizable branding — change name/color per client

**Client types:**
- E-commerce stores (product FAQ)
- Law firms (document Q&A)
- Schools (admission FAQ)
- Hospitals (service info)
- Real estate agencies

---

## 📦 Production Deployment

```bash
# Install gunicorn
pip install gunicorn

# Run production server
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

Deploy to: **Railway, Render, DigitalOcean, AWS EC2**

---

## 🔑 Get OpenRouter API Key

1. Go to [openrouter.ai](https://openrouter.ai)
2. Create free account
3. Go to **Keys** section
4. Create a new key
5. Paste in `.env`

**Free tier available!** Start with mistral-7b-instruct (free).
