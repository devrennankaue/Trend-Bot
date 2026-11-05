# Comparação exploratória de gêneros e engajamento

O TrendBot responde a perguntas como “Qual gênero de vídeo tem maior taxa de
engajamento?” com uma comparação calculada no `data/corpus_pesquisa_5000.csv`.
O resultado é exploratório: o campo `classificacao_conteudo` está vazio nesse
corpus, e os grupos abaixo são criados por regras textuais.

## Como os grupos são formados

O código em `src/genre_analysis.py` procura termos em `assuntos_llm`, nos
primeiros 250 caracteres de `postagem` e nos primeiros 400 caracteres de
`resumo`. Quando não existe resumo, usa o início de `descricaoVideo`. A busca
ignora diferenças entre maiúsculas e minúsculas e entre letras com e sem
acento. Um vídeo pode entrar em mais de um grupo.

| Grupo | Exemplos de termos usados |
| --- | --- |
| Humor e memes | humor, comédia, piada, meme, engraçado |
| Esportes | esporte, futebol, atleta, Copa do Mundo, basquete, vôlei |
| Culinária | receita, culinária, cozinha, bolo, ingrediente |
| Beleza e moda | maquiagem, skincare, beleza, moda, look, cabelo, roupa |
| Música e dança | cantor, cantora, dançando, coreografia, clipe |
| Cinema e séries | filme, série, novela, cinema, k-drama, Netflix |
| Notícias e política | notícia, política, governo, eleição, Congresso, STF |
| Games | game, gamer, gameplay, Minecraft, Free Fire, videogame |
| Saúde | saúde, médico, doença, vacina, hospital, tratamento |
| Animais | cachorro, gato, pet, cão, animal, cavalo |

A tabela resume as regras. Os padrões exatos e a ordem de execução ficam em
`src/genre_analysis.py`.

## Como o ranking é calculado

1. Leia a `taxaEngajamento_mais_recente` de cada vídeo com valor não negativo.
2. Atribua os grupos pelas regras textuais.
3. Exclua do ranking grupos com menos de 40 vídeos.
4. Ordene os demais pela mediana da taxa; mostre também a média e o tamanho
   de cada grupo.

O mínimo de 40 vídeos evita que um grupo muito pequeno lidere o ranking por
acaso. Nesta análise, “gênero” ou “estilo” significa tema amplo do conteúdo,
não formato audiovisual como POV ou tutorial.

Nos 5.000 registros atuais, a taxa corresponde, com arredondamento, a
`(curtidas + comentários + compartilhamentos + salvamentos) / visualizações × 100`.
A comparação usa a mediana para reduzir o efeito de vídeos com taxas extremas.

Na auditoria de 4 de novembro de 2026, 3.646 dos 5.000 vídeos receberam ao
menos um grupo pelas regras. “Humor e memes” ficou em primeiro entre os
grupos elegíveis: 978 vídeos, mediana de 9,857% e média de 11,345%. Os valores
mudam se o corpus ou as regras mudarem.

## Limitações

- A presença de um termo não confirma o gênero principal do vídeo. Os
  rótulos precisam de revisão humana antes de sustentar conclusões finais da
  pesquisa.
- Os grupos se sobrepõem. A soma das quantidades por grupo pode ultrapassar
  o número de vídeos classificados.
- A comparação descreve associação no corpus selecionado. Ela não demonstra
  que um gênero causa mais engajamento no TikTok brasileiro.
- O ranking usa a coleta mais recente disponível no CSV; não mede crescimento
  ao longo do tempo.
