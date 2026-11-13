# OCR do Windows (Windows.Media.Ocr, embutido no sistema) para o visao.py no PC: a versão Windows do visao.swift.
# Só texto (o Windows não tem detector de rosto e mãos embutido): rostos = [], maos = 0.
#   powershell -NoProfile -ExecutionPolicy Bypass -File visao_win.ps1 <lista.txt>
#   lista.txt = um caminho de imagem por linha (UTF-8). Saída: uma linha JSON por imagem (UTF-8), igual ao visao.swift:
#   {"arquivo":..., "rostos":[], "textos":[{"t":..,"c":1.0,"b":[x,y,w,h]}...], "maos":0}
# Caixas em fração do quadro, origem no canto de CIMA à esquerda. Uma caixa por linha de texto (união das palavras).
param([string]$Lista)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]
function Await($op, $tipo) {
    $t = $asTaskGeneric.MakeGenericMethod($tipo).Invoke($null, @($op)); $t.Wait(-1) | Out-Null; $t.Result
}
[void][Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime]
[void][Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime]
[void][Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics, ContentType = WindowsRuntime]
[void][Windows.Storage.Streams.IRandomAccessStream, Windows.Storage.Streams, ContentType = WindowsRuntime]
$motor = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
if (-not $motor) { Write-Error 'sem idioma de OCR instalado no Windows'; exit 2 }
function R4($v) { [math]::Round([double]$v, 4) }
foreach ($p in [System.IO.File]::ReadAllLines($Lista, [System.Text.Encoding]::UTF8)) {
    if (-not $p.Trim()) { continue }
    $saida = [ordered]@{ arquivo = $p; rostos = @(); textos = @(); maos = 0 }
    try {
        $arq = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($p)) ([Windows.Storage.StorageFile])
        $st = Await ($arq.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
        $dec = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($st)) ([Windows.Graphics.Imaging.BitmapDecoder])
        $bmp = Await ($dec.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
        $LARG = [double]$bmp.PixelWidth; $ALT = [double]$bmp.PixelHeight
        $res = Await ($motor.RecognizeAsync($bmp)) ([Windows.Media.Ocr.OcrResult])
        $tx = @()
        foreach ($ln in $res.Lines) {
            $x0 = 1e9; $y0 = 1e9; $x1 = -1e9; $y1 = -1e9
            foreach ($pal in $ln.Words) {
                $r = $pal.BoundingRect
                if ($r.X -lt $x0) { $x0 = $r.X }; if ($r.Y -lt $y0) { $y0 = $r.Y }
                if ($r.X + $r.Width -gt $x1) { $x1 = $r.X + $r.Width }; if ($r.Y + $r.Height -gt $y1) { $y1 = $r.Y + $r.Height }
            }
            if ($x1 -le $x0) { continue }
            $tx += [ordered]@{ t = $ln.Text; c = 1.0; b = @((R4 ($x0 / $LARG)), (R4 ($y0 / $ALT)), (R4 (($x1 - $x0) / $LARG)), (R4 (($y1 - $y0) / $ALT))) }
        }
        $saida.textos = $tx
        $st.Dispose(); $bmp.Dispose()
    } catch { $saida['erro'] = "nao abri: $($_.Exception.Message)" }
    $saida | ConvertTo-Json -Compress -Depth 5
}
