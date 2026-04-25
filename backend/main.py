import os, json, re
import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import anthropic
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"), override=True)

app = FastAPI(title="SafeNest AI")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Craigslist NYC area codes
BOROUGH_CODES = {
    "Brooklyn": "brk",
    "Queens": "que",
    "Bronx": "brx",
    "Manhattan": "mnh",
    "Staten Island": "stn",
}

ROOM_TYPE_CODES = {
    "Any room": "apa",
    "Private room": "roo",
    "Shared room": "roo",
    "Studio": "apa",
}

CHAT_SYSTEM = """You are SafeNest AI, a housing assistant helping New Yorkers find safe, affordable housing.

You help users:
- Find affordable rentals in NYC by neighborhood and budget
- Detect rental scams (prices too low, owner overseas, wire transfer demands, no-lease offers)
- Calculate affordability using the 30% income rule
- Understand NYC neighborhoods, tenant rights, and the rental process

Keep answers concise and practical. Use real NYC market context for prices.
NYC scam red flags: price way below market, owner abroad, wire/crypto/gift-card payment, no lease, no viewing."""

SEARCH_TOOL = {
    "name": "search_listings",
    "description": "Search for real rental listings on Craigslist NYC.",
    "input_schema": {
        "type": "object",
        "properties": {
            "borough": {"type": "string", "description": "NYC borough: Brooklyn, Queens, Bronx, Manhattan"},
            "max_budget": {"type": "number", "description": "Max monthly rent in dollars"},
        },
        "required": ["borough"]
    }
}

AFFORD_TOOL = {
    "name": "calculate_affordability",
    "description": "Calculate whether a rent is affordable given monthly income.",
    "input_schema": {
        "type": "object",
        "properties": {
            "monthly_rent": {"type": "number"},
            "monthly_income": {"type": "number"}
        },
        "required": ["monthly_rent", "monthly_income"]
    }
}


def scrape_craigslist(borough: str, budget: int = 9999, room_type: str = "Any room") -> list[dict]:
    area = BOROUGH_CODES.get(borough, "nyc")
    cl_type = ROOM_TYPE_CODES.get(room_type, "apa")
    url = f"https://newyork.craigslist.org/search/{area}/{cl_type}"
    params = []
    if budget < 9999:
        params.append(f"max_ask={budget}")
    if params:
        url += "?" + "&".join(params)

    try:
        resp = requests.get(
            f"https://r.jina.ai/{url}",
            headers={"Accept": "text/plain", "X-No-Cache": "true"},
            timeout=30
        )
        return parse_craigslist_text(resp.text, borough)
    except Exception as e:
        return []


SCAM_KEYWORDS = [
    "western union", "wire transfer", "money order", "gift card", "venmo upfront",
    "overseas", "out of country", "not in the us", "abroad", "in europe", "in africa",
    "no viewing", "no visit", "can't show", "cannot show", "until paid",
    "urgent", "asap", "immediately", "limited time",
    "crypto", "bitcoin", "zelle only", "cashapp only",
]

BOROUGH_MIN_PRICES = {
    "Brooklyn": 550, "Queens": 500, "Bronx": 450, "Manhattan": 800, "Staten Island": 450
}

def scam_score(title: str, description: str, price: int, borough: str) -> tuple[bool, int, list[str]]:
    text = (title + " " + description).lower()
    flags = []

    # Keyword checks
    for kw in SCAM_KEYWORDS:
        if kw in text:
            flags.append(kw.title())

    # Price too low
    min_price = BOROUGH_MIN_PRICES.get(borough, 500)
    if price > 0 and price < min_price * 0.6:
        flags.append(f"Price suspiciously low for {borough} (${price}/mo)")
    elif price > 0 and price < min_price * 0.75:
        flags.append(f"Price below typical {borough} range")

    # Excessive exclamation / urgency in title
    if title.count("!") >= 2 or title.upper() == title and len(title) > 10:
        flags.append("Suspicious all-caps or excessive punctuation in title")

    score = max(5, 95 - len(flags) * 18)
    safe = len(flags) == 0 or score >= 60
    return safe, score, flags


def parse_craigslist_text(text: str, borough: str) -> list[dict]:
    listings = []
    # Each Craigslist listing in Jina markdown looks like:
    # [Title](url) · $price · neighborhood
    # or lines with price and title mixed
    price_pattern = re.compile(r'\$(\d{2,4})(?:/mo|/month|\.00)?', re.IGNORECASE)
    lines = text.split('\n')

    i = 0
    while i < len(lines) and len(listings) < 8:
        line = lines[i].strip()

        # Look for lines with a price
        price_match = price_pattern.search(line)
        if price_match and len(line) > 15:
            price = int(price_match.group(1))
            # Extract title: remove URL markdown and price
            title = re.sub(r'\[|\]|\(http[^\)]+\)', '', line)
            title = re.sub(r'\$\d+(/mo|/month)?', '', title, flags=re.IGNORECASE)
            title = re.sub(r'\s+', ' ', title).strip(' ·-–')

            if len(title) < 5:
                i += 1
                continue

            # Grab next line as description if it has content
            desc = ""
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if next_line and not next_line.startswith('http') and len(next_line) > 10:
                    desc = next_line[:200]

            safe, score, flags = scam_score(title, desc, price, borough)
            listings.append({
                "title": title[:80],
                "price": price,
                "location": borough,
                "description": desc or f"Rental listing in {borough}, NYC.",
                "safe": safe,
                "score": score,
                "flags": flags,
            })
        i += 1

    return listings


def calculate_affordability(rent: float, income: float) -> dict:
    ratio = rent / income if income > 0 else 1
    affordable = ratio <= 0.30
    return {
        "monthly_rent": rent,
        "monthly_income": income,
        "rent_to_income_percent": round(ratio * 100, 1),
        "is_affordable": affordable,
        "max_affordable_rent": round(income * 0.30),
        "verdict": "Affordable" if affordable else "Over budget",
        "message": (
            f"Rent is {round(ratio*100,1)}% of income. "
            + ("Within the 30% threshold ✅" if affordable
               else f"Exceeds 30% rule. Max affordable: ${round(income*0.30):,}/mo.")
        )
    }


def run_tool(name: str, inputs: dict) -> str:
    if name == "search_listings":
        borough = inputs.get("borough", "Brooklyn")
        budget = int(inputs.get("max_budget", 9999))
        raw = scrape_craigslist(borough, budget)
        # Parse into structured listings via Claude
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1500,
            messages=[{"role": "user", "content": f"""Parse these Craigslist listings for {borough} NYC and return a JSON array.

Each item must have:
- title: string
- price: number (monthly $)
- location: string
- description: string (1-2 sentences)
- safe: boolean (false if scam red flags present)
- score: integer 0-100 (safety score)
- flags: string[] (red flags found, empty if none)

Scam red flags: price absurdly low for NYC, owner overseas, wire transfer/crypto/gift cards required, no in-person viewing, urgent pressure.
Typical NYC ranges: Brooklyn rooms $700-1400, Queens $650-1200, Bronx $600-1100, Manhattan $1000-2500.

Raw page content:
{raw}

Return only a valid JSON array, max 6 listings."""}]
        )
        text = resp.content[0].text.strip()
        m = re.search(r'\[.*\]', text, re.DOTALL)
        return m.group(0) if m else "[]"
    if name == "calculate_affordability":
        return json.dumps(calculate_affordability(inputs["monthly_rent"], inputs["monthly_income"]))
    return json.dumps({"error": "Unknown tool"})


# ── /api/search-analyze ───────────────────────────────────────
@app.get("/api/search-analyze")
async def search_analyze(borough: str, budget: int = 9999, room_type: str = "Any room"):
    listings = scrape_craigslist(borough, budget, room_type)
    return {"listings": listings}


# ── /api/analyze ─────────────────────────────────────────────
class AnalyzeReq(BaseModel):
    listing_text: str

@app.post("/api/analyze")
async def analyze(req: AnalyzeReq):
    resp = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        messages=[{"role": "user", "content": f"""Analyze this rental listing for scam indicators. Return JSON only:
{{
  "risk_level": "Low"|"Medium"|"High",
  "risk_score": 0-100,
  "red_flags": ["..."],
  "explanation": "2-3 sentences",
  "recommendation": "what to do"
}}

Listing:
{req.listing_text}"""}]
    )
    text = resp.content[0].text.strip()
    m = re.search(r'\{.*\}', text, re.DOTALL)
    if m:
        text = m.group(0)
    try:
        return json.loads(text)
    except Exception:
        return {"risk_level": "Unknown", "risk_score": 0, "red_flags": [], "explanation": text, "recommendation": ""}


# ── /api/chat ─────────────────────────────────────────────────
class ChatReq(BaseModel):
    messages: list[dict]

@app.post("/api/chat")
async def chat(req: ChatReq):
    def generate():
        current_messages = list(req.messages)
        while True:
            with client.messages.stream(
                model="claude-haiku-4-5-20251001",
                max_tokens=1024,
                system=CHAT_SYSTEM,
                tools=[SEARCH_TOOL, AFFORD_TOOL],
                messages=current_messages,
            ) as stream:
                tool_input_buffers: dict[str, dict] = {}
                cur_id = None

                for event in stream:
                    if event.type == "content_block_start":
                        if event.content_block.type == "tool_use":
                            cur_id = event.content_block.id
                            tool_input_buffers[cur_id] = {
                                "id": cur_id, "name": event.content_block.name, "raw": ""
                            }
                        else:
                            cur_id = None
                    elif event.type == "content_block_delta":
                        if event.delta.type == "text_delta":
                            yield f"data: {json.dumps({'type':'text','content':event.delta.text})}\n\n"
                        elif event.delta.type == "input_json_delta" and cur_id:
                            tool_input_buffers[cur_id]["raw"] += event.delta.partial_json
                    elif event.type == "content_block_stop":
                        if cur_id and cur_id in tool_input_buffers:
                            try:
                                tool_input_buffers[cur_id]["input"] = json.loads(tool_input_buffers[cur_id]["raw"])
                            except Exception:
                                tool_input_buffers[cur_id]["input"] = {}
                            cur_id = None

                final = stream.get_final_message()
                if final.stop_reason == "tool_use":
                    assistant_content = []
                    for block in final.content:
                        if block.type == "text":
                            assistant_content.append({"type": "text", "text": block.text})
                        elif block.type == "tool_use":
                            assistant_content.append({"type": "tool_use", "id": block.id, "name": block.name, "input": block.input})
                    current_messages.append({"role": "assistant", "content": assistant_content})

                    tool_results = []
                    for block in final.content:
                        if block.type == "tool_use":
                            yield f"data: {json.dumps({'type':'tool_call','name':block.name})}\n\n"
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": run_tool(block.name, block.input)
                            })
                    current_messages.append({"role": "user", "content": tool_results})
                    continue
                break

        yield f"data: {json.dumps({'type':'done'})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/api/health")
async def health():
    return {"status": "ok"}


# Serve Vite dist
dist_dir = os.path.join(os.path.dirname(__file__), "..", "dist")
if os.path.isdir(dist_dir):
    app.mount("/", StaticFiles(directory=dist_dir, html=True), name="static")
