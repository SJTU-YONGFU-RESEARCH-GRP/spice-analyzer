* Export Bode PNG via matplotlib-free gnuplot if available; else skip
set terminal png size 900,500
set output '../figures/bode_mag.png'
set xlabel 'Frequency (Hz)'
set ylabel 'Magnitude (dB)'
set title 'Alfio_RAFFC_Pin_3 ADM AC (stock sizing)'
set logscale x
set grid
plot '../figures/bode_mag.dat' using 1:2 with lines title 'vdb(opout)'
set output '../figures/bode_phase.png'
set ylabel 'Phase (rad)'
set title 'Alfio_RAFFC_Pin_3 ADM phase'
plot '../figures/bode_phase.dat' using 1:2 with lines title 'vp(opout)'
