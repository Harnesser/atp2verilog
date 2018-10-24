module scan_chains 
#(
	parameter SCAN_CHAIN_LENGTH = 8
)
(
	// Outputs
	output logic SO0,
	output logic SO1,

	// Inputs
	input CLK,
	input SE,
	input SI0,
	input SI1,
	input RSTN
	
);

logic [SCAN_CHAIN_LENGTH-1:0] chain_0;

always @(posedge CLK or negedge RSTN) begin : scan_chain_0
	if (!RSTN) begin
		chain_0 <= {SCAN_CHAIN_LENGTH{1'b0}};
	end
	else if (SE) begin 
		chain_0 <= {
			chain_0[SCAN_CHAIN_LENGTH-2:0],
			SI0
		};
	end
end : scan_chain_0

assign SO0 = chain_0[SCAN_CHAIN_LENGTH-1];



logic [SCAN_CHAIN_LENGTH-1:0] chain_1;

always @(posedge CLK or negedge RSTN) begin : scan_chain_1
	if (!RSTN) begin
		chain_1 <= {SCAN_CHAIN_LENGTH{1'b0}};
	end
	else if (SE) begin 
		chain_1 <= {
			chain_1[SCAN_CHAIN_LENGTH-2:0],
			SI1
		};
	end
end : scan_chain_1

assign SO1 = chain_1[SCAN_CHAIN_LENGTH-1];


endmodule
