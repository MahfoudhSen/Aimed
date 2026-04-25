# 🤖 SafeNest AI - Agent Files

This folder contains all the AI agent implementations.

---

## 📁 Files

### **demo_agent.py** ⭐ **USE THIS FOR DEMO**
- **Purpose:** Perfect for hackathon presentation
- **Features:**
  - Uses sample listings (reliable demo)
  - AI scam detection (REAL)
  - Clear step-by-step output
  - Professional presentation
- **Run:** `python demo_agent.py`
- **Best for:** Video recording, live demo, judges

---

### **ollama_agent.py**
- **Purpose:** Full agent with web search
- **Features:**
  - Real web search (DuckDuckGo)
  - Content extraction (Jina AI)
  - AI analysis (Ollama)
- **Run:** `python ollama_agent.py`
- **Best for:** Production testing

---

### **browsing_agent.py**
- **Purpose:** Paid version using OpenAI
- **Features:**
  - Uses OpenAI API (costs money)
  - Tavily search API
  - Premium quality
- **Run:** Requires API keys in .env file
- **Best for:** Reference implementation

---

## 🚀 Quick Start

### **For Hackathon Demo:**

```bash
# 1. Navigate to project
cd ~/Desktop/housing-ai-agent

# 2. Activate environment
source venv/bin/activate

# 3. Run the demo
python agent/demo_agent.py
```

---

## 📦 Requirements

### **For demo_agent.py and ollama_agent.py:**
```bash
pip install -r agent/requirements-free.txt
```

**Requires:**
- Ollama installed and running
- Llama 3.2 model downloaded

### **For browsing_agent.py:**
```bash
pip install -r agent/requirements.txt
```

**Requires:**
- OpenAI API key
- Tavily API key

---

## 🎯 Which File to Use?

| Scenario | Use This File |
|----------|--------------|
| Hackathon demo | `demo_agent.py` ⭐ |
| Video recording | `demo_agent.py` ⭐ |
| Live presentation | `demo_agent.py` ⭐ |
| Testing real search | `ollama_agent.py` |
| Production (paid) | `browsing_agent.py` |

---

## 🔧 Troubleshooting

**"Ollama not running":**
```bash
# In separate terminal:
ollama serve
```

**"Module not found":**
```bash
pip install -r agent/requirements-free.txt
```

---

## 📊 File Details

| File | Lines | Dependencies | Cost |
|------|-------|-------------|------|
| demo_agent.py | ~250 | requests | FREE |
| ollama_agent.py | ~300 | requests, duckduckgo-search | FREE |
| browsing_agent.py | ~280 | openai, tavily-python | PAID |

---

**For full documentation, see the parent directory README.md**
