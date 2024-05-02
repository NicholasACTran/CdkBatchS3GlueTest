FROM python

COPY test.py /


RUN pip install --upgrade pip && \
    pip install boto3 && \
    pip install boto 

RUN pwd
RUN ls

CMD ["python", "test.py"]