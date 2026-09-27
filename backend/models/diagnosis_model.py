"""
File: diagnosis_model.py
Purpose: Data access and management for crop pest/disease diagnosis logs.
Inputs:  farmer_location, crop, image_path, disease_detected, confidence
Outputs: Diagnosis record dictionary or list of history records
Usage:   from models.diagnosis_model import DiagnosisModel
         rec = DiagnosisModel.create(...)
         history = DiagnosisModel.get_recent()
"""

from database.db_connection import query_db, execute_db

class DiagnosisModel:
    """Diagnosis History Data Access Model"""

    @staticmethod
    def create(farmer_location, crop, image_path, disease_detected, confidence):
        """Creates a new diagnosis log record."""
        sql = """
        INSERT INTO diagnosis_history (
            farmer_location, crop, image_path, disease_detected, confidence
        ) VALUES (?, ?, ?, ?, ?);
        """
        diag_id = execute_db(
            sql,
            (farmer_location or "Unknown Location", crop or "Unknown Crop", image_path or "", disease_detected, float(confidence))
        )
        return DiagnosisModel.get_by_id(diag_id)

    @staticmethod
    def get_by_id(diagnosis_id):
        """Retrieve a diagnosis record by ID."""
        sql = "SELECT * FROM diagnosis_history WHERE id = ?;"
        rows = query_db(sql, (diagnosis_id,))
        return rows[0] if rows else None

    @staticmethod
    def get_recent(limit=20):
        """Retrieve recent diagnosis history logs."""
        sql = "SELECT * FROM diagnosis_history ORDER BY timestamp DESC LIMIT ?;"
        return query_db(sql, (limit,))
