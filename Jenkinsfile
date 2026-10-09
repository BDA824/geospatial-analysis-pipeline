pipeline {
    agent any
    options { timestamps() }
    environment { API_PORT = '5001' }   // el stack de CI no debe chocar con el puerto 5000 de producción

    stages {
        stage('Checkout') {
            steps { checkout scm }
        }
        stage('Build imágenes') {
            steps { sh 'docker compose build api spark-master' }
        }
        stage('Pytest') {
            steps { sh 'docker compose run --rm --no-deps api pytest -q tests/unit' }
        }
        stage('Levantar stack de pruebas') {
            steps { sh 'docker compose -p taxi-ci up -d --build mongo api' }
        }
        stage('Pruebas básicas API') {
            steps { sh 'docker compose -p taxi-ci exec -T api python tests/smoke.py' }
        }
        stage('Deploy') {
            when { expression { env.GIT_BRANCH ==~ /(origin\/)?main/ } }
            steps {
                sh 'API_PORT=5000 docker compose up -d --build mongo api spark-master spark-worker dask-scheduler dask-worker'
            }
        }
    }
    post {
        always { sh 'docker compose -p taxi-ci down -v || true' }
    }
}
