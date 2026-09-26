// Disassemble at an address Ghidra never turned into a function, then decompile it.
//
// Some of this client's routines are reached only through function pointers in `.data`, and
// auto-analysis leaves them as raw bytes — which is how the routine that asserted on our chat-log
// write (`0x00825858`, called from `CtUI::...` through a table) came back as "no function contains
// it". This script disassembles from a given address, creates the function there, and answers with
// the decompiled C, so a routine that has no name in the database can still be read.
//
// Usage:
//   analyzeHeadless <projdir> gw38888 -process Gw.exe -noanalysis \
//     -scriptPath tools/ghidra_scripts -postScript DisassembleAt.java 0x825840 0x825880
//
//@category Py4GW_Stealth

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;

public class DisassembleAt extends GhidraScript {

    private void report(long value) {
        Address at = toAddr(value);
        println("=== " + at);
        try {
            disassemble(at);
        } catch (Exception error) {
            println("    disassemble failed: " + error);
        }
        Function function = getFunctionContaining(at);
        if (function == null) {
            try {
                function = createFunction(at, null);
            } catch (Exception error) {
                println("    createFunction failed: " + error);
            }
        }
        if (function == null) {
            println("    still no function at " + at);
            return;
        }
        println("    entry " + function.getEntryPoint() + " body " + function.getBody());
        DecompInterface decompiler = new DecompInterface();
        try {
            decompiler.openProgram(currentProgram);
            DecompileResults results = decompiler.decompileFunction(function, 120, monitor);
            println(results != null && results.decompileCompleted()
                ? results.getDecompiledFunction().getC()
                : "    decompile failed");
        } finally {
            decompiler.dispose();
        }
    }

    @Override
    public void run() throws Exception {
        for (String arg : getScriptArgs()) {
            report(Long.parseLong(arg.replace("0x", ""), 16));
        }
    }
}
