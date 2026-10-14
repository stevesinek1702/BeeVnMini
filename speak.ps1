# Đọc to một câu bằng giọng Windows — ưu tiên giọng tiếng Việt (Microsoft An), không có thì giọng bất kỳ.
# Câu cần đọc truyền qua biến môi trường BEEVN_SAY (tránh lỗi dấu nháy khi ghép lệnh).
# Giọng tiếng Việt nằm trong bộ "OneCore" nên phải gọi qua Windows.Media.SpeechSynthesis (WinRT),
# System.Speech cũ của .NET chỉ thấy giọng tiếng Anh.
$ErrorActionPreference = 'Stop'
$text = $env:BEEVN_SAY
if (-not $text) { exit 0 }

Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Media.SpeechSynthesis.SpeechSynthesizer, Windows.Media.SpeechSynthesis, ContentType = WindowsRuntime]

# Chờ một tác vụ WinRT (IAsyncOperation) xong — PowerShell 5.1 không có await
$asTask = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and
    $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' } | Select-Object -First 1
function Await($op, [Type]$type) {
    $t = $asTask.MakeGenericMethod($type).Invoke($null, @($op))
    $t.Wait(-1) | Out-Null
    $t.Result
}

$synth = New-Object Windows.Media.SpeechSynthesis.SpeechSynthesizer
$vi = [Windows.Media.SpeechSynthesis.SpeechSynthesizer]::AllVoices | Where-Object { $_.Language -eq 'vi-VN' } | Select-Object -First 1
if ($vi) { $synth.Voice = $vi }
elseif ($env:BEEVN_SAY_EN) { $text = $env:BEEVN_SAY_EN }   # không có giọng Việt → câu tiếng Anh

$stream = Await ($synth.SynthesizeTextToStreamAsync($text)) ([Windows.Media.SpeechSynthesis.SpeechSynthesisStream])
$net = [System.IO.WindowsRuntimeStreamExtensions]::AsStreamForRead($stream)
$player = New-Object System.Media.SoundPlayer $net
$player.PlaySync()
