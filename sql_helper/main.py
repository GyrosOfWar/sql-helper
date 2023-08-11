from langchain.prompts.chat import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain.chat_models import ChatOpenAI
from dotenv import load_dotenv
import os
import subprocess


def dump_sql_schema():
    database_name = os.environ["DATABASE_NAME"]
    database_user = os.environ["DATABASE_USER"]
    database_password = os.environ["DATABASE_PASSWORD"]
    # run pg_dump process
    output = subprocess.check_output(
        [
            "pg_dump",
            "--schema-only",
            "-x",
            database_name,
        ]
    )
    lines = output.decode("utf-8").splitlines()
    result = []
    for line in lines:
        if not line.startswith("--") and line.strip() != "":
            result.append(line)
    return "\n".join(result)


def main():
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise Exception("API key not found")

    db_schema = dump_sql_schema()
    system_template = SystemMessagePromptTemplate.from_template(
        """You are a helpful SQL assistant. Your job is to help the user write SQL queries.
           The user will provide a database schema and a natural language query. 
           You will provide the SQL query that answers the question.
           Respond only with the SQL query, no other text."""
    )
    schema_template = HumanMessagePromptTemplate.from_template("{schema}")
    query_template = HumanMessagePromptTemplate.from_template("{query}")

    template = ChatPromptTemplate.from_messages(
        [
            system_template,
            schema_template,
            query_template,
        ]
    )
    query = input("What do you want to seach for? >> ")

    llm = ChatOpenAI(openai_api_key=api_key)
    result = llm(template.format_messages(schema=db_schema, query=query))
    print(result.content)


if __name__ == "__main__":
    main()
