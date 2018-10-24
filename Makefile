
def: testbench.v


testbench.v: atp2verilog/* vectors.atp
	python atp2verilog


sim: a.out
	./a.out

a.out: testbench.v
	iverilog -g2012 -D VCD testbench.v

waves.vcd: sim

waves: waves.vcd
	gtkwave --save=restore.gtkw


clean:
	@rm testbench.v
	@rm a.out
	@rm waves.vcd

bigsim: testbench.v big_sim.v scan_chains.v
	iverilog -g2012 -D VCD big_sim.v testbench.v scan_chains.v;\
	./a.out



