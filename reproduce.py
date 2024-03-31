#!/usr/bin/env python
import tomllib
import sys
import re
from pathlib import Path
import subprocess
from dataclasses import dataclass
import tarfile
import json
import hashlib


def main():
    reproducible_count = 0
    total_count = 0

    lockfile_path = Path(sys.argv[1])
    with lockfile_path.open("rb") as fp:
        lockfile = tomllib.load(fp)

    packages = lockfile["package"]
    crates = [
        package
        for package in packages
        if package.get("source")
        == "registry+https://github.com/rust-lang/crates.io-index"
    ]

    # Path for crates downloaded from crates.io
    orig_crates_path = Path("crates") / "orig"
    orig_crates_path.mkdir(parents=True, exist_ok=True)

    # Path for crate repositories
    git_repos_path = Path("crates") / "git"
    git_repos_path.mkdir(parents=True, exist_ok=True)

    # Path for rebuilt crates
    rebuilt_crates_path = Path("crates") / "rebuilt"
    rebuilt_crates_path.mkdir(parents=True, exist_ok=True)

    diff_path = Path("crates") / "diff"
    diff_path.mkdir(parents=True, exist_ok=True)

    for crate in crates:
        total_count += 1

        crate_name = crate["name"]
        crate_version = crate["version"]
        crate_fullname = f"{crate_name}-{crate_version}"
        crate_path = orig_crates_path / f"{crate_fullname}.crate"
        if not crate_path.exists():
            subprocess.run(
                [
                    "wget",
                    "-O",
                    str(crate_path),
                    "--",
                    f"https://static.crates.io/crates/{crate_name}/{crate_fullname}.crate",
                ]
            )
        with crate_path.open("rb") as fp:
            digest = hashlib.file_digest(fp, "sha256")
            assert digest.hexdigest() == crate["checksum"]

        crate_tarfile = tarfile.open(crate_path, "r:gz")
        cargo_toml = tomllib.load(
            crate_tarfile.extractfile(f"{crate_name}-{crate_version}/Cargo.toml")
        )
        try:
            vcs_info_file = crate_tarfile.extractfile(
                f"{crate_name}-{crate_version}/.cargo_vcs_info.json"
            )
            vcs_info = json.load(vcs_info_file)
        except KeyError:
            print(f"Crate {crate_name}-{crate_version} has no VCS info")
            continue

        if crate_name == "crunchy":
            # https://github.com/eira-fransham/crunchy/pull/11
            repository = "https://github.com/eira-fransham/crunchy/"
        elif crate_name == "dlopen2_derive":
            # https://github.com/OpenByteDev/dlopen2/pull/11
            repository = "https://github.com/OpenByteDev/dlopen2"
        elif crate_name == "openssl-macros":
            # https://github.com/sfackler/rust-openssl/pull/2211
            repository = "https://github.com/sfackler/rust-openssl"
        elif (
            crate_name
            in [
                "windows_i686_msvc",
                "windows_aarch64_msvc",
                "windows_i686_gnu",
                "windows_x86_64_gnu",
                "windows_x86_64_msvc",
            ]
            and crate_version == "0.32.0"
        ):
            # `repository` was silently added in
            # https://github.com/microsoft/windows-rs/pull/1508
            "https://github.com/microsoft/windows-rs"
        elif (
            crate_name
            in [
                "encoding-index-japanese",
                "encoding-index-korean",
                "encoding-index-simpchinese",
                "encoding-index-singlebyte",
                "encoding-index-tradchinese",
            ]
            and crate_version == "1.20141219.5"
        ) or crate_name == "encoding_index_tests":
            # https://github.com/lifthrasiir/rust-encoding/pull/129
            repository = "https://github.com/lifthrasiir/rust-encoding/"
        else:
            repository = cargo_toml["package"].get("repository")
            if not repository:
                print(f"Crate {crate_name}-{crate_version} has no repository")

        if repository == "http://github.com/tailhook/quick-error":
            # https://github.com/tailhook/quick-error/pull/60
            repository = "https://github.com/tailhook/quick-error"
        elif repository == "http://github.com/tailhook/resolv-conf":
            # https://github.com/tailhook/resolv-conf/pull/34
            repository = "https://github.com/tailhook/resolv-conf"

        if not repository.startswith("https://github.com/"):
            print(f"{crate_name}-{crate_version} is not hosted on GitHub: {repository}")
            continue

        # Workaround for URLs like `https://github.com/RustCrypto/formats/tree/master/base16ct`
        # Fix is submitted at <https://github.com/RustCrypto/formats/pull/1373>
        if matched := re.compile(
            "https://github.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)"
        ).match(repository):
            repository = matched.group(0)

        if (
            crate_fullname == "fast-socks5-0.9.5"
            or (crate_name == "kamadak-exif" and crate_version == "0.5.5")
            or (crate_name == "rust-hsluv" and crate_version == "0.1.4")
            or (crate_name == "rustc-hash" and crate_version == "1.1.0")
            or crate_fullname == "system-configuration-sys-0.5.0"
            or crate_fullname == "yansi-0.5.1"
        ):
            # Revision from vcs info is missing in the repository.
            continue

        if crate_fullname in [
            "convert_case-0.5.0",
            "gimli-0.28.1",
            "object-0.32.2",
            "qrcodegen-1.8.0",
            "serde_derive_internals-0.26.0",
            "strum-0.26.1",
            "strum_macros-0.26.1",
            "tokio-native-tls-0.3.1",
            "libsqlite3-sys",
            "unicode-bidi-0.3.15",
            "wasi-0.10.0+wasi-snapshot-preview1",
            "wasi-0.11.0+wasi-snapshot-preview1",
        ]:
            # Cargo.lock is missing?
            continue

        repo_path = git_repos_path / f"{crate_name}-{crate_version}"
        if not repo_path.exists():
            subprocess.run(
                [
                    "git",
                    "clone",
                    "--filter=blob:none",
                    "--",
                    repository,
                    str(repo_path),
                ],
                check=True,
            )

            subprocess.run(
                ["git", "switch", "--detach", vcs_info["git"]["sha1"]],
                cwd=repo_path,
                check=True,
            )

        if crate_fullname == "anes-0.1.6":
            vcs_info["path_in_vcs"] = "anes"

        rebuilt_package_path = (
            rebuilt_crates_path / "package" / f"{crate_fullname}.crate"
        )
        if not rebuilt_package_path.exists():
            print(rebuilt_package_path, " does not exist")
            cwd = repo_path / vcs_info.get("path_in_vcs", "")
            print(cwd)
            subprocess.run(
                [
                    "cargo",
                    "package",
                    "--no-verify",
                    "--target-dir",
                    str(rebuilt_crates_path.absolute()),
                ],
                cwd=cwd,
                check=True,
            )

        if not rebuilt_package_path.exists():
            print(f"Package {crate_fullname} was not rebuilt.")
            continue

        with rebuilt_package_path.open("rb") as fp:
            digest = hashlib.file_digest(fp, "sha256")
            if digest.hexdigest() != crate["checksum"]:
                print(f"Package {crate_fullname} is not reproducible.")
                diffoscope_output_path = diff_path / crate_fullname
                if not diffoscope_output_path.exists():
                    diffoscope = subprocess.run(
                        [
                            "diffoscope",
                            "--",
                            str(crate_path),
                            str(rebuilt_package_path),
                        ],
                        capture_output=True,
                    )
                    diffoscope_output_path.write_bytes(diffoscope.stdout)

        reproducible_count += 1

    print("Total number of packages:", total_count)
    print("Number of reproducible packages:", reproducible_count)


if __name__ == "__main__":
    main()
