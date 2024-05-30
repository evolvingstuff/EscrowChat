import pysqlite3
import sys
sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")  # handle incompatible OpenMP libs
from dotenv import load_dotenv
import textwrap
from langchain.docstore.document import Document
from langchain_chroma import Chroma
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableSequence
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
import requests
from bs4 import BeautifulSoup
import tqdm
import config as conf
import logging


class ConversationManager:
    """
    Purpose:
        Maintain state of ongoing conversation with the LLM
    """
    def __init__(self):
        self.history = ""

    def update(self, question: str, answer: str) -> None:
        self.history += f'QUESTION: {question}\nANSWER: {answer}\n'

    def get_history(self) -> str:
        return self.history


def execute_rag_chain(rag_chain: RunnableSequence, question: str, conversation_history: str) -> str:
    """
    Purpose:
        Run the LLM using RAG and output to screen using streaming,
        and limiting width of output to fixed width for added readability
        in CLI
    Outline:
        1. log question and current conversation history state
        2. MAIN LOOP: enumerate over chunked results of rag_chain, printing to stdout
        3. log full response
        4. return concatenated results
    """
    logging.info(f"Processing question: {question}")
    logging.info(f"Using conversation history: {conversation_history}")

    context = f"Previous Conversation: {conversation_history}\nQuestion: {question}"
    response = ""
    line_buffer = ""  # a line buffer to accumulate text for "smart" wrapping
    try:
        for chunk in rag_chain.stream(context):
            line_buffer += chunk  # append the newest chunk to the buffer
            while True:
                if '\n' in line_buffer:
                    pos_newline = line_buffer.find('\n')
                    # process text before the newline, if any
                    part_before_newline = line_buffer[:pos_newline]
                    if part_before_newline:
                        wrapped_text = textwrap.fill(part_before_newline, width=conf.max_width)
                        print(wrapped_text, end='')
                        response += wrapped_text
                    print()
                    response += '\n'
                    line_buffer = line_buffer[pos_newline + 1:]
                else:
                    break

            if len(line_buffer) > conf.max_width:
                last_space = line_buffer.rfind(' ', 0, conf.max_width+1)  # look for last space within limits
                if last_space != -1:
                    to_print = textwrap.fill(line_buffer[:last_space], width=conf.max_width)
                    print(to_print)
                    response += to_print + '\n'
                    line_buffer = line_buffer[last_space+1:]  # Continue with the rest in the buffer
    except Exception as e:
        logging.error(f"Error processing chunk: {e}")

    if line_buffer:  # handle any remaining text
        wrapped_text = textwrap.fill(line_buffer, width=conf.max_width)
        print(wrapped_text)
        response += wrapped_text + '\n'

    logging.info(f"Full response for the question:\n\n{response}")
    return response


def scrape_and_parse_data(url: str = conf.source_data_url) -> str:
    """
    Purpose:
        Get the data to be used for retrieval augmented generation
    Outline:
        1. get page source from provided url
        2. use BeautifulSoup library to parse out readable text
        3. return the full concatenated text
    """
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f'Failed to retrieve {url}. Status code: {response.status_code}')
    print(f'scraping data from {url}')
    soup = BeautifulSoup(response.content, 'html.parser')
    paragraphs = soup.find_all('p')
    chunks = []
    progress = tqdm.tqdm(range(len(paragraphs)))
    for i, p in enumerate(paragraphs, 1):
        text = ' '.join(p.stripped_strings)  # extract text
        progress.update(1)
        if conf.ignore_official_interpretation:
            if text.startswith('Official interpretation') or text.startswith('See interpretation'):
                continue
        chunks.append(text)
    return '\n'.join(chunks)


def main():
    """
    Purpose:
        Core program logic
    Outline:
        1.  setup logging
        2.  instantiate conversation manager
        3.  scrape and parse text from the source url
        4.  optionally add "sanity check" statements into data (for debugging)
        5.  load env vars, and possibly ask for OpenAI API key
        6.  instantiate llm from OpenAI
        7.  instantiate Chroma vector store and retriever
        8.  instantiate prompt using selected version in prompts/*
        9.  instantiate rag_chain object
        10. MAIN LOOP: loop over Q/A conversation
        11. garbage collection for Chroma vectorstore
    """

    try:
        logging.basicConfig(filename=conf.log_file, level=logging.INFO,
                            format='%(asctime)s - %(levelname)s - %(message)s')
        conversation_manager = ConversationManager()
        vectorstore = None
        text = scrape_and_parse_data()
        if conf.sanity_check:  # optionally add special clauses for debugging
            text += '\n' + conf.sanity_check_statement
        docs = [Document(page_content=text)]
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=conf.chunk_size, chunk_overlap=conf.chunk_overlap)
        splits = text_splitter.split_documents(docs)
        load_dotenv()
        llm = ChatOpenAI(model=conf.openai_model)
        vectorstore = Chroma.from_documents(documents=splits, embedding=OpenAIEmbeddings())
        retriever = vectorstore.as_retriever()

        with open(conf.prompt_path, 'r') as file:
            prompt_template = file.read()

        prompt = PromptTemplate(
            input_variables=["context", "question", "conversation"],
            template=prompt_template
        )

        def format_docs(docs):
            return "\n\n".join(doc.page_content for doc in docs)

        rag_chain = (
            {"context": retriever | format_docs, "question": RunnablePassthrough(), "conversation": RunnablePassthrough()}
            | prompt
            | llm
            | StrOutputParser()
        )

        while True:
            print('--------------------------------')
            question = input('QUESTION: ')
            print()
            print('ANSWER:')
            conversation_history = conversation_manager.get_history()
            response = execute_rag_chain(rag_chain, question, conversation_history)
            conversation_manager.update(question, response)

    except Exception as e:
        print(e)
        return
    finally:
        if vectorstore is not None:
            vectorstore.delete_collection()


if __name__ == '__main__':
    main()
