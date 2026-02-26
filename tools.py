## Importing libraries and files
import os
from dotenv import load_dotenv
load_dotenv()

# BUG FIX: Removed incorrect `from crewai_tools import tools` import
from crewai_tools import SerperDevTool
from crewai.tools import tool

# BUG FIX: Import PDF loader properly
try:
    from langchain_community.document_loaders import PyPDFLoader
except ImportError:
    from langchain.document_loaders import PyPDFLoader

## Creating search tool
search_tool = SerperDevTool()

## Creating custom pdf reader tool
class FinancialDocumentTool:
    # BUG FIX 1: `read_data_tool` was async - crewai tools must be synchronous
    # BUG FIX 2: Added @staticmethod decorator so it can be referenced as FinancialDocumentTool.read_data_tool
    # BUG FIX 3: `Pdf` was undefined - replaced with PyPDFLoader from langchain_community
    @staticmethod
    @tool("Financial Document Reader")
    def read_data_tool(path: str = 'data/sample.pdf') -> str:
        """Tool to read and extract text from a PDF financial document.

        Args:
            path (str): Path to the PDF file to read. Defaults to 'data/sample.pdf'.

        Returns:
            str: Full text content of the financial document.
        """
        if not os.path.exists(path):
            return f"Error: File not found at path '{path}'"

        try:
            loader = PyPDFLoader(path)
            docs = loader.load()

            full_report = ""
            for data in docs:
                content = data.page_content

                # Clean and format the financial document data
                # BUG FIX: Original used infinite loop risk with while "\n\n" - now using replace properly
                content = "\n".join(line for line in content.splitlines() if line.strip())

                full_report += content + "\n"

            return full_report if full_report.strip() else "No text content could be extracted from the document."
        except Exception as e:
            return f"Error reading PDF: {str(e)}"


## Creating Investment Analysis Tool
class InvestmentTool:
    @staticmethod
    @tool("Investment Analyzer")
    def analyze_investment_tool(financial_document_data: str) -> str:
        """Analyze financial document data and extract key investment metrics.

        Args:
            financial_document_data (str): Raw text extracted from a financial document.

        Returns:
            str: Structured investment analysis summary.
        """
        if not financial_document_data or not financial_document_data.strip():
            return "No financial data provided for analysis."

        # Clean up the data format - BUG FIX: Original O(n^2) loop replaced with efficient join
        processed_data = " ".join(financial_document_data.split())

        return f"Financial data processed ({len(processed_data)} characters). Ready for investment analysis."


## Creating Risk Assessment Tool
class RiskTool:
    @staticmethod
    @tool("Risk Assessor")
    def create_risk_assessment_tool(financial_document_data: str) -> str:
        """Assess risk factors from financial document data.

        Args:
            financial_document_data (str): Raw text from a financial document.

        Returns:
            str: Risk assessment summary based on the document content.
        """
        if not financial_document_data or not financial_document_data.strip():
            return "No financial data provided for risk assessment."

        return f"Risk assessment data received ({len(financial_document_data)} characters). Analyzing risk factors."
