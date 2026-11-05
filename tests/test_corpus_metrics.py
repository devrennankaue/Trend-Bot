"""Resultados calculados diretamente no corpus selecionado."""
import csv
import os
import tempfile
import unittest

from src.corpus_metrics import CorpusMetrics


class TestCorpusMetrics(unittest.TestCase):
    def setUp(self):
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8", newline="") as fixture:
            self.path = fixture.name
            writer = csv.DictWriter(fixture, fieldnames=["IDPostagem", "IDPostagemFonte", "plays_mais_recente",
                                                       "taxaEngajamento_mais_recente", "classificacao_conteudo",
                                                       "curtidas_mais_recente", "comentarios_mais_recente",
                                                       "compartilhamentos_mais_recente", "hashtags_postagem", "nomeMusica",
                                                       "resumo", "postagem"])
            writer.writeheader()
            writer.writerows([
                {"IDPostagem": "1", "IDPostagemFonte": "111", "plays_mais_recente": "10",
                 "taxaEngajamento_mais_recente": "2.5", "curtidas_mais_recente": "9",
                 "comentarios_mais_recente": "1", "compartilhamentos_mais_recente": "2", "nomeMusica": "Som A",
                 "resumo": "Homem conta uma piada. O vídeo tem cortes rápidos, gerando identificação. O apelo viral é alto.",
                 "postagem": "Trecho de comédia na Netflix."},
                {"IDPostagem": "2", "IDPostagemFonte": "222", "plays_mais_recente": "30",
                 "taxaEngajamento_mais_recente": "1.5", "curtidas_mais_recente": "3",
                 "comentarios_mais_recente": "7", "compartilhamentos_mais_recente": "1", "nomeMusica": "Som A"},
                {"IDPostagem": "3", "IDPostagemFonte": "333", "plays_mais_recente": "20",
                 "taxaEngajamento_mais_recente": "3.5", "curtidas_mais_recente": "4",
                 "comentarios_mais_recente": "2", "compartilhamentos_mais_recente": "8", "nomeMusica": "Som B",
                 "resumo": "Comédia visual com reação inesperada. A atriz faz uma expressão engraçada.",
                 "postagem": "Cena de série da Netflix."},
            ])
        self.metrics = CorpusMetrics(self.path)

    def tearDown(self):
        os.unlink(self.path)

    def test_contagem_usa_todas_as_linhas(self):
        self.assertEqual(self.metrics.answer("Quantos vídeos há no corpus?"),
                         "O corpus de pesquisa selecionado contém 3 vídeos.")

    def test_visualizacoes_usa_id_do_tiktok_e_maior_valor(self):
        answer = self.metrics.answer("Qual vídeo tem mais visualizações?")
        self.assertIn("[Vídeo ID: 222]", answer)
        self.assertIn("30 visualizações", answer)
        self.assertIn("3 de 3 vídeos", answer)

    def test_engajamento_usa_taxa_e_nao_infere_causa(self):
        answer = self.metrics.answer("Qual vídeo tem maior engajamento?")
        self.assertIn("[Vídeo ID: 333]", answer)
        self.assertIn("taxa de engajamento de 3,500", answer)
        self.assertIn("não demonstra o que causa engajamento", answer)

    def test_ranking_plural_retorna_mais_de_um_video(self):
        answer = self.metrics.answer("Quais vídeos têm mais visualizações?")
        self.assertLess(answer.index("[Vídeo ID: 222]"), answer.index("[Vídeo ID: 333]"))
        self.assertLess(answer.index("[Vídeo ID: 333]"), answer.index("[Vídeo ID: 111]"))

    def test_curtidas_comentarios_e_compartilhamentos_usam_csv_inteiro(self):
        self.assertIn("[Vídeo ID: 111]", self.metrics.answer("Qual vídeo tem mais curtidas?"))
        self.assertIn("[Vídeo ID: 222]", self.metrics.answer("Qual vídeo tem mais comentários?"))
        self.assertIn("[Vídeo ID: 333]", self.metrics.answer("Qual vídeo tem mais compartilhamentos?"))

    def test_media_e_calculada_sobre_todos_os_valores(self):
        answer = self.metrics.answer("Qual a média de visualizações dos vídeos?")
        self.assertIn("média de visualizações", answer)
        self.assertIn("20", answer)
        self.assertIn("3 de 3 vídeos", answer)

    def test_comparacao_de_generos_exige_grupos_minimos(self):
        answer = self.metrics.answer("Qual tipo de vídeo gera mais engajamento no TikTok?")
        self.assertIn("Não há grupos de conteúdo com pelo menos 40 vídeos", answer)
        self.assertNotIn("[Vídeo ID:", answer)

    def test_parafrases_preservam_pergunta_sobre_categorias(self):
        perguntas = [
            "Que formato de conteúdo consegue mais interações?",
            "Qual tema costuma performar melhor?",
            "Quais estilos de vídeo viralizam mais?",
            "Que conteúdo rende mais curtidas?",
        ]
        for pergunta in perguntas:
            with self.subTest(pergunta=pergunta):
                answer = self.metrics.answer(pergunta)
                self.assertIn("Não é possível comparar tipos de vídeo", answer)
                self.assertIn("classificar os vídeos por tipo", answer)

    def test_genero_e_estilo_usam_o_mesmo_calculo_de_engajamento(self):
        for question in ("Qual gênero de vídeo gera mais engajamento?",
                         "Qual gênero/estilo de vídeo gera mais engajamento?",
                         "Qual estilo de vídeo engaja mais?"):
            with self.subTest(question=question):
                self.assertIn("pelo menos 40 vídeos", self.metrics.answer(question))

    def test_classificacao_provisoria_responde_com_mediana_e_cobertura(self):
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8", newline="") as fixture:
            path = fixture.name
            writer = csv.DictWriter(fixture, fieldnames=["IDPostagemFonte", "resumo", "taxaEngajamento_mais_recente"])
            writer.writeheader()
            writer.writerows({"IDPostagemFonte": str(index), "resumo": "Piada de humor com meme.",
                              "taxaEngajamento_mais_recente": "10"} for index in range(40))
            writer.writerows({"IDPostagemFonte": str(index), "resumo": "Gameplay de Minecraft.",
                              "taxaEngajamento_mais_recente": "5"} for index in range(40, 80))
            writer.writerow({"IDPostagemFonte": "80", "resumo": "Cena sem gênero definido.",
                             "taxaEngajamento_mais_recente": "99"})
        try:
            answer = CorpusMetrics(path).answer("Qual gênero de vídeo tem maior engajamento?")
        finally:
            os.unlink(path)

        self.assertIn("Humor e memes: 40 vídeos; mediana 10,000%", answer)
        self.assertIn("Games: 40 vídeos; mediana 5,000%", answer)
        self.assertIn("cobriu 80 de 81 vídeos", answer)
        self.assertIn("não uma prova de que o gênero causa engajamento", answer)

    def test_hashtags_ausentes_nao_geram_ranking(self):
        self.assertEqual(self.metrics.answer("Quais hashtags são mais frequentes?"),
                         "Não há hashtags de postagens preenchidas nos 3 vídeos do corpus selecionado.")

    def test_musicas_usam_frequencia_de_todo_o_corpus(self):
        self.assertIn("Som A (2 vídeos)", self.metrics.answer("Quais músicas são mais frequentes?"))

    def test_musica_com_mais_visualizacoes_nao_confunde_frequencia(self):
        answer = self.metrics.answer("Qual música tem mais visualizações?")
        self.assertIn("comparação por hashtag ou música ainda não está definida", answer)
        self.assertNotIn("Som A (2 vídeos)", answer)

    def test_pergunta_descritiva_vai_para_o_rag(self):
        self.assertIsNone(self.metrics.answer("O que aparece visualmente no vídeo 222?"))

    def test_exemplos_usam_frases_completas_sem_promessa_de_viralidade(self):
        self.assertEqual(self.metrics.example_summaries(["111"]),
                         {"111": "Homem conta uma piada. O vídeo tem cortes rápidos."})

    def test_ranking_de_humor_filtra_resumo_e_explica_videos(self):
        answer = self.metrics.answer("Quais vídeos de humor têm mais visualizações e o que mostram?")

        self.assertLess(answer.index("[Vídeo ID: 333]"), answer.index("[Vídeo ID: 111]"))
        self.assertNotIn("[Vídeo ID: 222]", answer)
        self.assertIn("Comédia visual com reação inesperada.", answer)
        self.assertIn("critério provisório".capitalize(), answer)

    def test_ranking_de_humor_aceita_top_um(self):
        answer = self.metrics.answer("Top 1 vídeos de humor com mais views")

        self.assertIn("[Vídeo ID: 333]", answer)
        self.assertNotIn("[Vídeo ID: 111]", answer)

    def test_explicacao_de_humor_preserva_abreviacao_e_frase_relevante(self):
        row = {"resumo": "Neymar Jr. aparece em discussão durante uma partida. "
                         "A dublagem transforma a cena em humor. O apelo viral é alto."}

        self.assertEqual(self.metrics._factual_summary(row, focus_humor=True),
                         "Neymar Jr. aparece em discussão durante uma partida. "
                         "A dublagem transforma a cena em humor.")

    def test_pergunta_aberta_sobre_assunto_consulta_todo_o_corpus(self):
        answer = self.metrics.answer("O que estão falando sobre a Netflix no TikTok?")

        self.assertIn("Encontrei 2 vídeos que mencionam 'netflix'", answer)
        self.assertLess(answer.index("[Vídeo ID: 333]"), answer.index("[Vídeo ID: 111]"))
        self.assertNotIn("[Vídeo ID: 222]", answer)
        self.assertIn("Postagem: “Cena de série da Netflix.”", answer)
        self.assertIn("não resume opiniões dos comentários", answer)

    def test_assunto_sem_registros_recebe_resposta_especifica(self):
        self.assertEqual(self.metrics.answer("O que falam sobre astronomia no TikTok?"),
                         "Não encontrei menções a 'astronomia' nos textos dos 3 vídeos do corpus selecionado.")

    def test_pergunta_sobre_assunto_aceita_parafrase_sem_sobre(self):
        self.assertIn("Encontrei 2 vídeos", self.metrics.answer("O que falam da Netflix?"))

    def test_pergunta_especifica_com_sobre_continua_no_rag(self):
        self.assertIsNone(self.metrics.answer("Qual música aparece no vídeo sobre Netflix?"))


if __name__ == "__main__":
    unittest.main()
