FROM public.ecr.aws/docker/library/python:latest

COPY mondays.py /


RUN pip install --upgrade pip && \
    pip install boto3 && \
    pip install boto && \
    pip install pandas && \
    pip install requests && \
    pip install pyarrow && \
    pip install fastparquet

RUN pwd
RUN ls

CMD ["python", "mondays.py"]