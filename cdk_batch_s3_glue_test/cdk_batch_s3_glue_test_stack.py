from aws_cdk import (
                     aws_ecr as ecr,
                     aws_iam as iam,
                     App, Stack
                     )
from constructs import Construct

from cdk_batch_s3_glue_test.pipeline import Pipeline
from cdk_batch_s3_glue_test.batch_with_fargate import BatchWithFargate

class CdkBatchS3GlueTestStack(Stack):

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        user = iam.User(self, 'User')
        ecrRepo = ecr.Repository(self, 'TestRepo')

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