#!/bin/sh

OUTDIR=/home/bbzmsc/code/brc-pipeline-docker/_test_output
SUBJID=002_S_6103

# This is test configuration, would need changing in real environment
export MINIO_ENDPOINT="http://host.docker.internal:9090"
export MINIO_ACCESS="miniouser"
export MINIO_SECRET="miniopassword"

docker run -it -v $OUTDIR:/output \
    -e MINIO_ENDPOINT="$MINIO_ENDPOINT" \
    -e MINIO_ACCESS="$MINIO_ACCESS" \
    -e MINIO_SECRET="$MINIO_SECRET" \
    martincraig/brc-pipeline \
    struc_preproc \
    --path /output/ \
    --subject $SUBJID \
    --input "s3://adni/$SUBJID/raw/Accelerated_Sagittal_MPRAGE_(MSV21)_Si.nii.gz" \
    --t2 "s3://adni/$SUBJID/raw/Sagittal_3D_FLAIR_(MSV22)_Si.nii.gz" \
    --freesurfer \
    --subseg \
    --qc \
    --regtype 3

docker run -it -v $OUTDIR:/output \
   --gpus all -e CUDA_VISIBLE_DEVICES=$CUDA_VISIBLE_DEVICES \
    -e MINIO_ENDPOINT="$MINIO_ENDPOINT" \
    -e MINIO_ACCESS="$MINIO_ACCESS" \
    -e MINIO_SECRET="$MINIO_SECRET" \
   martincraig/brc-pipeline \
   dMRI_preproc \
   --path /output/ \
   --subject $SUBJID \
   --input s3://adni/$SUBJID/raw/Axial_MB_DTI_PA_\(MSV21\)_Si.nii.gz \
   --input_2 s3://adni/$SUBJID/raw/Axial_MB_DTI_AP_\(MSV21\)_Si.nii.gz \
   --slspec s3://adni/$SUBJID/raw/Axial_MB_DTI_PA_\(MSV21\)_Si.json \
   --pe_dir 2 \
   --echospacing 0.00055 \
   --p_im 1 \
   --dtimaxshell 1000 \
   --qc \
   --reg \
   --tbss \
   --noddi

docker run -it -v $OUTDIR:/output \
    -e MINIO_ENDPOINT="$MINIO_ENDPOINT" \
    -e MINIO_ACCESS="$MINIO_ACCESS" \
    -e MINIO_SECRET="$MINIO_SECRET" \
    martincraig/brc-pipeline \
    idp_extract \
    --in s3://adni/adni_subjects.txt \
    --indir /output/ \
    --outdir /output/idps

