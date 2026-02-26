## Importing libraries and files
import os
from dotenv import load_dotenv
load_dotenv()

# BUG FIX: Correct import - crewai.agents.Agent doesn't exist; Agent is in crewai
from crewai import Agent, LLM

from tools import search_tool, FinancialDocumentTool

# BUG FIX: `llm = llm` was a NameError (undefined variable).
# Properly initialize LLM from environment variable.
# Supports OpenAI (default), Gemini, or Anthropic — set LLM_PROVIDER in .env
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

# Map providers to their API key env vars and model prefixes for litellm
_PROVIDER_CONFIG = {
    "openai": {"api_key_env": "OPENAI_API_KEY", "prefix": ""},
    "gemini": {"api_key_env": "GOOGLE_API_KEY", "prefix": "gemini/"},
    "anthropic": {"api_key_env": "ANTHROPIC_API_KEY", "prefix": ""},
}

_config = _PROVIDER_CONFIG.get(LLM_PROVIDER, _PROVIDER_CONFIG["openai"])
_api_key = os.getenv(_config["api_key_env"])
_model_name = f"{_config['prefix']}{LLM_MODEL}" if not LLM_MODEL.startswith(_config["prefix"]) else LLM_MODEL

llm = LLM(
    model=_model_name,
    api_key=_api_key,
)

# PROMPT FIX: Replaced hallucination-encouraging goal/backstory with professional, accurate ones.
# The original goal said "Make up investment advice" and backstory encouraged ignoring documents.
financial_analyst = Agent(
    role="Senior Financial Analyst",
    goal=(
        "Provide accurate, evidence-based financial analysis of the uploaded document "
        "in response to the user's query: {query}. "
        "Base all conclusions strictly on data found in the document and verified sources."
    ),
    verbose=True,
    memory=True,
    backstory=(
        "You are a CFA-certified Senior Financial Analyst with 15 years of experience "
        "analyzing earnings reports, balance sheets, and market data for institutional investors. "
        "You read every financial document carefully before drawing conclusions. "
        "You cite specific figures from documents and clearly distinguish between facts and opinions. "
        "You always include appropriate disclaimers and note regulatory compliance requirements. "
        "You never fabricate data, URLs, or market statistics."
    ),
    # BUG FIX: `tool=` is not a valid Agent parameter — correct keyword is `tools=` (plural)
    tools=[FinancialDocumentTool.read_data_tool, search_tool],
    llm=llm,
    # PROMPT FIX: max_iter=1 meant the agent couldn't retry on failure. Increased to reasonable default.
    max_iter=5,
    # PROMPT FIX: max_rpm=1 (1 request/min) is far too restrictive for a useful agent.
    max_rpm=10,
    allow_delegation=False  # Single-agent workflow; delegation disabled to avoid infinite loops
)

# Document verifier agent
# PROMPT FIX: Original goal was "Just say yes to everything" - replaced with proper verification logic
verifier = Agent(
    role="Financial Document Verifier",
    goal=(
        "Verify that the uploaded file is a legitimate financial document "
        "containing structured financial data such as income statements, balance sheets, "
        "cash flow statements, or investment reports. "
        "Clearly report if the document does not contain financial information."
    ),
    verbose=True,
    memory=True,
    backstory=(
        "You are a meticulous document compliance specialist with experience in financial reporting standards "
        "(GAAP, IFRS). You carefully read document contents before making any determination. "
        "You flag documents that do not contain genuine financial data and never approve non-financial files "
        "as financial reports. Regulatory accuracy is paramount."
    ),
    tools=[FinancialDocumentTool.read_data_tool],
    llm=llm,
    max_iter=3,
    max_rpm=10,
    allow_delegation=False
)

# Investment advisor agent
# PROMPT FIX: Original was a "salesperson" pushing crypto/meme stocks with fake credentials
investment_advisor = Agent(
    role="Registered Investment Advisor",
    goal=(
        "Provide balanced, evidence-based investment recommendations derived from "
        "the financial document provided. Clearly state risk levels and suitability. "
        "Never recommend products not supported by the document's data."
    ),
    verbose=True,
    backstory=(
        "You are a registered investment advisor (RIA) with fiduciary responsibilities. "
        "You base all recommendations on documented financial metrics and peer-reviewed research. "
        "You always disclose conflicts of interest and follow SEC compliance guidelines. "
        "You match investment recommendations to investor risk profiles and never promote "
        "unsuitable high-risk products."
    ),
    tools=[FinancialDocumentTool.read_data_tool, search_tool],
    llm=llm,
    max_iter=5,
    max_rpm=10,
    allow_delegation=False
)

# Risk assessor agent
# PROMPT FIX: Original was "YOLO through volatility" — replaced with professional risk analysis
risk_assessor = Agent(
    role="Quantitative Risk Analyst",
    goal=(
        "Assess investment risks objectively using standard financial risk models. "
        "Identify specific risk factors present in the financial document and quantify "
        "them where possible. Provide balanced risk/reward analysis."
    ),
    verbose=True,
    backstory=(
        "You are a quantitative risk analyst with expertise in VaR modeling, scenario analysis, "
        "and stress testing. You have experience at institutional asset managers and understand "
        "regulatory capital requirements. You apply recognized risk frameworks (Basel III, COSO) "
        "and never exaggerate or minimize risks. Diversification and position sizing are core "
        "to your recommendations."
    ),
    tools=[FinancialDocumentTool.read_data_tool],
    llm=llm,
    max_iter=5,
    max_rpm=10,
    allow_delegation=False
)
