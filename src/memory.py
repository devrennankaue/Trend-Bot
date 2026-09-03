import os
import gc
import time
import json
import ctypes
import subprocess
import urllib.request
import urllib.error
from typing import Dict, Optional

try:
    import torch
except ImportError:
    torch = None


def limpar_memoria_gpu(model_name: Optional[str] = None, ollama_url: str = "http://localhost:11434"):
    """
    Otimização de Hardware para NVIDIA RTX 4060 Ti e processadores modernos:
    1. Descarrega o modelo Ollama especificado da VRAM via HTTP (keep_alive: 0).
    2. Consulta o endpoint /api/ps para descarregar qualquer modelo residual ativo.
    3. Executa coleta de lixo do Python (gc.collect).
    4. Esvazia o cache de tensores alocados no PyTorch (torch.cuda.empty_cache).
    """
    if model_name:
        try:
            req_data = json.dumps({"model": model_name, "keep_alive": 0}).encode("utf-8")
            req = urllib.request.Request(
                f"{ollama_url}/api/generate",
                data=req_data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=5):
                pass
        except Exception:
            pass

    try:
        req_ps = urllib.request.Request(f"{ollama_url}/api/ps", method="GET")
        with urllib.request.urlopen(req_ps, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            for m in data.get("models", []):
                active_model = m.get("name") or m.get("model")
                if active_model:
                    req_data = json.dumps({"model": active_model, "keep_alive": 0}).encode("utf-8")
                    req = urllib.request.Request(
                        f"{ollama_url}/api/generate",
                        data=req_data,
                        headers={"Content-Type": "application/json"},
                        method="POST"
                    )
                    with urllib.request.urlopen(req, timeout=5):
                        pass
    except Exception:
        pass

    gc.collect()

    if torch is not None and torch.cuda.is_available():
        torch.cuda.empty_cache()
        if hasattr(torch.cuda, "ipc_collect"):
            try:
                torch.cuda.ipc_collect()
            except Exception:
                pass

    time.sleep(0.5)


def obter_metricas_memoria() -> Dict[str, float]:
    """Retorna o consumo atual de RAM do sistema e VRAM da GPU NVIDIA em GB."""
    ram_usada_gb = 0.0
    ram_total_gb = 0.0

    # Coleta de RAM (compatível com Linux e Windows)
    try:
        if os.name == 'nt':
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]
            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
            ram_usada_gb = round((stat.ullTotalPhys - stat.ullAvailPhys) / (1024**3), 2)
            ram_total_gb = round(stat.ullTotalPhys / (1024**3), 2)
        else:
            with open("/proc/meminfo", "r") as f:
                meminfo = {}
                for line in f:
                    parts = line.split(":")
                    if len(parts) == 2:
                        key = parts[0].strip()
                        val = parts[1].strip().split()[0]
                        meminfo[key] = int(val)
                total_kb = meminfo.get("MemTotal", 0)
                available_kb = meminfo.get("MemAvailable", 0)
                ram_total_gb = round(total_kb / (1024**2), 2)
                ram_usada_gb = round((total_kb - available_kb) / (1024**2), 2)
    except Exception:
        pass

    # Coleta de VRAM NVIDIA
    vram_usada_mb = 0.0
    vram_total_mb = 0.0
    try:
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,nounits,noheader"],
            encoding="utf-8",
            startupinfo=startupinfo,
            stderr=subprocess.DEVNULL
        )
        parts = out.strip().split(",")
        if len(parts) == 2:
            vram_usada_mb = float(parts[0].strip())
            vram_total_mb = float(parts[1].strip())
    except Exception:
        pass

    return {
        "ram_usada_gb": ram_usada_gb,
        "ram_total_gb": ram_total_gb,
        "vram_usada_gb": round(vram_usada_mb / 1024, 2),
        "vram_total_gb": round(vram_total_mb / 1024, 2)
    }
