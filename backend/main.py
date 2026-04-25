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

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

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


def scrape_craigslist(borough: str, budget: int = 9999, room_type: str = "Any room") -> str:
    area = BOROUGH_CODES.get(borough, "nyc")
    cl_type = ROOM_TYPE_CODES.get(room_type, "apa")
    url = f"https://newyork.craigslist.org/search/{area}/{cl_type}"
    if budget < 9999:
        url += f"?max_ask={budget}"

    try:
        resp = requests.get(
            f"https://r.jina.ai/{url}",
            headers={"Accept": "text/plain", "X-No-Cache": "true"},
            timeout=30
        )
        return resp.text[:8000]  # limit to keep prompt small
    except Exception as e:
        return f"Error fetching listings: {e}"


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
    raw = scrape_craigslist(borough, budget, room_type)

    if not raw or raw.startswith("Error"):
        return {"listings": [], "error": raw}

    resp = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2000,
        messages=[{"role": "user", "content": f"""Parse these Craigslist rental listings for {room_type} in {borough} NYC (budget: ${budget}/mo).

Extract real listings and return a JSON array. Each item:
- title: string (listing title)
- price: number (monthly rent $; skip if price not found)
- location: string (neighborhood, {borough})
- description: string (2-3 sentences about the unit)
- safe: boolean (false = scam red flags detected)
- score: integer 0-100 (safety; 80+ = legit, <50 = likely scam)
- flags: string[] (specific red flags; [] if none)

NYC scam red flags: price way below market rate, owner overseas/unavailable, wire transfer/Western Union/crypto/gift cards required, no in-person viewing, extreme urgency, no address.
Typical NYC ranges: Brooklyn rooms $700-1400/mo, Queens $650-1200/mo, Bronx $600-1100/mo, Manhattan $1000-2500/mo.

Raw Craigslist page:
{raw}

Only include actual rental listings (skip ads, navigation, articles). Max 8 listings.
Respond with only a valid JSON array — no markdown, no explanation."""}]
    )

    text = resp.content[0].text.strip()
    m = re.search(r'\[.*\]', text, re.DOTALL)
    if m:
        text = m.group(0)
    try:
        listings = json.loads(text)
        return {"listings": listings}
    except Exception:
        return {"listings": []}


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
