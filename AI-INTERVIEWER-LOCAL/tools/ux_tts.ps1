$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$root = [IO.Path]::GetFullPath($env:UX_REAL_ROOT)
$output = [IO.Path]::GetFullPath($env:UX_TTS_OUTPUT)
if (-not $output.StartsWith($root + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'Audio output must stay inside the test directory' }
$speech = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    $speech.SelectVoice('Microsoft Zira Desktop')
    $speech.SetOutputToWaveFile($output)
    $speech.Speak($env:UX_TTS_TEXT)
} finally { $speech.Dispose() }
