#!/bin/bash

# Vlož svůj AbuseIPDB API klíč
API_KEY="a1d2002d5eb3f87f3b703580abeee4015ea8bf075ec436886f187fc8d7c04510104992d6ebae28b0"

# Kontrola, zda byla zadána IP adresa
if [ -z "$1" ]; then
    echo "Použití: $0 <IP_adresa>"
    exit 1
fi

IP="$1"

echo "Ověřuji IP adresu: $IP přes AbuseIPDB..."

# Volání AbuseIPDB API pomocí curl a zpracování přes jq
response=$(curl -s -G 'https://api.abuseipdb.com/api/v2/check' \
  --data-urlencode "ipAddress=$IP" \
  -d maxAgeInDays=90 \
  -H "Key: $API_KEY" \
  -H "Accept: application/json")

# Kontrola, zda odpověď obsahuje data
if echo "$response" | grep -q "errors"; then
    echo "Chyba při komunikaci s API:"
    echo "$response" | jq '.errors'
    exit 1
fi

# Parsování a výsledek pomocí jq
echo "----------------------------------------"
echo "IP adresa:        $(echo "$response" | jq -r '.data.ipAddress')"
echo "Veřejná/Whitelisted: $(echo "$response" | jq -r '.data.isWhitelisted')"
echo "Abuse skóre:      $(echo "$response" | jq -r '.data.abuseConfidenceScore')% (0-100)"
echo "Celkem hlášení:   $(echo "$response" | jq -r '.data.totalReports')"
echo "Země:             $(echo "$response" | jq -r '.data.countryCode')"
echo "ISP / Vlastník:   $(echo "$response" | jq -r '.data.isp')"
echo "Doména:           $(echo "$response" | jq -r '.data.domain')"
echo "Naposledy nahlášena: $(echo "$response" | jq -r '.data.lastReportedAt')"
echo "----------------------------------------"
