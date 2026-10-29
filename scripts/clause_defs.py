"""Print the definition of each defined term in a flattened agreement.

    python scripts/clause_defs.py <file.flat.txt> <chars> "Term A" "Term B" ...

Useful for reading credit agreements fast: cash traps, reserves, guarantees, termination triggers."""
import sys, re
f, n = sys.argv[1], int(sys.argv[2])
t = open(f).read()
for term in sys.argv[3:]:
    m = re.search(r'[“"]' + re.escape(term) + r'[”"] (shall mean|means|mean|has the meaning)', t)
    print(f"--- {term}: " + (t[m.start():m.start()+n] if m else "NOT FOUND"))
