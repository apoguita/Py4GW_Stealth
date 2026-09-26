// List the functions Ghidra found in an address range, so a module can be surveyed instead of
// guessed at.
//
// A getter nobody has named is a small function, and "small function in this module" is a question
// an inventory answers in one pass. Each line carries the entry, the body size, the number of call
// sites, and the decompiled signature, which is what tells a `wchar_t*(uint32_t)` apart from a
// `void(thiscall*)`.
//
// The name is deliberately not `ListFunctions`: this directory is searched *after* Ghidra's own
// script directories, so a name that matches a built-in loads the built-in instead (which is how
// the first run of this script ended up asking for a choice it was never given).
//
// Usage:
//   analyzeHeadless <projdir> gw38888 -process Gw.exe -noanalysis \
//     -scriptPath tools/ghidra_scripts -postScript ListModuleFunctions.java 0x4e0000 0x4e9000 0x400
//
//@category Py4GW_Stealth

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import ghidra.program.model.symbol.ReferenceIterator;

public class ListModuleFunctions extends GhidraScript {

    /** How many call sites, at most, are counted per function (a hot helper has thousands). */
    private static final int MAX_CALLERS = 3000;

    private String signature(Function function) {
        DecompInterface decompiler = new DecompInterface();
        try {
            decompiler.openProgram(currentProgram);
            DecompileResults results = decompiler.decompileFunction(function, 60, monitor);
            if (results == null || !results.decompileCompleted()) {
                return "(decompile failed)";
            }
            String c = results.getDecompiledFunction().getC();
            int brace = c.indexOf('{');
            String head = brace > 0 ? c.substring(0, brace) : c;
            head = head.replace('\n', ' ').replace('\r', ' ').trim();
            return head.length() > 160 ? head.substring(0, 160) + " ..." : head;
        } finally {
            decompiler.dispose();
        }
    }

    private int countCallers(Function function) {
        ReferenceIterator callers =
            currentProgram.getReferenceManager().getReferencesTo(function.getEntryPoint());
        int count = 0;
        while (callers.hasNext()) {
            if (callers.next().getReferenceType().isCall()) {
                count++;
                if (count >= MAX_CALLERS) {
                    return MAX_CALLERS;
                }
            }
        }
        return count;
    }

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 2) {
            println("usage: ListFunctions.java <start> <end> [max-size]");
            return;
        }
        Address start = toAddr(Long.parseLong(args[0].replace("0x", ""), 16));
        Address end = toAddr(Long.parseLong(args[1].replace("0x", ""), 16));
        long maxSize = args.length > 2 ? Long.parseLong(args[2].replace("0x", ""), 16) : 0x400L;

        FunctionIterator functions = currentProgram.getFunctionManager().getFunctions(start, true);
        int shown = 0;
        while (functions.hasNext()) {
            Function function = functions.next();
            if (function.getEntryPoint().compareTo(end) > 0) {
                break;
            }
            long size = function.getBody().getNumAddresses();
            if (maxSize > 0 && size > maxSize) {
                continue;
            }
            shown++;
            println(function.getEntryPoint() + "  size " + size + "  callers "
                + countCallers(function) + "  " + signature(function));
        }
        println("listed " + shown + " function(s) between " + start + " and " + end);
    }
}
