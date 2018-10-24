#! /usr/bin/env python
""" ATP pattern conversion to a verilog data source and check """

print "ATP to verilog conversion"

atp_filename = "vectors.atp"

scan_clk = "CLK"
scan_clk_return_val = "1'b0"

hATP = open(atp_filename, 'r')

pins = []
vectors = []

def get_pins(line):
    """ Extract the pin names from the vector line """
    line = line.replace('{','')
    line = line.replace(')','')
    line = line.replace('(','')
    bits = line.split(',')
    return [s.strip() for s in bits[1:]]


# extract vectors and pins from the ATP file
for line in hATP:
    line = line.strip()

    if line.startswith('vector'):
        pins = get_pins(line)
        print "Pins:", pins

    elif line.startswith('>'):
        comment = ''

        bits = line.split(';')
        if len(bits) == 2:
            comment = bits[1]
        vec = bits[0].split()[2:]

        assert(len(vec) == len(pins))
        vectors.append(vec)

        print "VEC :", vec

hATP.close()

vectors_per_pin = {}
pin_id_map = {}
for p_id, pin in enumerate(pins):
    vectors_per_pin[pin] = []
    pin_id_map[p_id] = pin

for vec in vectors:
    for p_id, v in enumerate(vec):
        pin = pin_id_map[p_id]
        vectors_per_pin[pin].append(v)

for pin in pins:
    print "> %+10s" %(pin), vectors_per_pin[pin]


# Timing
t_period = 10
t_lead = 2
t_trail = 8
t_strobe = 9

verilog_template = """//
// From file: {atp_filename}
//
`timescale 1ns / 100ps

module atp2verilog 
#(
    parameter T_PERIOD = 10.0,
    // return-to-zero timing (clocks)
    T_RZ_LEAD = 2.0,
    T_RZ_TRAIL = 8.0,
    T_RZ_STROBE = 9.0,
    // non-return timing (signals)
    T_NR_LEAD = 0.0,
    T_NR_TRAIL = 0.0,
    T_NR_STROBE = 1.0
)
(
    // Signals driven by test pattern
    {rtl_output_ports},
    // Signals checked by test pattern
    {rtl_input_ports}
);

// Expect values
{rtl_expects}

// Self-checking stuff
int chk_mismatches = 0;
int chk_checks = 0;

logic cycle;
initial begin : cycle_period_clock
    cycle = 0;
    forever begin : loop
        #(T_PERIOD) cycle = 1;
        #(T_PERIOD) cycle = 0;
    end
end : cycle_period_clock

initial begin : apply
    $display("Starting ATP pattern");
    {rtl_apply}

    #100;
    $display("Finished ATP pattern");
    $finish();
end : apply

initial begin : scan_clock
    {rtl_scan_clock}
end : scan_clock

initial begin : strobe
    {rtl_strobe}
end : strobe

initial begin : waveform_dump
`ifdef VCD
    $dumpfile("waves.vcd");
    $dumpvars();
`endif
end : waveform_dump

endmodule : atp2verilog
"""


def devine_direction(pin):
    global vectors_per_pin

    vec = vectors_per_pin[pin]
    counts_x = len( [ v for v in vec if v == 'X' ])
    counts_0 = len( [ v for v in vec if v == '0' ])
    counts_1 = len( [ v for v in vec if v == '1' ])
    counts_h = len( [ v for v in vec if v == 'H' ])
    counts_l = len( [ v for v in vec if v == 'L' ])

    if False:
        print "PIN:", pin
        print "  counts_x:", counts_x
        print "  counts_0:", counts_0
        print "  counts_1:", counts_1
        print "  counts_l:", counts_l
        print "  counts_h:", counts_h

    direction = "unknown"
    if counts_0 == 0 and counts_1 == 0:
        direction = "input"
    elif counts_l == 0 and counts_h == 0:
        direction = "output"

    return direction

directions = {}
for pin in pins:
    directions[pin] = devine_direction(pin)



##
## Write Verilog
##

# expect wire declarations
rtl_expects = []
for pin in pins:
    if directions[pin] != 'input':
        continue
    rtl_expects.append('logic {pin}_expect;'.format(pin=pin))


# input and output port declarations
rtl_input_ports = []
rtl_output_ports = []
for pin in pins:
    if directions[pin] == 'input':
        rtl_input_ports.append('input logic {0}'.format(pin))
    elif directions[pin] == 'output':
        rtl_output_ports.append('output logic {0}'.format(pin))
    else:
        print("Can't deal with inouts")
        assert(False)


# Apply logic
rtl_apply = ["//", "// Apply logic for scan inputs etc.", "//"]
    
for n,vec in enumerate(vectors):

    rtl_apply.append('\n// cycle {cycle}'.format(cycle=n))
    rtl_apply.append('@(cycle);')
    rtl_apply.append('#(T_NR_LEAD);')

    for p_id,state in enumerate(vec):
        pin = pin_id_map[p_id]
        if directions[pin] != 'output':
            continue
        if pin == scan_clk:
            continue
        rtl_apply.append('{pin} = {val};'.format(
            pin = pin,
            val = state,
            )
        )

# Scan Clock  - has a return-zero
rtl_scan_clock = ["//", "// Apply logic for scan clock which has return-to-zero format", "//"]
    
for n,vec in enumerate(vectors):

    rtl_scan_clock.append('\n// cycle {cycle}'.format(cycle=n))
    rtl_scan_clock.append('@(cycle);')

    for p_id, state in enumerate(vec):
        pin = pin_id_map[p_id]
        if pin != scan_clk:
            continue

        # initial value ( = return value)
        rtl_scan_clock.append('{pin} = {val};'.format(
            pin = pin,
            val = scan_clk_return_val,
            )
        )

        # lead
        rtl_scan_clock.append('#(T_RZ_LEAD);')
        rtl_scan_clock.append('{pin} = {val};'.format(
            pin = pin,
            val = state,
            )
        )

        # return/trail
        rtl_scan_clock.append('#(T_RZ_TRAIL-T_RZ_LEAD);')
        rtl_scan_clock.append('{pin} = {val};'.format(
            pin = pin,
            val = scan_clk_return_val,
            )
        )


# Capture logic
rtl_strobe = ["//", "// Apply logic for scan clock which has return-to-zero format", "//"]

for n,vec in enumerate(vectors):

    checks = {}

    for p_id, state in enumerate(vec):
        pin = pin_id_map[p_id]
        if directions[pin] != 'input':
            continue

        # lead
        vstate = "asdf"
        if state == "H":
            vstate = "1'b1"
        elif state == "L":
            vstate = "1'b0"
        elif state == "X":
            vstate = "1'b?"

        checks[pin] =  vstate


    rtl_strobe.append('\n// cycle {cycle}'.format(cycle=n))
    rtl_strobe.append('@(cycle);')

    # time 0
    for pin in checks:
        rtl_strobe.append('{pin}_expect = {val};'.format(
            pin = pin,
            val = "1'bZ",
            )
        )

    # strobe
    rtl_strobe.append('#(T_NR_STROBE);')
    for pin in checks:
        vstate = checks[pin]
        rtl_strobe.append('{pin}_expect = {val};'.format(
            pin = pin,
            val = vstate,
            )
        )
        if vstate.find('?') < 0:
            rtl_strobe.append('chk_checks += 1;')
            rtl_strobe.append('if ({pin} !== {val}) begin'.format(
                pin = pin,
                val = vstate,
                )
            )
            rtl_strobe.append('    chk_mismatches += 1;')
            rtl_strobe.append('end')

    # return/trail
    rtl_strobe.append('#(1);')
    for pin in checks:
        rtl_strobe.append('{pin}_expect = {val};'.format(
            pin = pin,
            val = "1'bZ",
            )
        )

# Write results
rtl_strobe.append("")
rtl_strobe.append("")
rtl_strobe.append("")
rtl_strobe.append('$display("Results");')
rtl_strobe.append('$display("CHECKS     = %8d", chk_checks);')
rtl_strobe.append('$display("MISMATCHES = %8d", chk_mismatches);')


# Write the RTL
rtl = verilog_template.format(
    atp_filename = atp_filename,
    rtl_expects = '\n'.join(rtl_expects),
    rtl_scan_clock = '\n    '.join(rtl_scan_clock),
    rtl_input_ports = ',\n    '.join(rtl_input_ports),
    rtl_output_ports = ',\n    '.join(rtl_output_ports),
    rtl_apply = '\n    '.join(rtl_apply),
    rtl_strobe = '\n    '.join(rtl_strobe),
)

hRTL = open('testbench.v', 'w')

hRTL.write(rtl)
hRTL.close()

