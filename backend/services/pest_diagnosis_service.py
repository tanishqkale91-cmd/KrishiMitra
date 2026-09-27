"""
File: pest_diagnosis_service.py
Purpose: Real crop pest & disease photo diagnosis using Gemini Vision Multimodal API.
         Enforces EXIF metadata stripping, Indian regional disease constraints,
         calibrated confidence scoring with visual evidence, and regional relevance flagging.
Inputs:  image_bytes (bytes), crop_hint (str)
Outputs: dict with status ("not_a_plant" | "crop_mismatch" | "valid_diagnosis"), disease_name, confidence_score, visual_evidence, treatment_organic, treatment_chemical, dosage, severity_level, regional_relevance_flag
Usage:   from services.pest_diagnosis_service import diagnose_crop_image
         res = diagnose_crop_image(image_bytes, crop_hint="cotton")
"""

import io
import os
import json
import base64
import logging
from PIL import Image
import requests
from config import Config

logging.basicConfig(level=logging.INFO)

# Regional Indian Crop Disease Reference Catalogs (ICAR / KVK reference advisories)
INDIAN_REGION_CROP_DISEASES = {
    "cotton": [
        "Cotton Bacterial Blight (Xanthomonas citri pv. malvacearum)",
        "Cotton Alternaria Leaf Spot (Alternaria macrospora)",
        "Cotton Grey Mildew / Dahiya Disease (Ramularia areola)",
        "Cotton Leaf Curl Virus (CLCuV)",
        "Cotton Pink Bollworm Leaf/Boll Damage (Pectinophora gossypiella)",
        "Cotton Fusarium Wilt (Fusarium oxysporum f. sp. vasinfectum)",
        "Cotton Leaf Spot (Cercospora / Helminthosporium)",
        "Healthy Cotton Crop"
    ],
    "soybean": [
        "Soybean Rust (Phakopsora pachyrhizi)",
        "Soybean Yellow Mosaic Virus (YMV)",
        "Soybean Charcoal Rot / Root Rot (Macrophomina phaseolina)",
        "Soybean Rhizoctonia Aerial Blight",
        "Soybean Anthracnose (Colletotrichum truncatum)",
        "Healthy Soybean Crop"
    ],
    "wheat": [
        "Wheat Stripe Rust / Yellow Rust (Puccinia striiformis)",
        "Wheat Leaf Rust / Brown Rust (Puccinia triticina)",
        "Wheat Powdery Mildew (Blumeria graminis)",
        "Wheat Loose Smut (Ustilago tritici)",
        "Wheat Karnal Bunt (Tilletia indica)",
        "Healthy Wheat Crop"
    ],
    "onion": [
        "Onion Purple Blotch (Alternaria porri)",
        "Onion Stemphylium Leaf Blight",
        "Onion Downy Mildew (Peronospora destructor)",
        "Onion Basal Rot (Fusarium oxysporum)",
        "Healthy Onion Crop"
    ],
    "tur": [
        "Tur Phytophthora Blight (Phytophthora cajani)",
        "Tur Fusarium Wilt (Fusarium udum)",
        "Tur Sterility Mosaic Disease (SMD)",
        "Healthy Tur Crop"
    ],
    "gram": [
        "Gram Ascochyta Blight (Ascochyta rabiei)",
        "Gram Dry Root Rot (Macrophomina phaseolina)",
        "Gram Pod Borer Damage (Helicoverpa armigera)",
        "Healthy Gram Crop"
    ]
}

def strip_image_metadata(image_bytes):
    """
    Re-encodes image buffer using PIL to completely strip EXIF, camera, GPS, and filename signal.
    Returns clean image bytes and mime type.
    """
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            img = img.convert("RGB")
            clean_buf = io.BytesIO()
            img.save(clean_buf, format="JPEG", quality=90)
            return clean_buf.getvalue(), "image/jpeg"
    except Exception as e:
        logging.warning(f"Metadata stripping fallback: {e}")
        return image_bytes, "image/jpeg"

def diagnose_crop_image(image_bytes, crop_hint="cotton", confidence_threshold=0.45):
    """
    Performs multimodal vision inference using Google's Gemini API on stripped crop image buffer.

    Parameters:
        image_bytes (bytes): Binary data of uploaded image
        crop_hint (str): Declared crop name ('Cotton', 'Soybean', 'Wheat', etc.)
        confidence_threshold (float): Minimum confidence score cutoff (default 0.45)

    Returns:
        dict: Grounded diagnosis details, image validation status, regional flags, and evidence
    """
    api_key = Config.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        logging.error("GEMINI_API_KEY is not set in environment or Config.")
        return {
            "status": "not_a_plant",
            "valid_image": False,
            "message": "GEMINI_API_KEY is missing. Please set GEMINI_API_KEY in .env file to enable live AI vision diagnosis.",
            "disease_name": "API Configuration Error",
            "confidence_score": 0.0,
            "severity_level": "Unknown",
            "treatment_organic": "GEMINI_API_KEY is missing.",
            "treatment_chemical": "N/A",
            "dosage": "N/A",
            "disclaimer": "This is an AI-assisted suggestion, not a certified diagnosis. For severe or uncertain cases, consult your local Krishi Vigyan Kendra."
        }

    crop_name = crop_hint or "Cotton"

    # Step 1: Strip EXIF and re-encode image in-memory
    clean_bytes, mime_type = strip_image_metadata(image_bytes)
    b64_image = base64.b64encode(clean_bytes).decode("utf-8")

    # Step 2: Determine Indian regional reference disease list
    norm_crop_key = "cotton"
    if crop_name:
        cn = crop_name.lower()
        for k in INDIAN_REGION_CROP_DISEASES:
            if k in cn:
                norm_crop_key = k
                break

    common_diseases = INDIAN_REGION_CROP_DISEASES.get(norm_crop_key, INDIAN_REGION_CROP_DISEASES["cotton"])
    common_list_str = "; ".join(common_diseases)

    prompt_text = (
        f"You are an agricultural expert analyzing a photo for crop disease diagnosis in INDIA (specifically Maharashtra / Vidarbha region).\n"
        f'The declared crop selected by the farmer is: "{crop_name}".\n\n'
        f"REGIONAL EPIDEMIOLOGICAL CONSTRAINTS:\n"
        f"Regionally common Indian diseases/conditions for {crop_name} are:\n"
        f"[{common_list_str}]\n"
        f"Prioritize matching symptoms against this Indian regional disease list. Do NOT suggest foreign rare pathogens (such as Phymatotrichopsis omnivora / Cotton Root Rot) unless visual evidence is truly unambiguous and no Indian disease fits.\n\n"
        f"CONFIDENCE CALIBRATION & VISUAL EVIDENCE REQUIREMENTS:\n"
        f"- Do NOT default to a high confidence score (e.g. 90-95%).\n"
        f"- You MUST provide a 'visual_evidence' field describing specific observed symptoms (lesion shape/color, leaf chlorosis, spot margins, image resolution, lighting/blur).\n"
        f"- If the image is ambiguous, low resolution, partially obscured, or symptoms overlap multiple diseases, your confidence score MUST be moderate or low (0.35 to 0.65).\n"
        f"- High confidence (>0.80) is reserved ONLY for clear, sharp photos with distinct diagnostic lesions.\n\n"
        f"Categorize the image into EXACTLY ONE of the following three statuses:\n\n"
        f"1. If the image contains NO plant, leaf, or crop material at all (e.g. graphic poster, person, object, non-agricultural item):\n"
        f'Respond ONLY with this JSON:\n'
        f'{{"status": "not_a_plant", "message": "No plant or crop material detected in this image. Please take a clear photo of the affected leaf or crop part."}}\n\n'
        f'2. If the image DOES show plant/leaf material, but it is clearly a DIFFERENT crop than "{crop_name}" (for example, image shows wheat, rice, corn, or tomato, but declared crop is "{crop_name}"):\n'
        f'Respond ONLY with this JSON:\n'
        f'{{"status": "crop_mismatch", "detected_crop_guess": "<detected crop>", "declared_crop": "{crop_name}", "message": "This looks like <detected crop>, but you selected {crop_name}. Please check your crop selection or re-upload a photo of {crop_name}."}}\n\n'
        f'3. If the image shows a plant/leaf consistent with "{crop_name}":\n'
        f'Respond ONLY with this JSON structure:\n'
        f'{{"status": "valid_diagnosis", "disease_name": "<exact disease name>", "confidence_score": 0.65, "severity": "low/moderate/high", "visual_evidence": "<detailed description of observed visual symptoms, spot colors, lesion borders, leaf yellowing, and image clarity>", "symptoms_observed": "<symptoms description>", "treatment_organic": "<organic remedy>", "treatment_chemical": "<chemical remedy>", "dosage": "<dosage guidance>", "caveat": "<caveat or disclaimer>"}}\n\n'
        f"Return ONLY valid raw JSON with no markdown formatting."
    )

    raw_response_text = ""

    # Strategy 1: Attempt SDK call via google.generativeai if available
    sdk_success = False
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        
        for model_name in ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content([
                    prompt_text,
                    {"mime_type": mime_type, "data": b64_image}
                ])
                raw_response_text = response.text
                if raw_response_text:
                    sdk_success = True
                    break
            except Exception as m_err:
                logging.info(f"Model {model_name} attempt note: {m_err}")
    except Exception as sdk_err:
        logging.info(f"SDK attempt note (falling back to REST API if needed): {sdk_err}")

    # Strategy 2: Direct REST API call if SDK call failed or wasn't used
    if not sdk_success:
        try:
            for m_name in ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{m_name}:generateContent?key={api_key}"
                payload = {
                    "contents": [{
                        "parts": [
                            {"text": prompt_text},
                            {
                                "inline_data": {
                                    "mime_type": mime_type,
                                    "data": b64_image
                                }
                            }
                        ]
                    }],
                    "generationConfig": {
                        "response_mime_type": "application/json"
                    }
                }
                res = requests.post(url, json=payload, timeout=20)
                if res.status_code == 200:
                    res_data = res.json()
                    candidates = res_data.get("candidates", [])
                    if candidates and "content" in candidates[0]:
                        parts = candidates[0]["content"].get("parts", [])
                        if parts:
                            raw_response_text = parts[0].get("text", "")
                            sdk_success = True
                            break
                else:
                    logging.warning(f"Gemini REST endpoint {m_name} returned status {res.status_code}: {res.text}")
        except Exception as rest_err:
            logging.error(f"Gemini REST API call error: {rest_err}")

    logging.info(f"Raw Gemini API response: {raw_response_text}")

    if not raw_response_text:
        return {
            "status": "not_a_plant",
            "valid_image": False,
            "message": "Could not complete AI vision diagnosis. Please check network connection or Gemini API key validity.",
            "disease_name": "Gemini API Connection Error",
            "confidence_score": 0.0,
            "severity_level": "Unknown",
            "treatment_organic": "N/A",
            "treatment_chemical": "N/A",
            "dosage": "N/A",
            "disclaimer": "This is an AI-assisted suggestion, not a certified diagnosis. For severe or uncertain cases, consult your local Krishi Vigyan Kendra."
        }

    # Clean code fences (```json ... ```)
    clean_text = raw_response_text.strip()
    if clean_text.startswith("```"):
        lines = clean_text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        clean_text = "\n".join(lines).strip()

    # Parse JSON
    parsed = {}
    try:
        parsed = json.loads(clean_text)
    except Exception as parse_err:
        logging.error(f"Failed to parse Gemini JSON output: {parse_err}. Text was: {clean_text}")
        return {
            "status": "not_a_plant",
            "valid_image": False,
            "message": "AI vision response could not be parsed as structured JSON. Please retry with a clearer leaf photo.",
            "disease_name": "Diagnosis Parse Error",
            "confidence_score": 0.0,
            "severity_level": "Unknown",
            "treatment_organic": "N/A",
            "treatment_chemical": "N/A",
            "dosage": "N/A",
            "disclaimer": "This is an AI-assisted suggestion, not a certified diagnosis. For severe or uncertain cases, consult your local Krishi Vigyan Kendra."
        }

    status = str(parsed.get("status", "")).strip().lower()

    # Case 1: not_a_plant
    if status == "not_a_plant" or (parsed.get("valid_image") is False and "not" in str(parsed.get("reason", "")).lower()):
        msg = parsed.get("message") or parsed.get("reason") or "No plant or crop material detected in this image. Please take a clear photo of the affected leaf or crop part."
        return {
            "status": "not_a_plant",
            "valid_image": False,
            "message": msg,
            "disease_name": "No Plant Material Detected",
            "confidence_score": 0.0,
            "severity_level": "Invalid",
            "treatment_organic": msg,
            "treatment_chemical": "N/A",
            "dosage": "N/A",
            "disclaimer": "This is an AI-assisted suggestion, not a certified diagnosis. For severe or uncertain cases, consult your local Krishi Vigyan Kendra."
        }

    # Case 2: crop_mismatch
    if status == "crop_mismatch" or (parsed.get("detected_crop_guess") and str(parsed.get("detected_crop_guess")).lower() not in crop_name.lower()):
        detected_guess = parsed.get("detected_crop_guess") or "a different crop"
        msg = parsed.get("message") or f"This looks like {detected_guess}, but you selected {crop_name}. Please check your crop selection and try again, or re-upload a photo of your {crop_name} crop."
        return {
            "status": "crop_mismatch",
            "valid_image": False,
            "detected_crop_guess": detected_guess,
            "declared_crop": crop_name,
            "message": msg,
            "disease_name": f"Crop Mismatch ({detected_guess})",
            "confidence_score": 0.0,
            "severity_level": "Mismatch",
            "treatment_organic": msg,
            "treatment_chemical": "N/A",
            "dosage": "N/A",
            "disclaimer": "This is an AI-assisted suggestion, not a certified diagnosis. For severe or uncertain cases, consult your local Krishi Vigyan Kendra."
        }

    # Case 3: valid_diagnosis
    conf_score = float(parsed.get("confidence_score", 0.65) or 0.65)
    disease_name_returned = str(parsed.get("disease_name", "Crop Condition Detected")).strip()

    if conf_score < confidence_threshold:
        return {
            "status": "not_a_plant",
            "valid_image": False,
            "message": "Low confidence in leaf photo analysis. Please retake photo in good lighting with the leaf filling the frame.",
            "disease_name": "Low Confidence Analysis",
            "confidence_score": conf_score,
            "severity_level": "Uncertain",
            "treatment_organic": "Please retake photo in good lighting with the leaf filling the frame.",
            "treatment_chemical": "N/A",
            "dosage": "N/A",
            "disclaimer": "This is an AI-assisted suggestion, not a certified diagnosis. For severe or uncertain cases, consult your local Krishi Vigyan Kendra."
        }

    # Check if returned disease is in Indian regional common list
    is_regionally_common = False
    for cd in common_diseases:
        cd_core = cd.split("(")[0].strip().lower()
        if cd_core in disease_name_returned.lower() or disease_name_returned.lower() in cd_core:
            is_regionally_common = True
            break

    regional_relevance_flag = False
    if "healthy" not in disease_name_returned.lower() and not is_regionally_common:
        regional_relevance_flag = True

    visual_evidence = str(parsed.get("visual_evidence", "") or parsed.get("symptoms_observed", "")).strip()

    return {
        "status": "valid_diagnosis",
        "valid_image": True,
        "disease_name": disease_name_returned,
        "confidence_score": round(conf_score, 2),
        "severity_level": str(parsed.get("severity", "Moderate")).strip().capitalize(),
        "visual_evidence": visual_evidence,
        "symptoms_observed": str(parsed.get("symptoms_observed", "")).strip(),
        "treatment_organic": str(parsed.get("treatment_organic", "Apply organic biopesticide or neem solution.")).strip(),
        "treatment_chemical": str(parsed.get("treatment_chemical", "Consult local extension officer for chemical fungicide formulation.")).strip(),
        "dosage": str(parsed.get("dosage", "Follow product label instructions.")).strip(),
        "caveat": str(parsed.get("caveat", "")).strip(),
        "regional_relevance_flag": regional_relevance_flag,
        "disclaimer": "This is an AI-assisted suggestion, not a certified diagnosis. For severe or uncertain cases, consult your local Krishi Vigyan Kendra."
    }
