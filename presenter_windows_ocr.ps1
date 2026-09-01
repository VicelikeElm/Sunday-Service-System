param(
    [Parameter(Mandatory=$true)]
    [string]$ManifestPath
)

$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.Runtime.WindowsRuntime

$null = [Windows.Storage.StorageFile, Windows.Storage, ContentType=WindowsRuntime]
$null = [Windows.Storage.FileAccessMode, Windows.Storage, ContentType=WindowsRuntime]
$null = [Windows.Storage.Streams.IRandomAccessStream, Windows.Storage.Streams, ContentType=WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics.Imaging, ContentType=WindowsRuntime]
$null = [Windows.Graphics.Imaging.SoftwareBitmap, Windows.Graphics.Imaging, ContentType=WindowsRuntime]
$null = [Windows.Media.Ocr.OcrEngine, Windows.Media.Ocr, ContentType=WindowsRuntime]
$null = [Windows.Media.Ocr.OcrResult, Windows.Media.Ocr, ContentType=WindowsRuntime]

$AsTaskGeneric = (
    [System.WindowsRuntimeSystemExtensions].GetMethods() |
    Where-Object {
        $_.Name -eq "AsTask" -and
        $_.IsGenericMethodDefinition -and
        $_.GetParameters().Count -eq 1
    } |
    Select-Object -First 1
)

function Await-WinRT(
    $Operation,
    [Type]$ResultType
) {
    $Method = $AsTaskGeneric.MakeGenericMethod($ResultType)
    $Task = $Method.Invoke($null, @($Operation))
    $Task.Wait()
    return $Task.Result
}

try {
    $Manifest = Get-Content -Path $ManifestPath -Raw | ConvertFrom-Json
    $Engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()

    if ($null -eq $Engine) {
        throw "Windows OCR is not available for the current Windows language."
    }

    $Results = @()

    foreach ($Item in $Manifest) {
        $Path = [string]$Item.path
        $Index = [int]$Item.index
        $Source = [string]$Item.source

        try {
            $File = Await-WinRT (
                [Windows.Storage.StorageFile]::GetFileFromPathAsync($Path)
            ) ([Windows.Storage.StorageFile])

            $Stream = Await-WinRT (
                $File.OpenAsync(
                    [Windows.Storage.FileAccessMode]::Read
                )
            ) ([Windows.Storage.Streams.IRandomAccessStream])

            $Decoder = Await-WinRT (
                [Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($Stream)
            ) ([Windows.Graphics.Imaging.BitmapDecoder])

            $Bitmap = Await-WinRT (
                $Decoder.GetSoftwareBitmapAsync()
            ) ([Windows.Graphics.Imaging.SoftwareBitmap])

            $OcrResult = Await-WinRT (
                $Engine.RecognizeAsync($Bitmap)
            ) ([Windows.Media.Ocr.OcrResult])

            $Results += [pscustomobject]@{
                index = $Index
                source = $Source
                success = $true
                text = [string]$OcrResult.Text
                error = ""
            }

            try {
                $Stream.Dispose()
            }
            catch {}
        }
        catch {
            $Results += [pscustomobject]@{
                index = $Index
                source = $Source
                success = $false
                text = ""
                error = [string]$_.Exception.Message
            }
        }
    }

    $Results | ConvertTo-Json -Compress -Depth 5
    exit 0
}
catch {
    [pscustomobject]@{
        success = $false
        error = [string]$_.Exception.Message
    } | ConvertTo-Json -Compress

    exit 1
}
