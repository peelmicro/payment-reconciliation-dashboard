from langchain_anthropic import ChatAnthropic
from langchain_community.utilities import SQLDatabase
from langchain_core.prompts import ChatPromptTemplate

from app.config import settings

# Only include our application tables (exclude n8n internal tables)
APP_TABLES = [
    "currencies",
    "providers",
    "merchants",
    "payments",
    "stripe_payments",
    "paypal_payments",
    "bank_transfer_payments",
    "reconciliations",
    "code_sequences",
]

SYSTEM_PROMPT = """You are a payment reconciliation analyst assistant.
You have access to a PostgreSQL database with the following business context:

- **payments**: Internal payment records (source of truth). Amounts are in cents.
- **stripe_payments**: External records from Stripe. Have payment_id linking to payments.
- **paypal_payments**: External records from PayPal. Have payment_id linking to payments.
- **bank_transfer_payments**: External records from bank transfers. Have payment_id linking to payments.
- **reconciliations**: Results of matching internal payments with provider records.
  Status values: matched, matched_with_fee, amount_mismatch, missing_internal, missing_external, duplicate, disputed.
  Has score, max_score, confidence (percentage) fields.
- **currencies**: USD, EUR, GBP with iso codes and symbols.
- **providers**: STRIPE, PAYPAL, BANKINTER.
- **merchants**: Business entities with vat_number, country, currency.

Important:
- All monetary amounts are stored in **cents** (minor units). Divide by 100 to show in major units.
- When answering, convert cents to the appropriate currency format (e.g., 49892 cents = €498.92).
- Answer in the same language as the question.
- Be concise but informative.
"""


def create_ask_service():
    """Create the LangChain SQL chain. Returns None if API key is not configured."""
    if not settings.anthropic_api_key:
        return None

    # Connect to the database (synchronous — LangChain requirement)
    db = SQLDatabase.from_uri(
        settings.sync_database_url,
        include_tables=APP_TABLES,
    )

    # Create the LLM
    llm = ChatAnthropic(
        model="claude-sonnet-4-20250514",
        api_key=settings.anthropic_api_key,
        temperature=0,
    )

    return db, llm


async def ask_question(question: str) -> dict:
    """Process a natural language question about the payment data."""
    result = create_ask_service()
    if result is None:
        return {
            "question": question,
            "answer": None,
            "error": "ANTHROPIC_API_KEY not configured. Set it in .env to enable natural language queries.",
        }

    db, llm = result

    # Step 1: Generate SQL from the question
    generate_query_prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT + "\n\nGiven the following database schema:\n{table_info}\n\n"
         "Write a PostgreSQL query to answer the user's question. "
         "Return ONLY the SQL query, nothing else. No markdown, no explanation."),
        ("human", "{input}"),
    ])

    # Get the schema
    table_info = db.get_table_info()

    # Generate the SQL query
    query_response = llm.invoke(
        generate_query_prompt.format_messages(
            table_info=table_info,
            input=question,
        )
    )
    sql_query = query_response.content.strip()

    # Clean up: remove markdown code blocks if present
    if sql_query.startswith("```"):
        sql_query = sql_query.split("\n", 1)[1]  # Remove first line
        sql_query = sql_query.rsplit("```", 1)[0]  # Remove last ```
        sql_query = sql_query.strip()

    # Step 2: Execute the query
    try:
        query_result = db.run(sql_query)
    except Exception as e:
        return {
            "question": question,
            "sql": sql_query,
            "answer": None,
            "error": f"Query execution failed: {str(e)}",
        }

    # Step 3: Generate a natural language answer from the results
    answer_prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", "Question: {question}\n\nSQL Query executed:\n{sql}\n\nQuery results:\n{results}\n\n"
         "Please provide a clear, concise answer to the question based on these results. "
         "Remember to convert cents to currency format (divide by 100)."),
    ])

    answer_response = llm.invoke(
        answer_prompt.format_messages(
            question=question,
            sql=sql_query,
            results=query_result,
        )
    )

    return {
        "question": question,
        "sql": sql_query,
        "answer": answer_response.content,
    }
