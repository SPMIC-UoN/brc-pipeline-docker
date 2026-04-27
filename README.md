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
