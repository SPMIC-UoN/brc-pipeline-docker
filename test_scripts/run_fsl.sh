docker run -it -v $PWD:/data localhost/martincraig/brc-pipeline struc_preproc \
  --input /data/_test_data/T1.nii.gz \
  --path /data/_test_output/ \
  --subject fsl \
  --freesurfer \
  --qc \
  --regtype 3
