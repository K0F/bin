#!/usr/bin/env python3
"""
moonphase.py - Calculate Lunar Phase
Author: Sean B. Palmer, inamidst.com
Enhanced for Samizdat & Observatoř Cybernetics
Cf. http://en.wikipedia.org/wiki/Lunar_phase#Lunar_phase_calculation
"""

import math, decimal, datetime, sys
dec = decimal.Decimal

def position(now=None): 
   if now is None: 
      now = datetime.datetime.now()

   diff = now - datetime.datetime(2001, 1, 1)
   days = dec(diff.days) + (dec(diff.seconds) / dec(86400))
   lunations = dec("0.20439731") + (days * dec("0.03386319269"))

   return lunations % dec(1)

def phase(pos): 
   index = (pos * dec(8)) + dec("0.5")
   index = math.floor(index)
   return {
      0: "New Moon", 
      1: "Waxing Crescent", 
      2: "First Quarter", 
      3: "Waxing Gibbous", 
      4: "Full Moon", 
      5: "Waning Gibbous", 
      6: "Last Quarter", 
      7: "Waning Crescent"
   }[int(index) & 7]

def phase_cz(pos):
   index = (pos * dec(8)) + dec("0.5")
   index = math.floor(index)
   return {
      0: "Nov (New Moon)", 
      1: "Dorůstající srpek (Waxing Crescent)", 
      2: "První čtvrť (First Quarter)", 
      3: "Dorůstající Měsíc (Waxing Gibbous)", 
      4: "Úplněk (Full Moon)", 
      5: "Ubývající Měsíc (Waning Gibbous)", 
      6: "Poslední čtvrť (Last Quarter)", 
      7: "Ubývající srpek (Waning Crescent)"
   }[int(index) & 7]

def illumination(pos):
   # Approximate illumination percentage
   # pos is 0 at New Moon, 0.5 at Full Moon, 1.0 at New Moon
   p = float(pos)
   return round((1 - math.cos(p * 2 * math.pi)) / 2 * 100, 1)

def moon_ascii(pos):
   index = int((pos * dec(8)) + dec("0.5")) & 7
   icons = ["🌑", "🌒", "🌓", "🌔", "🌕", "🌖", "🌗", "🌘"]
   return icons[index]

def get_moon_metrics(now=None):
   if now is None:
      now = datetime.datetime.now()
   pos = position(now)
   p_name = phase(pos)
   p_name_cz = phase_cz(pos)
   illum = illumination(pos)
   icon = moon_ascii(pos)
   lunation_num = int(math.floor(float((now - datetime.datetime(2001, 1, 1)).days) / 29.53058867)) + 300 # relative count
   roundedpos = round(float(pos), 4)
   
   return {
      "datetime": now.isoformat(),
      "position": roundedpos,
      "phase_en": p_name,
      "phase_cz": p_name_cz,
      "illumination_pct": illum,
      "icon": icon,
      "lunation_est": lunation_num,
      "summary": f"{icon} {p_name_cz} | Phase: {roundedpos} | Illumination: {illum}%"
   }

def main(): 
   now = datetime.datetime.now()
   m = get_moon_metrics(now)
   if len(sys.argv) > 1 and sys.argv[1] == "--json":
      import json
      print(json.dumps(m, indent=2))
   elif len(sys.argv) > 1 and sys.argv[1] == "--raw":
      print(m["position"])
   else:
      print(m["summary"])

if __name__=="__main__": 
   main()
