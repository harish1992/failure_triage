# Failure Triage

Triage CI test failures with a local LLM. `jparser.py` merges JUnit XML from one
or more test runs, classifies every failure with an Ollama model running on your
machine, and writes a new JUnit file with the verdict attached to each failure.

Nothing leaves the machine — the model runs locally, so tracebacks are never
sent to a third-party API.

## What it produces

Each failure is annotated in a json file and html report is generated:

```
{
  "test_case": "tests.test_uart.test_loopback_at_115200", 
  "category": "hardware_or_device_under_test",
  "reason": "firmware",
  "stability": "flaky",
  "confidence": "medium",
  "hypothesis": "The test failed due to a timeout error, indicating that the
                 device under test did not respond within the specified time."
  "stack_trace": TimeOutError
}
```

**category** — which layer owns the failure:

| Category | Meaning |
|---|---|
| `hardware_or_device_under_test` | The device or its firmware state, not the test logic |
| `product_bug` | The software under test |
| `test_framework` | The harness itself — fixtures, helpers, configuration |
| `environment` | Host OS, permissions, ports, paths |
| `tools` | Compiler, flasher, debugger, build system |
| `unknown` | Nothing in the evidence points anywhere |

**reason** — a narrowing of the category: `firmware`, `hardware`,
`product_code`, `test_framework`, `environment`, `tool_error`, `unknown`.

**stability** — derived from how many times the test appears in the input and
what happened each time:

| Value | Condition |
|---|---|
| `single_run` | The test appears once |
| `consistent` | Every run failed |
| `flaky` | Some runs passed, some failed |

**confidence** — `low` / `medium` / `high`, how far the evidence narrows the
cause. Timeouts and bare assertions are capped below `high`.

## Requirements

- Python 3.11+
- [Ollama](https://ollama.com/download) running locally
- ~6 GB free RAM for the default 8B model

## Setup

Pull the model:

```bash
ollama pull granite3.1-dense:8b
ollama serve          # skip if it already runs as a service
```

Clone and install:

```bash
git clone https://github.com/harish1992/failure_triage.git
cd failure-triage
python3 -m venv .venv
source .venv/bin/activate         # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Usage

```bash
python3 src/jparser.py "*.xml" -o "filename.json" -m "granite3.1-dense:8b"
```

Quote the pattern so the script expands it rather than the shell.

| Argument | Default | Meaning |
|---|---|---|
| `patterns` | — | Glob pattern(s) for the input JUnit XML |
| `-o`, `--output` | `junit-triaged.json` | Where to write the merged, annotated result |
| `-m`, `--model` | `granite3.1-dense:8b` | Ollama model tag |

If the requested model is not installed locally, the script says so and falls
back to `granite3.1-dense:8b`.

The output file is excluded from the input set, so re-running in place will not
re-merge the previous result.

## How it works

1. **Merge** — every matching XML file is parsed with `lxml` (`huge_tree`
   enabled for large CI dumps) and combined into a single suite.
2. **Tally** — each `<testcase>` is walked and its outcome recorded per test
   name, giving the run count and the pass/fail mix that `stability` is derived
   from. Passing and skipped cases are counted here even though they are never
   triaged.
3. **Deduplicate** — the failure body is reduced to its error tail, and that is
   used as a cache key so an identical error appearing across many tests costs a
   single model call.
4. **Classify** — the failure, its result type, and the computed run tally are
   sent to the model, which answers against a fixed JSON schema so the verdict
   is always one of the known categories rather than free text.
5. **Write** — verdicts are appended to each failure body and the merged suite
   is saved to the output path.

## Flakiness

Flakiness is counted, not inferred. A test that appears more than once in the
input with a mix of passes and failures is marked `flaky`; one that fails every
time is `consistent`, however many times it ran.

This only works when the input files are **repeated runs of the same suite** —
nightlies, or a job retried. If the files are **shards of one parallel run**,
each test appears exactly once and every result is `single_run`.

Intra-run reruns from `pytest-rerunfailures` are detected when the plugin emits
duplicate `<testcase>` elements. Versions that emit `<rerun>` child elements
instead are not currently picked up.

## Notes and limitations

The classification is a hypothesis, not a diagnosis. Treat it as a first pass
that turns a long failure list into something triageable by hand.

Verdicts are cached by error tail, so two tests failing identically share one
verdict. A flaky test that fails with two *different* errors across runs is
triaged from whichever signature was seen first.

Temperature is pinned to 0, but results still shift across model versions and
context sizes. An 8B model has limited embedded-systems knowledge and will
occasionally attribute a host-side error to the device, or the reverse.

`confidence` is the model's own estimate and is not calibrated. Check it against
failures you have triaged by hand before relying on it.
