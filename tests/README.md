# Tests

> 日本語: [README.ja.md](README.ja.md)

```sh
cd tests
uv sync
uv run pytest begin --profile host
```

Cores are never installed with `arduino-cli core install`. Each test's
`sketch.yaml` pins the version, and `--profile` unpacks it under
`~/.arduino15/internal/`, isolated per version.

## `begin/` — the bring-up golden

Records what `Board.begin()` did to the bus and compares it with a frozen
golden.

The recording rides on host-arduino-core's bus observation port — GPIO
through `<HostBus.h>`, I2C through the `TwoWire` hooks — so **there is no
instrumentation inside the library**. What runs is what a sketch would
compile.

The board arrives as `-DTINYM5_BOARD_HEADER="..."`, so one sketch covers
the whole catalogue. That is what the build-flag entry point is for.

### Goldens are frozen

They are not re-derived from M5GFX on every run. The question they answer
is "has this changed since it was blessed", not "does it still match
upstream". Update deliberately and read the diff:

```sh
uv run pytest begin --profile host --update-golden
git diff tests/begin/golden/
```

### Known gap

`Wire.begin()` is not hookable, so it does not appear in the ordered part
of the trace; the pins and clock it left behind are recorded in the state
section instead. Every I2C *transaction* is ordered correctly, which is
what a rail bring-up sequence needs.
