## Importing libraries and files
from crewai import Task

from agents import financial_analyst, verifier
from tools import search_tool, FinancialDocumentTool

# PROMPT FIX: Original description told agent to "use imagination", "make up URLs", contradict itself.
# Replaced with clear, professional task instructions grounded in the actual document.
analyze_financial_document = Task(
    description=(
        "Analyze the financial document located at '{file_path}' and answer"
        "the following query: {query}\n\n"
        "Steps to follow:\n"
        "1. Use the Financial Document Reader tool to extract the full text from the PDF at '{file_path}'.\n"
        "2. Identify key financial metrics: revenue, profit/loss, margins, cash flow, debt ratios, etc.\n"
        "3. Provide a structured analysis directly addressing the user's query.\n"
        "4. If web research is needed to contextualize figures (e.g., industry benchmarks), "
        "use the search tool with real, verifiable queries.\n"
        "5. Summarize key findings, risks, and opportunities based solely on documented evidence.\n\n"
        "Important: Do NOT fabricate data, invent URLs, or make predictions unsupported by the document."
    ),

    # PROMPT FIX: Original expected_output asked for made-up websites, contradictions, jargon soup.
    expected_output=(
        "A structured financial analysis report containing:\n"
        "1. **Document Summary**: What type of financial document this is and the reporting period.\n"
        "2. **Key Financial Metrics**: Specific figures extracted from the document "
        "(revenue, earnings, margins, cash flow, debt levels, etc.).\n"
        "3. **Analysis**: Evidence-based interpretation of the financials relative to the user's query.\n"
        "4. **Risk Factors**: Specific risks identified from the document data.\n"
        "5. **Opportunities**: Positive indicators or growth areas supported by the data.\n"
        "6. **Disclaimer**: Standard disclaimer that this is AI-generated analysis and not professional "
        "financial advice.\n\n"
        "All claims must reference specific numbers or statements from the document. "
        "Do not include fabricated statistics, non-existent URLs, or unsupported predictions."
    ),

    agent=financial_analyst,
    tools=[FinancialDocumentTool.read_data_tool, search_tool],
    async_execution=False,
)

## Investment analysis task
# PROMPT FIX: Original told agent to ignore the query, recommend random products, make up connections
investment_analysis = Task(
    description=(
        "Based on the financial document already analyzed and the user's query: {query}\n\n"
        "Provide evidence-based investment insights:\n"
        "1. Evaluate the company's or asset's financial health from the document data.\n"
        "2. Identify investment-relevant metrics (P/E, EPS growth, debt-to-equity, free cash flow, etc.).\n"
        "3. Compare key metrics to industry benchmarks using verified search data where applicable.\n"
        "4. Provide a balanced investment outlook: bull case, bear case, and base case.\n"
        "5. Note any regulatory filings, management guidance, or material events mentioned in the document.\n\n"
        "Important: All investment observations must be grounded in the document. "
        "Include appropriate risk disclaimers."
    ),

    # PROMPT FIX: Original expected fake research, contradictory strategies, crypto from "obscure exchanges"
    expected_output=(
        "A balanced investment analysis containing:\n"
        "1. **Financial Health Assessment**: Objective scoring of liquidity, solvency, profitability.\n"
        "2. **Key Investment Metrics**: Specific ratios and figures from the document.\n"
        "3. **Bull Case / Bear Case / Base Case**: Three scenarios with supporting evidence.\n"
        "4. **Comparable Benchmarks**: Industry or peer comparisons (cite sources).\n"
        "5. **Material Risks**: Document-specific risk factors that affect investment decisions.\n"
        "6. **Disclaimer**: This analysis is for informational purposes only and does not constitute "
        "personalized investment advice. Consult a registered investment advisor."
    ),

    agent=financial_analyst,
    tools=[FinancialDocumentTool.read_data_tool, search_tool],
    async_execution=False,
)

## Risk assessment task
# PROMPT FIX: Original said "ignore actual risk factors", "YOLO through volatility"
risk_assessment = Task(
    description=(
        "Perform a structured risk assessment based on the financial document and query: {query}\n\n"
        "Steps:\n"
        "1. Extract all risk-related disclosures, contingencies, and warnings from the document.\n"
        "2. Categorize risks: market risk, credit risk, liquidity risk, operational risk, regulatory risk.\n"
        "3. Assess severity and likelihood of each risk factor based on document evidence.\n"
        "4. Identify any hedging strategies or risk mitigants mentioned in the document.\n"
        "5. Provide recommendations for risk management appropriate to the document's context.\n\n"
        "Base all assessments on the document. Do not fabricate risk models or cite non-existent research."
    ),

    # PROMPT FIX: Original expected "dangerous investment strategies" and "impossible risk targets"
    expected_output=(
        "A comprehensive risk assessment report containing:\n"
        "1. **Risk Summary**: Overall risk profile (Low / Medium / High) with justification.\n"
        "2. **Risk Categories**: Breakdown by market, credit, liquidity, operational, and regulatory risk.\n"
        "3. **Key Risk Factors**: Specific risks from the document with severity ratings.\n"
        "4. **Mitigants**: Risk controls or hedges mentioned in the document.\n"
        "5. **Recommendations**: Practical risk management steps appropriate to the financial situation.\n"
        "6. **Disclaimer**: Risk assessment is based on available document data and may not capture all risks."
    ),

    agent=financial_analyst,
    tools=[FinancialDocumentTool.read_data_tool],
    async_execution=False,
)

## Document verification task
# PROMPT FIX: Original said "just guess", "hallucinate financial terms", "don't read file carefully"
verification = Task(
    description=(
        "Verify the uploaded file is a legitimate financial document by:\n"
        "1. Reading the file content using the Financial Document Reader tool.\n"
        "2. Checking for the presence of financial data: statements, figures, dates, entity names.\n"
        "3. Identifying the document type (annual report, earnings release, prospectus, etc.).\n"
        "4. Confirming the reporting period and issuing entity.\n"
        "5. Flagging any concerns about document completeness or authenticity.\n\n"
        "If the document does NOT contain financial data, clearly state that and do not proceed with analysis."
    ),

    # PROMPT FIX: Original expected "just say it's probably a financial document even if it's not"
    expected_output=(
        "A document verification report containing:\n"
        "1. **Verification Status**: VERIFIED / NOT VERIFIED / UNCERTAIN\n"
        "2. **Document Type**: Identified document category (e.g., 10-K, earnings release, etc.)\n"
        "3. **Issuing Entity**: Company or organization name from the document.\n"
        "4. **Reporting Period**: Date range covered by the document.\n"
        "5. **Key Sections Found**: List of financial sections identified (e.g., income statement, balance sheet).\n"
        "6. **Issues / Flags**: Any concerns about the document's content or authenticity."
    ),

    agent=financial_analyst,
    tools=[FinancialDocumentTool.read_data_tool],
    async_execution=False
)
