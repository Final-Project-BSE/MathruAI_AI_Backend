import logging
import os
from datetime import datetime

from flask import Blueprint, current_app, request
from werkzeug.utils import secure_filename

from chatbot.utils.file_utils import is_allowed_file
from chatbot.utils.response_utils import (
    create_error_response,
    create_success_response,
    log_api_request,
    validate_rag_system,
)

upload_bp = Blueprint("upload", __name__)
logger = logging.getLogger(__name__)
MAX_BATCH_FILES = 5


def _save_upload(file_storage):
    filename = secure_filename(file_storage.filename or "")
    if not filename:
        raise ValueError("Invalid filename")

    file_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
    file_storage.save(file_path)
    return filename, file_path, os.path.getsize(file_path)



def _cleanup_file(file_path: str | None) -> None:
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
    except OSError:
        logger.warning("Failed to clean up temporary file: %s", file_path)


@upload_bp.route("/upload", methods=["POST"])
def upload_pdf():
    log_api_request("/upload", "POST", request.remote_addr)

    is_valid, error_msg = validate_rag_system(current_app.rag_system)
    if not is_valid:
        return create_error_response(error_msg, 503)

    if "file" not in request.files:
        return create_error_response("No file provided", 400)

    file = request.files["file"]
    if file.filename == "":
        return create_error_response("No file selected", 400)

    if not is_allowed_file(file.filename, current_app.config.get("ALLOWED_EXTENSIONS", set())):
        return create_error_response("Invalid file format. Only PDF files are allowed.", 400)

    file_path = None
    try:
        filename, file_path, file_size = _save_upload(file)
        start_time = datetime.now()
        success = current_app.rag_system.update_knowledge_base_from_pdf(file_path)
        processing_time = (datetime.now() - start_time).total_seconds()

        if not success:
            return create_error_response("PDF content could not be processed or contained no valid text")

        stats = current_app.rag_system.get_system_stats()
        return create_success_response(
            {
                "filename": filename,
                "file_size_bytes": file_size,
                "processing_time_seconds": round(processing_time, 3),
                "updated_stats": stats,
            },
            f"Knowledge base updated from PDF: {filename}",
        )
    except Exception as exc:
        _cleanup_file(file_path)
        logger.exception("Error processing PDF upload: %s", exc)
        return create_error_response(f"Failed to process PDF: {exc}")


@upload_bp.route("/upload/batch", methods=["POST"])
def upload_batch():
    log_api_request("/upload/batch", "POST", request.remote_addr)

    is_valid, error_msg = validate_rag_system(current_app.rag_system)
    if not is_valid:
        return create_error_response(error_msg, 503)

    if "files" not in request.files:
        return create_error_response("No files provided", 400)

    files = request.files.getlist("files")
    if not files:
        return create_error_response("No files selected", 400)
    if len(files) > MAX_BATCH_FILES:
        return create_error_response(f"Maximum {MAX_BATCH_FILES} files allowed per batch", 400)

    results = []
    successful_uploads = 0
    start_time = datetime.now()

    try:
        for file in files:
            if not file.filename:
                continue

            if not is_allowed_file(file.filename, current_app.config.get("ALLOWED_EXTENSIONS", set())):
                results.append({"filename": file.filename, "status": "error", "message": "Invalid file format"})
                continue

            file_path = None
            try:
                filename, file_path, file_size = _save_upload(file)
                file_start_time = datetime.now()
                success = current_app.rag_system.update_knowledge_base_from_pdf(file_path)
                processing_time = (datetime.now() - file_start_time).total_seconds()

                if success:
                    successful_uploads += 1
                    results.append(
                        {
                            "filename": filename,
                            "status": "success",
                            "file_size_bytes": file_size,
                            "processing_time_seconds": round(processing_time, 3),
                        }
                    )
                else:
                    results.append(
                        {"filename": filename, "status": "error", "message": "PDF content could not be processed"}
                    )
            except Exception as file_error:
                _cleanup_file(file_path)
                results.append({"filename": file.filename, "status": "error", "message": str(file_error)})

        total_processing_time = (datetime.now() - start_time).total_seconds()
        updated_stats = current_app.rag_system.get_system_stats() if successful_uploads > 0 else None

        return create_success_response(
            {
                "results": results,
                "total_files": len(files),
                "successful_uploads": successful_uploads,
                "failed_uploads": len(files) - successful_uploads,
                "total_processing_time_seconds": round(total_processing_time, 3),
                "updated_stats": updated_stats,
            },
            f"Batch upload completed: {successful_uploads}/{len(files)} files processed successfully",
        )
    except Exception as exc:
        logger.exception("Error in batch upload: %s", exc)
        return create_error_response(f"Batch upload failed: {exc}")


@upload_bp.route("/upload/history", methods=["GET"])
def upload_history():
    log_api_request("/upload/history", "GET", request.remote_addr)

    is_valid, error_msg = validate_rag_system(current_app.rag_system)
    if not is_valid:
        return create_error_response(error_msg, 503)

    if not current_app.rag_system.db_manager or not current_app.rag_system.db_manager.connection:
        return create_error_response("Database not available", 503)

    try:
        chunk_stats = current_app.rag_system.get_system_stats()
        upload_history = {
            "total_documents_processed": chunk_stats.get("unique_sources", 0),
            "total_chunks_created": chunk_stats.get("total_chunks", 0),
            "average_chunk_size": chunk_stats.get("avg_chunk_size", 0),
            "processing_summary": chunk_stats,
        }
        return create_success_response(
            {
                "upload_history": upload_history,
                "note": "Detailed upload tracking will be enhanced in future versions",
            },
            "Upload history retrieved successfully",
        )
    except Exception as exc:
        logger.exception("Error getting upload history: %s", exc)
        return create_error_response(f"Failed to get upload history: {exc}")
