from aws_cdk import (
                     aws_ecr as ecr,
                     aws_s3 as s3,
                     App, Stack, RemovalPolicy
                     )
from constructs import Construct

from cdk_batch_s3_glue_test.pipeline import Pipeline
from cdk_batch_s3_glue_test.batch_with_fargate import BatchWithFargate

class CdkBatchS3GlueTestStack(Stack):

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        ecrRepo = ecr.Repository(self, 'TestRepo')
        bucket = s3.Bucket(
            self,
            'CDKBatchS3GlueTestBucket',
            bucket_name='cdk-batch-s3-glue-test-bucket',
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            versioned=True,
            removal_policy=RemovalPolicy.RETAIN
        )

        pipeline = Pipeline(
            self,
            id='TestPipeline',
            ecrRepo=ecrRepo
        )

        batch = BatchWithFargate(
            self, 
            id="TestJob", 
            ecrRepo=ecrRepo
        )

app = App()
CdkBatchS3GlueTestStack(app, "CdkBatchS3GlueTestStack")
app.synth()