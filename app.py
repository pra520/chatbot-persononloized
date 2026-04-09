"""
PersonaBot - Production-Grade AI Chatbot Backend
Flask API Server with OpenRouter Integration
"""

import os
import json
import time
import logging
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

from services.file_processor import FileProcessor
from services.ai_engine import AIEngine
from services.memory_manager import MemoryManager
from services.context_store import ContextStore

# ─── Setup ──────────────────────────────────────────────────────────────────
load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder="../frontend", static_url_path="")
CORS(app, origins="*")

# ─── Config ─────────────────────────────────────────────────────────────────
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
ALLOWED_EXTENSIONS = {"pdf", "csv", "txt", "xlsx"}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

# ─── Service Singletons ──────────────────────────────────────────────────────
file_processor = FileProcessor()
ai_engine = AIEngine(api_key=os.getenv("OPENROUTER_API_KEY", ""))
memory_manager = MemoryManager(max_turns=8)
context_store = ContextStore()


# ─── Helpers ────────────────────────────────────────────────────────────────
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_session_id(req):
    return req.headers.get("X-Session-ID", "default-session")


# ─── Routes ─────────────────────────────────────────────────────────────────

@app.route("/")
def serve_frontend():
    """Serve the frontend SPA"""
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/health", methods=["GET"])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "online",
        "version": "2.0.0",
        "product": "PersonaBot",
        "timestamp": int(time.time())
    })


@app.route("/api/config", methods=["GET"])
def get_config():
    """Return public chatbot configuration"""
    return jsonify({
        "bot_name": os.getenv("BOT_NAME", "PersonaBot"),
        "bot_tagline": os.getenv("BOT_TAGLINE", "Your Intelligent Business Assistant"),
        "bot_avatar": os.getenv("BOT_AVATAR", "🤖"),
        "primary_color": os.getenv("PRIMARY_COLOR", "#6C63FF"),
        "welcome_message": os.getenv("WELCOME_MESSAGE",
            "Hello! I'm your AI assistant. Upload your documents and ask me anything!"),
        "max_file_size_mb": 16,
        "supported_formats": list(ALLOWED_EXTENSIONS)
    })


@app.route("/api/upload", methods=["POST"])
def upload_file():
    """
    File Upload Endpoint
    Accepts: PDF, CSV, TXT, XLSX
    Process: Extract text → Chunk → Store in context
    """
    session_id = get_session_id(request)

    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    if not allowed_file(file.filename):
        return jsonify({
            "error": f"File type not supported. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        }), 400

    filename = secure_filename(file.filename)
    save_path = os.path.join(app.config["UPLOAD_FOLDER"], f"{session_id}_{filename}")
    file.save(save_path)

    try:
        # Extract and process file content
        extracted_text = file_processor.process(save_path)
        chunks = file_processor.chunk_text(extracted_text, chunk_size=500, overlap=50)
        combined_context = file_processor.build_context_string(chunks, filename)

        # Store in session context
        context_store.add_document(session_id, filename, combined_context)

        logger.info(f"[{session_id}] Uploaded: {filename} | Chunks: {len(chunks)}")

        return jsonify({
            "success": True,
            "filename": filename,
            "chunks": len(chunks),
            "characters": len(extracted_text),
            "preview": extracted_text[:300] + "..." if len(extracted_text) > 300 else extracted_text,
            "message": f"✅ '{filename}' processed successfully! You can now ask questions about it."
        })

    except Exception as e:
        logger.error(f"[{session_id}] Upload error: {str(e)}")
        return jsonify({"error": f"Processing failed: {str(e)}"}), 500

    finally:
        # Clean up temp file
        if os.path.exists(save_path):
            os.remove(save_path)


@app.route("/api/chat", methods=["POST"])
def chat():
    """
    Main Chat Endpoint
    Flow: Receive message → Load context → Build prompt → Call AI → Return response
    """
    session_id = get_session_id(request)
    data = request.get_json()

    if not data or "message" not in data:
        return jsonify({"error": "Message is required"}), 400

    user_message = data.get("message", "").strip()
    if not user_message:
        return jsonify({"error": "Empty message"}), 400

    if len(user_message) > 2000:
        return jsonify({"error": "Message too long (max 2000 chars)"}), 400

    try:
        # Fetch session context and memory
        context = context_store.get_context(session_id)
        history = memory_manager.get_history(session_id)
        bot_role = data.get("bot_role", os.getenv("BOT_ROLE", "professional business assistant"))
        business_name = data.get("business_name", os.getenv("BUSINESS_NAME", "our company"))

        # Call AI engine
        response_text = ai_engine.generate_response(
            user_message=user_message,
            context=context,
            history=history,
            bot_role=bot_role,
            business_name=business_name
        )

        # Update memory
        memory_manager.add_turn(session_id, user_message, response_text)

        logger.info(f"[{session_id}] Chat: '{user_message[:50]}...' → {len(response_text)} chars")

        return jsonify({
            "success": True,
            "response": response_text,
            "session_id": session_id,
            "has_context": bool(context),
            "memory_turns": len(history)
        })

    except Exception as e:
        logger.error(f"[{session_id}] Chat error: {str(e)}")
        return jsonify({
            "error": "AI service error. Please try again.",
            "details": str(e)
        }), 500


@app.route("/api/reset", methods=["POST"])
def reset_session():
    """Clear session memory and context"""
    session_id = get_session_id(request)
    memory_manager.clear_session(session_id)
    context_store.clear_session(session_id)
    return jsonify({"success": True, "message": "Session cleared successfully"})


@app.route("/api/documents", methods=["GET"])
def list_documents():
    """List uploaded documents for a session"""
    session_id = get_session_id(request)
    docs = context_store.list_documents(session_id)
    return jsonify({"documents": docs, "count": len(docs)})


@app.route("/api/documents/<doc_name>", methods=["DELETE"])
def delete_document(doc_name):
    """Remove a specific document from session context"""
    session_id = get_session_id(request)
    success = context_store.remove_document(session_id, doc_name)
    if success:
        return jsonify({"success": True, "message": f"'{doc_name}' removed"})
    return jsonify({"error": "Document not found"}), 404


# ─── Error Handlers ──────────────────────────────────────────────────────────
@app.errorhandler(413)
def file_too_large(e):
    return jsonify({"error": "File too large. Maximum size is 16MB"}), 413


@app.errorhandler(404)
def not_found(e):
    return send_from_directory(app.static_folder, "index.html")


@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Internal server error"}), 500


# ─── Run ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "true").lower() == "true"
    logger.info(f"🚀 PersonaBot starting on port {port}")
    app.run(host="0.0.0.0", port=port, debug=debug)
