module big_sim ();

wire CLK;
wire RSTN;
wire SE;
wire SI0, SI1;
wire SO0, SO1;

scan_chains dut (.*);

atp2verilog tb (.*);

endmodule
