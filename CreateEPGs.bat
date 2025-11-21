@echo off
setlocal
cd /d "%~dp0"
echo Starting EPG generators...

IF EXIST "Fetch.Epgs.py" (
  echo Running Fetch.Epgs.py ...
  python "Fetch.Epgs.py"
  IF ERRORLEVEL 1 echo FAILED Fetch.Epgs.py, continuing...
) ELSE (
  echo SKIPPED Fetch.Epgs.py (missing)
)
IF EXIST "Al-Jazeera.py" (
  echo Running Al-Jazeera.py ...
  python "Al-Jazeera.py"
  IF ERRORLEVEL 1 echo FAILED Al-Jazeera.py, continuing...
) ELSE (
  echo SKIPPED Al-Jazeera.py (missing)
)
IF EXIST "DW.py" (
  echo Running DW.py ...
  python "DW.py"
  IF ERRORLEVEL 1 echo FAILED DW.py, continuing...
) ELSE (
  echo SKIPPED DW.py (missing)
)
IF EXIST "TRT-World.py" (
  echo Running TRT-World.py ...
  python "TRT-World.py"
  IF ERRORLEVEL 1 echo FAILED TRT-World.py, continuing...
) ELSE (
  echo SKIPPED TRT-World.py (missing)
)
IF EXIST "NHK-World.py" (
  echo Running NHK-World.py ...
  python "NHK-World.py"
  IF ERRORLEVEL 1 echo FAILED NHK-World.py, continuing...
) ELSE (
  echo SKIPPED NHK-World.py (missing)
)
IF EXIST "CNA.py" (
  echo Running CNA.py ...
  python "CNA.py"
  IF ERRORLEVEL 1 echo FAILED CNA.py, continuing...
) ELSE (
  echo SKIPPED CNA.py (missing)
)
IF EXIST "CGTN.py" (
  echo Running CGTN.py ...
  python "CGTN.py"
  IF ERRORLEVEL 1 echo FAILED CGTN.py, continuing...
) ELSE (
  echo SKIPPED CGTN.py (missing)
)
IF EXIST "RT.py" (
  echo Running RT.py ...
  python "RT.py"
  IF ERRORLEVEL 1 echo FAILED RT.py, continuing...
) ELSE (
  echo SKIPPED RT.py (missing)
)
IF EXIST "France-24.py" (
  echo Running France-24.py ...
  python "France-24.py"
  IF ERRORLEVEL 1 echo FAILED France-24.py, continuing...
) ELSE (
  echo SKIPPED France-24.py (missing)
)
IF EXIST "Sky-News.py" (
  echo Running Sky-News.py ...
  python "Sky-News.py"
  IF ERRORLEVEL 1 echo FAILED Sky-News.py, continuing...
) ELSE (
  echo SKIPPED Sky-News.py (missing)
)
IF EXIST "BBC-News.py" (
  echo Running BBC-News.py ...
  python "BBC-News.py"
  IF ERRORLEVEL 1 echo FAILED BBC-News.py, continuing...
) ELSE (
  echo SKIPPED BBC-News.py (missing)
)
IF EXIST "CNN.py" (
  echo Running CNN.py ...
  python "CNN.py"
  IF ERRORLEVEL 1 echo FAILED CNN.py, continuing...
) ELSE (
  echo SKIPPED CNN.py (missing)
)
IF EXIST "CNN-International.py" (
  echo Running CNN-International.py ...
  python "CNN-International.py"
  IF ERRORLEVEL 1 echo FAILED CNN-International.py, continuing...
) ELSE (
  echo SKIPPED CNN-International.py (missing)
)
IF EXIST "CNN-News-18.py" (
  echo Running CNN-News-18.py ...
  python "CNN-News-18.py"
  IF ERRORLEVEL 1 echo FAILED CNN-News-18.py, continuing...
) ELSE (
  echo SKIPPED CNN-News-18.py (missing)
)
IF EXIST "CNBC-TV-18.py" (
  echo Running CNBC-TV-18.py ...
  python "CNBC-TV-18.py"
  IF ERRORLEVEL 1 echo FAILED CNBC-TV-18.py, continuing...
) ELSE (
  echo SKIPPED CNBC-TV-18.py (missing)
)
IF EXIST "CNBC.py" (
  echo Running CNBC.py ...
  python "CNBC.py"
  IF ERRORLEVEL 1 echo FAILED CNBC.py, continuing...
) ELSE (
  echo SKIPPED CNBC.py (missing)
)
IF EXIST "CNBC-World.py" (
  echo Running CNBC-World.py ...
  python "CNBC-World.py"
  IF ERRORLEVEL 1 echo FAILED CNBC-World.py, continuing...
) ELSE (
  echo SKIPPED CNBC-World.py (missing)
)
IF EXIST "MSNBC.py" (
  echo Running MSNBC.py ...
  python "MSNBC.py"
  IF ERRORLEVEL 1 echo FAILED MSNBC.py, continuing...
) ELSE (
  echo SKIPPED MSNBC.py (missing)
)
IF EXIST "ABC-News-AU.py" (
  echo Running ABC-News-AU.py ...
  python "ABC-News-AU.py"
  IF ERRORLEVEL 1 echo FAILED ABC-News-AU.py, continuing...
) ELSE (
  echo SKIPPED ABC-News-AU.py (missing)
)
IF EXIST "GB-News.py" (
  echo Running GB-News.py ...
  python "GB-News.py"
  IF ERRORLEVEL 1 echo FAILED GB-News.py, continuing...
) ELSE (
  echo SKIPPED GB-News.py (missing)
)
IF EXIST "Euronews.py" (
  echo Running Euronews.py ...
  python "Euronews.py"
  IF ERRORLEVEL 1 echo FAILED Euronews.py, continuing...
) ELSE (
  echo SKIPPED Euronews.py (missing)
)
IF EXIST "Africanews.py" (
  echo Running Africanews.py ...
  python "Africanews.py"
  IF ERRORLEVEL 1 echo FAILED Africanews.py, continuing...
) ELSE (
  echo SKIPPED Africanews.py (missing)
)
IF EXIST "Global-News.py" (
  echo Running Global-News.py ...
  python "Global-News.py"
  IF ERRORLEVEL 1 echo FAILED Global-News.py, continuing...
) ELSE (
  echo SKIPPED Global-News.py (missing)
)
IF EXIST "WION.py" (
  echo Running WION.py ...
  python "WION.py"
  IF ERRORLEVEL 1 echo FAILED WION.py, continuing...
) ELSE (
  echo SKIPPED WION.py (missing)
)
IF EXIST "Firstpost.py" (
  echo Running Firstpost.py ...
  python "Firstpost.py"
  IF ERRORLEVEL 1 echo FAILED Firstpost.py, continuing...
) ELSE (
  echo SKIPPED Firstpost.py (missing)
)
IF EXIST "Reuters.py" (
  echo Running Reuters.py ...
  python "Reuters.py"
  IF ERRORLEVEL 1 echo FAILED Reuters.py, continuing...
) ELSE (
  echo SKIPPED Reuters.py (missing)
)
IF EXIST "ABC-News-Live.py" (
  echo Running ABC-News-Live.py ...
  python "ABC-News-Live.py"
  IF ERRORLEVEL 1 echo FAILED ABC-News-Live.py, continuing...
) ELSE (
  echo SKIPPED ABC-News-Live.py (missing)
)
IF EXIST "LiveNOW-from-FOX.py" (
  echo Running LiveNOW-from-FOX.py ...
  python "LiveNOW-from-FOX.py"
  IF ERRORLEVEL 1 echo FAILED LiveNOW-from-FOX.py, continuing...
) ELSE (
  echo SKIPPED LiveNOW-from-FOX.py (missing)
)
IF EXIST "NBC-News-Now.py" (
  echo Running NBC-News-Now.py ...
  python "NBC-News-Now.py"
  IF ERRORLEVEL 1 echo FAILED NBC-News-Now.py, continuing...
) ELSE (
  echo SKIPPED NBC-News-Now.py (missing)
)
IF EXIST "HLN.py" (
  echo Running HLN.py ...
  python "HLN.py"
  IF ERRORLEVEL 1 echo FAILED HLN.py, continuing...
) ELSE (
  echo SKIPPED HLN.py (missing)
)
IF EXIST "ABC.py" (
  echo Running ABC.py ...
  python "ABC.py"
  IF ERRORLEVEL 1 echo FAILED ABC.py, continuing...
) ELSE (
  echo SKIPPED ABC.py (missing)
)
IF EXIST "Fox-News-Channel.py" (
  echo Running Fox-News-Channel.py ...
  python "Fox-News-Channel.py"
  IF ERRORLEVEL 1 echo FAILED Fox-News-Channel.py, continuing...
) ELSE (
  echo SKIPPED Fox-News-Channel.py (missing)
)
IF EXIST "Fox-Business.py" (
  echo Running Fox-Business.py ...
  python "Fox-Business.py"
  IF ERRORLEVEL 1 echo FAILED Fox-Business.py, continuing...
) ELSE (
  echo SKIPPED Fox-Business.py (missing)
)
IF EXIST "Bloomberg.py" (
  echo Running Bloomberg.py ...
  python "Bloomberg.py"
  IF ERRORLEVEL 1 echo FAILED Bloomberg.py, continuing...
) ELSE (
  echo SKIPPED Bloomberg.py (missing)
)
IF EXIST "Yahoo-Finance.py" (
  echo Running Yahoo-Finance.py ...
  python "Yahoo-Finance.py"
  IF ERRORLEVEL 1 echo FAILED Yahoo-Finance.py, continuing...
) ELSE (
  echo SKIPPED Yahoo-Finance.py (missing)
)
IF EXIST "Republic-TV.py" (
  echo Running Republic-TV.py ...
  python "Republic-TV.py"
  IF ERRORLEVEL 1 echo FAILED Republic-TV.py, continuing...
) ELSE (
  echo SKIPPED Republic-TV.py (missing)
)
IF EXIST "Zee-News.py" (
  echo Running Zee-News.py ...
  python "Zee-News.py"
  IF ERRORLEVEL 1 echo FAILED Zee-News.py, continuing...
) ELSE (
  echo SKIPPED Zee-News.py (missing)
)
IF EXIST "CGTN-Documentary.py" (
  echo Running CGTN-Documentary.py ...
  python "CGTN-Documentary.py"
  IF ERRORLEVEL 1 echo FAILED CGTN-Documentary.py, continuing...
) ELSE (
  echo SKIPPED CGTN-Documentary.py (missing)
)
IF EXIST "RT-Documentary.py" (
  echo Running RT-Documentary.py ...
  python "RT-Documentary.py"
  IF ERRORLEVEL 1 echo FAILED RT-Documentary.py, continuing...
) ELSE (
  echo SKIPPED RT-Documentary.py (missing)
)
IF EXIST "Documentary-Plus.py" (
  echo Running Documentary-Plus.py ...
  python "Documentary-Plus.py"
  IF ERRORLEVEL 1 echo FAILED Documentary-Plus.py, continuing...
) ELSE (
  echo SKIPPED Documentary-Plus.py (missing)
)
IF EXIST "VICE.py" (
  echo Running VICE.py ...
  python "VICE.py"
  IF ERRORLEVEL 1 echo FAILED VICE.py, continuing...
) ELSE (
  echo SKIPPED VICE.py (missing)
)
IF EXIST "Bloomberg-Originals.py" (
  echo Running Bloomberg-Originals.py ...
  python "Bloomberg-Originals.py"
  IF ERRORLEVEL 1 echo FAILED Bloomberg-Originals.py, continuing...
) ELSE (
  echo SKIPPED Bloomberg-Originals.py (missing)
)
IF EXIST "CNN-Originals.py" (
  echo Running CNN-Originals.py ...
  python "CNN-Originals.py"
  IF ERRORLEVEL 1 echo FAILED CNN-Originals.py, continuing...
) ELSE (
  echo SKIPPED CNN-Originals.py (missing)
)
IF EXIST "Geo-Entertainment.py" (
  echo Running Geo-Entertainment.py ...
  python "Geo-Entertainment.py"
  IF ERRORLEVEL 1 echo FAILED Geo-Entertainment.py, continuing...
) ELSE (
  echo SKIPPED Geo-Entertainment.py (missing)
)
IF EXIST "Green-Entertainment.py" (
  echo Running Green-Entertainment.py ...
  python "Green-Entertainment.py"
  IF ERRORLEVEL 1 echo FAILED Green-Entertainment.py, continuing...
) ELSE (
  echo SKIPPED Green-Entertainment.py (missing)
)
IF EXIST "Aaj-Entertainment.py" (
  echo Running Aaj-Entertainment.py ...
  python "Aaj-Entertainment.py"
  IF ERRORLEVEL 1 echo FAILED Aaj-Entertainment.py, continuing...
) ELSE (
  echo SKIPPED Aaj-Entertainment.py (missing)
)
IF EXIST "Hum-TV.py" (
  echo Running Hum-TV.py ...
  python "Hum-TV.py"
  IF ERRORLEVEL 1 echo FAILED Hum-TV.py, continuing...
) ELSE (
  echo SKIPPED Hum-TV.py (missing)
)
IF EXIST "Ary-News.py" (
  echo Running Ary-News.py ...
  python "Ary-News.py"
  IF ERRORLEVEL 1 echo FAILED Ary-News.py, continuing...
) ELSE (
  echo SKIPPED Ary-News.py (missing)
)
IF EXIST "Ary-Digital.py" (
  echo Running Ary-Digital.py ...
  python "Ary-Digital.py"
  IF ERRORLEVEL 1 echo FAILED Ary-Digital.py, continuing...
) ELSE (
  echo SKIPPED Ary-Digital.py (missing)
)
IF EXIST "Ary-Zauq.py" (
  echo Running Ary-Zauq.py ...
  python "Ary-Zauq.py"
  IF ERRORLEVEL 1 echo FAILED Ary-Zauq.py, continuing...
) ELSE (
  echo SKIPPED Ary-Zauq.py (missing)
)
IF EXIST "Ary-Zauq2.py" (
  echo Running Ary-Zauq2.py ...
  python "Ary-Zauq2.py"
  IF ERRORLEVEL 1 echo FAILED Ary-Zauq2.py, continuing...
) ELSE (
  echo SKIPPED Ary-Zauq2.py (missing)
)
IF EXIST "Ary-QTV.py" (
  echo Running Ary-QTV.py ...
  python "Ary-QTV.py"
  IF ERRORLEVEL 1 echo FAILED Ary-QTV.py, continuing...
) ELSE (
  echo SKIPPED Ary-QTV.py (missing)
)
IF EXIST "Geo-News.py" (
  echo Running Geo-News.py ...
  python "Geo-News.py"
  IF ERRORLEVEL 1 echo FAILED Geo-News.py, continuing...
) ELSE (
  echo SKIPPED Geo-News.py (missing)
)
IF EXIST "AJK-Television.py" (
  echo Running AJK-Television.py ...
  python "AJK-Television.py"
  IF ERRORLEVEL 1 echo FAILED AJK-Television.py, continuing...
) ELSE (
  echo SKIPPED AJK-Television.py (missing)
)
IF EXIST "PTV-Bolan.py" (
  echo Running PTV-Bolan.py ...
  python "PTV-Bolan.py"
  IF ERRORLEVEL 1 echo FAILED PTV-Bolan.py, continuing...
) ELSE (
  echo SKIPPED PTV-Bolan.py (missing)
)
IF EXIST "PTV-Global.py" (
  echo Running PTV-Global.py ...
  python "PTV-Global.py"
  IF ERRORLEVEL 1 echo FAILED PTV-Global.py, continuing...
) ELSE (
  echo SKIPPED PTV-Global.py (missing)
)
IF EXIST "PTV-Home.py" (
  echo Running PTV-Home.py ...
  python "PTV-Home.py"
  IF ERRORLEVEL 1 echo FAILED PTV-Home.py, continuing...
) ELSE (
  echo SKIPPED PTV-Home.py (missing)
)
IF EXIST "PTV-National.py" (
  echo Running PTV-National.py ...
  python "PTV-National.py"
  IF ERRORLEVEL 1 echo FAILED PTV-National.py, continuing...
) ELSE (
  echo SKIPPED PTV-National.py (missing)
)
IF EXIST "PTV-News.py" (
  echo Running PTV-News.py ...
  python "PTV-News.py"
  IF ERRORLEVEL 1 echo FAILED PTV-News.py, continuing...
) ELSE (
  echo SKIPPED PTV-News.py (missing)
)
IF EXIST "PTV-Sports.py" (
  echo Running PTV-Sports.py ...
  python "PTV-Sports.py"
  IF ERRORLEVEL 1 echo FAILED PTV-Sports.py, continuing...
) ELSE (
  echo SKIPPED PTV-Sports.py (missing)
)
IF EXIST "Express-Entertainment.py" (
  echo Running Express-Entertainment.py ...
  python "Express-Entertainment.py"
  IF ERRORLEVEL 1 echo FAILED Express-Entertainment.py, continuing...
) ELSE (
  echo SKIPPED Express-Entertainment.py (missing)
)
IF EXIST "Hum-Europe.py" (
  echo Running Hum-Europe.py ...
  python "Hum-Europe.py"
  IF ERRORLEVEL 1 echo FAILED Hum-Europe.py, continuing...
) ELSE (
  echo SKIPPED Hum-Europe.py (missing)
)
IF EXIST "Hum-Masala.py" (
  echo Running Hum-Masala.py ...
  python "Hum-Masala.py"
  IF ERRORLEVEL 1 echo FAILED Hum-Masala.py, continuing...
) ELSE (
  echo SKIPPED Hum-Masala.py (missing)
)
IF EXIST "9XM.py" (
  echo Running 9XM.py ...
  python "9XM.py"
  IF ERRORLEVEL 1 echo FAILED 9XM.py, continuing...
) ELSE (
  echo SKIPPED 9XM.py (missing)
)
IF EXIST "9X-Jalwa.py" (
  echo Running 9X-Jalwa.py ...
  python "9X-Jalwa.py"
  IF ERRORLEVEL 1 echo FAILED 9X-Jalwa.py, continuing...
) ELSE (
  echo SKIPPED 9X-Jalwa.py (missing)
)
IF EXIST "Zoom.py" (
  echo Running Zoom.py ...
  python "Zoom.py"
  IF ERRORLEVEL 1 echo FAILED Zoom.py, continuing...
) ELSE (
  echo SKIPPED Zoom.py (missing)
)
IF EXIST "B4U-Music.py" (
  echo Running B4U-Music.py ...
  python "B4U-Music.py"
  IF ERRORLEVEL 1 echo FAILED B4U-Music.py, continuing...
) ELSE (
  echo SKIPPED B4U-Music.py (missing)
)
IF EXIST "Mastiii.py" (
  echo Running Mastiii.py ...
  python "Mastiii.py"
  IF ERRORLEVEL 1 echo FAILED Mastiii.py, continuing...
) ELSE (
  echo SKIPPED Mastiii.py (missing)
)
IF EXIST "YRF-Music.py" (
  echo Running YRF-Music.py ...
  python "YRF-Music.py"
  IF ERRORLEVEL 1 echo FAILED YRF-Music.py, continuing...
) ELSE (
  echo SKIPPED YRF-Music.py (missing)
)
IF EXIST "Juice-TV.py" (
  echo Running Juice-TV.py ...
  python "Juice-TV.py"
  IF ERRORLEVEL 1 echo FAILED Juice-TV.py, continuing...
) ELSE (
  echo SKIPPED Juice-TV.py (missing)
)
IF EXIST "J2.py" (
  echo Running J2.py ...
  python "J2.py"
  IF ERRORLEVEL 1 echo FAILED J2.py, continuing...
) ELSE (
  echo SKIPPED J2.py (missing)
)
IF EXIST "Melo.py" (
  echo Running Melo.py ...
  python "Melo.py"
  IF ERRORLEVEL 1 echo FAILED Melo.py, continuing...
) ELSE (
  echo SKIPPED Melo.py (missing)
)
IF EXIST "Big-Rig.py" (
  echo Running Big-Rig.py ...
  python "Big-Rig.py"
  IF ERRORLEVEL 1 echo FAILED Big-Rig.py, continuing...
) ELSE (
  echo SKIPPED Big-Rig.py (missing)
)
IF EXIST "The-GROAT.py" (
  echo Running The-GROAT.py ...
  python "The-GROAT.py"
  IF ERRORLEVEL 1 echo FAILED The-GROAT.py, continuing...
) ELSE (
  echo SKIPPED The-GROAT.py (missing)
)
IF EXIST "myTV.py" (
  echo Running myTV.py ...
  python "myTV.py"
  IF ERRORLEVEL 1 echo FAILED myTV.py, continuing...
) ELSE (
  echo SKIPPED myTV.py (missing)
)
IF EXIST "PakistanEPG-Package.py" (
  echo Running PakistanEPG-Package.py ...
  python "PakistanEPG-Package.py"
  IF ERRORLEVEL 1 echo FAILED PakistanEPG-Package.py, continuing...
) ELSE (
  echo SKIPPED PakistanEPG-Package.py (missing)
)

echo All done.
endlocal