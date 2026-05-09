# Limitaciones

La estrategia ganadora por metricas fue VertebraPrompt + BoxRefiner. Aun asi, la principal limitacion encontrada no fue solamente la segmentacion, sino la asignacion anatomica estricta.

La metrica flexible se mantiene alta en varias pruebas, lo que indica que el modelo suele encontrar estructuras vertebrales razonables. Sin embargo, en escoliosis e imagenes parciales puede ocurrir que una mascara segmentada corresponda espacialmente a una vertebra pero quede nombrada como otra etiqueta anatomica.

BoxRefiner mejora el rendimiento promedio, pero no elimina completamente este problema. Por eso el proyecto debe presentar la mejora como una estrategia ganadora por metricas, manteniendo clara la limitacion de nombramiento anatomico.
