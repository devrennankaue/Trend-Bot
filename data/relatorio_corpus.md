# Relatório do corpus de pesquisa

Arquivo de origem: data/raw/postagens_tiktok.csv
Registros no CSV: 29537
Marcados como indexáveis (podeIndexar=1): 9082
Elegíveis após filtros e remoção de duplicados: 9082
Selecionados: 5000
IDs de origem ausentes no CSV: 112
IDs internos únicos no CSV: 29499
Datas ausentes ou inválidas no CSV: 157
País do usuário ausente no CSV: 29517
Tema principal ausente no CSV: 22948
IDs de origem duplicados entre elegíveis: 0

## Campos ausentes no CSV completo
- transcricaoVideo: 5557
- descricaoVideo: 111
- resumo: 7340
- nomeMusica: 165
- hashtags_postagem: 29514

## Período dos elegíveis
- 2026-02: 5
- 2026-03: 1819
- 2026-04: 7209
- 2026-05: 49

## Critério de seleção
Exige `podeIndexar=1`, URL do TikTok, idioma PT, ID de origem, data e pelo menos um de transcrição, descrição visual ou resumo. Remove duplicados pelo `IDPostagemFonte`. Ordena os elegíveis pelo SHA-256 desse ID e seleciona os primeiros 5.000 dessa ordem estável. A ordem do CSV não interfere na amostra.

Idioma PT e URL do TikTok não comprovam que o criador ou público seja brasileiro. O campo `usuario_pais` deve ser auditado antes de afirmar esse recorte. O campo `topico_principal` não foi usado para estratificação temática porque está majoritariamente ausente.
