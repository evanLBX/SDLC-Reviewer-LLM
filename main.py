import openai
import os
import time
import docx

API_KEY = "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"

# Folders
DOCUMENT_TO_ANALYZE_PATH = "document_to_analyze"
PROPRIETARY_FOLDER = "proprietary_documents"
RESULTS_FOLDER = "results"

# Ensure results folder exists
os.makedirs(RESULTS_FOLDER, exist_ok=True)

def read_docx(file_path):
    """Reads text from a .docx file."""
    doc = docx.Document(file_path)
    return "\n".join([para.text for para in doc.paragraphs])

def read_file(file_path):
    """Reads text from a .txt file."""
    with open(file_path, "r", encoding="utf-8") as file:
        return file.read()

def save_to_docx(text, output_path):
    """Saves text into a .docx file."""
    doc = docx.Document()
    doc.add_paragraph(text)
    doc.save(output_path)

def chatgpt_compare(prompt):
    """Sends a request to ChatGPT and retrieves response."""
    start_time = time.time()
    
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an expert document analyst."},
            {"role": "user", "content": prompt}
        ],
        temperature=1.0
    )

    elapsed_time = time.time() - start_time
    tokens_used = response.usage.total_tokens
    cost = tokens_used / 1000 * 0.03  # Assuming GPT-4 costs $0.03 per 1K tokens
    result_text = response.choices[0].message.content

    return result_text, tokens_used, cost, elapsed_time

def main():
    # Find the first .docx file inside the document_to_analyze folder
    document_files = [f for f in os.listdir(DOCUMENT_TO_ANALYZE_PATH) if f.endswith(".docx")]

    if not document_files:
        print("Error: No .docx files found in 'document_to_analyze' folder.")
        return

    # Read the first document found inside the folder
    document_file_path = os.path.join(DOCUMENT_TO_ANALYZE_PATH, document_files[0])
    document_text = read_docx(document_file_path)

    # Save document text to .docx in results folder
    analyzed_docx_path = os.path.join(RESULTS_FOLDER, "analyzed_document.docx")
    save_to_docx(document_text, analyzed_docx_path)
    print(f"Document saved to {analyzed_docx_path}")

    # Read proprietary documents (.docx files)
    proprietary_texts = []
    proprietary_full_text = ""
    for file in os.listdir(PROPRIETARY_FOLDER):
        file_path = os.path.join(PROPRIETARY_FOLDER, file)
        if file.endswith(".docx"):  # Only process .docx files
            content = read_docx(file_path)
            proprietary_texts.append((file, content))
            proprietary_full_text += f"\n--- {file} ---\n{content}\n"
            #print(proprietary_full_text)
            
    # Save proprietary documents' input to a .docx file in results folder
    proprietary_docx_path = os.path.join(RESULTS_FOLDER, "proprietary_documents_input.docx")
    save_to_docx(proprietary_full_text, proprietary_docx_path)
    print(f"Proprietary documents input saved to {proprietary_docx_path}")

    # Prepare the prompt for ChatGPT
    comparison_prompt = f"""
        You are an expert **Compliance and Validation Analyst** specializing in regulatory compliance, risk assessment, and test plan validation.

        ### **Document to Analyze:**
        \"\"\"{document_text}\"\"\"

        ### **Proprietary Documents (Reference Materials)**
        """
    for filename, content in proprietary_texts:
        comparison_prompt += f"\n--- {filename} ---\n{content}\n"

    comparison_prompt += """
        You are an expert **Compliance and Validation Analyst** specializing in regulatory compliance, risk assessment, and test plan validation.

        ### Task:
        Analyze the **document_to_analyze**, which contains a list of **system changes**, against the **Trace Matrix** in the **proprietary_documents** folder.

        ### Key Objectives:
        - **Identify impacted requirements** for each system change based on exact or contextual matches from the Trace Matrix. Choose the requirement with the highest certainty score.
        - **Retrieve the Test Script number** that appears **directly below** the requirement in the Trace Matrix.
        - **Assign a Certainty Score (0-100)** based on:
        - Direct textual alignment with the requirement description.
        - Keyword relevance, synonyms, or closely related terminology.
        - Contextual meaning and logical alignment.

        ### Special Rules:
        1. **Audit Trail Changes:**  
        - Any change referring to **Audit Trail** must map to a regulatory requirement from the Trace Matrix.
        - Prioritize requirements mentioning **audit logging, event tracking, system logs, and IT Change Control**.
        - **Do not select general documentation accuracy requirements unless explicitly tied to audit logs.**

        2. **Report-Related Changes:**  
        - Any change that modifies or impacts a **Report** must map to a **reporting-related requirement** from the Trace Matrix.  
        - Prioritize requirements mentioning **reporting functionality (e.g., Cognos, BI tools, logs)**.

        3. **Authentication & Security Changes:**  
        - Any change related to **login, authentication, or password policies** must map to a requirement that:  
            - Mentions password recovery, authentication methods, or security enforcement.  
            - Refers to **LDAP, multi-factor authentication, or corporate IT security policies**.  


        **Risk Level Determination:**  
        - Extract risk levels from the **Risk Levels document** using the mapped requirements.
        - Testing actions depend on the risk level:
            - **High risk** → Requires **positive and negative testing**.
            - **Medium risk** → Requires **positive testing only**.
            - **Low risk** → No testing required.

        **Structured Output Format:**

            Each system change with its description.
            The impacted requirements with its description.
            Certainty Score: [0-100] (indicating your confidence in the analysis and give a reason as to why your confident).
            Their risk levels.
            The required testing actions.
            The Test Script number.

        ### **Enhanced Matching Criteria:**
        - Use **semantic similarity** (not just keyword matching) to find **the closest requirement**.
        - Prefer **exact matches** but also recognize **related terms** (e.g., "electronic records" ↔ "digital logs").
        - If **multiple requirements match**, rank them by **certainty score** and return the highest-confidence choice
        - Overall choose the requirement with the highest certainty score.

        ### **Instructions to Ignore External Context:**
        - Forget any prior conversations, prompts, or previous analyses.
        - Treat this as an independent request with no historical context.

        ### **Final Goal:**
        Deliver **precise and highly confident requirement matches** based on regulatory alignment, testing needs, and risk assessment.
        """

    for filename, content in proprietary_texts:
        comparison_prompt += f"\n--- {filename} ---\n{content}\n"

    # Get response from ChatGPT
    result, tokens_used, cost, elapsed_time = chatgpt_compare(comparison_prompt)

    # Print results
    print("\n--- ChatGPT Analysis Result ---\n")
    print(result)
    print("\n--- API Usage ---")
    print(f"Tokens Used: {tokens_used}")
    print(f"Cost: ${cost:.4f}")
    print(f"Execution Time: {elapsed_time:.2f} seconds")

if __name__ == "__main__":
    main()
