**Use [cargo-goggles](https://github.com/M4SS-Code/cargo-goggles/) instead**

This repository contains a Python prototype
of the utility to test reproducibility of dependencies in `Cargo.lock`.

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

The approach of comparing produced `.crate` bit-for-bit
taken in this repository does not work for many packages
because of non-reproducible Cargo.lock packaged inside.
Copying Cargo.lock from .crate also does not always work
because it is sometimes not compatible with the latest `cargo`
version.

At the time of the writing, 2024-04-03,
[cargo-goggles](https://github.com/M4SS-Code/cargo-goggles/)
took a different appoarch of comparing the file contents instead.
Development of a tool usable for CI integration continues there.
