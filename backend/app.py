import os
from dotenv import load_dotenv

load_dotenv()  # must run BEFORE the Hugging Face imports (sets HF_HOME / tokens)
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from youtube_transcript_api import YouTubeTranscriptApi
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableParallel, RunnablePassthrough, RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from langchain_huggingface import HuggingFaceEmbeddings, ChatHuggingFace, HuggingFaceEndpoint

# ---------- models (loaded once at startup) ----------
embeddings = HuggingFaceEmbeddings(
    model_name="BAAI/bge-base-en-v1.5",
    encode_kwargs={"normalize_embeddings": True},
)

llm = ChatHuggingFace(
    llm=HuggingFaceEndpoint(
        repo_id="deepseek-ai/DeepSeek-V3",
        task="text-generation",
        temperature=0.2,
        max_new_tokens=512,
    )
)

splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)

prompt = PromptTemplate(
    template="""
You are a helpful assistant.
Answer ONLY from the provided transcript context.
If the context is insufficient, just say you don't know.

{context}
Question: {question}
""",
    input_variables=["context", "question"],
)

parser = StrOutputParser()


def format_docs(docs):
    return "\n\n".join(d.page_content for d in docs)


# video_id -> ready-to-use chain (so each video is indexed only once)
chains: dict = {}


def build_chain(video_id: str):
    fetched = YouTubeTranscriptApi().fetch(video_id, languages=["en", "hi"])
    transcript = " ".join(s.text for s in fetched)

    chunks = splitter.create_documents([transcript])
    vector_store = FAISS.from_documents(chunks, embeddings)
    # MMR returns more varied chunks, which helps broad questions like "summarize"
    retriever = vector_store.as_retriever(
        search_type="mmr", search_kwargs={"k": 6, "fetch_k": 20}
    )

    parallel = RunnableParallel(
        {
            "context": retriever | RunnableLambda(format_docs),
            "question": RunnablePassthrough(),
        }
    )
    return parallel | prompt | llm | parser, len(chunks)


# ---------- API ----------
app = FastAPI(title="YouTube RAG")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # fine for local use; the extension calls from chrome-extension://
    allow_methods=["*"],
    allow_headers=["*"],
)


class IndexReq(BaseModel):
    video_id: str


class AskReq(BaseModel):
    video_id: str
    question: str


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/index")
def index(req: IndexReq):
    if req.video_id in chains:
        return {"status": "cached"}
    try:
        chain, n = build_chain(req.video_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not get transcript: {e}")
    chains[req.video_id] = chain
    return {"status": "indexed", "chunks": n}


@app.post("/ask")
def ask(req: AskReq):
    chain = chains.get(req.video_id)
    if chain is None:
        raise HTTPException(status_code=404, detail="Video not indexed yet. Call /index first.")
    try:
        return {"answer": chain.invoke(req.question)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
