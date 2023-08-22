from langchain.prompts.chat import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain.chat_models import ChatOpenAI
from dotenv import load_dotenv
import os
import psycopg
from psycopg import Cursor
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt
from rich.syntax import Syntax


def execute_query(cursor: Cursor, query: str, max_results=10):
    console = Console()
    syntax = Syntax(query, "sql")
    console.print("[bold blue]Executing query:[/bold blue]")
    console.print(syntax)

    cursor.execute(query)
    results = cursor.fetchmany(max_results)
    table = Table(show_header=True, header_style="bold magenta")
    if cursor.description is not None:
        for column in cursor.description:
            table.add_column(column[0])
    for row in results:
        row = [str(cell) for cell in row]
        table.add_row(*row)
    console.print(table)

    if len(results) >= max_results:
        answer = Prompt.ask(
            "Do you want to see all the results?", choices=["yes", "no"]
        )
        if answer == "yes":
            results = cursor.fetchall()
            for row in results:
                row = [str(cell) for cell in row]
                table.add_row(*row)
            console.print(table)


def main():
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise Exception("Please set the `OPENAI_API_KEY` environment variable")

    ddl_path = os.getenv("DDL_PATH")
    if not ddl_path:
        raise Exception("Please set the `DDL_PATH` environment variable")

    db_schema = open(ddl_path).read()
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
    query = Prompt.ask("Enter your question")

    llm = ChatOpenAI(openai_api_key=api_key)
    result = llm(template.format_messages(schema=db_schema, query=query))
    query = result.content

    database_name = os.environ["DATABASE_NAME"]
    database_user = os.environ["DATABASE_USER"]
    database_password = os.environ["DATABASE_PASSWORD"]
    db_url = f"host=localhost dbname={database_name} user={database_user} password={database_password}"

    with psycopg.connect(db_url) as connection:
        with connection.cursor() as cursor:
            while True:
                try:
                    execute_query(cursor, query)
                    break

                except psycopg.ProgrammingError as e:
                    answer = input(
                        f"Query failed to execute with error {str(e)}, do you want to let the AI try to fix it?"
                    )
                    if answer.lower() in ["yes", "y"]:
                        result = llm(
                            template.format_messages(
                                schema=db_schema,
                                query="The query resulted in the following error, please fix it: "
                                + str(e),
                            )
                        )
                        query = result.content
                        cursor = connection.cursor()
                    else:
                        break


if __name__ == "__main__":
    main()
