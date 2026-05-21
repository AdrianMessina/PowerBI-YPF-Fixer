# ================================================================
# Power BI Fixer - Script de Empaquetado para Distribución
# ================================================================
# Versión: 2.0.1
# Fecha: 2026-05-19
# Propósito: Crear ZIP limpio sin venv ni archivos temporales
# ================================================================

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Power BI Fixer v2.0.1 - Empaquetador" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Configuración
$sourceDir = $PSScriptRoot
$parentDir = Split-Path $sourceDir -Parent
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$zipName = "PowerBI_Fixer_v2.0.1_$timestamp.zip"
$zipPath = Join-Path $parentDir $zipName

# Directorios y archivos a excluir
$excludePatterns = @(
    'venv',
    '__pycache__',
    '*.pyc',
    '*.pyo',
    '.git',
    '.gitignore',
    '.vscode',
    '.idea',
    '*.log',
    '.DS_Store',
    'Thumbs.db',
    '*.tmp',
    'package_for_distribution.ps1'  # No incluir este script
)

Write-Host "[1/4] Validando estructura..." -ForegroundColor Yellow

# Verificar archivos críticos
$criticalFiles = @(
    'requirements.txt',
    'README.md',
    'INSTALL.md',
    'Power BI Fixer.bat',
    'app.py'
)

$missing = @()
foreach ($file in $criticalFiles) {
    if (-not (Test-Path (Join-Path $sourceDir $file))) {
        $missing += $file
    }
}

if ($missing.Count -gt 0) {
    Write-Host "[ERROR] Archivos críticos faltantes:" -ForegroundColor Red
    $missing | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }
    Write-Host ""
    Write-Host "Abortando empaquetado." -ForegroundColor Red
    pause
    exit 1
}

Write-Host "[OK] Todos los archivos críticos presentes" -ForegroundColor Green
Write-Host ""

# Verificar que requirements.txt tiene el fix de numpy
Write-Host "[2/4] Verificando fix de NumPy..." -ForegroundColor Yellow
$reqContent = Get-Content (Join-Path $sourceDir "requirements.txt") -Raw
if ($reqContent -match "numpy\s*<\s*2\.0") {
    Write-Host "[OK] requirements.txt tiene numpy<2.0" -ForegroundColor Green
} else {
    Write-Host "[WARNING] requirements.txt NO tiene el fix de numpy<2.0" -ForegroundColor Yellow
    Write-Host "         La aplicación puede fallar en instalaciones nuevas." -ForegroundColor Yellow
}
Write-Host ""

Write-Host "[3/4] Creando archivo ZIP..." -ForegroundColor Yellow
Write-Host "Origen:  $sourceDir" -ForegroundColor Gray
Write-Host "Destino: $zipPath" -ForegroundColor Gray
Write-Host ""

# Crear ZIP temporal
$tempZip = Join-Path $env:TEMP "temp_pbi_fixer_$timestamp.zip"

try {
    # Obtener todos los archivos excepto excluidos
    $files = Get-ChildItem -Path $sourceDir -Recurse -File | Where-Object {
        $relativePath = $_.FullName.Substring($sourceDir.Length + 1)
        $exclude = $false

        foreach ($pattern in $excludePatterns) {
            if ($pattern.StartsWith('*')) {
                # Patrón de extensión
                if ($_.Name -like $pattern) {
                    $exclude = $true
                    break
                }
            } else {
                # Patrón de carpeta
                if ($relativePath -like "*$pattern*") {
                    $exclude = $true
                    break
                }
            }
        }

        -not $exclude
    }

    # Crear ZIP usando .NET
    Add-Type -Assembly System.IO.Compression.FileSystem
    $compression = [System.IO.Compression.CompressionLevel]::Optimal

    if (Test-Path $tempZip) {
        Remove-Item $tempZip -Force
    }

    $zip = [System.IO.Compression.ZipFile]::Open($tempZip, 'Create')

    $count = 0
    foreach ($file in $files) {
        $relativePath = $file.FullName.Substring($sourceDir.Length + 1)
        $entryName = "powerbi_analyzer_v2\$relativePath"

        [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
            $zip,
            $file.FullName,
            $entryName,
            $compression
        ) | Out-Null

        $count++
        if ($count % 50 -eq 0) {
            Write-Host "  Procesados $count archivos..." -ForegroundColor Gray
        }
    }

    $zip.Dispose()

    # Mover a destino final
    if (Test-Path $zipPath) {
        Remove-Item $zipPath -Force
    }
    Move-Item $tempZip $zipPath

    Write-Host "[OK] ZIP creado exitosamente" -ForegroundColor Green
    Write-Host "     Archivos incluidos: $count" -ForegroundColor Gray

} catch {
    Write-Host "[ERROR] Fallo al crear ZIP: $_" -ForegroundColor Red
    if (Test-Path $tempZip) {
        Remove-Item $tempZip -Force
    }
    pause
    exit 1
}

Write-Host ""
Write-Host "[4/4] Validando ZIP..." -ForegroundColor Yellow

# Validar contenido del ZIP
try {
    $zip = [System.IO.Compression.ZipFile]::OpenRead($zipPath)

    $zipSize = (Get-Item $zipPath).Length / 1MB
    Write-Host "Tamaño del ZIP: $([math]::Round($zipSize, 2)) MB" -ForegroundColor Gray

    # Verificar que no contiene venv
    $hasVenv = $zip.Entries | Where-Object { $_.FullName -like "*venv*" }
    if ($hasVenv) {
        Write-Host "[WARNING] El ZIP contiene archivos de venv (no debería)" -ForegroundColor Yellow
    } else {
        Write-Host "[OK] ZIP no contiene venv" -ForegroundColor Green
    }

    $zip.Dispose()

} catch {
    Write-Host "[WARNING] No se pudo validar el ZIP: $_" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "EMPAQUETADO COMPLETADO" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Archivo generado:" -ForegroundColor White
Write-Host "  $zipPath" -ForegroundColor Cyan
Write-Host ""
Write-Host "SIGUIENTE PASO:" -ForegroundColor Yellow
Write-Host "1. Probar el ZIP en una máquina limpia" -ForegroundColor White
Write-Host "2. Verificar que install.bat funciona" -ForegroundColor White
Write-Host "3. Distribuir a usuarios" -ForegroundColor White
Write-Host ""
Write-Host "Texto para email: Ver CHANGELOG_v2.0.1.md" -ForegroundColor Gray
Write-Host ""

# Abrir carpeta con el ZIP
Start-Process explorer.exe -ArgumentList "/select,`"$zipPath`""

Write-Host "Presiona cualquier tecla para salir..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
