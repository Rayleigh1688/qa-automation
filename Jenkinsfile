pipeline {
    agent any

    options {
        timestamps()
        buildDiscarder(logRotator(numToKeepStr: '20'))
    }

    parameters {
        choice(name: 'TARGET_ENV', choices: ['fat', 'uat'], description: 'fat runs before UAT release; uat runs after UAT release.')
        choice(name: 'P0_SCOPE', choices: ['api_all', 'api_ui', 'ui_only', 'api_write'], description: 'P0 execution scope.')
        booleanParam(name: 'EXECUTE_BET', defaultValue: false, description: 'Allow UI game smoke to click the in-game bet area.')
    }

    environment {
        DEVICE = '25'
        LANG_HEADER = 'en_US'
        ADMIN_LANG_HEADER = 'en'
        ADMIN_CLIENT_ID = '123'
        ADMIN_CLIENT_VERSION = 'Chrome/151.0.0.0'
        ADMIN_GOOGLE_CODE = '111111'
        ADMIN_APPROVAL_TOTP_ALGORITHM = 'SHA256'
        PLAYWRIGHT_CHANNEL = ''
    }

    stages {
        stage('Prepare') {
            steps {
                sh '''
                    set -eu
                    python3 scripts/clean-test-artifacts.py all
                    npm ci
                    npx playwright install chromium
                '''
            }
        }

        stage('Select Environment') {
            steps {
                script {
                    if (params.TARGET_ENV == 'uat') {
                        env.API_URL = env.UAT_API_URL ?: ''
                        env.ADMIN_URL = env.UAT_ADMIN_URL ?: ''
                        env.CLIENT_BASE_URL = env.UAT_CLIENT_BASE_URL ?: env.API_URL
                    } else {
                        env.API_URL = env.FAT_API_URL ?: 'https://client-fat.filbet2025.com'
                        env.ADMIN_URL = env.FAT_ADMIN_URL ?: 'https://admin-fat.filbet2025.com'
                        env.CLIENT_BASE_URL = env.FAT_CLIENT_BASE_URL ?: env.API_URL
                    }
                    if (!env.API_URL?.trim() || !env.ADMIN_URL?.trim() || !env.CLIENT_BASE_URL?.trim()) {
                        error("Missing target URLs for ${params.TARGET_ENV}")
                    }
                    echo "TARGET_ENV=${params.TARGET_ENV}"
                    echo "API_URL=${env.API_URL}"
                    echo "ADMIN_URL=${env.ADMIN_URL}"
                    echo "CLIENT_BASE_URL=${env.CLIENT_BASE_URL}"
                }
            }
        }

        stage('P0 API') {
            when {
                expression { params.P0_SCOPE in ['api_all', 'api_ui'] }
            }
            steps {
                sh '''
                    set -eu
                    python3 scripts/run-api-tests.py p0 --scope "${TARGET_ENV}"
                '''
            }
        }

        stage('P0 API Controlled Write') {
            when {
                expression { params.P0_SCOPE == 'api_write' }
            }
            steps {
                sh '''
                    set -eu
                    python3 scripts/run-api-tests.py p0 --scope "${TARGET_ENV}" --include-write
                '''
            }
        }

        stage('P0 UI Smoke') {
            when {
                expression { params.P0_SCOPE in ['api_ui', 'ui_only'] }
            }
            environment {
                EXECUTE_BET = "${params.EXECUTE_BET}"
            }
            steps {
                sh '''
                    set -eu
                    npm run test:ui:p0
                '''
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: 'api/p0/README.md,api/results/*.json,api/results/*.md,ui/reports/*.md,ui/results/**/*.json,ui/results/screenshots/**/*,playwright-report/**/*,test-results/**/*', allowEmptyArchive: true
        }
    }
}
