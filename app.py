import streamlit as st
import os
from dotenv import load_dotenv

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser


# =========================
# LOAD ENV
# =========================
load_dotenv()

# =========================
# STREAMLIT UI
# =========================
st.set_page_config(page_title="Financial RAG Chatbot")
st.title("📊 Financial RAG Chatbot")


# =========================
# LOAD + VECTOR DB
# =========================
@st.cache_resource
def load_vectorstore():
    loader = PyPDFLoader("data/company_report.pdf")
    docs = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )

    chunks = splitter.split_documents(docs)

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    vectorstore = FAISS.from_documents(chunks, embeddings)
    return vectorstore


vectorstore = load_vectorstore()
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})


# =========================
# FORMAT DOCS
# =========================
def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
# =========================
# GEMINI LLM (SAME MODEL)
# =========================
llm = ChatGoogleGenerativeAI(
    model="gemini-3.1-flash-lite",
    google_api_key=GOOGLE_API_KEY
)


# =========================
# PROMPT
# =========================
prompt = ChatPromptTemplate.from_template("""
You are a Financial Report Analyst.

Answer ONLY using the context below.

Context:
{context}

Question:
{input}
""")


# =========================
# RAG CHAIN
# =========================
chain = (
    {
        "context": retriever | format_docs,
        "input": RunnablePassthrough()
    }
    | prompt
    | llm
    | StrOutputParser()
)


# =========================
# UI INPUT
# =========================
question = st.text_input("Ask your financial question")

if st.button("Ask"):
    if question:

        response = chain.invoke(question)

        st.subheader("💡 Answer")
        st.write(response)

        with st.expander("📄 Retrieved Context"):
            docs = retriever.invoke(question)
            for i, doc in enumerate(docs):
                st.write(f"Chunk {i+1}")
                st.write(doc.page_content)