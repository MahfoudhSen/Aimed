"""
AI Housing Agent - BMCC Hackathon 2026
Real browsing agent for finding safe, affordable housing
"""

import os
from openai import OpenAI
from tavily import TavilyClient
import requests
from dotenv import load_dotenv
import json

load_dotenv()

# Initialize clients
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
tavily_client = TavilyClient(api_key=os.getenv("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"))

def search_web(query):
    """Actually search the web using Tavily"""
    print(f" Searching web for: {query}")

    response = tavily_client.search(
        query=query,
        search_depth="advanced",
        max_results=5
    )

    return response['results']

def read_webpage(url):
    """Extract content from URL using Jina AI Reader"""
    print(f"Reading: {url}")

    # Jina AI Reader - converts any URL to clean markdown
    reader_url = f"https://r.jina.ai/{url}"

    try:
        response = requests.get(reader_url, timeout=10)
        return response.text[:5000]  # First 5000 chars
    except Exception as e:
        print(f"    Could not read page: {e}")
        return "Could not read page"

def analyze_listing_with_ai(content, url):
    """AI extracts structured info from listing page"""

    prompt = f"""
Extract housing information from this webpage content:

URL: {url}
Content: {content}

Extract and return JSON:
{{
  "price": "monthly rent or null",
  "location": "area/neighborhood",
  "bedrooms": "number or null",
  "description": "brief summary",
  "contact_info": "how to contact",
  "red_flags": ["any suspicious elements"],
  "is_suspicious": true or false
}}
"""

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )

        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"   ⚠️  Analysis failed: {e}")
        return {
            "price": "unknown",
            "location": "unknown",
            "description": "Could not analyze",
            "is_suspicious": False,
            "red_flags": []
        }

def housing_browsing_agent(user_request):
    """Main agent that browses web for housing"""

    print(f"\n{'='*60}")
    print(f"USER REQUEST: {user_request}")
    print(f"{'='*60}\n")

    # Step 1: AI creates search query
    query_prompt = f"""
Convert this housing request into an effective Google search query:
"{user_request}"

Focus on: location, price range, housing type
Include sites like: craigslist, apartments.com, zillow

Return just the search query string.
"""

    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": query_prompt}]
    )

    search_query = response.choices[0].message.content.strip()
    print(f"🎯 Generated search query: {search_query}\n")

    # Step 2: Actually search the web
    search_results = search_web(search_query)

    print(f"✅ Found {len(search_results)} results\n")

    # Step 3: Browse each result
    analyzed_listings = []

    for i, result in enumerate(search_results[:3], 1):  # Top 3 results
        print(f"\n--- Analyzing Result {i} ---")
        print(f"Title: {result['title']}")
        print(f"URL: {result['url']}\n")

        # Read the actual webpage
        content = read_webpage(result['url'])

        # AI analyzes the content
        analysis = analyze_listing_with_ai(content, result['url'])

        analyzed_listings.append({
            "title": result['title'],S
            "url": result['url'],
            "snippet": result['content'],
            "analysis": analysis
        })

        # Show what we found
        if analysis.get('is_suspicious'):
            print(f"🚨 SCAM DETECTED")
        else:
            print(f"✅ Looks legitimate")

        print(f"Price: {analysis.get('price', 'Not found')}")
        print(f"Location: {analysis.get('location', 'Not found')}")
        if analysis.get('red_flags'):
            print(f"Red flags: {', '.join(analysis['red_flags'])}")

    # Step 4: AI creates final summary
    summary_prompt = f"""
You are a helpful housing assistant. Summarize these real listings you found online.

User request: "{user_request}"

Listings analyzed:
{json.dumps(analyzed_listings, indent=2)}

Provide:
1. Quick summary of what you found
2. Best option(s) with reasoning
3. Warning about any scams
4. Clear recommendation

Be specific and reference actual URLs.
"""

    final_response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": summary_prompt}]
    )

    print(f"\n{'='*60}")
    print("AGENT SUMMARY:")
    print(f"{'='*60}\n")
    print(final_response.choices[0].message.content)

    return {
        "summary": final_response.choices[0].message.content,
        "listings": analyzed_listings
    }

# Demo
if __name__ == "__main__":
    print("🏠 REAL WEB BROWSING HOUSING AGENT")
    print("SafeNest AI - BMCC Hackathon 2026\n")

    # Test with real query
    housing_browsing_agent("Find me affordable housing in Brooklyn under $900 per month")
