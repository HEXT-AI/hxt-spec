# hxt-spec
Open specification and reference implementations for `.hxt`, a Markdown format with a tamper-evident authorship ledger.

`.hxt` keeps the document human-readable while appending a machine-verifiable block between `<!--hxt:begin-->` and `<!--hxt:end-->`. The ledger stores timestamps, edit deltas, and hashes only. It never duplicates the document body.

## Files

- `README.md`: Project overview and quick start
- `SPEC.md`: Technical specification for the `.hxt` format
- `hxt.js`: Reference implementation for Node.js and browsers
- `hxt.py`: Reference implementation for Python, including a CLI
- `examples/sample.hxt`: Valid sample document
- `examples/invalid.hxt`: Tampered sample document that should fail verification

## Quick Start

Verify the bundled examples:

```bash
python3 hxt.py verify examples/sample.hxt
python3 hxt.py verify examples/invalid.hxt
python3 hxt.py summary examples/sample.hxt
```

Use the Python API:

```python
from hxt import crystallize, verify

body = "# Demo\n\nHuman reviewed text."
file_content = crystallize(body, author_type="HUMAN")
print(verify(file_content))
```

Use the JavaScript API in Node.js:

```js
const { crystallize, verify } = require("./hxt.js");

async function main() {
  const body = "# Demo\n\nHuman reviewed text.";
  const fileContent = await crystallize(body, "HUMAN");
  console.log(await verify(fileContent));
}

main();
```

Use the JavaScript API in a browser:

```html
<script src="./hxt.js"></script>
<script>
  HXT.crystallize("# Demo\n\nHuman reviewed text.", "HUMAN").then(console.log);
</script>
```

## Design Goals

- Valid Markdown first
- Tamper-evident verification
- No content duplication inside the ledger
- Matching reference logic in JavaScript and Python

## Specification

See `SPEC.md` for the format, schema, hashing rules, and validation rules.

## License

MIT © Gemmina Intelligence LLC
