
pipeline {
    agent any

    tools {
         nodejs 'Nodejs 24'
    }

    environment {
        CI = 'true'
    }

    stages {
        stage('Checkout') {
            steps {
                git branch: 'website',
                    url: 'https://github.com/LabdhiiShah/DimensionX.git'
            }
        }

        stage('Verify Repository') {
            steps {
                bat 'git branch --show-current'
                bat 'dir'
                bat 'dir client'
                bat 'dir server'
            }
        }

        stage('Install Frontend Dependencies') {
            steps {
                dir('client') {
                    bat 'npm install'
                }
            }
        }

        stage('Install Backend Dependencies') {
            steps {
                dir('server') {
                    bat 'npm install'
                }
            }
        }

        stage('Run Tests') {
            steps {
                dir('client') {
                    bat 'npm test --if-present'
                }
                dir('server') {
                    bat 'npm test --if-present'
                }
            }
        }

        stage('Build Frontend') {
            steps {
                dir('client') {
                    bat 'npm run build'
                }
            }
        }

        stage('Check Backend') {
            steps {
                dir('server') {
                    bat 'node --check index.js'
                    bat 'node --check projects.cjs'
                }
            }
        }

        stage('Deploy') {
            steps {
                bat 'echo Build completed. Deployment configuration is pending.'
            }
        }
    }

    post {
        always {
            echo 'Pipeline finished.'
        }
        success {
            echo 'Pipeline completed successfully.'
        }
        failure {
            echo 'Pipeline failed. Check the console output.'
        }
    }
}
