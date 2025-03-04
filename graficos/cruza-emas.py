//@version=4
study("EMA Cross", overlay=true)
// Einfacher EMA-Cross Indikator mit Indikation der Crosses auf EMA-Linie und am Chart-Bottom
// 
// durtig aber wahr!

// Userinput: EMA-Längen und Quelle
ema_01_len = input(8, title='Ema 1', step=1, type=input.integer)
ema_02_len = input(14, title='Ema 2', step=1, type=input.integer)
ema_03_len = input(50, title='Ema 3', step=1, type=input.integer)
ema_04_len = input(200, title='Ema 4', step=1, type=input.integer)
ema_src = input(title="Source", type=input.source, defval=close)

// EMA-Werte berechnen lassen
ema_01 = ema(ema_src, ema_01_len)
ema_02 = ema(ema_src, ema_02_len)
ema_03 = ema(ema_src, ema_03_len)
ema_04 = ema(ema_src, ema_04_len)

//EMAs in Chart zeichen
plot(ema_01, title='ema_01', color=#00FF00, style=plot.style_line, linewidth=1)
plot(ema_02, title='ema_02', color=#ff0040, style=plot.style_line, linewidth=1)

plot(ema_03, title='ema_03', color=#0000FF, style=plot.style_line, linewidth=1)
plot(ema_04, title='ema_04', color=#ff2080, style=plot.style_line, linewidth=1)


//Cross detect
cross_01_up = crossover(ema_01, ema_02)
cross_01_down = crossunder(ema_01, ema_02)
//Wenn cross dann cross  auf ema-level zeichnen
plot(cross_01_up or cross_01_down ? ema_01 : na, style=plot.style_cross, title="cross 01", linewidth=3, color=ema_01 > ema_02 ? color.green : color.red)
//Wenn cross, cross mit Text unten auf chart zeichnen
plotchar(cross_01_up or cross_01_down ? ema_01 : na, title="cross_01", char="x", location=location.bottom, color=ema_01 > ema_02 ? color.green : color.red, text="Cross 01", textcolor=ema_01 > ema_02 ? color.green : color.red)
//Cross2 detect
cross_02_up = crossover(ema_03, ema_04)
cross_02_down = crossunder(ema_03, ema_04)
//Wenn cross dann cross  auf ema-level zeichnen
plot(cross_02_up or cross_02_down ? ema_03 : na, style=plot.style_cross, title="cross 02", linewidth=3, color=ema_03 > ema_04 ? color.green : color.red)
//Wenn cross, cross mit Text unten auf chart zeichnen
plotchar(cross_02_up or cross_02_down ? ema_03 : na, title="cross_02", char="x", location=location.bottom, color=ema_03 > ema_04 ? color.green : color.red, text="Cross 02", textcolor=ema_03 > ema_04 ? color.green : color.red)

alertcondition(cross_01_up, title='cross_01_up', message='a simple script is not a reason to buy! ;)')
alertcondition(cross_01_down, title='cross_01_down', message='a simple script is not a reason to sell! ;)')
