#!/usr/bin/env python3
"""
Docker build script for QI-DOCKER project
Converts from bash to Python for better error handling and maintainability
"""

import argparse
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
LOG = logging.getLogger(__name__)

DOCKER_NAMESPACE = "martincraig"
DOCKER_USERNAME = "martincraig"
PRIVATE_KEY_FILE = None
PRODUCTS = {
    "brc-pipeline": {
        "components": [
            "base",
            "fsl",
            "ants",
            "cuda",
            "cudimot",
            "freesurfer",
            "mcr",
            "dvars",
            "c3d",
            "brc-pipelines",
            "minio",
        ],
        # "entrypoint": "bash",
        "entrypoint": "brc_pipeline",
        "image_name": "brc-pipeline",
        "use_buildscript_version": True,
    },
}


def _download_freesurfer(builddir):
    """
    Download and install FreeSurfer if not already present.
    """
    deps_dir = builddir / "_deps"
    deps_dir.mkdir(exist_ok=True)
    freesurfer7_dir = deps_dir / "freesurfer"
    if not freesurfer7_dir.exists():
        freesurfer_tarball = "freesurfer-linux-ubuntu22_amd64-7.4.1.tar.gz"

        # Remove old tarball if exists
        if Path(freesurfer_tarball).exists():
            os.remove(freesurfer_tarball)

        # Download and extract FreeSurfer tarball
        run_command(
            f"wget https://surfer.nmr.mgh.harvard.edu/pub/dist/freesurfer/7.4.1/{freesurfer_tarball}"
        )
        run_command(f"tar -xzf {freesurfer_tarball} --no-same-owner -C {deps_dir}")
        os.remove(freesurfer_tarball)

        # Patch with fixed version of recon-all-clinical.sh
        recon_script = "recon-all-clinical.sh"
        dest_script = freesurfer7_dir / "bin" / recon_script
        if Path(recon_script).exists():
            os.remove(recon_script)

        run_command(
            "wget https://raw.githubusercontent.com/freesurfer/freesurfer/refs/heads/dev/recon_all_clinical/recon-all-clinical.sh"
        )

        shutil.move(recon_script, dest_script)
        os.chmod(dest_script, 0o755)

    # Download synthstrip model if not present
    synthstrip_model = deps_dir / "synthstrip.1.pt"
    if not synthstrip_model.exists():
        LOG.info("Downloading synthstrip model")
        run_command(
            f"wget https://surfer.nmr.mgh.harvard.edu/docs/synthstrip/requirements/synthstrip.1.pt -P {deps_dir}"
        )

    # Check for freesurfer deb file
    freesurfer_debs = list(deps_dir.glob("freesurfer*.deb"))
    if not freesurfer_debs:
        # Original script has "wget fish" which seems incomplete
        # Leaving as comment for now
        # run_command("wget fish")
        pass


def _download_brc_pipeline(builddir):
    # Clone BRC pipeline from git as we need to modify some of it and comple the matlab
    deps_dir = builddir / "_deps"
    scripts_dir = builddir / "scripts"
    deps_dir.mkdir(exist_ok=True)
    pipeline_dir = deps_dir / "BRC_Pipeline"
    shutil.rmtree(pipeline_dir, ignore_errors=True)  # Remove old pipeline if exists
    if not pipeline_dir.exists():
        cwd = os.getcwd()
        os.chdir(deps_dir)
        run_command("git clone https://github.com/SPMIC-UoN/BRC_Pipeline")
        os.chdir("BRC_Pipeline")
        run_command("find . -type f \( -name '*.sh' -o -name '*.py' \) -exec chmod 755 {} \;")

        # Compile matlab code
        os.chdir("BRC_functional_pipeline/scripts")
        run_command(
            "MATLABPATH="" mcc -m extract_slice_specifications.m -o extract_slice_specifications"
        )
        run_command(
            "MATLABPATH="" mcc -m run_QC_analysis.m -o run_QC_analysis"
        )
        run_command(
            "MATLABPATH="" mcc -m run_spm_slice_time_correction.m -o run_spm_slice_time_correction"
        )
        os.chdir("../..")
        os.chdir("BRC_func_group_analysis/scripts/FSLNets")
        run_command(
            "MATLABPATH="" mcc -m run_FSL_Nets.m -o run_FSL_Nets"
        )
        run_command(
            "MATLABPATH="" mcc -m run_SS_FSL_Nets.m -o run_SS_FSL_Nets"
        )
        os.chdir(cwd)

        # Patch scripts to call compiled matlab versions of the functions
        for script in [
            "EddyPreprocessing.sh",
            "QC_analysis.sh",
            "Slice_Timing_Correction.sh",
        ]:
            run_command(f"cp {scripts_dir}/{script} {pipeline_dir}/BRC_functional_pipeline/scripts/{script}")
        for script in [
            "run_eddy.sh",
        ]:
            run_command(f"cp {scripts_dir}/{script} {pipeline_dir}/BRC_diffusion_pipeline/scripts/{script}")
        for script in [
            "Functional_Connectivity_Analysis.sh",
            "SS_FC_Analysis.sh",
        ]:
            run_command(f"cp {scripts_dir}/{script} {pipeline_dir}/BRC_func_group_analysis/scripts/{script}")

def _download_cuda(builddir):
    # Download CUDA deb files if not already present
    deps_dir = builddir / "_deps"
    deps_dir.mkdir(exist_ok=True)
    cuda_dir = deps_dir / "cuda"
    if not cuda_dir.exists():
        cuda_dir.mkdir()
        # wget https://developer.download.nvidia.com/compute/cuda/12.1.1/local_installers/cuda_12.1.1_530.30.02_linux.run
        # sudo sh cuda_12.1.1_530.30.02_linux.run

DEPS = {
    "freesurfer" : _download_freesurfer,
    "brc-pipeline" : _download_brc_pipeline,
    "cuda" : _download_cuda
}

def run_command(cmd, shell=True, capture_output=False, env=None):
    """Run a shell command and handle errors."""
    try:
        LOG.debug(cmd)
        if capture_output:
            result = subprocess.run(
                cmd, shell=shell, check=True, capture_output=True, text=True, env=env
            )
            return result.stdout.strip()
        else:
            subprocess.run(cmd, shell=shell, check=True, env=env)
    except subprocess.CalledProcessError as e:
        LOG.error(f"Error running command: {cmd}")
        LOG.error(f"Error: {e}")
        sys.exit(1)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Build Docker images for QI-DOCKER project",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Show buildscript version and exit",
    )
    parser.add_argument(
        "--products",
        help="Comma-separated list of products to build (ci,release,dev,pmp,long) or 'all' to build everything",
    )
    parser.add_argument(
        "--save-contents",
        action="store_true",
        help="Save image contents to _image_contents directory",
    )
    parser.add_argument(
        "--no-build",
        action="store_true",
        help="Only create Dockerfiles without building images",
    )
    parser.add_argument(
        "--no-dep",
        help="Comma separated list of dependencies to ignore",
        default="",
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="Push images to registry after building",
    )
    parser.add_argument(
        "--trivy",
        action="store_true",
        help="Run Trivy security scanning on built images",
    )
    parser.add_argument(
        "--sif",
        action="store_true",
        help="Build Singularity SIF files from Docker images",
    )
    parser.add_argument(
        "--bump",
        help="Comma-separated list of .docker files to bump REBUILD_* ARG values (e.g., 'qasl-dev,plugins')",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Build without using cache",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )

    return parser.parse_args()


def _get_products_to_build(args):
    """Determine which products to build based on command line arguments.

    Args:
        args: Command line arguments

    Returns:
        List of product names to build
    """
    if args.products.lower() == "all":
        products_to_build = list(PRODUCTS.keys())
    else:
        products_to_build = [p.strip() for p in args.products.split(",")]
        # Validate product names
        invalid_products = [p for p in products_to_build if p not in PRODUCTS]
        if invalid_products:
            LOG.error(f"Invalid product(s): {', '.join(invalid_products)}")
            LOG.error(f"Valid products are: {', '.join(PRODUCTS.keys())}")
            sys.exit(1)

    LOG.info(f"Building products: {', '.join(products_to_build)}")
    return products_to_build


def _get_buildscript_version(builddir):
    """Get the version of the build script from git.

    Args:
        builddir: Path to the build directory

    Returns:
        Version string without leading 'v'
    """
    # version = run_command(f"git -C {builddir} describe --dirty", capture_output=True)
    version = "v1.0.0"
    return version[1:]  # Remove leading 'v'


def _get_image_version(image_name, buildscript_version):
    """Get the version of a Docker image.

    Args:
        image_name: Name of the image (e.g., 'ci', 'qasl', 'qasl-dev')
        buildscript_version: Version of the build script

    Returns:
        Version string
    """
    if image_name == "ci":
        return buildscript_version
    else:
        full_image_name = f"{DOCKER_NAMESPACE}/{image_name}"
        full_version = run_command(
            f"docker run localhost/{full_image_name} --version",
            capture_output=True,
        )
        return full_version.split("+")[0]  # Return version before any '+' character


def _bump_rebuild_args(builddir, bump_list):
    """Bump REBUILD_* ARG values in specified .docker files.

    Args:
        builddir: Path to the build directory
        bump_list: Comma-separated list of .docker file names (without .docker extension)
    """
    import re

    files_to_bump = [f.strip() for f in bump_list.split(",")]
    recipes_dir = builddir / "recipes"

    for file_name in files_to_bump:
        docker_file = recipes_dir / f"{file_name}.docker"

        if not docker_file.exists():
            LOG.warning(f"File {docker_file} does not exist, skipping")
            continue

        with open(docker_file, "r") as f:
            content = f.read()

        # Find lines matching: ARG REBUILD_SOMETHING=NUMBER and increment the number
        pattern = r"^(ARG REBUILD_[A-Z_]+=)(\d+)$"

        def increment_number(match):
            prefix = match.group(1)
            number = int(match.group(2))
            new_number = number + 1
            LOG.info(
                f" - Bumping {file_name}.docker: {prefix}{number} -> {prefix}{new_number}"
            )
            return f"{prefix}{new_number}"

        new_content = re.sub(pattern, increment_number, content, flags=re.MULTILINE)

        with open(docker_file, "w") as f:
            f.write(new_content)


def _download_workbench(builddir):
    """Download and install Workbench if not already present.

    Args:
        builddir: Path to the build directory
    """
    deps_dir = builddir / "_deps"
    deps_dir.mkdir(exist_ok=True)
    workbench_dir = deps_dir / "workbench"
    if not workbench_dir.exists():
        # Remove old workbench zips
        for wb_zip in deps_dir.glob("workbench*.zip"):
            os.remove(wb_zip)

        # Download workbench and unzip
        workbench_zip = "workbench-linux64-v2.1.0.zip"
        run_command(
            f"wget https://www.humanconnectome.org/storage/app/media/workbench/{workbench_zip} -C {deps_dir}"
        )
        run_command(f"unzip {deps_dir}/{workbench_zip}")

        for wb_zip in deps_dir.glob("workbench*.zip"):
            os.remove(wb_zip)


def _create_dockerfile(product, config, builddir):
    """Create a Dockerfile by concatenating component files.

    Args:
        product: Name of the product
        config: Product configuration dictionary
        builddir: Path to the build directory
    """
    recipes_dir = builddir / "recipes"
    entrypoints_dir = builddir / "entrypoints"

    dockerfiles_dir = builddir / "_dockerfiles"
    dockerfiles_dir.mkdir(exist_ok=True)

    LOG.info(f"Creating Dockerfile.{product}")
    with open(dockerfiles_dir / f"Dockerfile.{product}", "w") as outfile:
        for component in config["components"]:
            with open(recipes_dir / f"{component}.docker", "r") as infile:
                outfile.write(infile.read())

        with open(
            entrypoints_dir / f"{config['entrypoint']}.entrypoint", "r"
        ) as infile:
            outfile.write(infile.read())


def _run_trivy_scan(product, config, builddir):
    """Run Trivy security scanning on a Docker image.

    Args:
        product: Name of the product
        config: Product configuration dictionary
        builddir: Path to the build directory
    """
    image_name = f"localhost/{DOCKER_NAMESPACE}/{config['image_name']}"

    logs_dir = builddir / "_logs"
    logs_dir.mkdir(exist_ok=True)
    output_file = logs_dir / f"trivy-{product}.out"

    LOG.info(f"Running Trivy security scan for {product}")
    run_command(f"trivy image {image_name} -s CRITICAL,HIGH > {output_file}")
    LOG.info(f" - Trivy results saved to {output_file}")


def _build_sif(product, config, builddir, buildscript_version):
    """Build a Singularity SIF file from a Docker image.

    Args:
        product: Name of the product
        config: Product configuration dictionary
        builddir: Path to the build directory
        buildscript_version: Version of the build script
    """
    image_name = f"{DOCKER_NAMESPACE}/{config['image_name']}"
    version = _get_image_version(config["image_name"], buildscript_version)

    sifs_dir = builddir / "_sifs"
    sifs_dir.mkdir(exist_ok=True)
    sif_file = sifs_dir / f"{config['image_name']}-{version}.sif"

    LOG.info(f"Building Singularity SIF for {product}")
    if product == "release" and version != buildscript_version:
        # We will not have pushed the actual release image, just an RC image
        image_name = f"{image_name}-rc"

    # Build SIF file (--force to overwrite without prompting)
    env_vars = os.environ.copy()
    env_vars["SINGULARITY_DOCKER_USERNAME"] = DOCKER_USERNAME
    run_command(
        f"singularity build --force --docker-login {sif_file} docker://{image_name}:{version}",
        env=env_vars,
    )
    LOG.info(f" - SIF file created: {sif_file}")


def _build_image(product, config, builddir, priv_key, buildscript_version, args):
    """Build and tag a Docker image.

    Args:
        product: Name of the product
        config: Product configuration dictionary
        builddir: Path to the build directory
        priv_key: Private key for build
        buildscript_version: Version of the build script
        args: Command line arguments
    """
    image_name = f"{DOCKER_NAMESPACE}/{config['image_name']}"

    logs_dir = builddir / "_logs"
    logs_dir.mkdir(exist_ok=True)
    log_file = logs_dir / f"{product}.log"

    LOG.info(f"Building {product} docker image")

    build_cmd = "docker buildx build --sbom=true"
    if args.no_cache:
        build_cmd += " --no-cache"
    if args.save_contents:
        output_dir = f"_image_contents/{config['image_name']}"
        build_cmd += f" -o {output_dir}"

    build_cmd += (
        f" --format docker -t {image_name} -f _dockerfiles/Dockerfile.{product}"
    )
    build_cmd += f' --build-arg PRIV_KEY="{priv_key}"'
    build_cmd += f' "{builddir}" >{log_file} 2>&1'

    run_command(build_cmd)

    version = _get_image_version(config["image_name"], buildscript_version)
    LOG.info(f" - {product.capitalize()} container has version {version}")

    if product == "release":
        LOG.info(" - Tagging RC image")
        run_command(
            f"docker tag localhost/{image_name} {image_name}-rc:{version} >>{log_file} 2>&1"
        )

        # Check version matches build script version for release - so we only tag official releases
        if buildscript_version == version:
            LOG.info(" - Tagging release image")
            run_command(f"docker tag localhost/{image_name} {image_name}:{version}")
        else:
            LOG.info(
                " - Release version does not match buildscript version - will not tag release image"
            )
    else:
        LOG.info(" - Tagging image")
        run_command(
            f"docker tag localhost/{image_name} {image_name}:{version} >>{log_file} 2>&1"
        )

    LOG.info("DONE")


def _push_image(product, config, builddir, buildscript_version):
    """Push a Docker image to the registry.

    Args:
        product: Name of the product
        config: Product configuration dictionary
        builddir: Path to the build directory
        buildscript_version: Version of the build script
    """
    image_name = f"{DOCKER_NAMESPACE}/{config['image_name']}"

    version = _get_image_version(config["image_name"], buildscript_version)

    logs_dir = builddir / "_logs"
    logs_dir.mkdir(exist_ok=True)
    log_file = logs_dir / f"{product}.log"

    LOG.info(f"Pushing {product} docker image")

    if product == "release":
        LOG.info(" - Pushing RC image")
        run_command(f"docker push {image_name}-rc:{version} >>{log_file} 2>&1")

        # Only push if version matches build script version so we only push official releases
        if buildscript_version == version:
            LOG.info(" - Pushing release image")
            run_command(f"docker push {image_name}:{version}")
            run_command(f"docker push {image_name}:latest")
    else:
        # Standard pushing for all other images
        LOG.info(" - Pushing image")
        run_command(f"docker push {image_name}:{version} >>{log_file} 2>&1")
        run_command(f"docker push {image_name}:latest >>{log_file} 2>&1")

    LOG.info("DONE")


def main():
    args = parse_args()

    if args.debug:
        LOG.setLevel(logging.DEBUG)
        logging.getLogger().setLevel(logging.DEBUG)

    builddir = Path(__file__).parent.absolute()

    if args.version:
        buildscript_version = _get_buildscript_version(builddir)
        print(f"v{buildscript_version}")
        sys.exit(0)

    if not args.products:
        LOG.error("--products is required")
        sys.exit(1)

    products_to_build = _get_products_to_build(args)

    buildscript_version = _get_buildscript_version(builddir)
    LOG.info(f"QI-DOCKER build script v{buildscript_version}")
    LOG.info(f" - Products to build: {', '.join(products_to_build)}")
    LOG.info(f" - build directory: {builddir}")

    if args.bump:
        LOG.info(f"Bumping REBUILD_* values in: {args.bump}")
        _bump_rebuild_args(builddir, args.bump)


    deps_to_skip = [p.strip() for p in args.no_dep.split(",")]
    for dep, fn in DEPS.items():
        if dep not in deps_to_skip:
            LOG.info(f"Checking for dependency: {dep}")
            fn(builddir)

    # Read private key so the build can access private repos
    if PRIVATE_KEY_FILE:
        try:
            with open(builddir / PRIVATE_KEY_FILE, "r") as f:
                priv_key = f.read().strip()
        except FileNotFoundError:
            LOG.warning(f"Private key file {PRIVATE_KEY_FILE} not found")
            priv_key = "none"
    else:
        priv_key = "none"

    # Create Dockerfiles, build, tag, and push specified products
    for product in products_to_build:
        config = PRODUCTS[product]

        _create_dockerfile(product, config, builddir)

        if not args.no_build:
            _build_image(
                product,
                config,
                builddir,
                priv_key,
                buildscript_version,
                args,
            )

        if args.push:
            _push_image(product, config, builddir, buildscript_version)

        if args.trivy:
            _run_trivy_scan(product, config, builddir)

        if args.sif:
            _build_sif(product, config, builddir, buildscript_version)


if __name__ == "__main__":
    main()
