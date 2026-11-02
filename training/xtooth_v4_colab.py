# -*- coding: utf-8 -*-
"""
================================================================================
X-TOOTH — Classificação de Lesões Endo-Periodontais em Radiografias Periapicais
Protocolo Experimental v4.0
Autor: Thiago da Cruz de Araujo — IFMA Campus Caxias
================================================================================

COMO USAR NO GOOGLE COLAB:
  1. Runtime > Change runtime type > GPU.
  2. Cole este arquivo inteiro em UMA célula (ou faça upload e `%run`).
  3. Ao final, um .zip com todos os resultados é baixado automaticamente.

ETAPAS:
  0 — Instalação, ambiente e semente fixa.
  1 — Aquisição do dataset via kagglehub.
  2 — Inventário dos dados.
  3 — Partição estratificada: 15% teste + 85% treino/validação.
  4 — Comparação de 5 arquiteturas por validação cruzada estratificada k=5.
  5 — Otimização de hiperparâmetros (Optuna/TPE) da melhor arquitetura.
  6 — Treino final e avaliação no conjunto de teste.
  7 — Grad-CAM, tabela de erros e relatórios.
================================================================================
"""

# ==============================================================================
# ETAPA 0 — INSTALAÇÃO, AMBIENTE E SEMENTE
# ==============================================================================
import subprocess, sys

def pip_install(pkgs):
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", *pkgs])

pip_install(["kagglehub", "optuna", "grad-cam", "albumentations", "torchinfo"])

import os, json, time, random, shutil, hashlib, platform, logging, copy
from datetime import datetime
from pathlib import Path
from collections import Counter

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from PIL import Image

import torch
import torch.nn as nn
import torchvision
from torchvision import models
from torch.utils.data import DataLoader, Dataset, Subset
from torchvision.datasets import ImageFolder

import albumentations as A
from albumentations.pytorch import ToTensorV2

from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.metrics import (accuracy_score, balanced_accuracy_score, f1_score,
                             classification_report, confusion_matrix,
                             roc_auc_score, roc_curve, auc)
from sklearn.preprocessing import label_binarize

import optuna
from pytorch_grad_cam import GradCAM
from pytorch_grad_cam.utils.image import show_cam_on_image

# ------------------------------- CONFIGURAÇÃO --------------------------------
CONFIG = {
    "version": "4.0.0",
    "seed": 42,
    "image_size": 224,
    "num_classes": 5,
    "test_fraction": 0.15,          # fração do teste hold-out
    "k_folds": 5,                   # folds da validação cruzada
    "epochs_cv": 25,                # épocas por fold na comparação
    "epochs_final": 40,             # épocas do treino final
    "batch_size": 16,
    "learning_rate": 1e-4,
    "weight_decay": 1e-4,
    "early_stopping_patience": 7,
    "selection_metric": "macro_f1", # métrica de seleção de modelos
    "optuna_trials": 15,            # nº de trials do HPO (Etapa 5)
    "models": ["resnet50", "efficientnet_b0", "densenet121",
               "mobilenet_v3_large", "vit_b_16"],
    "kaggle_dataset": "muhammadsajad/periapical-xrays",
}

def set_seed(seed: int):
    """Fixa todas as fontes de aleatoriedade."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    os.environ["PYTHONHASHSEED"] = str(seed)

set_seed(CONFIG["seed"])

# Diretórios de saída
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
ROOT = Path(f"/content/results/xtooth_v4_{STAMP}")
DIRS = {k: ROOT / k for k in
        ["logs", "data_dictionary", "cv", "hpo", "final", "gradcam", "errors"]}
for d in [ROOT, *DIRS.values()]:
    d.mkdir(parents=True, exist_ok=True)

# Logging para arquivo + console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.FileHandler(DIRS["logs"] / "run.log"),
              logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("xtooth").info

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

def capture_environment():
    """Registra o ambiente de execução."""
    env = {
        "timestamp": STAMP,
        "python": platform.python_version(),
        "torch": torch.__version__,
        "torchvision": torchvision.__version__,
        "albumentations": A.__version__,
        "optuna": optuna.__version__,
        "cuda_available": torch.cuda.is_available(),
        "cuda_version": torch.version.cuda,
        "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU",
        "platform": platform.platform(),
        "config": CONFIG,
    }
    with open(DIRS["logs"] / "environment.json", "w") as f:
        json.dump(env, f, indent=2)
    log(f"AMBIENTE: {json.dumps(env, indent=2)}")
    return env

ENV = capture_environment()

# ==============================================================================
# ETAPA 1 — AQUISIÇÃO DO DATASET
# ==============================================================================
import kagglehub
log("Baixando dataset do Kaggle via kagglehub...")
DATASET_DOWNLOAD = kagglehub.dataset_download(CONFIG["kaggle_dataset"])
log(f"Dataset baixado em: {DATASET_DOWNLOAD}")

# Localiza a pasta que contém as 5 classes
def find_class_root(base):
    for root, dirs, _ in os.walk(base):
        if len([d for d in dirs if "Lesion" in d or "Perio" in d or "Endo" in d]) >= 4:
            return root
    return base

DATA_DIR = find_class_root(DATASET_DOWNLOAD)
log(f"Raiz das classes: {DATA_DIR}")

# ==============================================================================
# ETAPA 2 — INVENTÁRIO E DICIONÁRIO DE DADOS
# ==============================================================================
def build_data_dictionary(data_dir):
    rows = []
    for cls in sorted(os.listdir(data_dir)):
        cdir = Path(data_dir) / cls
        if not cdir.is_dir():
            continue
        for img_path in sorted(cdir.glob("*")):
            if img_path.suffix.lower() not in (".jpg", ".jpeg", ".png"):
                continue
            try:
                with Image.open(img_path) as im:
                    w, h = im.size
                    mode = im.mode
                arr = np.array(Image.open(img_path).convert("L"))
                rows.append({
                    "file": img_path.name, "class": cls, "width": w, "height": h,
                    "mode": mode, "mean_intensity": float(arr.mean()),
                    "std_intensity": float(arr.std()),
                    "md5": hashlib.md5(img_path.read_bytes()).hexdigest(),
                })
            except Exception as e:
                log(f"AVISO imagem ilegível: {img_path} ({e})")
    df = pd.DataFrame(rows)
    df.to_csv(DIRS["data_dictionary"] / "data_dictionary.csv", index=False)

    summary = {
        "total_images": len(df),
        "class_distribution": df["class"].value_counts().to_dict(),
        "width": {"min": int(df.width.min()), "max": int(df.width.max()),
                  "mean": float(df.width.mean())},
        "height": {"min": int(df.height.min()), "max": int(df.height.max()),
                   "mean": float(df.height.mean())},
        "intensity_mean": float(df.mean_intensity.mean()),
        "duplicated_md5": int(df.md5.duplicated().sum()),
    }
    with open(DIRS["data_dictionary"] / "dataset_summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    log(f"DICIONÁRIO DE DADOS:\n{json.dumps(summary, indent=2)}")

    # Gráfico de distribuição de classes
    plt.figure(figsize=(9, 4))
    df["class"].value_counts().plot(kind="bar")
    plt.title("Distribuição de imagens por classe")
    plt.ylabel("Nº de imagens"); plt.tight_layout()
    plt.savefig(DIRS["data_dictionary"] / "class_distribution.png", dpi=150)
    plt.close()
    return df, summary

DATA_DF, DATA_SUMMARY = build_data_dictionary(DATA_DIR)

# ==============================================================================
# ETAPA 3 — PARTIÇÃO ESTRATIFICADA (teste isolado) + TRANSFORMAÇÕES
# ==============================================================================
base_dataset = ImageFolder(root=DATA_DIR)
CLASS_NAMES = base_dataset.classes
targets = np.array([t for _, t in base_dataset.samples])
indices = np.arange(len(base_dataset))

trainval_idx, test_idx = train_test_split(
    indices, test_size=CONFIG["test_fraction"], stratify=targets,
    random_state=CONFIG["seed"])
log(f"Partição: {len(trainval_idx)} treino/val | {len(test_idx)} teste (isolado)")
json.dump({"trainval_idx": trainval_idx.tolist(), "test_idx": test_idx.tolist(),
           "classes": CLASS_NAMES},
          open(DIRS["logs"] / "split_indices.json", "w"), indent=2)

IMAGENET_MEAN, IMAGENET_STD = [0.485, 0.456, 0.406], [0.229, 0.224, 0.225]

def get_transforms(phase, aug_strength=1.0):
    """Transformações de treino: flip horizontal, rotação leve,
    brilho/contraste e CLAHE. Validação/teste: apenas resize + normalização."""
    if phase == "train":
        s = aug_strength
        return A.Compose([
            A.Resize(CONFIG["image_size"], CONFIG["image_size"]),
            A.HorizontalFlip(p=0.5),
            A.Affine(scale=(1 - 0.1*s, 1 + 0.1*s), rotate=(-10*s, 10*s),
                     translate_percent=(0.0, 0.05*s), p=0.7),
            A.RandomBrightnessContrast(brightness_limit=0.2*s,
                                       contrast_limit=0.2*s, p=0.5),
            A.CLAHE(clip_limit=3.0, p=0.3),
            A.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
            ToTensorV2(),
        ])
    return A.Compose([
        A.Resize(CONFIG["image_size"], CONFIG["image_size"]),
        A.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
        ToTensorV2(),
    ])

class XrayDataset(Dataset):
    def __init__(self, image_folder, indices, transform):
        self.samples = [image_folder.samples[i] for i in indices]
        self.transform = transform
    def __len__(self):
        return len(self.samples)
    def __getitem__(self, i):
        path, label = self.samples[i]
        img = np.array(Image.open(path).convert("RGB"))
        img = self.transform(image=img)["image"]
        return img, label, path

def make_loader(idxs, phase, aug_strength=1.0, batch_size=None):
    ds = XrayDataset(base_dataset, idxs, get_transforms(phase, aug_strength))
    return DataLoader(ds, batch_size=batch_size or CONFIG["batch_size"],
                      shuffle=(phase == "train"), num_workers=2,
                      pin_memory=torch.cuda.is_available(),
                      worker_init_fn=lambda wid: np.random.seed(CONFIG["seed"] + wid))

def class_weights_from(idxs):
    """Pesos inversamente proporcionais à frequência de cada classe."""
    counts = Counter(targets[idxs])
    total = sum(counts.values())
    w = [total / (len(counts) * counts[c]) for c in range(CONFIG["num_classes"])]
    return torch.FloatTensor(w)

# ==============================================================================
# MODELOS — transferência de aprendizado (pesos ImageNet)
# ==============================================================================
def create_model(name, dropout=0.3):
    if name == "resnet50":
        m = models.resnet50(weights=models.ResNet50_Weights.IMAGENET1K_V2)
        m.fc = nn.Sequential(nn.Dropout(dropout),
                             nn.Linear(m.fc.in_features, CONFIG["num_classes"]))
        target_layer = m.layer4[-1]
    elif name == "efficientnet_b0":
        m = models.efficientnet_b0(weights=models.EfficientNet_B0_Weights.IMAGENET1K_V1)
        m.classifier[1] = nn.Sequential(
            nn.Dropout(dropout), nn.Linear(m.classifier[1].in_features,
                                           CONFIG["num_classes"]))
        target_layer = m.features[-1]
    elif name == "densenet121":
        m = models.densenet121(weights=models.DenseNet121_Weights.IMAGENET1K_V1)
        m.classifier = nn.Sequential(
            nn.Dropout(dropout), nn.Linear(m.classifier.in_features,
                                           CONFIG["num_classes"]))
        target_layer = m.features[-1]
    elif name == "mobilenet_v3_large":
        m = models.mobilenet_v3_large(
            weights=models.MobileNet_V3_Large_Weights.IMAGENET1K_V2)
        m.classifier[3] = nn.Sequential(
            nn.Dropout(dropout), nn.Linear(m.classifier[3].in_features,
                                           CONFIG["num_classes"]))
        target_layer = m.features[-1]
    elif name == "vit_b_16":
        m = models.vit_b_16(weights=models.ViT_B_16_Weights.IMAGENET1K_V1)
        m.heads.head = nn.Sequential(
            nn.Dropout(dropout), nn.Linear(m.heads.head.in_features,
                                           CONFIG["num_classes"]))
        target_layer = m.encoder.layers[-1].ln_1
    else:
        raise ValueError(name)
    return m, target_layer

# ==============================================================================
# TREINO / AVALIAÇÃO (rotina comum a todas as etapas)
# ==============================================================================
def evaluate(model, loader, criterion):
    model.eval()
    loss_sum, ys, ps, probs, paths = 0.0, [], [], [], []
    with torch.no_grad():
        for x, y, pth in loader:
            x, y = x.to(DEVICE), y.to(DEVICE)
            out = model(x)
            loss_sum += criterion(out, y).item() * x.size(0)
            prob = torch.softmax(out, 1)
            ps += prob.argmax(1).cpu().tolist()
            probs += prob.cpu().tolist()
            ys += y.cpu().tolist()
            paths += list(pth)
    n = len(ys)
    return {
        "loss": loss_sum / n,
        "acc": accuracy_score(ys, ps),
        "balanced_acc": balanced_accuracy_score(ys, ps),
        "macro_f1": f1_score(ys, ps, average="macro"),
        "weighted_f1": f1_score(ys, ps, average="weighted"),
        "y_true": ys, "y_pred": ps, "y_prob": probs, "paths": paths,
    }

def train_one(model, train_loader, val_loader, *, epochs, lr, weight_decay,
              class_weights, tag, patience=None, log_every_epoch=True):
    patience = patience or CONFIG["early_stopping_patience"]
    model = model.to(DEVICE)
    criterion = nn.CrossEntropyLoss(weight=class_weights.to(DEVICE))
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr,
                                  weight_decay=weight_decay)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer,
                                                           T_max=epochs)
    best = {"macro_f1": -1}
    best_state, no_improve, history = None, 0, []

    for ep in range(1, epochs + 1):
        model.train()
        t0, loss_sum, n = time.time(), 0.0, 0
        for x, y, _ in train_loader:
            x, y = x.to(DEVICE), y.to(DEVICE)
            optimizer.zero_grad()
            loss = criterion(model(x), y)
            loss.backward()
            optimizer.step()
            loss_sum += loss.item() * x.size(0); n += x.size(0)
        scheduler.step()

        val = evaluate(model, val_loader, criterion)
        history.append({"epoch": ep, "train_loss": loss_sum / n,
                        "val_loss": val["loss"], "val_acc": val["acc"],
                        "val_balanced_acc": val["balanced_acc"],
                        "val_macro_f1": val["macro_f1"],
                        "lr": optimizer.param_groups[0]["lr"],
                        "sec": round(time.time() - t0, 1)})
        if log_every_epoch:
            h = history[-1]
            log(f"[{tag}] ep {ep:02d}/{epochs} | train_loss {h['train_loss']:.4f} "
                f"| val_loss {h['val_loss']:.4f} | acc {h['val_acc']:.4f} "
                f"| bal_acc {h['val_balanced_acc']:.4f} "
                f"| macroF1 {h['val_macro_f1']:.4f} | {h['sec']}s")

        if val["macro_f1"] > best["macro_f1"]:
            best, best_state, no_improve = val, copy.deepcopy(model.state_dict()), 0
            best["epoch"] = ep
        else:
            no_improve += 1
            if no_improve >= patience:
                log(f"[{tag}] early stopping na época {ep} "
                    f"(melhor macroF1 {best['macro_f1']:.4f} na ep {best['epoch']})")
                break

    model.load_state_dict(best_state)
    return model, best, history

# ==============================================================================
# ETAPA 4 — COMPARAÇÃO DE ARQUITETURAS (validação cruzada estratificada k=5)
# ==============================================================================
def run_model_comparison():
    log("=" * 80); log("ETAPA 4 — COMPARAÇÃO DE ARQUITETURAS (CV estratificada k=5)")
    skf = StratifiedKFold(n_splits=CONFIG["k_folds"], shuffle=True,
                          random_state=CONFIG["seed"])
    results = []
    for name in CONFIG["models"]:
        fold_metrics = []
        for fold, (tr, va) in enumerate(skf.split(trainval_idx,
                                                  targets[trainval_idx]), 1):
            set_seed(CONFIG["seed"] + fold)   # mesma sequência para todos os modelos
            tr_idx, va_idx = trainval_idx[tr], trainval_idx[va]
            tag = f"{name}_fold{fold}"
            model, _ = create_model(name)
            _, best, hist = train_one(
                model, make_loader(tr_idx, "train"), make_loader(va_idx, "val"),
                epochs=CONFIG["epochs_cv"], lr=CONFIG["learning_rate"],
                weight_decay=CONFIG["weight_decay"],
                class_weights=class_weights_from(tr_idx), tag=tag)
            fold_metrics.append({k: best[k] for k in
                                 ("acc", "balanced_acc", "macro_f1",
                                  "weighted_f1", "epoch")})
            pd.DataFrame(hist).to_csv(DIRS["cv"] / f"{tag}_history.csv",
                                      index=False)
            del model; torch.cuda.empty_cache()

        agg = {f"mean_{k}": float(np.mean([m[k] for m in fold_metrics]))
               for k in ("acc", "balanced_acc", "macro_f1", "weighted_f1")}
        agg |= {f"std_{k}": float(np.std([m[k] for m in fold_metrics]))
                for k in ("acc", "balanced_acc", "macro_f1", "weighted_f1")}
        agg |= {"model": name, "folds": fold_metrics}
        results.append(agg)
        log(f">>> {name}: macroF1 {agg['mean_macro_f1']:.4f}"
            f" ±{agg['std_macro_f1']:.4f} | acc {agg['mean_acc']:.4f}"
            f" ±{agg['std_acc']:.4f}")
        json.dump(results, open(DIRS["cv"] / "cv_results.json", "w"), indent=2)

    df = pd.DataFrame([{k: v for k, v in r.items() if k != "folds"}
                       for r in results])
    df.to_csv(DIRS["cv"] / "model_comparison.csv", index=False)

    plt.figure(figsize=(10, 5))
    plt.bar(df["model"], df["mean_macro_f1"], yerr=df["std_macro_f1"],
            capsize=6, alpha=0.8)
    plt.ylabel("Macro F1 (média ± dp, CV k=5)"); plt.xticks(rotation=20)
    plt.title("Comparação de arquiteturas — validação cruzada estratificada")
    plt.tight_layout()
    plt.savefig(DIRS["cv"] / "model_comparison.png", dpi=150); plt.close()

    best_model_name = df.sort_values("mean_macro_f1", ascending=False
                                     ).iloc[0]["model"]
    log(f"MELHOR ARQUITETURA (macro F1): {best_model_name}")
    return best_model_name, results

BEST_ARCH, CV_RESULTS = run_model_comparison()

# ==============================================================================
# ETAPA 5 — OTIMIZAÇÃO DE HIPERPARÂMETROS (Optuna / TPE)
# ==============================================================================
def run_hpo(arch):
    log("=" * 80); log(f"ETAPA 5 — HPO (Optuna/TPE) para {arch}, "
                       f"{CONFIG['optuna_trials']} trials")
    tv_targets = targets[trainval_idx]
    tr, va = train_test_split(np.arange(len(trainval_idx)), test_size=0.2,
                              stratify=tv_targets, random_state=CONFIG["seed"])
    tr_idx, va_idx = trainval_idx[tr], trainval_idx[va]

    def objective(trial):
        set_seed(CONFIG["seed"])
        lr = trial.suggest_float("lr", 1e-5, 5e-4, log=True)
        wd = trial.suggest_float("weight_decay", 1e-6, 1e-3, log=True)
        dropout = trial.suggest_float("dropout", 0.1, 0.5)
        aug = trial.suggest_float("aug_strength", 0.5, 1.5)
        bs = trial.suggest_categorical("batch_size", [8, 16, 32])
        model, _ = create_model(arch, dropout=dropout)
        _, best, _ = train_one(
            model, make_loader(tr_idx, "train", aug, bs),
            make_loader(va_idx, "val", batch_size=bs),
            epochs=15, lr=lr, weight_decay=wd,
            class_weights=class_weights_from(tr_idx),
            tag=f"hpo_t{trial.number}", patience=5, log_every_epoch=False)
        log(f"[HPO trial {trial.number}] macroF1={best['macro_f1']:.4f} "
            f"| params={trial.params}")
        del model; torch.cuda.empty_cache()
        return best["macro_f1"]

    study = optuna.create_study(
        direction="maximize",
        sampler=optuna.samplers.TPESampler(seed=CONFIG["seed"]))
    study.optimize(objective, n_trials=CONFIG["optuna_trials"])

    json.dump({"best_params": study.best_params,
               "best_macro_f1": study.best_value,
               "trials": [{"number": t.number, "value": t.value,
                           "params": t.params} for t in study.trials]},
              open(DIRS["hpo"] / "optuna_study.json", "w"), indent=2)
    log(f"HPO concluído. Melhores hiperparâmetros: {study.best_params} "
        f"(macroF1={study.best_value:.4f})")
    return study.best_params

BEST_PARAMS = run_hpo(BEST_ARCH)

# ==============================================================================
# ETAPA 6 — TREINO FINAL + AVALIAÇÃO ÚNICA NO TESTE ISOLADO
# ==============================================================================
def run_final(arch, params):
    log("=" * 80); log(f"ETAPA 6 — TREINO FINAL ({arch}) e teste hold-out")
    set_seed(CONFIG["seed"])
    tv_targets = targets[trainval_idx]
    tr, va = train_test_split(np.arange(len(trainval_idx)), test_size=0.1,
                              stratify=tv_targets, random_state=CONFIG["seed"])
    tr_idx, va_idx = trainval_idx[tr], trainval_idx[va]
    bs = params.get("batch_size", CONFIG["batch_size"])

    model, target_layer = create_model(arch, dropout=params.get("dropout", 0.3))
    model, best_val, hist = train_one(
        model,
        make_loader(tr_idx, "train", params.get("aug_strength", 1.0), bs),
        make_loader(va_idx, "val", batch_size=bs),
        epochs=CONFIG["epochs_final"], lr=params.get("lr", 1e-4),
        weight_decay=params.get("weight_decay", 1e-4),
        class_weights=class_weights_from(tr_idx), tag=f"{arch}_final",
        patience=10)
    pd.DataFrame(hist).to_csv(DIRS["final"] / "final_history.csv", index=False)

    # Curvas de aprendizado
    h = pd.DataFrame(hist)
    fig, ax = plt.subplots(1, 2, figsize=(12, 4))
    ax[0].plot(h.epoch, h.train_loss, label="treino")
    ax[0].plot(h.epoch, h.val_loss, label="validação")
    ax[0].set_title("Perda"); ax[0].legend()
    ax[1].plot(h.epoch, h.val_acc, label="acurácia")
    ax[1].plot(h.epoch, h.val_macro_f1, label="macro F1")
    ax[1].set_title("Métricas (validação)"); ax[1].legend()
    plt.tight_layout()
    plt.savefig(DIRS["final"] / "learning_curves.png", dpi=150); plt.close()

    # ---- Avaliação única no conjunto de teste isolado ----
    criterion = nn.CrossEntropyLoss(weight=class_weights_from(tr_idx).to(DEVICE))
    test = evaluate(model, make_loader(test_idx, "test", batch_size=bs), criterion)
    log(f"TESTE (hold-out): acc={test['acc']:.4f} | "
        f"bal_acc={test['balanced_acc']:.4f} | macroF1={test['macro_f1']:.4f}")

    report = classification_report(test["y_true"], test["y_pred"],
                                   target_names=CLASS_NAMES, output_dict=True,
                                   zero_division=0)
    json.dump(report, open(DIRS["final"] / "classification_report.json", "w"),
              indent=2)
    log("Relatório por classe:\n" +
        classification_report(test["y_true"], test["y_pred"],
                              target_names=CLASS_NAMES, zero_division=0))

    # Matriz de confusão
    cm = confusion_matrix(test["y_true"], test["y_pred"])
    plt.figure(figsize=(9, 7))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
                xticklabels=CLASS_NAMES, yticklabels=CLASS_NAMES)
    plt.xlabel("Predito"); plt.ylabel("Real")
    plt.title(f"{arch} — teste hold-out | acc {test['acc']:.2%} "
              f"| macroF1 {test['macro_f1']:.4f}")
    plt.xticks(rotation=30, ha="right"); plt.tight_layout()
    plt.savefig(DIRS["final"] / "confusion_matrix_test.png", dpi=150)
    plt.close()

    # Curvas ROC (um-contra-todos) + AUC
    y_bin = label_binarize(test["y_true"], classes=range(CONFIG["num_classes"]))
    probs = np.array(test["y_prob"])
    plt.figure(figsize=(8, 6))
    aucs = {}
    for i, cname in enumerate(CLASS_NAMES):
        fpr, tpr, _ = roc_curve(y_bin[:, i], probs[:, i])
        aucs[cname] = auc(fpr, tpr)
        plt.plot(fpr, tpr, label=f"{cname} (AUC={aucs[cname]:.3f})")
    plt.plot([0, 1], [0, 1], "k--")
    plt.xlabel("1 - Especificidade"); plt.ylabel("Sensibilidade")
    plt.title("Curvas ROC (um-contra-todos) — teste hold-out")
    plt.legend(fontsize=8); plt.tight_layout()
    plt.savefig(DIRS["final"] / "roc_curves_test.png", dpi=150); plt.close()
    aucs["macro_ovr"] = float(roc_auc_score(test["y_true"], probs,
                                            multi_class="ovr", average="macro"))
    json.dump(aucs, open(DIRS["final"] / "roc_auc.json", "w"), indent=2)

    # Tabela de predições e erros do teste
    err_rows = []
    for yt, yp, pb, pth in zip(test["y_true"], test["y_pred"],
                               test["y_prob"], test["paths"]):
        err_rows.append({"file": os.path.basename(pth),
                         "true": CLASS_NAMES[yt], "pred": CLASS_NAMES[yp],
                         "confidence": round(max(pb), 4),
                         "correct": yt == yp})
    err_df = pd.DataFrame(err_rows)
    err_df.to_csv(DIRS["errors"] / "test_predictions.csv", index=False)
    err_df[~err_df.correct].to_csv(DIRS["errors"] / "test_errors.csv",
                                   index=False)
    log(f"Tabela de erros salva ({(~err_df.correct).sum()} erros / "
        f"{len(err_df)} imagens de teste)")

    # Salvar modelo final
    torch.save({"state_dict": model.state_dict(), "arch": arch,
                "params": params, "classes": CLASS_NAMES,
                "test_metrics": {k: test[k] for k in
                                 ("acc", "balanced_acc", "macro_f1",
                                  "weighted_f1")}},
               DIRS["final"] / "final_model.pth")
    return model, target_layer, test, report

FINAL_MODEL, TARGET_LAYER, TEST_METRICS, REPORT = run_final(BEST_ARCH, BEST_PARAMS)

# ==============================================================================
# ETAPA 7 — EXPLICABILIDADE (Grad-CAM): o que o modelo "olhou"
# ==============================================================================
def run_gradcam(model, target_layer, n_per_class=3):
    log("=" * 80); log("ETAPA 7 — Grad-CAM (explicabilidade)")
    if BEST_ARCH == "vit_b_16":
        def reshape_transform(t):
            t = t[:, 1:, :]
            s = int(t.size(1) ** 0.5)
            return t.reshape(t.size(0), s, s, t.size(2)).permute(0, 3, 1, 2)
        cam = GradCAM(model=model, target_layers=[target_layer],
                      reshape_transform=reshape_transform)
    else:
        cam = GradCAM(model=model, target_layers=[target_layer])

    tfm = get_transforms("test")
    picked = {c: 0 for c in range(CONFIG["num_classes"])}
    for idx in test_idx:
        path, label = base_dataset.samples[idx]
        if picked[label] >= n_per_class:
            continue
        raw = np.array(Image.open(path).convert("RGB"))
        inp = tfm(image=raw)["image"].unsqueeze(0).to(DEVICE)
        with torch.no_grad():
            pred = int(model(inp).argmax(1))
        gray = cam(input_tensor=inp)[0]
        vis_base = A.Resize(CONFIG["image_size"], CONFIG["image_size"])(
            image=raw)["image"] / 255.0
        vis = show_cam_on_image(vis_base.astype(np.float32), gray, use_rgb=True)
        ok = "OK" if pred == label else "ERRO"
        fig, ax = plt.subplots(1, 2, figsize=(8, 4))
        ax[0].imshow(vis_base); ax[0].set_title("Radiografia"); ax[0].axis("off")
        ax[1].imshow(vis); ax[1].axis("off")
        ax[1].set_title(f"Grad-CAM | real: {CLASS_NAMES[label]}\n"
                        f"pred: {CLASS_NAMES[pred]} [{ok}]", fontsize=8)
        plt.tight_layout()
        fname = f"{CLASS_NAMES[label].replace(' ', '_')}_{picked[label]}_{ok}.png"
        plt.savefig(DIRS["gradcam"] / fname, dpi=150); plt.close()
        picked[label] += 1
    log(f"Grad-CAM salvo em {DIRS['gradcam']}")

try:
    run_gradcam(FINAL_MODEL, TARGET_LAYER)
except Exception as e:
    log(f"AVISO: Grad-CAM falhou ({e}); prossiga, demais resultados estão salvos.")

# ==============================================================================
# RELATÓRIO FINAL + EMPACOTAMENTO
# ==============================================================================
FINAL_REPORT = {
    "version": CONFIG["version"],
    "environment": {k: ENV[k] for k in ("gpu", "torch", "cuda_version", "python")},
    "dataset": DATA_SUMMARY,
    "split": {"trainval": len(trainval_idx), "test": len(test_idx),
              "stratified": True, "seed": CONFIG["seed"]},
    "cv_comparison": [{k: v for k, v in r.items() if k != "folds"}
                      for r in CV_RESULTS],
    "best_architecture": BEST_ARCH,
    "best_hyperparameters": BEST_PARAMS,
    "test_metrics": {k: TEST_METRICS[k] for k in
                     ("acc", "balanced_acc", "macro_f1", "weighted_f1")},
    "per_class_report": REPORT,
}
json.dump(FINAL_REPORT, open(ROOT / "final_report.json", "w"), indent=2)
log("=" * 80)
log("RELATÓRIO FINAL:\n" + json.dumps(FINAL_REPORT["test_metrics"], indent=2))
log(f"Resultados completos em: {ROOT}")

zip_path = shutil.make_archive(f"/content/xtooth_v4_results_{STAMP}", "zip", ROOT)
log(f"ZIP gerado: {zip_path}")
try:
    from google.colab import files
    files.download(zip_path)
except Exception:
    pass
