#!/bin/sh

DATADIR=/home/bbzmsc/code/brc-pipeline-docker/_test_data
OUTDIR=/home/bbzmsc/code/brc-pipeline-docker/_test_output
SUBJID=002_S_6103

docker run -it -v $DATADIR:/data -v $OUTDIR:/output \
    martincraig/brc-pipeline \
    struc_preproc \
    --path /output/ \
    --subject $SUBJID \
    --input /data/$SUBJID/raw/Accelerated_Sagittal_MPRAGE_\(MSV21\)_Si.nii.gz \
    --t2 /data/$SUBJID/raw/Sagittal_3D_FLAIR_\(MSV22\)_Si.nii.gz \
    --freesurfer \
    --subseg \
    --qc \
    --regtype 3


docker run -it -v $DATADIR:/data -v $OUTDIR:/output \
   --gpus all -e CUDA_VISIBLE_DEVICES=$CUDA_VISIBLE_DEVICES \
   martincraig/brc-pipeline \
   dMRI_preproc \
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
   --tbss \
   --noddi

docker run -it -v $DATADIR:/data -v $OUTDIR:/output \
    martincraig/brc-pipeline \
    idp_extract \
    --in /data/adni_subjects.txt \
    --indir /output/ \
    --outdir /output/idps
