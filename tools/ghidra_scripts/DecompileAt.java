// Decompile a client function — and, on request, the functions it calls — from Ghidra's analysis.
//
// The port's questions are of the form "what does this function do with that table" and "which
// function hands this value out", and both are answered by reading the client's own code. This
// script is the reusable half of that: give it addresses and it prints the decompiled C, the
// callers, and (with -c) what the function itself calls — one level, which is as far as a question
// about a call site usually reaches.
//
// Addresses are the imported image's own (ImageBase 0x00400000), which is the same space as the
// port's file virtual addresses. The live client is this binary relocated to 0x00610000, so a live
// address is an address here plus 0x210000.
//
// Usage:
//   analyzeHeadless <projdir> gw38888 -process Gw.exe -noanalysis \
//     -scriptPath tools/ghidra_scripts -postScript DecompileAt.java 0x7c9860 -c
//
//@category Py4GW_Stealth

import java.util.ArrayList;
import java.util.List;

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;

public class DecompileAt extends GhidraScript {

    /** A function like ``007c9860`` has thousands of call sites; printing them all buries the C. */
    private static final int CALLERS_SHOWN = 12;

    /** Decompiled C, or null when the decompiler could not finish. */
    private String decompile(Function function) {
        DecompInterface decompiler = new DecompInterface();
        try {
            decompiler.openProgram(currentProgram);
            DecompileResults results = decompiler.decompileFunction(function, 120, monitor);
            if (results == null || !results.decompileCompleted()) {
                return null;
            }
            return results.getDecompiledFunction().getC();
        } finally {
            decompiler.dispose();
        }
    }

    private void report(long value, boolean callsCallees) {
        Address at = toAddr(value);
        Function function = getFunctionAt(at);
        if (function == null) {
            function = getFunctionContaining(at);
        }
        println("=== " + Long.toHexString(value) + " -> "
            + (function == null ? "no function contains it" : function.getName()));
        if (function == null) {
            return;
        }
        println("    entry " + function.getEntryPoint() + " body " + function.getBody());
        println("    callers (first " + CALLERS_SHOWN + "):");
        ReferenceIterator callers =
            currentProgram.getReferenceManager().getReferencesTo(function.getEntryPoint());
        int shown = 0;
        int total = 0;
        while (callers.hasNext()) {
            Reference reference = callers.next();
            if (!reference.getReferenceType().isCall()) {
                continue;
            }
            total++;
            if (shown >= CALLERS_SHOWN) {
                continue;
            }
            shown++;
            Address from = reference.getFromAddress();
            Function owner = getFunctionContaining(from);
            println("       " + from + " in "
                + (owner == null ? "no function" : owner.getEntryPoint() + " " + owner.getName()));
        }
        println("    total call sites: " + total);
        String source = decompile(function);
        println(source == null ? "    decompile failed" : source);
        println("    -- calls:");
        List<Function> callees = new ArrayList<>(function.getCalledFunctions(monitor));
        for (Function callee : callees) {
            println("       " + callee.getEntryPoint() + "  " + callee.getName());
        }
        if (!callsCallees) {
            return;
        }
        for (Function callee : callees) {
            if (callee.isThunk() || callee.getEntryPoint().equals(function.getEntryPoint())) {
                continue;
            }
            println("");
            println("=== CALLEE of " + Long.toHexString(value) + ":");
            println("    entry " + callee.getEntryPoint() + " body " + callee.getBody());
            String calleeSource = decompile(callee);
            println(calleeSource == null ? "    decompile failed" : calleeSource);
        }
    }

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        boolean callsCallees = false;
        for (String arg : args) {
            if (arg.equals("-c")) {
                callsCallees = true;
                continue;
            }
            try {
                report(Long.parseLong(arg.replace("0x", ""), 16), callsCallees);
            } catch (Exception error) {
                println("=== " + arg + " failed: " + error);
            }
        }
    }
}
