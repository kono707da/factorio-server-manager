pipeline {
    agent any

    environment {
        IMAGE_NAME    = 'factorio-manager'
        REGISTRY      = credentials('docker-registry-url')
        IMAGE_TAG     = "${REGISTRY}/${IMAGE_NAME}:${BUILD_NUMBER}"
        IMAGE_LATEST  = "${REGISTRY}/${IMAGE_NAME}:latest"
        WEB_PORT      = '8199'
        GAME_PORT     = '34197'
        DATA_VOLUME   = 'factorio-manager-data'
        FACTORIO_VOLUME = 'factorio-data'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                sh 'git log --oneline -1'
            }
        }

        stage('Build Image') {
            steps {
                sh "docker build -t ${IMAGE_NAME} -t ${IMAGE_TAG} -t ${IMAGE_LATEST} ."
            }
        }

        stage('Push to Registry') {
            steps {
                sh "docker push ${IMAGE_TAG}"
                sh "docker push ${IMAGE_LATEST}"
            }
        }

        stage('Deploy to Server') {
            steps {
                sshPublisher(publishers: [
                    sshPublisherDesc(
                        configName: 'hongkong',
                        transfers: [
                            sshTransfer(
                                execCommand: "docker pull ${IMAGE_LATEST} && docker stop factorio-manager 2>/dev/null || true && docker rm factorio-manager 2>/dev/null || true && docker volume create ${DATA_VOLUME} 2>/dev/null || true && docker volume create ${FACTORIO_VOLUME} 2>/dev/null || true && docker run -d --name factorio-manager --restart unless-stopped -p ${WEB_PORT}:8199 -p ${GAME_PORT}:34197/udp -v ${DATA_VOLUME}:/app/data -v ${FACTORIO_VOLUME}:/opt/factorio -e TZ=Asia/Shanghai -e FACTORIO_DIR=/opt/factorio -e DATA_DIR=/app/data -e FRONTEND_DIST=/app/frontend/dist ${IMAGE_LATEST}"
                            )
                        ]
                    )
                ])
            }
        }
    }

    post {
        success {
            echo '部署成功！'
        }
        failure {
            echo '部署失败，请检查 Jenkins 日志'
        }
        always {
            sh "docker rmi ${IMAGE_TAG} ${IMAGE_LATEST} ${IMAGE_NAME} 2>/dev/null || true"
            cleanWs()
        }
    }
}
