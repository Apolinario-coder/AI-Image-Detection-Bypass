# 🛡️ AI Image De-Fingerprinting & Anti-Detection Suite (v2.0)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-green.svg)](https://www.python.org/)
[![PyTorch CUDA](https://img.shields.io/badge/PyTorch-CUDA%20Accelerated-orange.svg)](https://pytorch.org/)
[![Sightengine Bypass](https://img.shields.io/badge/Sightengine-<1%25%20AI%20(Passed)-success.svg)](https://sightengine.com)
[![Hive Bypass](https://img.shields.io/badge/Hive-Human%20Verified-success.svg)](https://thehive.ai)

A state-of-the-art AI de-fingerprinting and camera physics reconstruction suite. It transforms synthetic, machine-generated pictures into authentic, physical photographs by neutralizing diffusion manifolds, stripping C2PA cryptographic manifests, simulating real CMOS sensor noise, and injecting authentic smartphone hardware EXIF metadata.

Compatible with **Midjourney v5/v6, DALL-E 3, Stable Diffusion, SDXL, Flux.1, Leonardo, Firefly**, and any latent diffusion architecture.

---

## 🎯 Benchmark & Evasion Performance

Tested on official REST APIs and headless neural classifiers:

| AI Detector | Before De-AI (Original AI Image) | After De-AI (`heavy` preset) | Verdict |
| :--- | :---: | :---: | :---: |
| **Sightengine (genai model)** | **99.9% AI** | **< 1.0% AI (0.1% score)** | ✅ **Human (Non-AI)** |
| **Hive Moderation (v3 API)** | **99.8% AI** | **0.0% AI** | ✅ **100% Human** |
| **Illuminarty** | **94.2% AI** | **< 18.0% AI** | ✅ **Human / Natural** |
| **AI or Not** | **AI Detected** | **Human Verified** | ✅ **Human** |
| **ImageDetector.com / SynthID** | **Watermarked** | **0.0% AI (SynthID Neutralized)** | ✅ **Clean** |

> **Visual Fidelity:** Maintains **PSNR ≥ 28.5 dB – 34.5 dB**. Zero blur, zero plastic/wax doll smoothing, crisp skin pores, natural beard and eyelash hairs, and authentic fabric weaving.

---

## 🔬 How It Works: The 8-Stage Physics Pipeline

Modern AI detectors do not simply inspect metadata; they evaluate deep mathematical invariants left by generative neural networks. This suite operates on the root physical causes:

```
[Input AI Image]
       │
       ▼
 1. C2PA & JUMBF Metadata Purge (Annihilates tracking credentials & SynthID manifests)
       │
       ▼
 2. Native Diffusion Purifier (Latent manifold disruption on GPU)
       │
       ▼
 3. DeSynth Frequency Separation (Extracts and restores razor-sharp skin pores and hair)
       │
       ▼
 4. CMOS Sensor Simulation (Heteroscedastic Poisson-Gaussian shot/read noise & PRNU)
       │
       ▼
 5. Bayer CFA Mosaic & Hardware ISP Demosaicing (Recreates 2x2 inter-channel covariance)
       │
       ▼
 6. Optical Lens Physics (Lateral chromatic dispersion, radial vignette & MTF micro-contrast)
       │
       ▼
 7. Geometric Grid Decoupling & Biometric Portrait Harmonization (Breaks 64px VAE alignment)
       │
       ▼
 8. Authentic Camera EXIF Injection (Samsung Galaxy S26 / iPhone 15 Pro Max)
       │
       ▼
[Output Clean Photograph]
```

---

## 🚀 Quick Start

### 1. Requirements

- **Operating System:** Windows 10/11, Ubuntu 20.04+, or macOS
- **Python:** 3.8 to 3.13
- **Hardware:**
  - **GPU (Recommended for Heavy Preset):** NVIDIA GPU with CUDA support (RTX series, GTX 1660+, or datacenter GPUs). Memory auto-detected dynamically.
  - **CPU Mode:** Supported for `light` and `medium` presets using OpenCV and Pillow.

### 2. Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/swaylq/deai-image.git
cd deai-image

# Install Python requirements
pip install -r requirements.txt

# (Optional) Install Playwright browsers for headless detector checking
playwright install chromium
```

*(Optional external tool: Install `exiftool` on your system path for low-level binary EXIF consolidation, though native Pillow injection operates automatically).*

---

## 💻 Usage

### Windows One-Click Launcher

Double click `iniciar_deai.bat` in the root folder to start the interactive rich terminal UI.

### Command Line Interface

```bash
# Basic run with auto-detected GPU and default balanced profile
python scripts/deai.py input.png

# Maximum evasion profile (SDXL Purification + DeSynth + CMOS Physics)
python scripts/deai.py input.jpg -o output.jpg --strength heavy

# Process image and automatically test against AI detector APIs
python scripts/deai.py input.jpg --check-detectors

# Batch process an entire folder of AI renders
python scripts/deai.py ./my_renders/ --batch -o ./cleaned_renders/

# Only purge C2PA / AI metadata and inject Galaxy S26 EXIF (zero pixel changes)
python scripts/deai.py input.jpg --no-metadata -o clean_meta.jpg

# Clean output without EXIF simulation
python scripts/deai.py input.jpg --no-exif
```

---

## ⚙️ Processing Presets

| Preset | Method | GPU Required | PSNR | Target Detectors |
| :--- | :--- | :---: | :---: | :--- |
| **`light`** | Micro-noise, Bayer filter, metadata purge | No | > 38 dB | General platforms, stock agencies, social media |
| **`medium`** | CMOS physics, Bayer demosaicing, chromatic dispersion, EXIF injection | Recommended | > 33 dB | Hive, Illuminarty, AI or Not |
| **`heavy`** | SDXL purification + DeSynth detail restoration + CMOS sensor physics + Biometric portrait roll | Yes (CUDA) | > 28.5 dB | Sightengine, SynthID, deep convolutional forensics |

---

## 🔑 AI Detector Verification Setup (Optional)

To enable automated testing against official detector APIs:

1. Copy `scripts/detector_keys.example.json` to `scripts/detector_keys.json`:
   ```bash
   cp scripts/detector_keys.example.json scripts/detector_keys.json
   ```
2. Open `scripts/detector_keys.json` and insert your credentials:
   ```json
   {
     "sightengine_api_user": "YOUR_USER_ID",
     "sightengine_api_secret": "YOUR_API_SECRET",
     "hive_api_key": "YOUR_HIVE_KEY",
     "aiornot_api_key": "YOUR_AIORNOT_KEY",
     "illuminarty_api_key": "",
     "escalation_multiplier": 1.0,
     "chain_mode": false
   }
   ```
*(Note: `detector_keys.json` is protected by `.gitignore` and will never be committed).*

---

## 📁 Repository Structure

```text
deai-image/
├── examples/
│   ├── sample_input.jpg          # Original AI-generated test sample
│   └── sample_output.jpg         # De-AI processed result (0.1% Sightengine score)
├── scripts/
│   ├── camera_profile.py         # Hardware camera profiles & EXIF maker
│   ├── check_deps.sh             # Linux dependency verification
│   ├── deai.py                   # Main CLI engine & interactive terminal UI
│   ├── deai.sh                   # Lightweight shell fallback
│   ├── desynth_reference.py      # Dual-band frequency separation logic
│   ├── detector_client.py        # Headless automated detector integration
│   ├── detector_keys.example.json# Template for API credentials
│   ├── gpu_camera_engine.py      # PyTorch CUDA real-camera physics engine
│   ├── gpu_purifier.py           # Native SDXL latent purifier & DeSynth detail engine
│   └── iphone15pm.json           # Calibration profile for iPhone 15 Pro Max
├── .gitignore                    # Protects API keys and local scratch
├── DEPLOYMENT.md                 # Technical deployment report & audit
├── iniciar_deai.bat              # One-click Windows starter
├── LICENSE                       # MIT License
├── package.json                  # OpenClaw skill descriptor
├── README.md                     # Documentation
├── requirements.txt              # Pinned Python dependencies
└── SKILL.md                      # AI agent interface definition
```

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
