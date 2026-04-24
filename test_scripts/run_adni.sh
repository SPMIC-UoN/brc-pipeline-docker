#!/bin/sh

DATADIR=/home/bbzmsc/code/brc-pipeline-docker/_test_data
OUTDIR=/home/bbzmsc/code/brc-pipeline-docker/_test_output
SUBJID=002_S_6103

docker run -it -v $DATADIR:/data $OUTDIR:/output martincraig/brc-pipeline struc_preproc \
    --path /output/ \
    --subject $SUBJID \
    --input /data/$SUBJID/raw/Accelerated_Sagittal_MPRAGE_\(MSV21\)_Si.nii.gz \
    --freesurfer \
    --qc \
    --regtype 3

docker run -it -v $DATADIR:/data $OUTDIR:/output martincraig/brc-pipeline dMRI_preproc \
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

docker run -it -v $PWD:/data martincraig/brc-pipeline idp_extract \
    --in /data/adni_subjids.txt \
    --indir /output/ \
    --outdir /output/idps

