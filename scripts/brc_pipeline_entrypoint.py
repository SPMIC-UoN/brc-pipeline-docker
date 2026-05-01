#!/opt/conda/envs/minio/bin/python
import os
import shutil
import subprocess
import sys
import tempfile

try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse


class S3Url(object):
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

if len(sys.argv) < 2:
    print("Usage: python brc_pipeline_entrypoint.py <script_name> <args>")
    sys.exit(1)
if sys.argv[1] in ("--version", "-v"):
    print("v0.0.1")
    sys.exit(0)

script = sys.argv[1] + ".sh"
args = sys.argv[2:]
script_name = shutil.which(script)
if script_name is None:
    print(f"Error: {script} not found in PATH.")
    sys.exit(1)

try:
    from minio import Minio
    env_vars = {}
    for var in ("endpoint", "access", "secret"):
        env_vars[var] = os.environ.get("MINIO_" + var.upper(), None)
        if env_vars[var] is None:
            raise ValueError(f"Environment variable MINIO_{var.upper()} not specified")

    endpoint = urlparse(env_vars["endpoint"])
    secure = endpoint.scheme == "https"

    minio_client = Minio(
        endpoint.netloc,
        access_key=env_vars["access"],
        secret_key=env_vars["secret"],
        secure=secure
    )
except Exception as exc:
    print(f"WARNING: Could not start Minio client: {exc} - will not be able to use S3 URLs as input")
    minio_client = None

def _handle_s3(client, arg, tmpdir):
    try:
        s3url = S3Url(arg)
    except Exception:
        return arg

    try:
        local_fname = s3url.key.replace("/", "_")
        local_path = os.path.join(tmpdir, local_fname)
        client.fget_object(s3url.bucket, s3url.key, local_path)
        return local_path
    except Exception as exc:
        raise RuntimeError("S3 URL could not be downloaded") from exc

with tempfile.TemporaryDirectory() as tmpdir:
    if minio_client is not None:
        args = [_handle_s3(minio_client, arg, tmpdir) for arg in args]
    subprocess.run([script_name] + args, check=True)
