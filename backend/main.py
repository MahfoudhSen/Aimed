import os, json, re
import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import anthropic
from duckduckgo_search import DDGS
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

app = FastAPI(title="SafeNest AI")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

CHAT_SYSTEM = """You are SafeNest AI, a housing assistant helping New Yorkers find safe, affordable housing.

You help users:
- Find affordable rentals in NYC by neighborhood and budget
- Detect rental scams (prices too low, owner overseas, wire transfer demands, no-lease offers)
- Calculate affordability using the 30% income rule
- Understand NYC neighborhoods, tenant rights, and the rental process

Keep answers concise and practical. When giving prices, use real NYC market context.
Scam red flags: price way below market, owner abroad, wire/crypto/gift-card payment, no lease, no viewing."""

SEARCH_TOOL = {
    "name": "search_listings",
    "description": "Search for rental listings in NYC.",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query, e.g. '1BR apartment Brooklyn under $1500'"}
        },
        "required": ["query"]
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


def ddg_search(query: str, max_results: int = 6) -> list[dict]:
    try:
        with DDGS() as ddgs:
            return list(ddgs.text(query, max_results=max_results))
    except Exception:
        return []


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
        raw = ddg_search(
            f"site:craigslist.org OR site:streeteasy.com OR site:zillow.com {inputs['query']} NYC rental",
            max_results=5
        )
        results = [{"title": r.get("title", ""), "url": r.get("href", ""), "snippet": r.get("body", "")} for r in raw]
        return json.dumps(results)
    if name == "calculate_affordability":
        return json.dumps(calculate_affordability(inputs["monthly_rent"], inputs["monthly_income"]))
    return json.dumps({"error": "Unknown tool"})


# ── /api/search-analyze ───────────────────────────────────────
@app.get("/api/search-analyze")
async def search_analyze(borough: str, budget: int = 9999, room_type: str = "Any room"):
    query = f"{room_type} rental {borough} NYC"
    if budget < 9999:
        query += f" under ${budget} per month"

    raw = ddg_search(
        f"site:craigslist.org OR site:streeteasy.com OR site:apartments.com {query}",
        max_results=8
    )

    if not raw:
        return {"listings": []}

    snippets = json.dumps(
        [{"title": r.get("title", ""), "snippet": r.get("body", ""), "url": r.get("href", "")} for r in raw],
        indent=2
    )

    resp = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2000,
        messages=[{"role": "user", "content": f"""Analyze these NYC rental search results for {room_type} in {borough} (budget: ${budget}/mo).

{snippets}

Return a JSON array of actual rental listings. Each object must have:
- title: string
- price: number (monthly $; estimate from context or use typical {borough} market rate if unclear)
- location: string (neighborhood, {borough})
- description: string (2-3 sentences about the unit)
- safe: boolean (false if scam red flags present)
- score: integer 0-100 (safety; 80+ = legit, <50 = scam)
- flags: string[] (specific red flags; [] if none)

NYC scam red flags: price absurdly below market, owner overseas, wire/Western Union/crypto required,
no in-person viewing, urgent pressure, no lease. Brooklyn/Queens rooms typically $700-1300,
Manhattan $1000-2500, Bronx $600-1100.

Exclude non-listing results (articles, directories). Only include listings ≤ $${budget}.
Respond with only a valid JSON array."""}]
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


# ── /api/analyze (paste-a-listing scam check) ────────────────
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


# ── /api/chat (SSE streaming with tool use) ──────────────────
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
                        elif event.content_block.type == "text":
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


# Serve Vite dist build
dist_dir = os.path.join(os.path.dirname(__file__), "..", "dist")
if os.path.isdir(dist_dir):
    app.mount("/", StaticFiles(directory=dist_dir, html=True), name="static")
