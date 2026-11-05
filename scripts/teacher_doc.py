"""teacher_doc CLI. Keep the existing engine and stored record format compatible."""
import sys

# In particular, `check` must not create/update the imported engine's bytecode.
sys.dont_write_bytecode = True
from hwpdoc import main

if __name__ == '__main__':
    raise SystemExit(main())
