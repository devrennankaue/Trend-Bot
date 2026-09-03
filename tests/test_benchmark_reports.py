"""
Testes unitários e de integração para a geração de relatórios de benchmark em Markdown.
"""
import os
import glob
import shutil
import unittest
from datetime import datetime

# Adiciona o diretório raiz ao path
import sys
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from benchmark.benchmark import (
    formatar_cabecalho_markdown,
    formatar_resumo_e_destaques_markdown,
    formatar_detalhes_perguntas_markdown,
    gerar_conteudo_markdown,
    exportar_para_markdown
)


class TestBenchmarkReports(unittest.TestCase):

    def setUp(self):
        self.sample_metadados = {
            "data_inicio": "2026-09-03 12:30:00",
            "data_fim": "2026-09-03 12:30:45",
            "duracao_total_segundos": 45.12,
            "gpu_info": "NVIDIA GeForce RTX 4060 Ti (16.0 GB VRAM)",
            "ram_total_gb": 32.0,
            "sistema_operacional": "Linux",
            "ollama_url": "http://localhost:11434",
            "modelo_embedding": "neuralmind/bert-base-portuguese-cased",
            "caminho_db": "/home/renan/LSI/Trend-Bot/data/chroma_db",
            "k_retrieval": 4,
            "fetch_k": 25,
            "keep_alive": "0",
            "total_perguntas": 2,
            "modelos": ["llama3", "mistral"]
        }

        self.sample_resumo = [
            {
                "modelo": "llama3",
                "tempo_medio": 2.50,
                "tempo_min": 2.10,
                "tempo_max": 2.90,
                "media_palavras": 60.0,
                "ram_media": 3.20,
                "vram_pico": 5.50,
                "taxa_sucesso": "2/2",
                "erros": 0
            },
            {
                "modelo": "mistral",
                "tempo_medio": 3.80,
                "tempo_min": 3.20,
                "tempo_max": 4.40,
                "media_palavras": 55.0,
                "ram_media": 3.10,
                "vram_pico": 4.80,
                "taxa_sucesso": "2/2",
                "erros": 0
            }
        ]

        self.sample_resultados = [
            {
                "timestamp": "2026-09-03 12:30:10",
                "modelo": "llama3",
                "pergunta": "Quais são as músicas em alta?",
                "resposta": "As músicas em alta incluem sertanejo e pop viral.",
                "contexto": "Vídeo ID 123: música sertaneja em alta.",
                "tempo_segundos": 2.10,
                "ram_usada_gb": 3.20,
                "vram_usada_gb": 5.50,
                "qtd_palavras": 8,
                "qtd_caracteres": 52
            },
            {
                "timestamp": "2026-09-03 12:30:20",
                "modelo": "llama3",
                "pergunta": "Qual a capital da França?",
                "resposta": "Com base no corpus atual, não há informações.",
                "contexto": "Nenhum contexto recuperado.",
                "tempo_segundos": 2.90,
                "ram_usada_gb": 3.20,
                "vram_usada_gb": 5.40,
                "qtd_palavras": 8,
                "qtd_caracteres": 48
            },
            {
                "timestamp": "2026-09-03 12:30:30",
                "modelo": "mistral",
                "pergunta": "Quais são as músicas em alta?",
                "resposta": "Remixes e pop nacional.",
                "contexto": "Vídeo ID 123: música sertaneja em alta.",
                "tempo_segundos": 3.80,
                "ram_usada_gb": 3.10,
                "vram_usada_gb": 4.80,
                "qtd_palavras": 4,
                "qtd_caracteres": 23
            }
        ]

        self.test_reports_dir = os.path.join(os.path.dirname(__file__), "temp_test_reports")

    def tearDown(self):
        if os.path.exists(self.test_reports_dir):
            shutil.rmtree(self.test_reports_dir)

    def test_formatar_cabecalho_markdown(self):
        """BMD-02: Verifica inclusão de metadados de hardware, timestamps e RAG no cabeçalho."""
        cabecalho = formatar_cabecalho_markdown(self.sample_metadados)
        self.assertIn("# 📊 Relatório de Benchmark — TrendBot-BR", cabecalho)
        self.assertIn("2026-09-03 12:30:00", cabecalho)
        self.assertIn("45.12s", cabecalho)
        self.assertIn("NVIDIA GeForce RTX 4060 Ti", cabecalho)
        self.assertIn("neuralmind/bert-base-portuguese-cased", cabecalho)
        self.assertIn("MMR, k=4", cabecalho)

    def test_formatar_cabecalho_cpu_fallback(self):
        """BMD-02 / Edge Case: Verifica fallback gracioso de hardware para CPU-only."""
        meta_cpu = dict(self.sample_metadados)
        meta_cpu["gpu_info"] = "N/A (CPU-only)"
        cabecalho = formatar_cabecalho_markdown(meta_cpu)
        self.assertIn("N/A (CPU-only)", cabecalho)

    def test_formatar_resumo_e_destaques_markdown(self):
        """BMD-03, BMD-07: Verifica geração da tabela de resumo e destaques de performance."""
        resumo_md = formatar_resumo_e_destaques_markdown(self.sample_resumo)
        self.assertIn("| **llama3** | 2.50s |", resumo_md)
        self.assertIn("| **mistral** | 3.80s |", resumo_md)
        self.assertIn("🚀 **Modelo Mais Rápido:** `llama3`", resumo_md)
        self.assertIn("🧠 **Menor Consumo de VRAM:** `mistral`", resumo_md)
        self.assertIn("🎯 **Estabilidade:** 100% de sucesso", resumo_md)

    def test_formatar_detalhes_perguntas_markdown(self):
        """BMD-04: Verifica formatação detalhada por pergunta, tags colapsáveis e avaliação humana."""
        detalhes_md = formatar_detalhes_perguntas_markdown(["llama3", "mistral"], self.sample_resultados)
        self.assertIn("### 🤖 Modelo: `llama3`", detalhes_md)
        self.assertIn("[Q1/2] \"Quais são as músicas em alta?\"", detalhes_md)
        self.assertIn("<details>", detalhes_md)
        self.assertIn("<summary>📂 Ver Contexto RAG Recuperado", detalhes_md)
        self.assertIn("</details>", detalhes_md)
        self.assertIn("[ ] Fidelidade (1-5): `___`", detalhes_md)
        self.assertIn("[ ] Eficácia (1-5): `___`", detalhes_md)

    def test_exportar_para_markdown_e_preservacao(self):
        """BMD-01, BMD-05, BMD-06: Verifica criação de arquivo único timestamped e latest.md sem sobrescrever antigos."""
        caminho_1 = exportar_para_markdown(
            self.sample_metadados,
            self.sample_resumo,
            self.sample_resultados,
            pasta_reports=self.test_reports_dir
        )
        self.assertTrue(os.path.exists(caminho_1))
        
        caminho_latest = os.path.join(self.test_reports_dir, "latest.md")
        self.assertTrue(os.path.exists(caminho_latest))

        with open(caminho_1, "r", encoding="utf-8") as f:
            conteudo_1 = f.read()
        with open(caminho_latest, "r", encoding="utf-8") as f:
            conteudo_latest = f.read()

        self.assertEqual(conteudo_1, conteudo_latest)
        self.assertIn("Relatório de Benchmark — TrendBot-BR", conteudo_1)

        # Executa uma segunda exportação (com timestamp ou chamada sequencial)
        import time
        time.sleep(1.1)
        caminho_2 = exportar_para_markdown(
            self.sample_metadados,
            self.sample_resumo,
            self.sample_resultados,
            pasta_reports=self.test_reports_dir
        )
        self.assertTrue(os.path.exists(caminho_2))
        self.assertNotEqual(caminho_1, caminho_2, "O segundo benchmark deve gerar um arquivo com nome único")
        self.assertTrue(os.path.exists(caminho_1), "O primeiro relatório NÃO deve ser deletado ou sobrescrito")


if __name__ == "__main__":
    unittest.main()
