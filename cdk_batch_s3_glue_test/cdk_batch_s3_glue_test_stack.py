from aws_cdk import (
                     aws_ec2 as ec2, 
                     aws_batch as batch,
                     aws_ecs as ecs,
                     aws_ecr as ecr,
                     aws_ecr_assets as ecr_assets,
                     aws_iam as iam,
                     App, Stack, CfnOutput, Size
                     )
from constructs import Construct
from pipeline import Pipeline

class CdkBatchS3GlueTestStack(Stack):

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        user = iam.User(self, 'User')
        ecrRepo = ecr.Repository(self, 'TestRepo')

        pipeline = Pipeline({
            'id': 'TestPipeline',
            'ecrRepo': ecrRepo
        })
        # ecrRepo.grantPullPush()


        # # This resource alone will create a private/public subnet in each AZ as well as nat/internet gateway(s)
        # vpc = ec2.Vpc(self, "VPC")

        # # To create number of Batch Compute Environment
        # count = 3

        # # Create AWS Batch Job Queue
        # self.batch_queue = batch.JobQueue(self, "JobQueue")

        # # For loop to create Batch Compute Environments
        # for i in range(count):
        #     name = "MyFargateEnv" + str(i)
        #     fargate_spot_environment = batch.FargateComputeEnvironment(self, name,
        #         vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
        #         vpc=vpc
        #     )

        #     self.batch_queue.add_compute_environment(fargate_spot_environment, i)

        # # Task execution IAM role for Fargate
        # task_execution_role = iam.Role(self, "TaskExecutionRole",
        #                           assumed_by=iam.ServicePrincipal(
        #                               "ecs-tasks.amazonaws.com"),
        #                           managed_policies=[iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonECSTaskExecutionRolePolicy")])
        
        # user = iam.User(self, 'User')
        # ecr.PublicGalleryAuthorizationToken.grant_read(user)
        
        # image = ecr_assets.DockerImageAsset(self, "TestBuildImage",
        #                                     directory="./src",
        #                                     cache_disabled=True)

        # # Create Job Definition to submit job in batch job queue.
        # batch_jobDef = batch.EcsJobDefinition(self, "MyJobDef",
        #                                    container=batch.EcsFargateContainerDefinition(self, "FargateCDKJobDef",
        #                                        image=ecs.ContainerImage.from_ecr_repository(image.repository),
        #                                        command=["python", "test.py"],
        #                                        memory=Size.mebibytes(512),
        #                                        cpu=0.25,
        #                                        execution_role=task_execution_role
        #                                    )
        # )

        # # Output resources
        # CfnOutput(self, "BatchJobQueue",value=self.batch_queue.job_queue_name)
        # CfnOutput(self, "JobDefinition",value=batch_jobDef.job_definition_name)
        # CfnOutput(self, "DockerImageRepoArn",value=image.Repository.RepositoryArn)



app = App()
CdkBatchS3GlueTestStack(app, "CdkBatchS3GlueTestStack")
app.synth()