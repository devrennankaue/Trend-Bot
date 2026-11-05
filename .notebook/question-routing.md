# Roteamento de perguntas
> Métricas do corpus selecionado e respostas com fontes

Entry: `main.py:main()`
Flow: `main.py:main()` → `src/bot.py:TrendBot.ask()` → `src/corpus_metrics.py:CorpusMetrics.answer()` → RAG em `src/bot.py:TrendBot._answer()`.

- `src/corpus_metrics.py:CorpusMetrics.answer()` lê `data/corpus_pesquisa_5000.csv` para contagens e rankings; preserva `IDPostagemFonte` como ID público.
- `src/genre_analysis.py:compare_engagement()` cria grupos textuais provisórios e compara medianas de `taxaEngajamento_mais_recente`. Regras e limites em `docs/criterios-generos-engajamento.md`.
- `src/bot.py:TrendBot._answer()` recebe no máximo os trechos de `src/retriever.py`; eles não representam amostra estatística do corpus.
- Perguntas sobre formato típico usam exemplos observáveis. Se a LLM recusar ou não citar IDs válidos, `src/bot.py:TrendBot._pattern_examples()` mostra trechos recuperados; `src/retriever.py:TrendRetriever.find_examples()` complementa com busca textual quando a recuperação semântica não encontra o assunto.
- Para vídeos presentes no corpus selecionado, `src/corpus_metrics.py:CorpusMetrics.example_summaries()` fornece frases completas do resumo à resposta alternativa, removendo alegações de potencial de viralização.
- Ranking de vídeos com menção textual a humor por visualizações: `src/corpus_metrics.py:CorpusMetrics._humor_views_answer()`. Filtro provisório no início do resumo ou descrição visual, sem rótulo validado de conteúdo.
- Consultas abertas sobre assuntos usam `src/corpus_metrics.py:CorpusMetrics._topic_answer()` no CSV selecionado; a resposta cita exemplos e não interpreta comentários.
- `src/retriever.py:TrendRetriever.search()` combina até dois candidatos com correspondência lexical com a seleção semântica. Em 2026-11-04, a busca semântica sozinha perdeu o ID verificado `7629013107884444946` para desengasgo; a busca combinada o trouxe em primeiro lugar.
- `src/analytics.py:TrendAnalytics.answer()` é um caminho antigo separado, sem uso em `main.py`.
- `evaluation/perguntas_referencia.csv` inclui perguntas com IDs de fonte para recuperação e perguntas calculadas sem IDs de recuperação.
- No corpus selecionado de 2026-11-04, `classificacao_conteudo` e `hashtags_postagem` não têm valores preenchidos. Revalidar se o CSV mudar.

Updated: 2026-11-04
