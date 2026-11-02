# -*- coding: utf-8 -*-
"""
X-TOOTH API — serve o modelo final (ViT-B/16, protocolo v4.4) para o app.

Como executar localmente:
  1. Coloque o checkpoint em  api/model/final_model.pth
     (arquivo `final/final_model.pth` do resultado da Execução 5).
  2. pip install -r requirements.txt
  3. uvicorn main:app --host 0.0.0.0 --port 8000

Endpoints:
  GET  /health            -> status e metadados do modelo carregado
  POST /predict           -> multipart com campo "file" (imagem da radiografia)
                             JSON: classe predita, confiança e probabilidades
  POST /predict?gradcam=1 -> idem + imagem Grad-CAM (base64 PNG)
"""

import base64
import io
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from torchvision import models

import albumentations as A
from albumentations.pytorch import ToTensorV2

MODEL_PATH = Path(__file__).parent / "model" / "final_model.pth"
IMAGE_SIZE = 224
IMAGENET_MEAN, IMAGENET_STD = [0.485, 0.456, 0.406], [0.229, 0.224, 0.225]

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

app = FastAPI(title="X-TOOTH API", version="1.0.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------- carregamento do modelo ---------------------------
def build_model(num_classes: int, dropout: float):
    m = models.vit_b_16(weights=None)
    m.heads.head = nn.Sequential(
        nn.Dropout(dropout), nn.Linear(m.heads.head.in_features, num_classes))
    return m

if not MODEL_PATH.exists():
    raise FileNotFoundError(
        f"Checkpoint não encontrado em {MODEL_PATH}. Copie o final_model.pth "
        f"da Execução 5 para api/model/.")

CKPT = torch.load(MODEL_PATH, map_location=DEVICE, weights_only=False)
CLASSES = CKPT["classes"]
PARAMS = CKPT.get("params", {})
MODEL = build_model(len(CLASSES), PARAMS.get("dropout", 0.195))
MODEL.load_state_dict(CKPT["state_dict"])
MODEL.to(DEVICE).eval()

TRANSFORM = A.Compose([
    A.Resize(IMAGE_SIZE, IMAGE_SIZE),
    A.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
    ToTensorV2(),
])

# ------------------------------- Grad-CAM -----------------------------------
def gradcam_overlay(inp: torch.Tensor, raw: np.ndarray, pred: int) -> str:
    from pytorch_grad_cam import GradCAM
    from pytorch_grad_cam.utils.image import show_cam_on_image
    from pytorch_grad_cam.utils.model_targets import ClassifierOutputTarget

    def reshape_transform(t):
        t = t[:, 1:, :]
        s = int(t.size(1) ** 0.5)
        return t.reshape(t.size(0), s, s, t.size(2)).permute(0, 3, 1, 2)

    cam = GradCAM(model=MODEL,
                  target_layers=[MODEL.encoder.layers[-1].ln_1],
                  reshape_transform=reshape_transform)
    gray = cam(input_tensor=inp, targets=[ClassifierOutputTarget(pred)])[0]
    base = A.Resize(IMAGE_SIZE, IMAGE_SIZE)(image=raw)["image"] / 255.0
    vis = show_cam_on_image(base.astype(np.float32), gray, use_rgb=True)
    buf = io.BytesIO()
    Image.fromarray(vis).save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()

# ------------------------------- endpoints ----------------------------------
@app.get("/health")
def health():
    return {
        "status": "ok",
        "model": CKPT.get("arch", "vit_b_16"),
        "protocol_version": "4.4.0",
        "classes": CLASSES,
        "device": str(DEVICE),
        "test_metrics": CKPT.get("test_metrics", {}),
    }

@app.post("/predict")
async def predict(file: UploadFile = File(...),
                  gradcam: int = Query(0, description="1 = incluir Grad-CAM")):
    data = await file.read()
    try:
        raw = np.array(Image.open(io.BytesIO(data)).convert("RGB"))
    except Exception:
        raise HTTPException(status_code=400,
                            detail="Arquivo não é uma imagem válida.")

    inp = TRANSFORM(image=raw)["image"].unsqueeze(0).to(DEVICE)
    with torch.no_grad():
        probs = torch.softmax(MODEL(inp), dim=1)[0].cpu().tolist()
    pred = int(np.argmax(probs))

    result = {
        "predicted_class": CLASSES[pred],
        "confidence": round(probs[pred], 4),
        "probabilities": {c: round(p, 4) for c, p in zip(CLASSES, probs)},
        "disclaimer": ("Ferramenta de auxílio ao diagnóstico. O resultado não "
                       "substitui a avaliação de um profissional de "
                       "odontologia."),
    }
    if gradcam:
        try:
            result["gradcam_png_base64"] = gradcam_overlay(inp, raw, pred)
        except Exception as e:
            result["gradcam_error"] = str(e)
    return result
