BRC pipelines docker container
==============================

Building the container
----------------------

python build.py --products=brc-pipeline

There is a lot of local setup hardcoded so this is not intended to work out of the box. To use the pipelines pull a pre-built image from Docker Hub, see below.

Pulling/running the container
-----------------------------

The container image is stored on docker hub in ``martincraig/brc-pipeline``

Basic usage is:

docker run martincraig/brc-pipeline <pipeline> [<args1> <arg2>...]

``pipeline`` is the name of the BRC pipeline script without .sh suffix, e.g. ``struc_preproc``, ``dMRI_preproc``...

Arguments are specific to the pipeline, run without args to get a brief usage message

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

There is currently no support for writing output back to an S3 bucket.
