#!/usr/bin/env python3
"""
Camera Profiling Tool
Extrai assinatura estatística de fotos reais (iPhone, Pixel, Samsung) e
aplica em imagens de IA para herdar a "impressão digital" de uma câmera real.

Suporta HEIC/HEIF (iPhone padrão), JPEG, PNG e WebP.

Uso:
    python camera_profile.py extract pasta/ -o iphone15pm.json -n "iPhone 15 Pro Max"
    python camera_profile.py apply imagem.jpg -p iphone15pm.json -o saida.jpg -s 1.0
    python camera_profile.py info iphone15pm.json
    python camera_profile.py compare a.json b.json

Dependência para HEIC:
    pip install pillow-heif
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import cv2

# HEIC/HEIF support (opcional, mas necessário para fotos do iPhone)
try:
    from pillow_heif import register_heif_opener
    from PIL import Image
    register_heif_opener()
    HEIC_SUPPORTED = True
except ImportError:
    HEIC_SUPPORTED = False


# =====================================================================
# I/O
# =====================================================================

IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.heic', '.heif', '.tif', '.tiff'}


def load_image(path):
    """Carrega imagem preservando pipeline pós-ISP. Suporta HEIC."""
    p = Path(path)
    if p.suffix.lower() in {'.heic', '.heif'}:
        if not HEIC_SUPPORTED:
            raise RuntimeError(
                f"HEIC detectado ({p.name}) mas pillow-heif não está instalado.\n"
                "Instale com: pip install pillow-heif"
            )
        pil = Image.open(p).convert("RGB")
        return cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
    img = cv2.imread(str(p))
    if img is None:
        # Fallback via Pillow (TIF, WebP raro, etc.)
        pil = Image.open(p).convert("RGB")
        img = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
    return img


def collect_images(path):
    """Coleta imagens de um arquivo ou pasta."""
    p = Path(path)
    if p.is_file():
        return [p]
    if not p.is_dir():
        return []
    files = [f for f in p.rglob("*") if f.suffix.lower() in IMAGE_EXTS]
    return sorted(files)


# =====================================================================
# CAMERA PROFILE
# =====================================================================

class CameraProfile:
    VERSION = 2  # v2: noise_curve normalizada, chroma stats, per-lens

    @staticmethod
    def extract(photo_paths, name="custom", max_dim=1024, verbose=True):
        """Analisa N fotos reais e produz o perfil estatístico."""
        photos = []
        skipped = 0
        for p in photo_paths:
            try:
                img = load_image(p)
            except Exception as e:
                if verbose:
                    print(f"  [skip] {Path(p).name}: {e}")
                skipped += 1
                continue
            if img is None:
                skipped += 1
                continue

            # Normaliza para 1024px máx — estatística não depende de resolução
            h, w = img.shape[:2]
            if max(h, w) > max_dim:
                s = max_dim / max(h, w)
                img = cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
            photos.append(img)

        if len(photos) < 5:
            raise ValueError(
                f"Mínimo de 5 fotos válidas (recebi {len(photos)}, "
                f"{skipped} puladas). Junte mais fotos para estabilidade estatística."
            )

        if verbose:
            print(f"  Analisadas: {len(photos)} fotos "
                  f"({skipped} puladas)")

        # --- 1. Estatística Lab (Reinhard color matching) ---
        labs = [cv2.cvtColor(p, cv2.COLOR_BGR2LAB).astype(np.float32) for p in photos]
        lab_stats = {}
        for i, ch in enumerate(["L", "a", "b"]):
            vals = np.concatenate([lab[:, :, i].ravel() for lab in labs])
            lab_stats[ch] = {
                "mean": float(vals.mean()),
                "std": float(vals.std()),
                "p5": float(np.percentile(vals, 5)),
                "p95": float(np.percentile(vals, 95)),
                "p50": float(np.percentile(vals, 50)),
            }

        # --- 2. Curva de ruído por faixa de luminância ---
        # Isto captura a assinatura de shot noise do sensor: mais ruído em
        # sombras, mais limpo em luz boa. É a parte mais valiosa do perfil.
        bins = np.linspace(0, 255, 17)  # 16 bins
        accum = [[] for _ in range(len(bins) - 1)]
        for p in photos:
            gray = cv2.cvtColor(p, cv2.COLOR_BGR2GRAY).astype(np.float32)
            # High-pass: subtrai blur para isolar ruído de alta frequência
            blur = cv2.GaussianBlur(gray, (0, 0), 1.5)
            hp = gray - blur
            for i in range(len(bins) - 1):
                mask = (gray >= bins[i]) & (gray < bins[i + 1])
                if mask.sum() > 300:
                    v = hp[mask]
                    # Trim outliers (bordas, transições)
                    lim = np.percentile(np.abs(v), 90)
                    v_trimmed = v[np.abs(v) < lim]
                    if len(v_trimmed) > 100:
                        accum[i].append(float(np.std(v_trimmed)))

        noise_curve = []
        for i, vals in enumerate(accum):
            mid = float((bins[i] + bins[i + 1]) / 2)
            sigma = float(np.median(vals)) if vals else 0.0
            noise_curve.append({"lum": mid, "sigma": sigma})

        # --- 3. Contraste local (proxy para sharpening do ISP) ---
        lap_vars = []
        for p in photos:
            gray = cv2.cvtColor(p, cv2.COLOR_BGR2GRAY)
            lap = cv2.Laplacian(gray, cv2.CV_64F)
            lap_vars.append(float(lap.var()))

        # --- 4. Estatística de croma (saturação média HSV) ---
        sats = []
        for p in photos:
            hsv = cv2.cvtColor(p, cv2.COLOR_BGR2HSV)
            sats.append(float(hsv[:, :, 1].mean()))

        return {
            "version": CameraProfile.VERSION,
            "name": name,
            "num_photos": len(photos),
            "lab": lab_stats,
            "noise_curve": noise_curve,
            "laplacian_var_median": float(np.median(lap_vars)),
            "hsv_sat_mean": float(np.median(sats)),
        }

    @staticmethod
    def apply(img_bgr, profile, strength=1.0):
        """Aplica o perfil à imagem. strength 0=no-op, 1=full, >1=overshoot."""
        if strength <= 0:
            return img_bgr

        h, w = img_bgr.shape[:2]
        img = img_bgr.astype(np.float32)

        # --- 1. Color/tone matching em Lab (Reinhard) ---
        lab = cv2.cvtColor(np.clip(img, 0, 255).astype(np.uint8),
                           cv2.COLOR_BGR2LAB).astype(np.float32)
        for i, ch in enumerate(["L", "a", "b"]):
            stats = profile["lab"][ch]
            src_mean = float(lab[:, :, i].mean())
            src_std = float(lab[:, :, i].std())
            tgt_mean = stats["mean"]
            tgt_std = stats["std"]
            if src_std > 0.5:
                normalized = (lab[:, :, i] - src_mean) / src_std
                remapped = normalized * tgt_std + tgt_mean
                lab[:, :, i] = lab[:, :, i] * (1.0 - strength) + remapped * strength
        img = cv2.cvtColor(np.clip(lab, 0, 255).astype(np.uint8),
                           cv2.COLOR_LAB2BGR).astype(np.float32)

        # --- 2. Saturação (matching HSV S médio) ---
        if "hsv_sat_mean" in profile:
            hsv = cv2.cvtColor(np.clip(img, 0, 255).astype(np.uint8),
                               cv2.COLOR_BGR2HSV).astype(np.float32)
            src_sat = float(hsv[:, :, 1].mean())
            tgt_sat = profile["hsv_sat_mean"]
            if src_sat > 1.0:
                ratio = (tgt_sat / src_sat)
                adjusted = ratio ** strength  # interpolação geométrica
                hsv[:, :, 1] = np.clip(hsv[:, :, 1] * adjusted, 0, 255)
                img = cv2.cvtColor(hsv.astype(np.uint8),
                                   cv2.COLOR_HSV2BGR).astype(np.float32)

        # --- 3. Ruído de sensor calibrado (a parte mais importante) ---
        if "noise_curve" in profile and profile["noise_curve"]:
            curve = profile["noise_curve"]
            lums = np.array([n["lum"] for n in curve], dtype=np.float32)
            sigmas = np.array([n["sigma"] for n in curve], dtype=np.float32)

            # Reamostra para 256 níveis de L
            grid = np.linspace(0, 255, 256)
            sigma_table = np.interp(grid, lums, sigmas).astype(np.float32)

            gray = cv2.cvtColor(np.clip(img, 0, 255).astype(np.uint8),
                                cv2.COLOR_BGR2GRAY)
            sigma_map = sigma_table[gray]

            # Ruído correlacionado espacialmente (não branco puro)
            # Gera em baixa res e upscale → cria correlação espacial
            # característica de sensores CMOS reais (PRNU + read noise)
            low_h, low_w = max(1, h // 2), max(1, w // 2)
            low_noise = np.random.normal(0, 1.0, (low_h, low_w, 3)).astype(np.float32)
            up_noise = cv2.resize(low_noise, (w, h), interpolation=cv2.INTER_CUBIC)

            # Modulação por sigma local. Fator 0.7 evita overshoot.
            img += up_noise * sigma_map[:, :, np.newaxis] * strength * 0.7

        return np.clip(img, 0, 255).astype(np.uint8)

    # ---- Persistência ----

    @staticmethod
    def save(profile, path):
        Path(path).write_text(json.dumps(profile, indent=2))

    @staticmethod
    def load(path):
        data = json.loads(Path(path).read_text())
        if data.get("version", 1) < 2:
            print(f"[aviso] Perfil '{path}' é v{data.get('version', 1)}. "
                  "Recomendado re-extrair para usar a v2 (melhor precisão de ruído).")
        return data

    # ---- Info ----

    @staticmethod
    def print_info(profile):
        print(f"Perfil: {profile['name']} (v{profile.get('version', 1)})")
        print(f"Fotos usadas: {profile['num_photos']}")
        print("\n── Lab stats ──")
        for ch in ["L", "a", "b"]:
            s = profile["lab"][ch]
            print(f"  {ch}: mean={s['mean']:6.1f}  std={s['std']:5.1f}  "
                  f"p5={s['p5']:6.1f}  p50={s['p50']:6.1f}  p95={s['p95']:6.1f}")

        if "hsv_sat_mean" in profile:
            print(f"\nSaturação HSV média: {profile['hsv_sat_mean']:.1f}")

        print("\n── Curva de ruído (L → σ) ──")
        for n in profile.get("noise_curve", []):
            bar = "█" * max(0, int(n["sigma"] * 6))
            print(f"  L={n['lum']:6.1f}  σ={n['sigma']:.3f}  {bar}")

        print(f"\nLaplacian var (sharpening proxy): "
              f"{profile.get('laplacian_var_median', 0):.1f}")

    @staticmethod
    def compare(p1, p2):
        """Compara dois perfis lado a lado."""
        print(f"{'Métrica':<28} {p1['name'][:20]:<22} {p2['name'][:20]:<22}")
        print("─" * 74)
        for ch in ["L", "a", "b"]:
            for k in ["mean", "std"]:
                v1 = p1["lab"][ch][k]
                v2 = p2["lab"][ch][k]
                diff = v2 - v1
                mark = "←" if abs(diff) > 3 else " "
                print(f"{ch}.{k:<25} {v1:>10.1f}{'':<10} {v2:>10.1f}"
                      f"   Δ={diff:+.1f} {mark}")

        print(f"{'Laplacian var':<28} "
              f"{p1.get('laplacian_var_median', 0):>20.1f} "
              f"{p2.get('laplacian_var_median', 0):>20.1f}")

        if "hsv_sat_mean" in p1 and "hsv_sat_mean" in p2:
            print(f"{'HSV sat mean':<28} "
                  f"{p1['hsv_sat_mean']:>20.1f} {p2['hsv_sat_mean']:>20.1f}")


# =====================================================================
# CLI
# =====================================================================

def main():
    ap = argparse.ArgumentParser(
        description="Camera Profiling Tool — extraia e aplique assinatura de câmera real",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # Extrair perfil de 20 fotos do iPhone
  python camera_profile.py extract fotos_iphone/ -o iphone15pm.json -n "iPhone 15 Pro Max"

  # Aplicar em imagem de IA
  python camera_profile.py apply minha_ia.jpg -p iphone15pm.json -o saida.jpg

  # Aplicar com força reduzida (75%)
  python camera_profile.py apply minha_ia.jpg -p iphone15pm.json -o saida.jpg -s 0.75

  # Ver info do perfil
  python camera_profile.py info iphone15pm.json

  # Comparar dois perfis (ex.: iPhone vs Samsung)
  python camera_profile.py compare iphone15pm.json samsung_s26.json
        """)

    sub = ap.add_subparsers(dest="cmd", required=True)

    # extract
    p_ext = sub.add_parser("extract", help="Extrair perfil de fotos reais")
    p_ext.add_argument("input", help="Pasta com fotos reais (ou arquivo único)")
    p_ext.add_argument("-o", "--output", required=True, help="Arquivo .json de saída")
    p_ext.add_argument("-n", "--name", default="custom", help="Nome do perfil")
    p_ext.add_argument("--max-dim", type=int, default=1024,
                       help="Dimensão máxima para normalização (default: 1024)")

    # apply
    p_app = sub.add_parser("apply", help="Aplicar perfil em imagem")
    p_app.add_argument("input", help="Imagem de entrada")
    p_app.add_argument("-p", "--profile", required=True, help="Arquivo .json do perfil")
    p_app.add_argument("-o", "--output", required=True, help="Imagem de saída")
    p_app.add_argument("-s", "--strength", type=float, default=1.0,
                       help="Força da aplicação (0-2, default 1.0)")
    p_app.add_argument("-q", "--quality", type=int, default=95,
                       help="Qualidade JPEG de saída (default: 95)")

    # info
    p_info = sub.add_parser("info", help="Mostrar info do perfil")
    p_info.add_argument("profile", help="Arquivo .json")

    # compare
    p_cmp = sub.add_parser("compare", help="Comparar dois perfis")
    p_cmp.add_argument("p1", help="Primeiro perfil .json")
    p_cmp.add_argument("p2", help="Segundo perfil .json")

    args = ap.parse_args()

    # Aviso de HEIC
    if not HEIC_SUPPORTED:
        print("[aviso] pillow-heif não instalado. Fotos .HEIC não serão lidas.")
        print("        Para suporte HEIC: pip install pillow-heif\n")

    if args.cmd == "extract":
        files = collect_images(args.input)
        if not files:
            print(f"Erro: nenhuma imagem encontrada em '{args.input}'")
            sys.exit(1)
        print(f"Coletadas {len(files)} imagens. Analisando...")
        try:
            profile = CameraProfile.extract(files, name=args.name,
                                            max_dim=args.max_dim, verbose=True)
        except ValueError as e:
            print(f"Erro: {e}")
            sys.exit(1)
        CameraProfile.save(profile, args.output)
        print(f"\n✓ Perfil salvo em {args.output}\n")
        CameraProfile.print_info(profile)

    elif args.cmd == "apply":
        try:
            profile = CameraProfile.load(args.profile)
        except FileNotFoundError:
            print(f"Erro: perfil não encontrado: {args.profile}")
            sys.exit(1)

        try:
            img = load_image(args.input)
        except Exception as e:
            print(f"Erro ao ler imagem: {e}")
            sys.exit(1)

        if img is None:
            print(f"Erro: não consegui ler {args.input}")
            sys.exit(1)

        print(f"Aplicando perfil '{profile['name']}' (strength={args.strength})...")
        out = CameraProfile.apply(img, profile, strength=args.strength)
        cv2.imwrite(args.output, out, [cv2.IMWRITE_JPEG_QUALITY, args.quality])
        print(f"✓ Salvo em {args.output}")

    elif args.cmd == "info":
        try:
            profile = CameraProfile.load(args.profile)
        except FileNotFoundError:
            print(f"Erro: arquivo não encontrado: {args.profile}")
            sys.exit(1)
        CameraProfile.print_info(profile)

    elif args.cmd == "compare":
        try:
            p1 = CameraProfile.load(args.p1)
            p2 = CameraProfile.load(args.p2)
        except FileNotFoundError as e:
            print(f"Erro: {e}")
            sys.exit(1)
        CameraProfile.compare(p1, p2)


if __name__ == "__main__":
    main()