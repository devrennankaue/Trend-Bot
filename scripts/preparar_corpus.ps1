param(
    [int]$Tamanho = 5000
)

$ErrorActionPreference = 'Stop'
$raiz = Split-Path -Parent $PSScriptRoot
$entrada = Join-Path $raiz 'data/raw/postagens_tiktok.csv'
$saida = Join-Path $raiz 'data/corpus_pesquisa_5000.csv'
$relatorio = Join-Path $raiz 'data/relatorio_corpus.md'
$campos = @('transcricaoVideo', 'descricaoVideo', 'resumo', 'nomeMusica', 'hashtags_postagem')
$ausentes = @{}
foreach ($campo in $campos) { $ausentes[$campo] = 0 }
$total = 0
$indexaveis = 0
$elegiveis = [System.Collections.Generic.List[object]]::new()
$ids = [System.Collections.Generic.HashSet[string]]::new()
$duplicados = 0
$semId = 0
$semData = 0
$semPais = 0
$semTema = 0
$idsInternos = [System.Collections.Generic.HashSet[string]]::new()
$meses = @{}
$hash = [System.Security.Cryptography.SHA256]::Create()

foreach ($registro in (Import-Csv -LiteralPath $entrada -Encoding UTF8)) {
    $total++
    foreach ($campo in $campos) {
        if (-not $registro.$campo -or $registro.$campo -eq 'NULL') { $ausentes[$campo]++ }
    }
    if ($registro.podeIndexar -eq '1') { $indexaveis++ }
    if (-not $registro.IDPostagemFonte -or $registro.IDPostagemFonte -eq 'NULL') { $semId++ }
    if ($registro.dataPublicacao -notmatch '^\d{4}-\d{2}-\d{2}') { $semData++ }
    if (-not $registro.usuario_pais -or $registro.usuario_pais -eq 'NULL') { $semPais++ }
    if (-not $registro.topico_principal -or $registro.topico_principal -eq 'NULL') { $semTema++ }
    if ($registro.IDPostagem -and $registro.IDPostagem -ne 'NULL') { [void]$idsInternos.Add($registro.IDPostagem) }

    $temTexto = (($registro.transcricaoVideo -and $registro.transcricaoVideo -ne 'NULL') -or
        ($registro.descricaoVideo -and $registro.descricaoVideo -ne 'NULL') -or
        ($registro.resumo -and $registro.resumo -ne 'NULL'))
    if ($registro.podeIndexar -ne '1' -or $registro.URL -notmatch '^https?://(www\.)?tiktok\.com/' -or
        $registro.siglaIdioma -ne 'PT' -or -not $registro.IDPostagemFonte -or
        $registro.IDPostagemFonte -eq 'NULL' -or $registro.dataPublicacao -notmatch '^\d{4}-\d{2}-\d{2}' -or
        -not $temTexto) { continue }

    if (-not $ids.Add($registro.IDPostagemFonte)) { $duplicados++; continue }
    $mes = $registro.dataPublicacao.Substring(0, 7)
    if (-not $meses.ContainsKey($mes)) { $meses[$mes] = 0 }
    $meses[$mes]++
    $bytes = [Text.Encoding]::UTF8.GetBytes($registro.IDPostagemFonte)
    $chave = [Convert]::ToHexString($hash.ComputeHash($bytes))
    $elegiveis.Add([pscustomobject]@{ Chave = $chave; Registro = $registro })
}
$hash.Dispose()

$selecionados = @($elegiveis | Sort-Object Chave | Select-Object -First $Tamanho)
if ($selecionados.Count -eq 0) { throw 'Nenhum vídeo elegível encontrado.' }
$colunas = @($selecionados[0].Registro.PSObject.Properties.Name)
$selecionados | ForEach-Object { $_.Registro } | Select-Object -Property $colunas |
    Export-Csv -LiteralPath $saida -Encoding UTF8 -NoTypeInformation

$linhas = @(
    '# Relatório do corpus de pesquisa',
    '',
    "Arquivo de origem: data/raw/postagens_tiktok.csv",
    "Registros no CSV: $total",
    "Marcados como indexáveis (`podeIndexar=1`): $indexaveis",
    "Elegíveis após filtros e remoção de duplicados: $($elegiveis.Count)",
    "Selecionados: $($selecionados.Count)",
    "IDs de origem ausentes no CSV: $semId",
    "IDs internos únicos no CSV: $($idsInternos.Count)",
    "Datas ausentes ou inválidas no CSV: $semData",
    "País do usuário ausente no CSV: $semPais",
    "Tema principal ausente no CSV: $semTema",
    "IDs de origem duplicados entre elegíveis: $duplicados",
    '',
    '## Campos ausentes no CSV completo'
)
foreach ($campo in $campos) { $linhas += "- ${campo}: $($ausentes[$campo])" }
$linhas += @('', '## Período dos elegíveis')
foreach ($mes in ($meses.Keys | Sort-Object)) { $linhas += "- ${mes}: $($meses[$mes])" }
$linhas += @(
    '',
    '## Critério de seleção',
    'Exige `podeIndexar=1`, URL do TikTok, idioma PT, ID de origem, data e pelo menos um de transcrição, descrição visual ou resumo. Remove duplicados pelo `IDPostagemFonte`. Ordena os elegíveis pelo SHA-256 desse ID e seleciona os primeiros 5.000 dessa ordem estável. A ordem do CSV não interfere na amostra.',
    '',
    'Idioma PT e URL do TikTok não comprovam que o criador ou público seja brasileiro. O campo `usuario_pais` deve ser auditado antes de afirmar esse recorte. O campo `topico_principal` não foi usado para estratificação temática porque está majoritariamente ausente.'
)
$linhas | Set-Content -LiteralPath $relatorio -Encoding UTF8
Write-Host "Corpus: $saida ($($selecionados.Count) vídeos)"
Write-Host "Relatório: $relatorio"
