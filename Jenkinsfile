pipeline {
  agent any
  options { timestamps(); disableConcurrentBuilds() }
  triggers { githubPush() }
  environment {
    IMAGE = 'saivyshnavi06/asda'
    K8S_NAMESPACE = 'default'
  }
  stages {
    stage('Checkout') { steps { checkout scm } }
    stage('Validate and test') {
      steps {
        sh 'python -m pip install -r requirements.txt'
        sh 'SECRET_KEY=test-only-pipeline-secret python -m unittest discover -s asda/tests -v'
        sh 'python -m compileall -q asda'
      }
    }
    stage('Build image') {
      steps { script { env.IMAGE_TAG = "${env.BUILD_NUMBER}-${env.GIT_COMMIT.take(8)}"; sh 'docker build --pull -t "$IMAGE:$IMAGE_TAG" -t "$IMAGE:latest" .' } }
    }
    stage('Push image') {
      steps { withCredentials([usernamePassword(credentialsId: 'dockerhub-asda', usernameVariable: 'DOCKER_USER', passwordVariable: 'DOCKER_TOKEN')]) { sh 'echo "$DOCKER_TOKEN" | docker login -u "$DOCKER_USER" --password-stdin'; sh 'docker push "$IMAGE:$IMAGE_TAG"'; sh 'docker push "$IMAGE:latest"'; sh 'docker logout' } }
    }
    stage('Deploy to Kubernetes') {
      steps {
        withCredentials([file(credentialsId: 'docker-desktop-kubeconfig', variable: 'KUBECONFIG_FILE'), string(credentialsId: 'asda-secret-key', variable: 'ASDA_SECRET_KEY'), string(credentialsId: 'asda-database-url', variable: 'ASDA_DATABASE_URL')]) {
          sh '''
            export KUBECONFIG="$KUBECONFIG_FILE"
            kubectl create secret generic asda-secrets --namespace "$K8S_NAMESPACE" --from-literal=secret-key="$ASDA_SECRET_KEY" --from-literal=database-url="$ASDA_DATABASE_URL" --dry-run=client -o yaml | kubectl apply -f -
            kubectl apply -f k8s/pvc.yaml
            kubectl apply -f k8s/service.yaml
            kubectl apply -f k8s/deployment.yaml
            kubectl set image deployment/asda asda="$IMAGE:$IMAGE_TAG" --namespace "$K8S_NAMESPACE"
            kubectl rollout status deployment/asda --namespace "$K8S_NAMESPACE" --timeout=180s
            kubectl get pods,service -l app=asda --namespace "$K8S_NAMESPACE"
          '''
        }
      }
    }
    stage('Health verification') {
      steps { withCredentials([file(credentialsId: 'docker-desktop-kubeconfig', variable: 'KUBECONFIG_FILE')]) { sh 'export KUBECONFIG="$KUBECONFIG_FILE"; kubectl run asda-health-$BUILD_NUMBER --rm -i --restart=Never --image=curlimages/curl:8.12.1 --namespace "$K8S_NAMESPACE" -- curl --fail --retry 10 --retry-connrefused --retry-delay 3 http://asda/healthz' } }
    }
  }
  post { always { sh 'docker logout >/dev/null 2>&1 || true' } }
}
