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
        self.output()
        pass

    def __createPipeline__(self) -> codepipeline.Pipeline:
        sourceOutput = codepipeline.Artifact()
        buildOutput = codepipeline.Artifact()
        return codepipeline.Pipeline(self, 'Pipeline', {
            'stages': [
                self.__createSourceStage__('Source', sourceOutput),
                self.__createImageBuildStage__('Build', sourceOutput, buildOutput),
                # self.__createDeployStage__('Deploy', buildOutput)
            ]
        })

    def __createSourceStage__(self, stageName: str, output: codepipeline.Artifact) -> codepipeline.StageProps:
        secret = cdk.SecretValue.secretsManager('/github/dev/GITHUB_TOKEN')
        repo = ssm.StringParameter.valueForStringParameter(self, '/github/dev/GITHUB_REPO')
        owner = ssm.StringParameter.valueForStringParameter(self, '/github/dev/GITHUB_OWNER')
        
        githubAction = codepipeline_actions.GitHubSourceAction({
            'actionName': 'Github_Source',
            'owner': owner,
            'repo': repo,
            'oauthToken': secret,
            'output': output
        })

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
            {
                'buildSpec': self.__createBuildSpec__(),
                'environment': {
                    'buildImage': codebuild.LinuxBuildImage.STANDARD_2_0,
                    'privileged': True
                },
                'environmentVariables': {
                    'REPOSITORY_URI': {
                        'value': self.ecrRepo.repositoryUri
                    }
                }
            }
        )

        self.ecrRepo.grantPullPush(project.grantPrincipal)

        codebuildAction = codepipeline_actions.CodeBuildAction({
            'actionName': 'CodeBuild_Action',
            'input': input,
            'outputs': [output],
            'project': project
        })

        return {
            'stageName': stageName,
            'actions': [codebuildAction]
        }
    
    def __createBuildSpec__(self) -> codebuild.BuildSpec:
        return codebuild.BuildSpec.fromObject({
            'version': '0.2',
            'phases': {
                'install': {
                    'runtime-versions': {
                        'nodejs': '10',
                        'php': '7.3'
                    },
                    'commands': [
                        'npm install',
                        'composer install',
                    ],
                },
                'pre_build': {
                    'commands': [
                        'aws --version',
                        '$(aws ecr get-login --region ${AWS_DEFAULT_REGION} --no-include-email |  sed \'s|https://||\')',
                        'COMMIT_HASH=$(echo $CODEBUILD_RESOLVED_SOURCE_VERSION | cut -c 1-7)',
                        'IMAGE_TAG=${COMMIT_HASH:=latest}'
                    ]
                },
                'build': {
                    'commands': [
                        'docker build -t $REPOSITORY_URI:latest .',
                        'docker tag $REPOSITORY_URI:latest $REPOSITORY_URI:$IMAGE_TAG',
                    ]
                },
                'post_build': {
                    'commands': [
                        'docker push $REPOSITORY_URI:latest',
                        'docker push $REPOSITORY_URI:$IMAGE_TAG',
                        'printf "[{\\"name\\":\\"${CONTAINER_NAME}\\",\\"imageUri\\":\\"${REPOSITORY_URI}:latest\\"}]" > imagedefinitions.json'
                    ]
                }
            },
            'artifacts': {
                'files': [
                    'imagedefinitions.json'
                ]
            }
        })

    def __output__(self):
        cdk.CfnOutput(self, 'Pipeline ARN', {
            'value': self.pipeline.pipelineArn
        })