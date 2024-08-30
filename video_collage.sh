#!/bin/bash

# Nastav proměnné
input_dir="/run/media/kof/kof17/recordings/field/2024/101NIKON"
output_file="sběr2_kof_24.mp4"
interval=14.88  # každých 15 sekund
duration=0.12  # délka klipu


rm /tmp/*.mp4
# Dočasný soubor pro seznam klipů
temp_list=$(mktemp)


# Vymaž dočasný seznam, pokud existuje
> "$temp_list"

# Funkce pro porovnávání dvou čísel pomocí bc
compare_numbers() {
  local num1="$1"
  local num2="$2"
  if [ "$(echo "$num1 < $num2" | bc)" -eq 1 ]; then
    return 0
  else
    return 1
  fi
}

# Funkce pro sčítání dvou čísel pomocí bc
add_numbers() {
  local num1="$1"
  local num2="$2"
  echo "$num1 + $num2" | bc
}

# Projdi všechny soubory ve složce
for video in "$input_dir"/*.MP4; do
  # Zjisti délku videa (v sekundách, s přesností na tři desetinná místa)
  total_seconds=$(ffmpeg -i "$video" 2>&1 | grep "Duration" | awk '{split($2,a,":"); print a[1]*3600 + a[2]*60 + a[3]}' | bc)

  # Kontrola, zda byl správně získán total_seconds
  if [ -z "$total_seconds" ] || [ "$(echo "$total_seconds < 0" | bc)" -eq 1 ]; then
    echo "Nelze získat délku videa pro $video. Přeskočeno."
    continue
  fi

  # Každých $interval sekund vystřihni klip o délce $duration sekund
  start="0"
  while compare_numbers "$start" "$total_seconds"; do
    output_clip=$(mktemp --suffix=.mp4)

    # Přidání nuly před desetinné číslo, pokud je potřeba
    start_formatted=$(printf "%.6f\n" "$start")
    start_formatted=$(echo "$start_formatted" | awk '{print ($1 < 1 && $1 > 0) ? "0"$0 : $0}')
    
    # Výstup z ffmpeg se nyní zapisuje do /dev/null pro odstranění výstupu
    ffmpeg -y -ss "$start_formatted" -i "$video" -t "$duration" -c copy "$output_clip"

    # Ověření, že klip byl správně vytvořen
    if [ $? -eq 0 ]; then
      echo "file '$output_clip'" >> "$temp_list"
    else
      echo "Při zpracování souboru $video došlo k chybě, přeskočeno."
      rm "$output_clip"
    fi

    # Zvýšíme startovací čas o interval
    start=$(add_numbers "$start" "$interval")
  done
done

# Spoj všechny klipy do jednoho souboru, pokud je seznam klipů neprázdný
if [ -s "$temp_list" ]; then
  ffmpeg -loglevel warning -f concat -safe 0 -i "$temp_list" -c copy "$output_file"
else
  echo "Žádné klipy nebyly vytvořeny."
fi

# Smaž dočasné soubory
rm "$temp_list"
