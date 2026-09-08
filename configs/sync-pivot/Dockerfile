FROM pytorch/pytorch@sha256:14611869895df612b7b07227d5925f30ec3cd6673bad58ce3d84ed107950e014

# Isolated compatibility environment; never install into the repository's envs.
RUN python -m pip install --no-cache-dir \
    numpy==1.26.4 scipy==1.14.1 networkx==3.4.2 matplotlib==3.9.2 \
    opencv-python-headless==4.10.0.84 imageio==2.36.0 imageio-ffmpeg==0.5.1 \
    rich==13.9.4 imgcat==0.5.0 tabulate==0.9.0 pandas==2.2.3 \
    lpips==0.1.4 torchmetrics==1.6.0 configargparse==1.7 \
    kornia==0.7.4 tensorboard==2.18.0 pytest==8.3.4
RUN python -m pip freeze > /opt/sync-pivot-requirements.lock
ENV MPLBACKEND=Agg PYTHONDONTWRITEBYTECODE=1
WORKDIR /work
