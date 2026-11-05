"""Verifica regras reproduzíveis dos grupos de conteúdo."""
import unittest

from src.genre_analysis import classify_genres, compare_engagement


class TestGenreAnalysis(unittest.TestCase):
    def test_um_video_pode_ter_mais_de_um_genero(self):
        genres = classify_genres({"resumo": "Piada em uma partida de Minecraft."})

        self.assertIn("Humor e memes", genres)
        self.assertIn("Games", genres)

    def test_jogador_de_game_nao_vira_esporte_so_por_ser_jogador(self):
        genres = classify_genres({"resumo": "Jogador mostra uma partida de Minecraft."})

        self.assertIn("Games", genres)
        self.assertNotIn("Esportes", genres)

    def test_grupo_pequeno_fica_fora_do_ranking(self):
        rows = ([{"IDPostagemFonte": str(index), "resumo": "Piada de humor.",
                  "taxaEngajamento_mais_recente": "50"} for index in range(39)] +
                [{"IDPostagemFonte": str(index), "resumo": "Gameplay de Minecraft.",
                  "taxaEngajamento_mais_recente": "5"} for index in range(39, 79)])

        result = compare_engagement(rows)

        self.assertEqual([item["genre"] for item in result["results"]], ["Games"])
        self.assertEqual(result["labeled"], 79)


if __name__ == "__main__":
    unittest.main()
