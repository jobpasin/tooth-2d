FROM tensorflow/tensorflow:1.13.1-gpu-py3

RUN apt-get update && apt-get install -y git

RUN git clone https://github.com/jobpasin/tooth

WORKDIR tooth/Model/my2DCNN

CMD python3 train.py tooth.config