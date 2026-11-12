#!/opt/conda/envs/minio/bin/python
import logging
import os
import shutil
import subprocess
import sys
import tempfile

try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse


LOG = logging.getLogger(__name__)
LOG_LEVEL = os.environ.get("BRC_PIPELINE_LOG_LEVEL", "INFO").upper()

def _get_var(var):
    ALTERNATES = {
        "endpoint" : "endPoint",
        "access" : "accessKey",
        "secret" : "secretKey",
        "bucket" : "submissionBucket",
    }
    value = os.environ.get("MINIO_" + var.upper(), None)
    if not value:
        value = os.environ.get(ALTERNATES.get(var, None), None)
    if value is None:
        raise ValueError(f"Could not find MINIO environment variable '{var}' - tried MINIO_{var.upper} and {ALTERNATES.get(var, None)}")
    return value

class S3Url(object):
    """
    Simple class to parse S3 URLs of the form s3://bucket/key?query
    """
    def __init__(self, url):
        self._parsed = urlparse(url, allow_fragments=False)
        if self._parsed.scheme != "s3":
            raise ValueError(f"{url} is not an S3 URL")

    @property
    def bucket(self):
        return self._parsed.netloc

    @property
    def key(self):
        if self._parsed.query:
            return self._parsed.path.lstrip('/') + '?' + self._parsed.query
        else:
            return self._parsed.path.lstrip('/')

    @property
    def url(self):
        return self._parsed.geturl()

def _handle_s3(client, arg, env_vars, tmpdir):
    """
    Check if a command line argument looks like and S3 URL, and if so download it to a local temp file

    One complication here is that some pipelines expect .nii.gz files to be accompanied by sidecar files
    (.bval, .bvec, .json). So if we have a Nifti file reference, we will also download other files with the
    same stem but different extensions.
    """
    if "bucket" in env_vars:
        arg = arg.replace("s3://", "s3://" + env_vars.get("bucket") + "/")
    try:
        s3url = S3Url(arg)
    except Exception:
        # Doesn't look like an S3 URL, that's fine just return it as is
        return arg

    try:
        def _split_key_ext(key):
            if key.endswith(".nii.gz"):
                return key[:-7], ".nii.gz"
            return os.path.splitext(key)

        matching_keys = [s3url.key]
        if s3url.key.endswith(".nii.gz"):
            key_root, _ = _split_key_ext(s3url.key)
            matching_keys = []
            for obj in client.list_objects(s3url.bucket, prefix=key_root, recursive=True):
                obj_root, obj_ext = _split_key_ext(obj.object_name)
                if obj_root == key_root and obj_ext:
                    matching_keys.append(obj.object_name)

            if s3url.key not in matching_keys:
                matching_keys.append(s3url.key)

        original_local_path = None
        for key in sorted(set(matching_keys)):
            local_fname = key.replace("/", "_")
            local_path = os.path.join(tmpdir, local_fname)
            LOG.debug("Downloading S3 URL %s / %s to local path %s", s3url.bucket, key, local_path)
            client.fget_object(s3url.bucket, key, local_path)
            if key == s3url.key:
                original_local_path = local_path

        if original_local_path is None:
            raise RuntimeError("Original S3 key was not downloaded")

        return original_local_path
    except Exception as exc:
        raise RuntimeError("S3 URL could not be downloaded") from exc


def main():
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if len(sys.argv) < 2:
        print("Usage: python brc_pipeline_entrypoint.py <script_name> <args>")
        return 1
    if sys.argv[1] in ("--version", "-v"):
        try:
            with open("/usr/local/BRC_Pipeline/version.txt", "r") as f:
                version = f.read().strip().replace("Ver", "v")
        except FileNotFoundError:
            version = "unknown"
        print(version)
        return 0

    script = sys.argv[1] + ".sh"
    args = sys.argv[2:]
    script_name = shutil.which(script)
    if script_name is None:
        LOG.error("%s not found in PATH.", script)
        return 1

    # Attempt to initialize a Minio client using environment variables MINIO_ENDPOINT, 
    # MINIO_ACCESS, and MINIO_SECRET. Any failure we will just not try to handle S3 URLs
    # and assume all inputs are local files.
    try:
        from minio import Minio
        env_vars = {}
        for var in ("endpoint", "access", "secret", "bucket"):
            env_vars[var] = _get_var(var)

        endpoint = urlparse(env_vars["endpoint"])
        secure = endpoint.scheme == "https"

        LOG.debug("Initializing Minio client with endpoint %s, access key %s, secure=%s",
                  env_vars["endpoint"], env_vars["access"], secure)
        minio_client = Minio(
            endpoint.netloc,
            access_key=env_vars["access"],
            secret_key=env_vars["secret"],
            secure=secure
        )
    except Exception as exc:
        LOG.warning(
            "Could not start Minio client: %s - will not be able to use S3 URLs as input",
            exc,
        )
        minio_client = None

    with tempfile.TemporaryDirectory() as tmpdir:
        if minio_client is not None:
            args = [_handle_s3(minio_client, arg, env_vars, tmpdir) for arg in args]
        subprocess.run([script_name] + args, check=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
