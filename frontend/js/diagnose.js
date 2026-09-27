/**
 * File: diagnose.js
 * Purpose: Frontend interactions for Crop Pest & Disease Photo Diagnosis screen.
 * Handles camera/file upload preview, API submit to /api/diagnose-crop,
 * result rendering, and voice audio playback.
 */

document.addEventListener("DOMContentLoaded", () => {
  const diagnoseForm = document.getElementById("diagnoseForm");
  const imageInput = document.getElementById("imageInput");
  const imagePreviewContainer = document.getElementById("imagePreviewContainer");
  const imagePreview = document.getElementById("imagePreview");
  const uploadPlaceholder = document.getElementById("uploadPlaceholder");
  const submitBtn = document.getElementById("submitBtn");
  const diagnosisLoading = document.getElementById("diagnosisLoading");
  const diagnosisResult = document.getElementById("diagnosisResult");
  const listenBtn = document.getElementById("listenBtn");

  const cropSelect = document.getElementById("cropSelect");
  const diseaseTitle = document.getElementById("diseaseTitle");
  const severityBadge = document.getElementById("severityBadge");
  const confidenceVal = document.getElementById("confidenceVal");
  const organicTreatment = document.getElementById("organicTreatment");
  const chemicalTreatment = document.getElementById("chemicalTreatment");
  const dosageVal = document.getElementById("dosageVal");

  let currentAudioBase64 = null;
  let audioPlayer = null;
  let activeLanguage = localStorage.getItem("krishi_lang") || "en";

  // Initialize Language Switcher Pills
  const langBtns = document.querySelectorAll(".lang-btn");
  langBtns.forEach(btn => {
    if (btn.dataset.lang === activeLanguage) {
      langBtns.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
    }
    btn.addEventListener("click", (e) => {
      langBtns.forEach(b => b.classList.remove("active"));
      e.target.classList.add("active");
      activeLanguage = e.target.dataset.lang;
      localStorage.setItem("krishi_lang", activeLanguage);
    });
  });

  // Image Upload Preview
  imageInput.addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (event) => {
        imagePreview.src = event.target.result;
        uploadPlaceholder.style.display = "none";
        imagePreviewContainer.style.display = "block";
      };
      reader.readAsDataURL(file);
    }
  });

  // Drag and drop handlers
  const dropArea = document.getElementById("dropArea");
  if (dropArea) {
    ["dragenter", "dragover"].forEach(eventName => {
      dropArea.addEventListener(eventName, (e) => {
        e.preventDefault();
        dropArea.style.borderColor = "var(--primary)";
        dropArea.style.background = "var(--primary-bg)";
      }, false);
    });
    ["dragleave", "drop"].forEach(eventName => {
      dropArea.addEventListener(eventName, (e) => {
        e.preventDefault();
        dropArea.style.borderColor = "var(--border-color)";
        dropArea.style.background = "#fafafa";
      }, false);
    });
    dropArea.addEventListener("drop", (e) => {
      const dt = e.dataTransfer;
      const files = dt.files;
      if (files && files.length > 0) {
        imageInput.files = files;
        const event = new Event("change");
        imageInput.dispatchEvent(event);
      }
    });
  }

  // Handle Form Submission
  diagnoseForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!imageInput.files || imageInput.files.length === 0) {
      alert("Please upload or take a photo of the crop leaf.");
      return;
    }

    const file = imageInput.files[0];
    const cropValue = cropSelect.value;

    const formData = new FormData();
    formData.append("image", file);
    formData.append("crop", cropValue);
    formData.append("language", activeLanguage);
    formData.append("location", "Local Farm");

    // UI Loading State
    submitBtn.disabled = true;
    submitBtn.textContent = "⏳ Analyzing Photo...";
    diagnosisLoading.style.display = "block";
    diagnosisResult.style.display = "none";

    try {
      const res = await fetch("/api/diagnose-crop", {
        method: "POST",
        body: formData
      });

      const data = await res.json();
      diagnosisLoading.style.display = "none";
      submitBtn.disabled = false;
      submitBtn.textContent = "🔍 Diagnose Crop Disease";

      const notAPlantCard = document.getElementById("notAPlantCard");
      const notAPlantMsg = document.getElementById("notAPlantMsg");
      const cropMismatchCard = document.getElementById("cropMismatchCard");
      const cropMismatchMsg = document.getElementById("cropMismatchMsg");

      if (notAPlantCard) notAPlantCard.style.display = "none";
      if (cropMismatchCard) cropMismatchCard.style.display = "none";
      if (diagnosisResult) diagnosisResult.style.display = "none";

      if (data.status === "success" && data.diagnosis) {
        const diag = data.diagnosis;
        const status = diag.status || (diag.valid_image ? "valid_diagnosis" : "not_a_plant");

        if (status === "not_a_plant") {
          if (notAPlantMsg) notAPlantMsg.textContent = diag.message || "No plant or crop material detected in this image. Please take a clear photo of the affected leaf or crop part.";
          if (notAPlantCard) {
            notAPlantCard.style.display = "block";
            notAPlantCard.scrollIntoView({ behavior: "smooth" });
          }
        } else if (status === "crop_mismatch") {
          if (cropMismatchMsg) cropMismatchMsg.textContent = diag.message || `This image shows a different crop than selected. Please check your crop selection or re-upload a photo of your crop.`;
          if (cropMismatchCard) {
            cropMismatchCard.style.display = "block";
            cropMismatchCard.scrollIntoView({ behavior: "smooth" });
          }
        } else {
          // valid_diagnosis
          diseaseTitle.textContent = diag.disease_name;
          confidenceVal.textContent = Math.round(diag.confidence_score * 100) + "%";
          organicTreatment.textContent = diag.treatment_organic;
          chemicalTreatment.textContent = diag.treatment_chemical;
          dosageVal.textContent = diag.dosage || "N/A";

          // Visual Evidence
          const visualEvidenceText = document.getElementById("visualEvidenceText");
          if (visualEvidenceText) {
            visualEvidenceText.textContent = diag.visual_evidence || diag.symptoms_observed || "Visual symptoms analyzed against Indian regional crop reference database.";
          }

          // Regional Relevance Warning Banner
          const regionalWarningBanner = document.getElementById("regionalWarningBanner");
          if (regionalWarningBanner) {
            if (diag.regional_relevance_flag === true) {
              regionalWarningBanner.style.display = "block";
            } else {
              regionalWarningBanner.style.display = "none";
            }
          }

          // Severity Color Code
          const sev = (diag.severity_level || "Medium").toLowerCase();
          if (sev === "critical" || sev === "high") {
            severityBadge.style.background = "var(--danger-bg)";
            severityBadge.style.color = "var(--danger)";
            severityBadge.textContent = "⚠️ " + diag.severity_level + " Severity";
          } else if (sev === "none") {
            severityBadge.style.background = "var(--primary-subtle)";
            severityBadge.style.color = "var(--primary-dark)";
            severityBadge.textContent = "✅ Healthy Crop";
          } else {
            severityBadge.style.background = "var(--accent-gold-bg)";
            severityBadge.style.color = "var(--accent-gold)";
            severityBadge.textContent = "⚡ " + diag.severity_level + " Severity";
          }

          if (diagnosisResult) {
            diagnosisResult.style.display = "block";
            diagnosisResult.scrollIntoView({ behavior: "smooth" });
          }
        }

        // Store Audio Base64
        if (data.audio && data.audio.audio_base64) {
          currentAudioBase64 = data.audio.audio_base64;
          playAudio(currentAudioBase64);
        } else {
          currentAudioBase64 = null;
        }
      } else {
        alert(data.message || "Failed to analyze crop photo.");
      }
    } catch (err) {
      console.error("Diagnosis error:", err);
      diagnosisLoading.style.display = "none";
      submitBtn.disabled = false;
      submitBtn.textContent = "🔍 Diagnose Crop Disease";
      alert("Error connecting to server. Please try again.");
    }
  });

  // Audio Playback Handler
  function playAudio(base64Data) {
    if (!base64Data) return;
    try {
      if (audioPlayer) {
        audioPlayer.pause();
      }
      audioPlayer = new Audio("data:audio/mp3;base64," + base64Data);
      audioPlayer.play().catch(e => console.log("Audio autoplay prevented:", e));
    } catch (e) {
      console.error("Audio playback error:", e);
    }
  }

  listenBtn.addEventListener("click", () => {
    if (currentAudioBase64) {
      playAudio(currentAudioBase64);
    } else {
      alert("Voice speech audio not available.");
    }
  });
});
