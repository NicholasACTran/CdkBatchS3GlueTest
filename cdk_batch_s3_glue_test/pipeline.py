import aws_cdk as cdk
from aws_cdk import (
                     aws_codebuild as codebuild, 
                     aws_codepipeline as codepipeline,
                     aws_codepipeline_actions as codepipeline_actions,
                     aws_ssm as ssm,
                     aws_ecr as ecr,
                     App, Stack, CfnOutput, Size
                     )
from constructs import Construct

class Pipeline(Construct):
    def __init__(self, scope: Construct, id: str, ecrRepo, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        self.ecrRepo = ecrRepo
        self.pipeline = self.__createPipeline__()
        self.__output__()
        pass

    def __createPipeline__(self) -> codepipeline.Pipeline:
        sourceOutput = codepipeline.Artifact()
        buildOutput = codepipeline.Artifact()
        return codepipeline.Pipeline(self, 'Pipeline', 
            stages=[
                self.__createSourceStage__('Source', sourceOutput),
                self.__createImageBuildStage__('Build', sourceOutput, buildOutput),
                # self.__createDeployStage__('Deploy', buildOutput)
            ]
        )

    def __createSourceStage__(self, stageName: str, output: codepipeline.Artifact) -> codepipeline.StageProps:
        secret = cdk.SecretValue.secrets_manager('/github/dev/GITHUB_TOKEN', json_field='/github/dev/GITHUB_TOKEN')
        repo = ssm.StringParameter.value_for_string_parameter(self, '/github/dev/GITHUB_REPO')
        owner = ssm.StringParameter.value_for_string_parameter(self, '/github/dev/GITHUB_OWNER')
        
        githubAction = codepipeline_actions.GitHubSourceAction(
            action_name='Github_Source',
            owner=owner,
            repo=repo,
            oauth_token=secret,
            output=output
        )

        return {
            'stageName': stageName,
            'actions': [githubAction]
        }
    
    def __createImageBuildStage__(
            self, 
            stageName: str, 
            input: codepipeline.Artifact, 
            output: codepipeline.Artifact) -> codepipeline.StageProps:
        
        project = codebuild.PipelineProject(
            self,
            'Project',
            build_spec=self.__createBuildSpec__(),
            environment={
                'build_image': codebuild.LinuxBuildImage.STANDARD_5_0,
                'privileged': True
            },
            environment_variables={
                'REPOSITORY_URI': {
                    'value': self.ecrRepo.repository_uri
                }
            }
            
        )

        self.ecrRepo.grant_pull_push(project.grant_principal)

        codebuildAction = codepipeline_actions.CodeBuildAction(
            action_name='CodeBuild_Action',
            input=input,
            outputs=[output],
            project=project
        )

        return {
            'stageName': stageName,
            'actions': [codebuildAction]
        }
    
    def __createBuildSpec__(self) -> codebuild.BuildSpec:
        return codebuild.BuildSpec.from_object({
            'version': '0.2',
            'phases': {
                'install': {
                    'runtime-versions': {},
                    'commands': [],
                },
                'pre_build': {
                    'commands': [
                        'aws --version',
                        'aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 934939427723.dkr.ecr.us-east-1.amazonaws.com',
                        'COMMIT_HASH=$(echo $CODEBUILD_RESOLVED_SOURCE_VERSION | cut -c 1-7)',
                        'IMAGE_TAG=${COMMIT_HASH:=latest}'
                    ]
                },
                'build': {
                    'commands': [
                        'cd src',
                        'docker build -t $REPOSITORY_URI:latest .',
                        'docker tag $REPOSITORY_URI:latest $REPOSITORY_URI:$IMAGE_TAG',
                    ]
                },
                'post_build': {
                    'commands': [
                        'docker push $REPOSITORY_URI:latest',
                        'docker push $REPOSITORY_URI:$IMAGE_TAG',
                        'printf "[{\\"name\\":\\"Test\\",\\"imageUri\\":\\"${REPOSITORY_URI}:latest\\"}]" > imagedefinitions.json'
                    ]
                }
            }
        })

    def __output__(self):
        cdk.CfnOutput(self, 'Pipeline ARN', value=self.pipeline.pipeline_arn)