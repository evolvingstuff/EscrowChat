import pysqlite3
import sys
sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
from dotenv import load_dotenv
import random
from langchain.docstore.document import Document
from langchain_chroma import Chroma
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI
from langchain import PromptTemplate
import requests
from bs4 import BeautifulSoup
import tqdm
from urllib.parse import urljoin
import config as conf
import logging


class ConversationManager:
    def __init__(self):
        self.history = ""

    def update(self, question, answer):
        self.history += f'QUESTION: {question}\nANSWER: {answer}\n'

    def get_history(self):
        return self.history


def execute_rag_chain(question, rag_chain, conversation_history):
    context = f"Previous Conversation: {conversation_history}\nQuestion: {question}"
    response = ""
    logging.info(f"Processing question: {question}")
    logging.info(f"Using conversation history: {conversation_history}")
    try:
        for chunk in rag_chain.stream(context):
            response += chunk
            print(chunk, end='')
        print('')
    except Exception as e:
        logging.error(f"Error processing chunk: {e}")
    logging.info(f"Full response for the question:\n\n{response}")
    return response


def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)


def extract_text(element):
    return ' '.join(element.stripped_strings)


def scrape_and_parse_data(url=conf.source_data_url):
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f'Failed to retrieve {url}. Status code: {response.status_code}')

    soup = BeautifulSoup(response.content, 'html.parser')

    paragraphs = soup.find_all('p')
    chunks = []

    print(f'scraping data from {url}')

    progress = tqdm.tqdm(range(len(paragraphs)))

    for i, p in enumerate(paragraphs, 1):
        text = extract_text(p)
        progress.update(1)
        if conf.ignore_official_interpretation:
            if text.startswith('Official interpretation') or text.startswith('See interpretation'):
                continue
        chunks.append(text)

        # links = p.find_all('a')
        # for j, link in enumerate(links, 1):
        #     link_text = extract_text(link)
        #     rel_href = link.get('href')
        #     abs_href = urljoin(url, rel_href)
        #     print(f"  Link {j}: {abs_href} - Text: {link_text}")

    return '\n'.join(chunks)


def main():
    random.seed(42)
    logging.basicConfig(filename=conf.log_file, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    conversation_manager = ConversationManager()
    vectorstore = None

    try:
        load_dotenv()
        llm = ChatOpenAI(model=conf.openai_model, temperature=conf.model_temperature)
        text = scrape_and_parse_data()
        if conf.sanity_check:
            text += '\n' + conf.sanity_check_statement
        docs = [Document(page_content=text)]
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=conf.chunk_size, chunk_overlap=conf.chunk_overlap)
        splits = text_splitter.split_documents(docs)
        vectorstore = Chroma.from_documents(documents=splits, embedding=OpenAIEmbeddings())
        retriever = vectorstore.as_retriever()

        with open(conf.prompt_path, 'r') as file:
            prompt_template = file.read()

        prompt = PromptTemplate(
            input_variables=["context", "question", "conversation"],
            template=prompt_template
        )

        rag_chain = (
            {"context": retriever | format_docs, "question": RunnablePassthrough(), "conversation": RunnablePassthrough()}
            | prompt
            | llm
            | StrOutputParser()
        )

        while True:
            print('--------------------------------')
            question = input('QUESTION: ')
            conversation_history = conversation_manager.get_history()
            response = execute_rag_chain(question, rag_chain, conversation_history)
            conversation_manager.update(question, response)

    except Exception as e:
        print(e)
        return
    finally:
        if vectorstore is not None:
            vectorstore.delete_collection()


if __name__ == '__main__':
    main()
