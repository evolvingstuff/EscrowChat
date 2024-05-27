import pysqlite3
import sys
sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
from dotenv import load_dotenv
import random
import bs4
from langchain import hub
from langchain_community.document_loaders import WebBaseLoader
from langchain.docstore.document import Document
from langchain_chroma import Chroma
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI
from langchain import PromptTemplate
from scrape import scrape_and_parse_data

import config as conf


def main():
    random.seed(42)
    try:
        text = scrape_and_parse_data()

        load_dotenv()
        llm = ChatOpenAI(model=conf.openai_model, temperature=conf.model_temperature)

        docs = [Document(page_content=text)]

        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        splits = text_splitter.split_documents(docs)
        print('setting up vectorstore/embeddings')
        vectorstore = Chroma.from_documents(documents=splits, embedding=OpenAIEmbeddings())

        # Retrieve and generate using the relevant snippets of the blog.
        retriever = vectorstore.as_retriever()
        # prompt = hub.pull("rlm/rag-prompt")

        with open(conf.prompt_path, 'r') as file:
            prompt_template = file.read()
        # prompt = PromptTemplate.from_template(prompt_template)  # (input_variables=["context", "question"], template=prompt_template)

        # prompt_template = """You are a knowledgeable assistant. Use the following context to answer the question.
        # Context:
        # {context}
        #
        # Question:
        # {question}
        #
        # Answer the question in detail and provide references to the context."""
        prompt = PromptTemplate(input_variables=["context", "question"], template=prompt_template)

        # print(prompt.messages[0].prompt.template)

        # custom_template = prompt.messages[0].prompt.template + "\nPlease provide detailed references for your answers."
        # prompt.messages[0].prompt.template = custom_template

        # TODO: what is the current prompt?

        def format_docs(docs):
            return "\n\n".join(doc.page_content for doc in docs)

        rag_chain = (
                {"context": retriever | format_docs, "question": RunnablePassthrough()}
                | prompt
                | llm
                | StrOutputParser()
        )

        test_questions = [
            "What actions are considered a violation of the RESPA?",
            "Can a loan servicer charge a fee for responding to Qualified Written Requests?",
            "What is required for a mortgage servicing transfer notice?"
        ]

        for question in test_questions:
            print('\n')
            print('------------------------------------------')
            print(f'QUESTION: {question}')
            print('')
            line_length = 0
            for chunk in rag_chain.stream(question):  # TODO: handle newlines properly
                if line_length >= conf.line_length:
                    print('')
                    line_length = 0
                    if chunk.startswith(' '):
                        chunk = chunk[1:]
                print(chunk, end="", flush=True)
                line_length += len(chunk)

        while True:
            print('\n')
            print('------------------------------------------')
            question = input('QUESTION: ')
            print('')
            line_length = 0
            for chunk in rag_chain.stream(question):  # TODO: handle newlines properly
                if line_length >= conf.line_length:
                    print('')
                    line_length = 0
                    if chunk.startswith(' '):
                        chunk = chunk[1:]
                print(chunk, end="", flush=True)
                line_length += len(chunk)


        # cleanup
        vectorstore.delete_collection()

    except Exception as e:
        print(e)
        # TODO: further error handling
        return


if __name__ == '__main__':
    main()
