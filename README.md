# YouTube Chat (RAG)

Chat with any YouTube video from a Chrome extension. It reads the video's transcript, indexes it, and answers your questions using only what was said in the video.

## How it works

```
Chrome extension (popup)  ->  FastAPI backend  ->  Hugging Face
  reads video ID from tab      /index, /ask         embeddings + LLM
```

1. The extension gets the video ID from your current YouTube tab.
2. The backend fetches the transcript and splits it into overlapping chunks.
3. Chunks are embedded with `BAAI/bge-base-en-v1.5` and stored in FAISS.
4. For each question, the most relevant chunks are retrieved (MMR) and sent to DeepSeek-V3 with a prompt that restricts answers to the transcript.

## Tech stack

- **LangChain** (chains, retrievers, prompts)
- **FAISS** vector store
- **Hugging Face** embeddings (local) and chat model (Inference API)
- **FastAPI** backend
- **Chrome Extension** (Manifest V3)

## Setup

### 1. Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
pip install torch --index-url https://download.pytorch.org/whl/cpu
copy .env.example .env         # then add your Hugging Face token
python -m uvicorn app:app --port 8000
```

Get a token at https://huggingface.co/settings/tokens (type: Read).
Check http://localhost:8000/health returns `{"ok": true}`.

### 2. Extension

1. Open `chrome://extensions`
2. Turn on **Developer mode**
3. Click **Load unpacked** and select the `extension` folder
4. Open a YouTube video that has captions, click the extension icon, wait for **Ready**, and ask a question

The backend must be running while you use the extension.

## Limitations

- Needs a video with captions (English or Hindi).
- Broad questions such as "summarize the video" work poorly, because retrieval only fetches a few chunks.
- Runs locally only; not packaged for the Chrome Web Store.

## Roadmap

- [ ] Side panel instead of popup
- [ ] Timestamped sources that link to the video
- [ ] Chat memory for follow-up questions
- [ ] Map-reduce summarization
- [ ] Dark mode and formatted answers
