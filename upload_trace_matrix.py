import os
import re
import docx
from openai import OpenAI
from pinecone import Pinecone, ServerlessSpec

# === Environment Setup ===
PINECONE_API_KEY = os.getenv("pcsk_4ZtuSM_TTtxev4rxpTPGcVcfu2FNrwerLxJHUyG3WCgzgSSHtG7kXyADsr6xZ3fNX6pRKG")
PINECONE_ENV = "us-east-1"
INDEX_NAME = "sdlc-rag-index"
TRACE_MATRIX_PATH = "proprietary_documents/Trace Matrix v8.docx"

# === Initialize OpenAI + Pinecone Clients ===
client = OpenAI()
pc = Pinecone(api_key=PINECONE_API_KEY)

# === Access Pinecone Index ===
index = pc.Index(INDEX_NAME)

# === Step 1: Parse Requirements from Trace Matrix ===
def extract_requirements(file_path):
    doc = docx.Document(file_path)
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    
    requirements = []
    seen_ids = set()
    i = 0

    while i < len(paragraphs):
        line = paragraphs[i]

        # Match types like BR 1.4, FR 6.1.1, UR-REG-35, FS-REG-35
        match = re.match(r"^(BR|FR|UR\-REG|FS\-REG)[\s\-]+([\d\.]+)$", line)
        if match:
            prefix = match.group(1)
            number = match.group(2)
            req_id = f"{prefix} {number}" if " " in prefix else f"{prefix}-{number}"

            if req_id in seen_ids:
                i += 1
                continue

            i += 1
            description_lines = []

            while i < len(paragraphs):
                next_line = paragraphs[i]

                # If the next line is another requirement ID, stop here
                if re.match(r"^(BR|FR|UR\-REG|FS\-REG)[\s\-]+[\d\.]+$", next_line):
                    break

                if not next_line.lower().startswith("test script"):
                    description_lines.append(next_line)
                i += 1

            full_description = " ".join(description_lines).strip()
            if full_description:
                requirements.append((req_id, full_description))
                seen_ids.add(req_id)
        else:
            i += 1

    return requirements

# === Step 2: Embed Text Using OpenAI ===
def get_embedding(text):
    try:
        response = client.embeddings.create(
            model="text-embedding-ada-002",
            input=[text]
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"❌ Embedding failed: {e}")
        return None

# === Step 3: Upload Embeddings to Pinecone ===
def upload_to_pinecone(requirements, batch_size=50):
    vectors = []
    for i, (req_id, text) in enumerate(requirements):
        embedding = get_embedding(text)
        if embedding:
            vectors.append({
                "id": f"req_{i}",
                "values": embedding,
                "metadata": {
                    "requirement_id": req_id,
                    "text": text
                }
            })
            print(f"✅ Embedded {req_id}")
        else:
            print(f"⚠️ Skipped {req_id} due to embedding error")

    # 🔁 Upload in small batches
    for i in range(0, len(vectors), batch_size):
        batch = vectors[i:i + batch_size]
        try:
            index.upsert(vectors=batch)
            print(f"📦 Uploaded batch {i // batch_size + 1} ({len(batch)} vectors)")
        except Exception as e:
            print(f"❌ Error uploading batch {i // batch_size + 1}: {e}")


# === Main ===
if __name__ == "__main__":
    print("🚀 Starting upload script")
    if not os.path.exists(TRACE_MATRIX_PATH):
        print(f"❌ Trace Matrix not found at: {TRACE_MATRIX_PATH}")
        exit(1)

    requirements = extract_requirements(TRACE_MATRIX_PATH)
    print(f"📄 Found {len(requirements)} requirements")

    if requirements:
        upload_to_pinecone(requirements)
    else:
        print("❌ No requirements parsed. Check your document format.")
