from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import time
import docx
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
import openai
import re

# 🔹 OpenAI API Key (Replace with your actual API key)
# Original LLMApp2 api key
API_KEY = "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"
# LLMApp3 api key
#API_KEY = "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"
openai.api_key = API_KEY

# 🔹 Folders
DOCUMENT_TO_ANALYZE_PATH = "document_to_analyze"
PROPRIETARY_FOLDER = "proprietary_documents"
RESULTS_FOLDER = "results"

# 🔹 Ensure required folders exist
os.makedirs(DOCUMENT_TO_ANALYZE_PATH, exist_ok=True)
os.makedirs(PROPRIETARY_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

# 🔹 Flask App Setup
app = Flask(__name__)
CORS(app)  # Enable CORS for frontend communication

# ✅ Helper function to read a .docx file
def read_docx(file_path):
    """Reads text from a .docx file."""
    doc = docx.Document(file_path)
    return "\n".join([para.text for para in doc.paragraphs])

# ✅ Helper function to save text to a .docx file
def save_to_docx(text, output_path):
    """Saves text into a .docx file."""
    doc = docx.Document()
    doc.add_paragraph(text)
    doc.save(output_path)

def format_ai_output(ai_text, output_path):
    """
    Formats AI response text into a structured .docx file with font sizes based on hash level.
    """
    doc = Document()
    
    lines = ai_text.strip().split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith("# "):  # Largest Title (Bold)
            paragraph = doc.add_paragraph()
            run = paragraph.add_run(line[2:].strip())  # Remove "# "
            run.bold = True
            run.font.size = Pt(22)
            paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.LEFT

        elif line.startswith("## "):  # Medium Title (Bold)
            paragraph = doc.add_paragraph()
            run = paragraph.add_run(line[3:].strip())  # Remove "## "
            run.bold = True
            run.font.size = Pt(16)
            paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.LEFT

        elif line.startswith("### "):  # Small Title (Bold)
            paragraph = doc.add_paragraph()
            run = paragraph.add_run(line[4:].strip())  # Remove "### "
            run.bold = True
            run.font.size = Pt(13)
            paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.LEFT

        else:  # Regular Text (Not Bold)
            paragraph = doc.add_paragraph()
            run = paragraph.add_run(line)
            run.font.size = Pt(11)
            paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.LEFT

    doc.save(output_path)

    # ✅ Function to extract "Operational Testing (OQ) will be performed" to "Purpose and Scope"
def extract_operational_testing_section(text):
    """
    Extracts the relevant operational testing section from the document.
    This function looks for the section starting with "Operational Testing (OQ)" 
    and captures everything until "See section 16 for IQ and OQ test script details."
    """
    match = re.search(r'performed to validate the following Medium and low risk functional requirements:(.*?)Purpose and Scope', text, re.DOTALL)
    if match:
        extracted_text = match.group(1).strip()
        print("✅ Extracted Operational Testing Section:", extracted_text[:600])  # Print preview for debugging
        return extracted_text

    return None  # If no match is found

# ✅ OpenAI ChatGPT Processing Function
def chatgpt_compare(prompt):
    """Sends a request to ChatGPT and retrieves response."""
    try:
        start_time = time.time()

        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert document analyst."},
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )

        elapsed_time = time.time() - start_time
        tokens_used = response['usage']['total_tokens']
        cost = tokens_used / 1000 * 0.03  # Assuming GPT-4o costs $0.03 per 1K tokens
        result_text = response['choices'][0]['message']['content']

        return result_text, tokens_used, cost, elapsed_time

    except Exception as e:
        print(f"❌ ChatGPT API Error: {e}")
        return "AI processing failed.", 0, 0.0, 0.0

# ✅ Route to Upload Document
@app.route("/upload-document", methods=["POST"])
def upload_document():
    """Handles document upload and saves it to the server."""
    if 'file' not in request.files:
        print("❌ No file part in request")
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']

    if file.filename == '':
        print("❌ No selected file")
        return jsonify({"error": "No selected file"}), 400

    # Save the uploaded file
    file_path = os.path.join(DOCUMENT_TO_ANALYZE_PATH, file.filename)
    file.save(file_path)
    print(f"✅ Received file: {file.filename}")

    return jsonify({"message": "File uploaded successfully", "filename": file.filename}), 200

@app.route("/list-proprietary-documents", methods=["GET"])
def list_proprietary_documents():
    """Lists all proprietary documents in the folder."""
    try:
        files = [f for f in os.listdir(PROPRIETARY_FOLDER) if f.endswith(".docx")]
        return jsonify({"documents": files}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/upload-proprietary-document", methods=["POST"])
def upload_proprietary_document():
    """Uploads a new document to the proprietary_documents folder."""
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    file_path = os.path.join(PROPRIETARY_FOLDER, file.filename)
    file.save(file_path)
    print(f"✅ Proprietary file uploaded: {file.filename}")
    return jsonify({"message": "File uploaded successfully", "filename": file.filename}), 200


@app.route("/delete-proprietary-document", methods=["DELETE"])
def delete_proprietary_document():
    """Deletes a selected document from the proprietary_documents folder."""
    data = request.json
    filename = data.get("filename")

    if not filename:
        return jsonify({"error": "Filename is required"}), 400

    file_path = os.path.join(PROPRIETARY_FOLDER, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        print(f"✅ Deleted proprietary file: {filename}")
        return jsonify({"message": "File deleted successfully"}), 200
    else:
        return jsonify({"error": "File not found"}), 404

# ✅ Route to Analyze Document Against Proprietary Documents
@app.route("/analyze", methods=["POST"])
def analyze_document():
    """Finds the uploaded document, compares it against proprietary documents, processes it with ChatGPT, and returns results."""
    try:
        # 1. Load .docx file
        document_files = [f for f in os.listdir(DOCUMENT_TO_ANALYZE_PATH) if f.endswith(".docx")]
        if not document_files:
            error_msg = "❌ Error: No .docx files found in 'document_to_analyze' folder."
            print(error_msg)
            return jsonify({"error": error_msg}), 400

        document_file_path = os.path.join(DOCUMENT_TO_ANALYZE_PATH, document_files[0])
        print(f"✅ Reading document: {document_file_path}")
        
        try:
            document_text = read_docx(document_file_path)
        except Exception as e:
            error_msg = f"❌ Failed to read .docx file: {document_file_path} — {e}"
            print(error_msg)
            return jsonify({"error": error_msg}), 400

        # 2. Extract Operational Testing Section
        try:
            operational_testing_text = extract_operational_testing_section(document_text)
        except Exception as e:
            error_msg = f"❌ Failed to extract 'Operational Testing' section: {e}"
            print(error_msg)
            return jsonify({"error": error_msg}), 400

        if not operational_testing_text:
            error_msg = "❌ Could not find 'Operational Testing' section in document."
            print(error_msg)
            return jsonify({"error": error_msg}), 400

        # 3. Save base document to results folder
        analyzed_docx_path = os.path.join(RESULTS_FOLDER, "analyzed_document.docx")
        save_to_docx(document_text, analyzed_docx_path)
        print(f"✅ Document saved to {analyzed_docx_path} before ChatGPT processing.")

        # 4. Load proprietary docs
        proprietary_texts = []
        proprietary_full_text = ""

        print("✅ Loading proprietary documents:")
        for file in os.listdir(PROPRIETARY_FOLDER):
            if file.endswith(".docx"):
                file_path = os.path.join(PROPRIETARY_FOLDER, file)
                try:
                    content = read_docx(file_path)
                    proprietary_texts.append((file, content))
                    proprietary_full_text += f"\n--- {file} ---\n{content}\n"
                    print(f"   - Loaded: {file}")
                except Exception as e:
                    print(f"⚠️ Skipped {file} due to read error: {e}")

        # 5. Save proprietary input
        proprietary_docx_path = os.path.join(RESULTS_FOLDER, "proprietary_documents_input.docx")
        save_to_docx(proprietary_full_text, proprietary_docx_path)
        print(f"✅ Proprietary documents input saved to {proprietary_docx_path}")

        # 6. Save extracted Operational Testing text
        operational_testing_docx_path = os.path.join(RESULTS_FOLDER, "operational_testing_section.docx")
        save_to_docx(operational_testing_text, operational_testing_docx_path)
        print(f"✅ Operational Testing section saved to {operational_testing_docx_path}")

        # 7. Build prompt
        comparison_prompt = f"""
        You are an expert Compliance and Validation Analyst specializing in regulatory compliance, risk assessment, and test plan validation. 
        Your task is to analyze a regulatory document ("document_to_analyze") against several reference documents located in the "proprietary_documents" folder. 
        Treat this as a new, independent request and forget any prior context.

        Reference documents include:
        - GAMP5 - Validated IT Systems Info
        - Guidance-Computer-Software-Assurance
        - Test Plan Template
        - Trace Matrix v8
        - Risk Levels

----------------------------------------------------------------------------------------------------------------------------------
        {document_text}
        1. Compliance Findings (GAMP5 & CSA Standards)

            Compare the document_to_analyze to the GAMP5 and CSA guidance documents.

            For each compliance issue found:
                - **Issue**: The non-compliant text or policy.
                - **Section**: Where in the document the issue appears (e.g., section title and line reference).
                - **Regulatory Reference**: The specific GAMP5 or CSA principle violated.
                - **Correction**: A recommended fix to ensure compliance with regulatory standards.

            Notes:
                - Focus only on compliance-related gaps — skip document approval sections and IQ/OQ scripts.
                - Only reference GAMP5 or CSA when applicable, and provide precise reasoning.

            Output Format
            Compliance Findings (GAMP5 & CSA Standards)
                Issue: [Description of non-compliance]
                Section: [Section title and line number]
                Regulatory Reference: [CSA or GAMP5 clause]
                Correction: [Recommended fix]
                Structural & Consistency Findings (Test Plan Alignment)
                Issue: [Structural error]
                Location: [Section and line reference]
                Correction: [Fix based on Test Plan Template]

----------------------------------------------------------------------------------------------------------------------------------
        {document_text}
        2. Structural & Consistency Findings (Test Plan Alignment)

            Compare the structure of the document_to_analyze to the Test Plan Template and report any of the following:
            - Misaligned or missing headings
            - Incorrect section ordering
            - Structural inconsistencies

            For each structural issue:
            - **Issue**: Description of what's misaligned or missing.
            - **Location**: Section and line where the issue occurs.
            - **Correction**: Instruction on how to align it with the Test Plan Template.

----------------------------------------------------------------------------------------------------------------------------------
        {document_text}
        3. System Name Consistency Check

            Identify the **official system name** from the **first page** of the document. Then:
            - Scan the entire document for any other names or variants used for the system.
            - Report only names that **do not match** the official system name (exclude similar variations).

            For each inconsistent reference:
            - **Incorrect Name Used**: Exact name used incorrectly.
            - **Sentence**: Full sentence containing the incorrect name.
            - **Correction**: Suggest replacing it with the correct system name.

            Output format
            Official System Name: [Extracted from first page]
                Incorrect Usage:
                    Sentence: “...”
                    Incorrect Name: [Used term]
                    Correction: Replace with: [Correct name]

----------------------------------------------------------------------------------------------------------------------------------
        {operational_testing_text}
        4. System Change & Requirement Validation

            You will receive a block of text called operational_testing_text, which contains multiple system change descriptions. 
            Each system change description is followed by a chosen requirement number for the change.
            For Each System Change:
                Extract the exact system change description from the operational_testing_text block. This becomes your:
                    SystemChangeDescription
                Extract the requirement number listed for that change (if any). This becomes your:
                    DChosenRequirement
                Using the Trace Matrix v8 (located in the proprietary_documents folder), identify all requirements that are potentially impacted by the system change. You must:
                    ✅ Match by direct text similarity to the requirement descriptions.
                    ✅ Consider relevant terminology, keywords, synonyms, or logical meaning that align with the system change.
                    ❌ Do not invent new terms, components, database tables, or rewrite any change description.
                For each matched requirement:
                    Extract its ID and exact description from the Trace Matrix.
                    Assign a Certainty Score from 0 to 100 based on how well it aligns with the system change description.

            Output Format (Repeat for Each Change):
                Change Description: [SystemChangeDescription]  
                Chosen Requirement: [DChosenRequirement]  
                AI Chosen Impacted Requirements:
                    [Requirement ID] — [Description] - Certainty Score: [0-100]
                    [Requirement ID] — [Description] - Certainty Score: [0-100]
                    ...

            You must follow these instructions exactly. 
            Do not generate any extra content, summaries, or inferred conclusions. 
            Do not skip or change any input. 
            Do not refer to anything outside of the provided input.

----------------------------------------------------------------------------------------------------------------------------------
        ✅ Final Notes:
        - Be detailed, but structured and concise.
        - Use bullet points. **Avoid tables**.
        - Ensure compliance issues cite exact violations.
        - Trace Matrix matches must be well-justified.
        - This is a formal validation report for regulatory review — precision is critical.
 """

        for filename, content in proprietary_texts:
            comparison_prompt += f"\n--- {filename} ---\n{content}\n"

        # 8. Call ChatGPT
        try:
            result, tokens_used, cost, elapsed_time = chatgpt_compare(comparison_prompt)
        except Exception as e:
            error_msg = f"❌ Error during AI processing: {e}"
            print(error_msg)
            return jsonify({"error": error_msg}), 500

        # 9. Save AI response
        result_txt_path = os.path.join(RESULTS_FOLDER, "raw_ai_output.txt")
        with open(result_txt_path, "w", encoding="utf-8") as f:
            f.write(result)

        formatted_docx_path = os.path.join(RESULTS_FOLDER, "formatted_analysis.docx")
        format_ai_output(result, formatted_docx_path)

        print("✅ Analysis completed and results saved.")

        return jsonify({
            "result": result.encode('utf-8', 'ignore').decode('utf-8'),
            "tokens_used": tokens_used,
            "cost": cost,
            "elapsed_time": elapsed_time,
            "saved_path": formatted_docx_path
        }), 200

    except Exception as e:
        # Final safety net
        error_msg = f"❌ Unexpected failure: {e}"
        print(error_msg)
        return jsonify({"error": error_msg}), 500


    
@app.route("/download-results", methods=["GET"])
def download_results():
    """Serves the formatted analysis file for download."""
    result_docx_path = os.path.join(RESULTS_FOLDER, "formatted_analysis.docx")  

    if not os.path.exists(result_docx_path):
        print("❌ Error: Results file not found.")
        return jsonify({"error": "Formatted analysis file not found"}), 404

    print(f"✅ Sending file for download: {result_docx_path}")
    return send_file(result_docx_path, as_attachment=True)

# ✅ Run Flask App
if __name__ == "__main__":
    app.run(debug=True)
