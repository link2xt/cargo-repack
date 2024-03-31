Utility to test reproducibility of dependencies in `Cargo.lock`

It downloads crates listed in `Cargo.lock` from crates.io
and tries to rebuild them from source repsitory with `cargo package`,
then compares downloaded and rebuilt version with `diffoscope` if they don't match.

If you use `rustup`, run `export RUSTUP_TOOLCHAIN=stable`
to avoid `rust-toolchain` files triggering installation of other toolchains.

Make sure to install `diffoscope`.

Run with `./reproduce.py path/to/Cargo.lock`.

As the result, script creates directories:
- `crates/orig` - downloaded crates from crates.io
- `crates/git` - cloned git repositories
- `crates/rebuilt/package` - rebuilt crates
- `crates/diff` - `diffoscope` output for crates that are not reproducible
