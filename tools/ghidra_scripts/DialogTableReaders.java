// Report the client functions that read the dialog metadata table, from Ghidra's own analysis.
//
// The offline byte scan (tools/dialog_loader_hunt.py, "table-users") finds *where* the table's
// addresses are named in code. This script is the other half: what those functions do with the
// rows. It decompiles them, lists what they call, and lists every reference the analyzer found to
// the table, so `DialogLoader_GetText` can be looked for among the truth rather than among guesses.
//
// Addresses are the imported image's own (ImageBase 0x00400000), which is the port's file virtual
// address space: the live client is the same binary relocated to 0x00610000, so a live address is
// this one plus 0x210000.
//
// Usage (after tools/dialog_loader_hunt.py has imported and analyzed the build):
//   analyzeHeadless <projdir> gw38888 -process Gw.exe -noanalysis \
//     -scriptPath tools/ghidra_scripts -postScript DialogTableReaders.java
//
//@category Py4GW_Stealth

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;

public class DialogTableReaders extends GhidraScript {

    /** The row readers the offline scan found, as this image's virtual addresses. */
    private static final long[] READERS = {
        0x004E2300L,  // dialog table, row 0 (the dialog window: the live 0x006F2300)
        0x004E8240L,  // dialog table, row 0
        0x004E7870L,  // dialog table, row 0
        0x0040765CL,  // dialog table, row 20
        0x0040213BL,  // dialog table, row 34
        0x006F1520L,  // dialog table, row 53
    };

    /** The resolved dialog metadata table (flags column 0x0094CF10, rows from 0x0094CF08). */
    private static final long TABLE_START = 0x0094CF08L;

    private void decompile(long address) {
        Address at = toAddr(address);
        Function function = getFunctionAt(at);
        if (function == null) {
            function = getFunctionContaining(at);
        }
        println("=== READER " + Long.toHexString(address) + " -> "
            + (function == null ? "no function contains it" : function.getName()));
        if (function == null) {
            return;
        }
        println("    entry " + function.getEntryPoint() + " body " + function.getBody());
        DecompInterface decompiler = new DecompInterface();
        try {
            decompiler.openProgram(currentProgram);
            DecompileResults results = decompiler.decompileFunction(function, 120, monitor);
            if (results != null && results.decompileCompleted()) {
                println(results.getDecompiledFunction().getC());
            } else {
                println("    decompile failed: " + (results == null ? "null" : results.getErrorMessage()));
            }
        } finally {
            decompiler.dispose();
        }
        println("    -- calls:");
        for (Function callee : function.getCalledFunctions(monitor)) {
            println("       " + callee.getEntryPoint() + "  " + callee.getName());
        }
    }

    @Override
    public void run() throws Exception {
        for (long reader : READERS) {
            try {
                decompile(reader);
            } catch (Exception error) {
                println("=== READER " + Long.toHexString(reader) + " failed: " + error);
            }
        }

        println("=== REFERENCES to the table start " + Long.toHexString(TABLE_START));
        ReferenceIterator iterator =
            currentProgram.getReferenceManager().getReferencesTo(toAddr(TABLE_START));
        while (iterator.hasNext()) {
            Reference reference = iterator.next();
            Address from = reference.getFromAddress();
            Function owner = getFunctionContaining(from);
            println("    " + from + " (" + reference.getReferenceType() + ") in "
                + (owner == null ? "no function" : owner.getEntryPoint() + " " + owner.getName()));
        }
    }
}
