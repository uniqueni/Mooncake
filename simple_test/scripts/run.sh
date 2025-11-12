#!/bin/bash
set -euo pipefail

# 环境变量：MOONCAKE 地址
: "${MOONCAKE_MASTER_ADDRESS:?Need to set MOONCAKE_MASTER_ADDRESS (e.g. host:port)}"
: "${MOONCAKE_METADATA_SERVER_URL:?Need to set MOONCAKE_METADATA_SERVER_URL (e.g. http://host:port/metadata)}"

CONFIG_FILE="/vllm-workspace/lmcache-config.yaml"
MASTER_IP="${MOONCAKE_MASTER_ADDRESS%%:*}"
MASTER_PORT="${MOONCAKE_MASTER_ADDRESS##*:}"
NODE_IP="localhost"

# 生成或更新 LMCache 配置
if [ ! -f "${CONFIG_FILE}" ]; then
  echo "Config file ${CONFIG_FILE} not found — creating new file."
  cat > "${CONFIG_FILE}" <<EOF
chunk_size: 256
local_device: "cpu"
remote_url: "mooncakestore://${MOONCAKE_MASTER_ADDRESS}"
remote_serde: "naive"
local_cpu: False
max_local_cpu_size: 5

extra_config:
  local_hostname: "${NODE_IP}"
  metadata_server: "${MOONCAKE_METADATA_SERVER_URL}"
  protocol: "rdma"
  device_name: ""
  master_server_address: "${MOONCAKE_MASTER_ADDRESS}"
  global_segment_size: 107374182400
  local_buffer_size: 4294967296
  transfer_timeout: 3000
  save_chunk_meta: False
EOF
else
  echo "Config file ${CONFIG_FILE} found — updating placeholders."
  sed -i "s|remote_url:.*|remote_url: \"mooncakestore://${MOONCAKE_MASTER_ADDRESS}\"|g" "${CONFIG_FILE}"
  sed -i "s|metadata_server:.*|metadata_server: \"${MOONCAKE_METADATA_SERVER_URL}\"|g" "${CONFIG_FILE}"
  sed -i "s|master_server_address:.*|master_server_address: \"${MOONCAKE_MASTER_ADDRESS}\"|g" "${CONFIG_FILE}"
  sed -i "s|local_hostname:.*|local_hostname: \"${NODE_IP}\"|g" "${CONFIG_FILE}"
  echo "Updated file contents:"
  cat "${CONFIG_FILE}"
fi

echo "Using config file: ${CONFIG_FILE}"

# 设置环境变量
export LMCACHE_CONFIG_FILE="${CONFIG_FILE}"
export VLLM_HTTP_TIMEOUT_KEEP_ALIVE=200
export TORCH_CUDA_ARCH_LIST=9.0
export CUDA_VISIBLE_DEVICES=0
export PYTHONHASHSEED=0
export CUDA_VISIBLE_DEVICES=0,1

MODEL_PATH="/mnt/models/Qwen-Qwen2.5-72B-Instruct"
SERVED_MODEL_NAME="Qwen2.5-72B-Instruct"
TP_SIZE=2
GPU_MEMORY_UTILIZATION=0.9
PORT=8080

GLOG_v=2
GLOG_logtostderr=1
FLAGS_v=2
FLAGS_logtostderr=1
MC_TE_METRICS_ENABLED=true
MC_LOG_LEVEL=TRACE
MC_LOG_DIR="/vllm-workspace/logs"

# 启动服务
GLOG_v=${GLOG_v} GLOG_logtostderr=${GLOG_logtostderr} \
FLAGS_v=${FLAGS_v} FLAGS_logtostderr=${FLAGS_logtostderr} \
MC_TE_METRICS_ENABLED=${MC_TE_METRICS_ENABLED} \
MC_LOG_LEVEL=${MC_LOG_LEVEL} MC_LOG_DIR=${MC_LOG_DIR} \
vllm serve ${MODEL_PATH} \
    --served-model-name ${SERVED_MODEL_NAME} \
    --host 0.0.0.0 \
    --tensor-parallel-size ${TP_SIZE} \
    --gpu-memory-utilization ${GPU_MEMORY_UTILIZATION} \
    --port ${PORT} \
    --no-enable-prefix-caching \
    --kv-transfer-config '{"kv_connector":"LMCacheConnectorV1","kv_role":"kv_both"}'