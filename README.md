ATP to Verilog
======================

Basic script to convert Tetradyne ATP vectors to a verilog module
that can be used for a simulation.

Includes a small fake scan chain DUT sim, using `iverilog`.

The scan clock is assumed to be Return-Low, and must be named in 
the Python script. All other things are assumed to be Non-return.

Bi-directional ports are not supported.

Repeat statements are not supported.

Most things are hard-coded in the script, including input pattern
filename and output testbench name.


