"""
AI Housing Agent - FREE VERSION using Ollama
BMCC Hackathon 2026

Uses:
- Ollama (FREE local LLM)
- DuckDuckGo search (FREE)
- Jina AI Reader (FREE)
"""

import requests
import json
from duckduckgo_search import DDGS

def ollama_chat(prompt, model="llama3.2"):
    """Chat with Ollama (local LLM)"""
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False
            },
            timeout=60
        )
        return response.json()["response"]
    except Exception as e:
        print(f"⚠️  Ollama error: {e}")
        return None

def search_web(query, max_results=5):
    """Search web using DuckDuckGo (FREE)"""
    print(f"🔍 Searching web for: {query}")

    try:
        with DDGS() as ddgs:
            results = []
            for result in ddgs.text(query, max_results=max_results):
                results.append({
                    "title": result.get("title", ""),
                    "url": result.get("href", ""),
                    "snippet": result.get("body", "")
                })
            return results
    except Exception as e:
        print(f"⚠️  Search error: {e}")
        # Fallback to sample data
        return get_sample_listings()

def get_sample_listings():
    """Fallback sample data if search fails"""
    print("   💡 Using demo sample data for presentation")
    return [
        {
            "title": "Affordable Room in Brooklyn - $750/month",
            "url": "https://brooklyn.craigslist.org/listing1",
            "snippet": "Nice room near subway. Contact via email. References required. Standard lease agreement available. Utilities included."
        },
        {
            "title": "URGENT: Luxury Apartment $400!!",
            "url": "https://scam-site.com/listing2",
            "snippet": "Amazing deal! Luxury 2BR for only $400! Owner overseas, send deposit via Western Union to secure. No viewing needed! Act fast before it's gone!"
        },
        {
            "title": "Shared apartment in Bushwick - $850/month",
            "url": "https://brooklyn.craigslist.org/listing3",
            "snippet": "Clean shared apartment with 2 roommates. Close to L train. Available immediately. Call to schedule viewing. First month + deposit required."
        }
    ]

def read_webpage(url):
    """Extract content from URL using Jina AI Reader (FREE)"""
    print(f"📄 Reading: {url}")

    reader_url = f"https://r.jina.ai/{url}"

    try:
        response = requests.get(reader_url, timeout=10)
        return response.text[:3000]  # First 3000 chars
    except Exception as e:
        print(f"   ⚠️  Could not read page: {e}")
        return "Could not read page"

def analyze_listing(listing):
    """Use Ollama to analyze listing for scams"""

    prompt = f"""Analyze this housing listing for scam indicators. Be concise.

Title: {listing['title']}
Description: {listing['snippet']}

Look for red flags like:
- Unrealistically low prices
- Wire transfer/Western Union requests
- Owner unavailable/overseas
- No viewing allowed
- Urgency tactics

Respond in this format:
SCAM: yes or no
CONFIDENCE: high/medium/low
RED FLAGS: list them
RECOMMENDATION: brief advice
"""

    response = ollama_chat(prompt)

    if not response:
        return {
            "is_scam": False,
            "confidence": "low",
            "red_flags": ["Could not analyze"],
            "recommendation": "Verify manually"
        }

    # Parse response
    is_scam = "yes" in response.lower()[:50]

    return {
        "is_scam": is_scam,
        "analysis": response,
        "confidence": "medium"
    }

def housing_agent(user_request):
    """Main AI housing agent using Ollama"""

    print(f"\n{'='*60}")
    print(f"USER REQUEST: {user_request}")
    print(f"{'='*60}\n")

    # Step 1: Extract search intent
    print("🤖 Understanding your request...")

    intent_prompt = f"""Extract housing search parameters from this request:
"{user_request}"

Respond with just:
LOCATION: [location or NYC]
MAX_PRICE: [number or 1000]
SEARCH_QUERY: [optimized Google search for housing sites]
"""

    intent_response = ollama_chat(intent_prompt)

    if not intent_response:
        print("❌ Ollama not running. Please start Ollama first.")
        print("Run: ollama serve")
        return None

    print(f"✅ Understood!\n")

    # Extract search query from response
    search_query = user_request + " site:craigslist.org OR site:apartments.com"
    if "brooklyn" in user_request.lower():
        search_query = f"housing Brooklyn affordable {search_query}"

    # Step 2: Search the web
    results = search_web(search_query)

    print(f"✅ Found {len(results)} results\n")

    # Step 3: Analyze each listing
    analyzed_listings = []

    for i, result in enumerate(results[:3], 1):
        print(f"\n--- Analyzing Result {i} ---")
        print(f"Title: {result['title']}")
        print(f"URL: {result['url']}\n")

        # Analyze for scams
        analysis = analyze_listing(result)

        analyzed_listings.append({
            **result,
            "analysis": analysis
        })

        # Show result
        if analysis.get('is_scam'):
            print(f"🚨 POTENTIAL SCAM DETECTED")
        else:
            print(f"✅ Looks safer")

        print(f"Analysis: {analysis.get('analysis', 'N/A')[:200]}...\n")

    # Step 4: Final summary
    print(f"\n{'='*60}")
    print("🤖 GENERATING SUMMARY...")
    print(f"{'='*60}\n")

    summary_prompt = f"""Based on these housing listings, provide a helpful summary.

User asked: "{user_request}"

Listings found:
{json.dumps([{
    'title': l['title'],
    'scam': l['analysis'].get('is_scam', False)
} for l in analyzed_listings], indent=2)}

Provide:
1. Brief overview
2. Best option(s)
3. Warning about scams
4. Clear recommendation

Be conversational and helpful. Keep it under 150 words.
"""

    summary = ollama_chat(summary_prompt)

    if summary:
        print(summary)
    else:
        print("✅ Analysis complete. Check results above.")

    return {
        "summary": summary,
        "listings": analyzed_listings
    }

# Main execution
if __name__ == "__main__":
    print("🏠 FREE AI HOUSING AGENT")
    print("Powered by Ollama (Local LLM)\n")

    # Check if Ollama is running
    try:
        test = requests.get("http://localhost:11434/api/tags", timeout=2)
        print("✅ Ollama is running!\n")
    except:
        print("❌ Ollama is not running!")
        print("\nTo start Ollama:")
        print("1. Install: https://ollama.ai")
        print("2. Run: ollama pull llama3.2")
        print("3. Run: ollama serve")
        print("\nThen run this script again.\n")
        exit(1)

    # Run demo
    housing_agent("Find me affordable housing in Brooklyn under $900 per month")
