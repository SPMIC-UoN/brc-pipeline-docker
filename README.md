BRC pipelines docker container
==============================

Building the container
----------------------

```
python build.py --products=brc-pipeline
```

There is a lot of local setup hardcoded so this is not intended to work out of the box. To use the pipelines pull a pre-built image from Docker Hub, see below.

Pulling/running the container
-----------------------------

The container image is stored on docker hub in ``martincraig/brc-pipeline``

Basic usage is:

```
docker run martincraig/brc-pipeline <pipeline> [<args1> <arg2>...]
```

``pipeline`` is the name of the BRC pipeline script without .sh suffix, e.g. ``struc_preproc``, ``dMRI_preproc``...

Arguments are specific to the pipeline, run without args to get a brief usage message.

Full documentation of the BRC pipeline scripts and inputs/outputs is found at:

[https://github.com/SPMIC-UoN/BRC_Pipeline/wiki](https://github.com/SPMIC-UoN/BRC_Pipeline/wiki)

Examples can be found in the ``test_scripts`` folder

The diffusion pipeline requires GPU support. To support this add the flag ``--gpus=all`` to the ``docker run`` command.
To direct to a specific GPU the suggested approach is to set the ``CUDA_VISIBLE_DEVICES`` environment variable. A full
example might look like this:

```
docker run -it -v $DATADIR:/data -v $OUTDIR:/output \
    --gpus all -e CUDA_VISIBLE_DEVICES=$CUDA_VISIBLE_DEVICES \
    martincraig/brc-pipeline dMRI_preproc \
    --path /output/ \
    --subject $SUBJID \
    --input /data/$SUBJID/raw/Axial_MB_DTI_PA_\(MSV21\)_Si.nii.gz \
    --input_2 /data/$SUBJID/raw/Axial_MB_DTI_AP_\(MSV21\)_Si.nii.gz \
    --slspec /data/$SUBJID/raw/Axial_MB_DTI_PA_\(MSV21\)_Si.json \
    --pe_dir 2 \
    --echospacing 0.00055 \
    --p_im 1 \
    --dtimaxshell 1000 \
    --qc \
    --reg \
    --noddi
```

Use of MINIO data
-----------------

The container supports the use of S3 URLs for *input* data. Essentially, any argument
passed to a pipeline script is first parsed as a URL. If it is a valid S3 URL, the 
contents are saved to a temporary file, and the path of this file is substituted for
the argument.

Environment variables ``MINIO_ENDPOINT``, ``MINIO_ACCESS`` and ``MINIO_SECRET`` must be
set and passed to the container to support S3 URLs. If these are missing, or the Minio
client cannot connect, S3 URLs will not be supported and all input files must be local
file paths.

``MINIO_ENDPOINT`` should include ``http`` or ``https`` prefix, the protocol will be 
set to secure or not depending on this.

If the MINIO server is running locally, the host name in ``MINIO_ENDPOINT`` should be 
set to ``host.docker.internal``. If it is running on an external server, docker must
be able to make external network connections.

An example might look like this:

```
docker run -it -v $OUTDIR:/output \
    -e MINIO_ENDPOINT="http://host.docker.internal:9000" \
    -e MINIO_ACCESS="miniousername" \
    -e MINIO_SECRET="miniopassword" \
    martincraig/brc-pipeline \
    struc_preproc \
    --path /output/ \
    --subject $SUBJID \
    --input "s3://data-bucket/$SUBJID/raw/Accelerated_Sagittal_MPRAGE_(MSV21)_Si.nii.gz" \
    --t2 "s3://data-bucket/$SUBJID/raw/Sagittal_3D_FLAIR_(MSV22)_Si.nii.gz" \
    --regtype 3
```

There is currently no support for writing output back to an S3 bucket.
