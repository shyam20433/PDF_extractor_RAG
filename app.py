from flask import Flask, render_template, request, jsonify
import os
from rag_engine import (
    load_pdf,
    create_chunks,
    build_faiss_index,
    save_objects,
    load_objects,
    answer_question
)

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload_pdf():
    pdf = request.files.get("pdf")
    if not pdf:
        return jsonify({"message": "No PDF uploaded"}), 400

    path = os.path.join(UPLOAD_FOLDER, pdf.filename)
    pdf.save(path)

    pages = load_pdf(path)
    create_chunks(pages)
    build_faiss_index()
    save_objects()

    return jsonify({"message": "PDF uploaded successfully"})

@app.route("/ask", methods=["POST"])
def ask():
    question = request.json.get("question")
    if not question:
        return jsonify({"answer": "No question provided"}), 400

    load_objects()
    answer, _ = answer_question(question)

    return jsonify({"answer": answer})

if __name__ == "__main__":
    app.run(debug=True)
