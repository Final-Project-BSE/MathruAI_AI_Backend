"""
File upload and document processing API endpoints.
"""
from flask import Blueprint, request, current_app
from werkzeug.utils import secure_filename
import os
from datetime import datetime
import logging

from chatbot.utils.response_utils import (
    create_success_response, 
    create_error_response, 
    validate_rag_system,
    log_api_request
)
from chatbot.core.app import allowed_file

upload_bp = Blueprint('upload', __name__)
logger = logging.getLogger(__name__)


@upload_bp.route('/upload', methods=['POST'])
def upload_pdf():
    """Upload and process PDF files."""
    log_api_request('/upload', 'POST', request.remote_addr)
    
    is_valid, error_msg = validate_rag_system(current_app.rag_system)
    if not is_valid:
        return create_error_response(error_msg, 503)
        
    if 'file' not in request.files:
        return create_error_response("No file provided", 400)
        
    file = request.files['file']
    if file.filename == '':
        return create_error_response("No file selected", 400)
        
    if not file or not allowed_file(file.filename, current_app):
        return create_error_response("Invalid file format. Only PDF files are allowed.", 400)
        
    try:
        filename = secure_filename(file.filename)
        if not filename:
            return create_error_response("Invalid filename", 400)
            
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        
        # Save file
        file.save(file_path)
        logger.info(f"Uploaded file saved: {filename}")
        
        # Get file size for logging
        file_size = os.path.getsize(file_path)
        logger.info(f"Processing PDF: {filename} ({file_size} bytes)")
        
        start_time = datetime.now()
        
        # Process PDF
        success = current_app.rag_system.update_knowledge_base_from_pdf(file_path)
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        if success:
            # Get updated stats
            stats = current_app.rag_system.get_system_stats()
            
            logger.info(f"Successfully processed PDF: {filename} in {processing_time:.2f}s")
            return create_success_response({
                "filename": filename,
                "file_size_bytes": file_size,
                "processing_time_seconds": round(processing_time, 3),
                "updated_stats": stats
            }, f"Knowledge base updated from PDF: {filename}")
        else:
            return create_error_response("PDF content could not be processed or contained no valid text")
            
    except Exception as e:
        # Clean up file in case of error
        try:
            if 'file_path' in locals() and os.path.exists(file_path):
                os.remove(file_path)
        except:
            pass
            
        logger.error(f"Error processing PDF upload: {str(e)}")
        return create_error_response(f"Failed to process PDF: {str(e)}")


@upload_bp.route('/upload/batch', methods=['POST'])
def upload_batch():
    """
    Upload multiple PDF files for batch processing.
    New endpoint for future batch upload needs.
    """
    log_api_request('/upload/batch', 'POST', request.remote_addr)
    
    is_valid, error_msg = validate_rag_system(current_app.rag_system)
    if not is_valid:
        return create_error_response(error_msg, 503)
    
    if 'files' not in request.files:
        return create_error_response("No files provided", 400)
    
    files = request.files.getlist('files')
    if not files or len(files) == 0:
        return create_error_response("No files selected", 400)
    
    if len(files) > 5:  # Limit batch size
        return create_error_response("Maximum 5 files allowed per batch", 400)
    
    try:
        results = []
        total_processing_time = 0
        successful_uploads = 0
        
        start_time = datetime.now()
        
        for file in files:
            if not file.filename:
                continue
                
            if not allowed_file(file.filename, current_app):
                results.append({
                    "filename": file.filename,
                    "status": "error",
                    "message": "Invalid file format"
                })
                continue
            
            try:
                filename = secure_filename(file.filename)
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                
                # Save file
                file.save(file_path)
                file_size = os.path.getsize(file_path)
                
                # Process PDF
                file_start_time = datetime.now()
                success = current_app.rag_system.update_knowledge_base_from_pdf(file_path)
                file_processing_time = (datetime.now() - file_start_time).total_seconds()
                
                if success:
                    successful_uploads += 1
                    results.append({
                        "filename": filename,
                        "status": "success",
                        "file_size_bytes": file_size,
                        "processing_time_seconds": round(file_processing_time, 3)
                    })
                else:
                    results.append({
                        "filename": filename,
                        "status": "error",
                        "message": "PDF content could not be processed"
                    })
                
            except Exception as file_error:
                results.append({
                    "filename": file.filename,
                    "status": "error",
                    "message": str(file_error)
                })
        
        total_processing_time = (datetime.now() - start_time).total_seconds()
        
        # Get updated stats if any files were processed
        updated_stats = None
        if successful_uploads > 0:
            updated_stats = current_app.rag_system.get_system_stats()
        
        return create_success_response({
            "results": results,
            "total_files": len(files),
            "successful_uploads": successful_uploads,
            "failed_uploads": len(files) - successful_uploads,
            "total_processing_time_seconds": round(total_processing_time, 3),
            "updated_stats": updated_stats
        }, f"Batch upload completed: {successful_uploads}/{len(files)} files processed successfully")
        
    except Exception as e:
        logger.error(f"Error in batch upload: {str(e)}")
        return create_error_response(f"Batch upload failed: {str(e)}")


@upload_bp.route('/upload/status', methods=['GET'])
def upload_status():
    """
    Get upload status and processing capabilities.
    New endpoint for future upload monitoring.
    """
    log_api_request('/upload/status', 'GET', request.remote_addr)
    
    try:
        upload_folder = current_app.config['UPLOAD_FOLDER']
        max_file_size = current_app.config['MAX_CONTENT_LENGTH']
        allowed_extensions = current_app.config['ALLOWED_EXTENSIONS']
        
        # Get upload folder info
        upload_info = {
            "upload_folder_exists": os.path.exists(upload_folder),
            "max_file_size_bytes": max_file_size,
            "max_file_size_mb": round(max_file_size / (1024 * 1024), 2),
            "allowed_extensions": list(allowed_extensions),
            "upload_folder": upload_folder
        }
        
        # Check available disk space (if folder exists)
        if os.path.exists(upload_folder):
            try:
                stat = os.statvfs(upload_folder)
                available_space = stat.f_frsize * stat.f_bavail
                upload_info["available_disk_space_bytes"] = available_space
                upload_info["available_disk_space_mb"] = round(available_space / (1024 * 1024), 2)
            except (OSError, AttributeError):
                # statvfs not available on Windows
                upload_info["available_disk_space"] = "unavailable"
        
        # RAG system readiness
        is_valid, error_msg = validate_rag_system(current_app.rag_system)
        upload_info["rag_system_ready"] = is_valid
        if not is_valid:
            upload_info["rag_system_error"] = error_msg
        
        return create_success_response({
            "upload_capabilities": upload_info,
            "processing_features": [
                "PDF text extraction",
                "Smart text chunking",
                "FAISS vector indexing",
                "Knowledge base integration",
                "Batch processing support"
            ]
        }, "Upload status retrieved successfully")
        
    except Exception as e:
        logger.error(f"Error getting upload status: {str(e)}")
        return create_error_response(f"Failed to get upload status: {str(e)}")


@upload_bp.route('/upload/history', methods=['GET'])
def upload_history():
    """
    Get upload history from database.
    New endpoint for future upload tracking.
    """
    log_api_request('/upload/history', 'GET', request.remote_addr)
    
    is_valid, error_msg = validate_rag_system(current_app.rag_system)
    if not is_valid:
        return create_error_response(error_msg, 503)
    
    if not current_app.rag_system.db_manager or not current_app.rag_system.db_manager.connection:
        return create_error_response("Database not available", 503)
    
    try:
        # Get chunk statistics grouped by source file
        chunk_stats = current_app.rag_system.db_manager.get_chunk_stats()
        
        # This is a basic implementation - can be enhanced with more detailed tracking
        upload_history = {
            "total_documents_processed": chunk_stats.get("unique_sources", 0),
            "total_chunks_created": chunk_stats.get("total_chunks", 0),
            "average_chunk_size": chunk_stats.get("avg_chunk_size", 0),
            "processing_summary": chunk_stats
        }
        
        return create_success_response({
            "upload_history": upload_history,
            "note": "Detailed upload tracking will be enhanced in future versions"
        }, "Upload history retrieved successfully")
        
    except Exception as e:
        logger.error(f"Error getting upload history: {str(e)}")
        return create_error_response(f"Failed to get upload history: {str(e)}")