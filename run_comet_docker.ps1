param(
    [ValidateRange(1, 1000)]
    [int]$Rounds = 1,
    [ValidateRange(0, 86400)]
    [int]$UiSeconds = 0
)

$ErrorActionPreference = 'Stop'
$benchmark = @'
set -eu
apt-get update -qq
apt-get install -y -qq --no-install-recommends openjdk-17-jre-headless
python -m pip install --quiet pyspark==3.5.9
curl -fsSL https://repo.maven.apache.org/maven2/org/apache/datafusion/comet-spark-spark3.5_2.12/1.2.0/comet-spark-spark3.5_2.12-1.2.0.jar -o /tmp/comet.jar
python -u benchmark_stock_sail.py --comet-jar /tmp/comet.jar --rounds "$1" --ui-seconds "$2"
'@

$uiArgs = @()
if ($UiSeconds -gt 0) { $uiArgs = @('-p', '127.0.0.1:4040:4040') }
docker --context desktop-linux run --rm --cpus 2 --memory 4g @uiArgs `
    --mount "type=bind,source=$PSScriptRoot,target=/work,readonly" `
    --workdir /work python:3.11-bookworm bash -c ($benchmark -replace "`r", '') benchmark "$Rounds" "$UiSeconds"
exit $LASTEXITCODE
