#!/bin/bash

set -e

# Configure git for the action
git config --global user.email "action@github.com"
git config --global user.name "Dev Agent"
git config --global --add safe.directory /github/workspace

# Change to the workspace directory
cd /github/workspace

# Set up environment variables for dev-agent
export TEST_COMMAND="${DEV_AGENT_TEST_COMMAND:-pytest --maxfail=1}"
export MAX_ITERATIONS="${DEV_AGENT_MAX_ITERATIONS:-5}"
export MODEL_PATH="${DEV_AGENT_MODEL_PATH:-llama-cpp:models/codellama.gguf}"
export AUTO_PR="${DEV_AGENT_AUTO_PR:-true}"
export BRANCH_PREFIX="${DEV_AGENT_BRANCH_PREFIX:-dev-agent/fix}"

# Create a basic dev-agent config if none exists
if [ ! -f "${DEV_AGENT_CONFIG:-dev-agent.yaml}" ]; then
    cat > "${DEV_AGENT_CONFIG:-dev-agent.yaml}" << EOF
max_iterations: ${MAX_ITERATIONS}
test_command: "${TEST_COMMAND}"
git:
  branch_prefix: "${BRANCH_PREFIX}"
  remote: "origin"
  auto_pr: ${AUTO_PR}
llm:
  model_path: "${MODEL_PATH}"
metrics:
  enabled: true
  storage_path: null
EOF
fi

# Run dev-agent
echo "Starting Dev Agent with configuration:"
cat "${DEV_AGENT_CONFIG:-dev-agent.yaml}"

# Capture dev-agent output and exit code
if python -m dev_agent; then
    echo "success=true" >> $GITHUB_OUTPUT
    echo "Dev Agent completed successfully"
    exit 0
else
    exit_code=$?
    echo "success=false" >> $GITHUB_OUTPUT
    echo "Dev Agent failed with exit code: $exit_code"
    exit $exit_code
fi
