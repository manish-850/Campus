from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from langchain_groq import ChatGroq
from langchain_core.embeddings import Embeddings  

import numpy as np
from pathlib import Path
import streamlit as st

load_dotenv()
llm=ChatGroq(model="llama-3.3-70b-versatile")

prompt = PromptTemplate(
    template="""You are a very helpful AI assistant answering questions 
    from the given context only.
    RULES:
    rule_1: Use only the information present in the context and answer in your own way
    rule_2: Do not add external knowledge to it
    rule_3: be factual and answer in a informative way 
    rule_4: If the answer is not clearly mentioned, say "Not mentioned in the document
    rule_5: While answering remember that you are a first year Btech student
    rule_6: If asked about personal details like family details and friends then answer like you dont want to disclose it.
    rule_6: If asked about love life then answer like you dont want to disclose it and say in a very shy manner.
    Context:{context}
    Question:{question}
    """,
    input_variables=['context','question']
)
class CustomSentenceEmbedding(Embeddings):
    def __init__(self, model_name="all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)

    def __call__(self, text):
        return self.model.encode([text])[0].tolist()

    def embed_documents(self, texts):
        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        return embeddings.tolist()

    def embed_query(self, query):
        embedding = self.model.encode(
            query,
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        return embedding.tolist()

def load_retriever():
    embedding = CustomSentenceEmbedding()

    BASE_DIR = Path(__file__).resolve().parent
    file_path = BASE_DIR / "data" / "Personal_Profile.md"

    loader = TextLoader(file_path, encoding="utf-8")
    documents = loader.load()

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200,
        chunk_overlap=220
    )

    chunks = text_splitter.split_documents(documents)

    vector_store = FAISS.from_documents(
        documents=chunks,
        embedding=embedding
    )

    return vector_store.as_retriever(search_kwargs={"k": 5})

retriever = load_retriever()
def ask_rag(question):

    doc = retriever.invoke(question)
    context = "\n\n".join([doc.page_content for doc in doc])

    finalPrompt = prompt.format(
        context = context,
        question = question
    )
    response = llm.invoke(finalPrompt)
    return response.content

st.set_page_config(
    page_title="Personal Rag AI",
    layout="centered"
)
with st.sidebar:
    st.markdown("##  About Me")
    st.markdown(
        """
        **Personal RAG AI**  
        Built using:
        - Gemini LLM
        - LangChain
        - FAISS
        - HuggingFace Embeddings

         Ask anything about my profile.
        """
    )

    st.markdown("---")
    st.markdown(" Settings ")
    show_context = st.checkbox("Show retrieved context")

st.markdown(
    """
    <style>
    /* Main background */
    .stApp {
        background-color: #0e1117;
        color: #fafafa;
    }

    /* Text input & textarea */
    textarea, input {
        background-color: #161b22 !important;
        color: #ffffff !important;
        border-radius: 10px;
        border: 1px solid #30363d;
    }

    /* Button */
    .stButton>button {
        background-color: #00ff9c;
        color: black;
        border-radius: 10px;
        height: 3em;
        width: 100%;
        font-weight: bold;
        border: none;
    }

    .stButton>button:hover {
        background-color: #00cc7a;
        color: black;
    }

    /* Answer card */
    .answer-box {
        background-color: #161b22;
        padding: 20px;
        border-radius: 12px;
        border-left: 5px solid #00ff9c;
        margin-top: 20px;
    }

    </style>
    """,
    unsafe_allow_html=True
)

st.markdown(
    """
    <h1 style='text-align:center; color:#00ff9c;'> Personal RAG AI</h1>
    <p style='text-align:center; color:gray;'>
    Gemini • LangChain • FAISS
    </p>
    """,
    unsafe_allow_html=True
)
question = st.text_area(
    " Ask something about me",
    placeholder="e.g. What projects have you worked on?",
    height=120
)

ask_btn = st.button(" Ask AI")
if ask_btn:
    if question.strip() == "":
        st.warning("Bhai kuch toh puch ")
    else:
        with st.spinner("AI soch raha hai... "):
            answer = ask_rag(question)

        st.markdown("###  Answer")
        st.markdown(
            f"<div class='answer-box'>{answer}</div>",
            unsafe_allow_html=True
        )
